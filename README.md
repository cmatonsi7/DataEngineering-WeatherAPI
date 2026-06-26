# Phase 3 — Cloud-Native Weather Pipeline

## Overview
An automated ELT pipeline that pulls daily weather data for 5 South African cities
from the Open-Meteo API, lands raw JSON in AWS S3, transforms it using Python and
dbt, and orchestrates the entire flow with Apache Airflow.

## Architecture

Open-Meteo API → Python → AWS S3 (raw JSON) → Python → DuckDB → dbt → Mart Tables

↑

Airflow DAG

(runs daily at 6AM)
## Tech Stack
- **Python 3.11** — extraction and transformation scripts
- **AWS S3** — cloud storage for raw JSON files (date-partitioned)
- **boto3** — AWS SDK for Python (S3 uploads/downloads)
- **DuckDB** — local analytical data warehouse
- **dbt** — data transformation and testing
- **Apache Airflow 2.9.1** — pipeline orchestration and scheduling

## Project Structure
Phase3-Weather-Pipeline/

├── extract/

│   └── extract_weather.py      # Pulls from Open-Meteo API, uploads to S3

├── transform/

│   └── load_to_duckdb.py       # Reads from S3, flattens JSON, loads DuckDB

├── weather_dw/                 # dbt project

│   └── models/

│       ├── staging/

│       │   ├── stg_weather.sql

│       │   └── schema.yml

│       └── marts/

│           ├── fct_weather_daily.sql

│           └── schema.yml

├── dags/

│   └── weather_pipeline_dag.py # Airflow DAG

└── README.md

## Data Sources
**Open-Meteo API** (free, no key required)
- 5 South African cities: Johannesburg, Cape Town, Durban, Pretoria, Port Elizabeth
- Daily metrics: max/min/mean temperature, precipitation, wind speed, weather code

## S3 Structure
Raw files land in a date-partitioned structure:

s3://weather-pipeline-calvin-010526241741-us-east-1-an/

└── raw/

└── YYYY/

└── MM/

└── DD/

├── johannesburg.json

├── cape_town.json

├── durban.json

├── pretoria.json

└── port_elizabeth.json
## dbt Models
| Model | Layer | Type | Description |
|-------|-------|------|-------------|
| stg_weather | Staging | View | Cleaned weather data with derived columns |
| fct_weather_daily | Marts | Table | Final fact table, one row per city per day |

## dbt Tests
7 data quality tests — all passing:
- not_null on city, date, temp_max, weather_description
- accepted_values on weather_description (8 valid WMO weather categories)

## Airflow DAG
**DAG ID:** `weather_pipeline`
**Schedule:** Daily at 6:00 AM UTC (`0 6 * * *`)
**Tasks:**

extract_weather → load_to_duckdb → dbt_run

## Sample Data (2026-06-26)
| City | Temp Max | Temp Min | Precipitation | Weather |
|------|----------|----------|---------------|---------|
| Cape Town | 21.4°C | 10.3°C | 0.0mm | Partly Cloudy |
| Durban | 25.3°C | 12.7°C | 0.0mm | Partly Cloudy |
| Johannesburg | 17.1°C | 7.1°C | 0.0mm | Clear Sky |
| Port Elizabeth | 23.1°C | 15.5°C | 2.0mm | Rain |
| Pretoria | 19.4°C | 8.0°C | 0.0mm | Partly Cloudy |

## Known Issues & Lessons Learned
**Airflow + dbt dependency conflict:**
Installing Airflow and dbt in the same virtual environment causes package
conflicts — Airflow downgrades several packages that dbt requires (protobuf,
click, sqlparse, jinja2). In production this is resolved by running dbt in a
separate virtual environment and using Airflow's BashOperator to call it with
the correct Python path, or by using the DbtCloudOperator.

**AWS credentials:**
Never commit AWS credentials to GitHub. Always use environment variables or
AWS IAM roles for credential management. Credentials used in this project
have been rotated after use.

## How to Run
1. Clone the repo
2. Create virtual environment: `python3.11 -m venv .venv`
3. Activate: `source .venv/bin/activate`
4. Install dependencies: `pip install requests boto3 duckdb pandas dbt-duckdb`
5. Configure AWS: `aws configure`
6. Run extraction: `python3.11 extract/extract_weather.py`
7. Run transform: `python3.11 transform/load_to_duckdb.py`
8. Run dbt: `cd weather_dw && ../.venv/bin/dbt run && ../.venv/bin/dbt test`