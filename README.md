# London Bike Share Data Pipeline
### Project Identifier: `BA_DENG_MM.F2601`

This project implements an automated ETL (Extract, Transform, Load) pipeline for the **London Bike Share Usage Dataset**. It utilizes Docker to orchestrate a PostgreSQL database, pgAdmin for visualization, and Apache Airflow for workflow management.

---

## 1. Dataset Overview
* **Source:** [Kaggle - London Bike Share Usage Dataset](https://www.kaggle.com/datasets/kalacheva/london-bike-share-usage-dataset)
* **Description:** HHistorical trip data from London’s bike-sharing system (Aug 1 – Aug 31, 2023).
* **Scope:** ~776,527 bicycle journeys.

### Main Features
| Feature | Description |
| :--- | :--- |
| **Number** | Unique identifier for each trip (Trip ID) |
| **Start Date** | Date and time when the trip began |
| **Start Station** | Name and ID of the starting station |
| **End Date** | Date and time when the trip ended |
| **End Station** | Name and ID of the ending station |
| **Bike Number** | Unique identifier for the bicycle used |
| **Bike Model** | The model of the bicycle used |
| **Total Duration** | Trip length (Human-readable and Milliseconds) |

---

## 2. Prerequisites
Ensure the following are installed on your local machine:
**Docker**

---
## 3. Project Structure
```bash
.
├── app/
│   └── local_ingestion/
│       ├── Dockerfile
│       └── pipeline.py
├── london_bike_share_data/
├── orchestration/
│   └── airflow/
│       ├── dags/
│       │   └── bike_pipeline_day.py
│       ├── Dockerfile
│       └── simple_auth_manager_passwords.json
├── postgres/
│   └── init_airflow.sql
├── transformations/
│   ├── create_bike_trips_clean.sql
│   ├── create_route_daily_demand.sql
│   ├── create_station_hourly_demand.sql
│   └── create_top_routes.sql
├── .python-version
├── docker-compose.yaml
├── pyproject.toml
└── uv.lock
```
## 4. Infrastructure Setup

### Database & Administration

The environment is fully containerized. To launch the entire stack:

```bash
# Start all services (Database, Airflow, API Server, Scheduler)
docker compose up --build
```
## 5. Data Pipeline Structure
The pipeline processes data through three distinct layers:

```
    --> Kaggle (CSV Source)
    --> Raw Table: london_bike_data
    --> Clean Layer: bike_trips_clean
        --> Agg: station_hourly_demand
        --> Agg: route_daily_demand
        --> Agg: top_routes
        --> Agg: station_daily_demand
```

### Raw Layer (london_bike_data):
The initial ingestion of raw CSV data.

### Clean Layer (bike_trips_clean):

Standardized column naming and timestamp formatting.

Data preparation for downstream analytical queries.

### Aggregation Layer:

Station Hourly: Identifies peak demand and maintenance needs.

Route Daily: Tracks movement patterns between specific stations.

Top Routes: Focuses on the highest-traffic segments.

## 6. Workflow Orchestration (Airflow)
The pipeline is managed by Apache Airflow to handle task dependencies and scheduling.

### Run for a Single Date
1. Open Airflow UI: http://localhost:8081
2. Select DAG `bike_pipeline_day`
3. Click **Trigger DAG**
4. Set the execution date (e.g., `2023-08-10`)
5. Trigger the run

→ Runs the pipeline only for that specific day.

### Run Backfill (Historical Data)
1. Select DAG `bike_pipeline_day`
2. Click **Trigger DAG**
3. Select **Run Backfills**
4. Set a date range (Aug 1–31, 2023)

→ Airflow executes one run per day for the selected range.

**Note:** Only dates within Aug 2023 contain data.

### Access & Credentials
|Service| URL | Username | Password |
| :--- | :--- | :--- | :--- |
| Airflow | http://localhost:8081 |admin| admin|
| pgAdmin | http://localhost:8085 |admin@admin.com| root|
| postgres | http://localhost:5432 |root| root|

The Airflow DAG executes the following logic:

ingest_raw_data

create_bike_trips_clean

create_station_hourly_demand

create_route_daily_demand

## 7. Connecting pgAdmin to Postgres
Once logged into pgAdmin, register the server with these settings:

General Tab:

Name: London Bike Share DB

Connection Tab:
| Field | Value |
| :--- | :--- |
| Host name/address | postgres |
| Port | 5432 |
| Maintenance database | london_bike_share |
| Username | root |
| Password | root |

press ***Save***
## 8. Final Quick Check (Testing)
To verify the pipeline's success after the Airflow Grid shows all green, run the following check in pgAdmin:
Connect to the London Bike Share DB.

Open the Query Tool and execute:
```bash
SQL
-- Check if data exists and is cleaned
SELECT trip_date, count(*)
FROM bike_trips_clean
GROUP BY trip_date
ORDER BY trip_date ASC;
```
Expected Result: You should see row counts for every day in August 2023, confirming the ingestion and transformation were successful.

## 9. Additional Data Sources
London Transport Open Data (TfL):
https://tfl.gov.uk/info-for/open-data-users/our-open-data$0
