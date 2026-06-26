import requests
import json
import boto3
import os
from datetime import datetime

# ── WHAT IS THIS? ──────────────────────────────────────────────────────────────
# This script pulls daily weather data from the Open-Meteo API for 5 SA cities.
# Open-Meteo is completely free — no API key needed.
#
# For each city it fetches:
# - Max/min/mean temperature
# - Total precipitation
# - Max wind speed
# - Weather condition code
#
# The raw JSON is uploaded to S3 in a date-partitioned structure:
# s3://bucket/raw/YYYY/MM/DD/city_name.json
#
# Why date-partitioned? So you can query specific time periods efficiently
# and each daily run doesn't overwrite the previous day's data.
# ───────────────────────────────────────────────────────────────────────────────

BUCKET = "weather-pipeline-calvin-010526241741-us-east-1-an"
REGION = "us-east-1"

# 5 South African cities with their coordinates
# Open-Meteo uses latitude/longitude instead of city names
CITIES = {
    "johannesburg": {"latitude": -26.2041, "longitude": 28.0473},
    "cape_town":    {"latitude": -33.9249, "longitude": 18.4241},
    "durban":       {"latitude": -29.8587, "longitude": 31.0218},
    "pretoria":     {"latitude": -25.7479, "longitude": 28.2293},
    "port_elizabeth":{"latitude": -33.9608, "longitude": 25.6022},
}

# Open-Meteo API base URL
# daily= specifies which weather variables we want
BASE_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}"
    "&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
    "precipitation_sum,windspeed_10m_max,weathercode"
    "&timezone=Africa%2FJohannesburg"
    "&forecast_days=1"
)

def fetch_weather(city, coords):
    """
    Hits the Open-Meteo API for a single city and returns the JSON response.
    
    The API returns a dictionary with:
    - latitude, longitude, timezone
    - daily: a dict where each key is a weather variable
              and each value is a list (one entry per day)
    """
    url = BASE_URL.format(lat=coords["latitude"], lon=coords["longitude"])
    response = requests.get(url)

    if response.status_code != 200:
        print(f"  ERROR fetching {city}: {response.status_code}")
        return None

    data = response.json()
    # Add city name to the response so we know which city this belongs to
    data["city"] = city
    data["extracted_at"] = datetime.utcnow().isoformat()
    return data


def upload_to_s3(data, city, date_str):
    """
    Uploads a single city's weather JSON to S3.

    Why use boto3.client instead of boto3.resource?
    client gives you low-level direct access to AWS APIs.
    It's more explicit and better for simple upload operations.

    The S3 key (path) follows the date-partition pattern:
    raw/YYYY/MM/DD/city_name.json
    """
    s3 = boto3.client("s3", region_name=REGION)

    year, month, day = date_str.split("-")
    s3_key = f"raw/{year}/{month}/{day}/{city}.json"

    # Convert the Python dict to a JSON string for upload
    body = json.dumps(data, indent=2)

    s3.put_object(
        Bucket=BUCKET,
        Key=s3_key,
        Body=body,
        ContentType="application/json"
    )

    print(f"  Uploaded to s3://{BUCKET}/{s3_key}")
    return s3_key


if __name__ == "__main__":
    today = datetime.utcnow().strftime("%Y-%m-%d")
    print(f"Extracting weather data for {today}...\n")

    uploaded = []

    for city, coords in CITIES.items():
        print(f"Fetching {city}...")
        data = fetch_weather(city, coords)

        if data:
            key = upload_to_s3(data, city, today)
            uploaded.append(key)

    print(f"\nDone. {len(uploaded)}/5 cities uploaded to S3.")