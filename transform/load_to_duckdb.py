import boto3
import json
import duckdb
import pandas as pd
import os
from datetime import datetime

# ── WHAT IS THIS? ──────────────────────────────────────────────────────────────
# This script does two things:
# 1. Reads the raw JSON files from S3 for today's date
# 2. Flattens the nested weather data into a clean DataFrame
# 3. Loads it into a DuckDB database as a raw table
#
# ───────────────────────────────────────────────────────────────────────────────

BUCKET = "weather-pipeline-calvin-010526241741-us-east-1-an"
REGION = "us-east-1"
DB_PATH = "weather.duckdb"

def read_from_s3(date_str):
    """
    Lists and reads all JSON files from S3 for a given date.
    
    The prefix filters to only the files for today's date:
    raw/2026/06/26/
    
    s3.list_objects_v2() returns metadata about matching files.
    s3.get_object() downloads the actual file content.
    """
    s3 = boto3.client("s3", region_name=REGION)
    year, month, day = date_str.split("-")
    prefix = f"raw/{year}/{month}/{day}/"

    print(f"Reading from s3://{BUCKET}/{prefix}")

    # List all objects under today's prefix
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)

    if "Contents" not in response:
        print("No files found for today.")
        return []

    records = []
    for obj in response["Contents"]:
        key = obj["Key"]

        # Skip folder placeholders
        if key.endswith("/"):
            continue

        # Download the file content
        file_obj = s3.get_object(Bucket=BUCKET, Key=key)
        content = file_obj["Body"].read().decode("utf-8")
        data = json.loads(content)
        records.append(data)
        print(f"  Read: {key}")

    return records


def flatten_weather(records, date_str):
    """
    Flattens the nested Open-Meteo JSON into a flat DataFrame.
    
    The API returns daily data as lists — even for a single day.
    So temperature_2m_max comes back as [28.5] not 28.5.
    We use index [0] to get the single day's value.
    """
    rows = []
    for record in records:
        daily = record.get("daily", {})
        row = {
            "city":             record.get("city"),
            "date":             date_str,
            "latitude":         record.get("latitude"),
            "longitude":        record.get("longitude"),
            "timezone":         record.get("timezone"),
            "temp_max":         daily.get("temperature_2m_max", [None])[0],
            "temp_min":         daily.get("temperature_2m_min", [None])[0],
            "temp_mean":        daily.get("temperature_2m_mean", [None])[0],
            "precipitation_mm": daily.get("precipitation_sum", [None])[0],
            "windspeed_max":    daily.get("windspeed_10m_max", [None])[0],
            "weather_code":     daily.get("weathercode", [None])[0],
            "extracted_at":     record.get("extracted_at"),
        }
        rows.append(row)

    return pd.DataFrame(rows)


def load_to_duckdb(df):
    """
    Loads the flattened DataFrame into DuckDB.

    We use INSERT instead of full replace here because this pipeline
    runs daily — we want to append each day's data, not overwrite it.
    The raw.weather_daily table grows by 5 rows every day it runs.
    """
    conn = duckdb.connect(DB_PATH)

    # Create schema and table if they don't exist yet
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw.weather_daily (
            city            VARCHAR,
            date            DATE,
            latitude        DOUBLE,
            longitude       DOUBLE,
            timezone        VARCHAR,
            temp_max        DOUBLE,
            temp_min        DOUBLE,
            temp_mean       DOUBLE,
            precipitation_mm DOUBLE,
            windspeed_max   DOUBLE,
            weather_code    INTEGER,
            extracted_at    VARCHAR
        )
    """)

    # Delete today's records first to avoid duplicates on re-runs
    conn.execute(f"DELETE FROM raw.weather_daily WHERE date = '{df['date'].iloc[0]}'")

    # Insert the new records
    conn.execute("INSERT INTO raw.weather_daily SELECT * FROM df")

    count = conn.execute("SELECT COUNT(*) FROM raw.weather_daily").fetchone()[0]
    print(f"\nLoaded {len(df)} rows. Total in raw.weather_daily: {count}")

    # Preview
    print("\nToday's data:")
    result = conn.execute(
        f"SELECT city, date, temp_max, temp_min, precipitation_mm FROM raw.weather_daily WHERE date = '{df['date'].iloc[0]}'"
    ).df()
    print(result.to_string())

    conn.close()


if __name__ == "__main__":
    today = datetime.utcnow().strftime("%Y-%m-%d")
    print(f"Transforming weather data for {today}\n")

    records = read_from_s3(today)
    if records:
        df = flatten_weather(records, today)
        load_to_duckdb(df)
        print("\nTransform complete.")
