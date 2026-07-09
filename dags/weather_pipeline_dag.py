from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# ── WHAT IS THIS? ──────────────────────────────────────────────────────────────
# This is an Airflow DAG (Directed Acyclic Graph).
# A DAG defines a pipeline — what tasks to run, in what order, on what schedule.
#
#
# 
# 
# 
#
# Our pipeline has 3 tasks that run in sequence every day at 6AM:
# 1. extract_weather  — pulls data from Open-Meteo API and uploads to S3
# 2. load_to_duckdb   — reads from S3, flattens JSON, loads into DuckDB
# 3. dbt_run          — runs dbt models to build staging and mart tables
#
# If any task fails, all downstream tasks are skipped automatically.
# ───────────────────────────────────────────────────────────────────────────────

# Project paths
PROJECT_DIR = "/Users/calvinmatonsi/Desktop/DATA ENGINEERING DATA PROJECTS/Phase3-Weather-Pipeline"
PYTHON = f"{PROJECT_DIR}/.venv/bin/python3.11"
DBT = f"{PROJECT_DIR}/.venv/bin/dbt"
DBT_PROJECT = f"{PROJECT_DIR}/weather_dw"

# Default arguments applied to every task in the DAG
default_args = {
    "owner": "calvin",
    "retries": 1,                           # retry once if a task fails
    "retry_delay": timedelta(minutes=5),    # wait 5 mins before retrying
    "email_on_failure": False,
    "depends_on_past": False,               # each run is independent
}

with DAG(
    dag_id="weather_pipeline",
    description="Daily weather pipeline: Open-Meteo → S3 → DuckDB → dbt",
    default_args=default_args,
    start_date=datetime(2026, 6, 26),
    schedule_interval="0 6 * * *",          # run daily at 6:00 AM
    catchup=False,                          # don't backfill missed runs
    tags=["weather", "s3", "duckdb", "dbt"],
) as dag:

    # ── TASK 1: Extract ───────────────────────────────────────────────────────
    # BashOperator runs a shell command
    # We call our extract script directly using the venv's Python
    extract = BashOperator(
        task_id="extract_weather",
        bash_command=f"{PYTHON} {PROJECT_DIR}/extract/extract_weather.py",
    )

    # ── TASK 2: Load ──────────────────────────────────────────────────────────
    # Reads from S3 and loads into DuckDB
    load = BashOperator(
        task_id="load_to_duckdb",
        bash_command=f"{PYTHON} {PROJECT_DIR}/transform/load_to_duckdb.py",
    )

    # ── TASK 3: Transform ─────────────────────────────────────────────────────
    # Runs all dbt models in the correct dependency order
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_PROJECT} && {DBT} run && {DBT} test",
    )

    # ── DEPENDENCY CHAIN ──────────────────────────────────────────────────────
    # The >> operator defines task order
    # extract must finish before load starts
    # load must finish before dbt_run starts
    extract >> load >> dbt_run
