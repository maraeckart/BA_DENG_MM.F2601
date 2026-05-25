# London Bike Share Data Pipeline
### Project Identifier: `BA_DENG_MM.F2601`

This project implements an automated batch data pipeline for the **London Bike Share Usage Dataset**. It supports two reproducible ingestion paths:

- **Local ingestion** into PostgreSQL, with transformations and validation through pgAdmin.
- **Cloud ingestion** into Google Cloud Storage and BigQuery, provisioned with Terraform.

Apache Airflow is used for workflow orchestration, and Docker Compose is used to make the local development environment reproducible.

---

## Table of Contents

1. [Dataset Overview](#1-dataset-overview)
2. [Prerequisites](#2-prerequisites)
3. [Project Structure](#3-project-structure)
4. [Local Ingestion Pipeline](#4-local-ingestion-pipeline)
   - [Local Architecture](#local-architecture)
   - [Start the Local Stack](#start-the-local-stack)
   - [Run the Local Airflow DAG](#run-the-local-airflow-dag)
   - [Connect pgAdmin to PostgreSQL](#connect-pgadmin-to-postgresql)
   - [Validate the Local Pipeline](#validate-the-local-pipeline)
5. [Cloud Ingestion Pipeline](#5-cloud-ingestion-pipeline)
   - [Cloud Architecture](#cloud-architecture)
   - [Provision Cloud Infrastructure with Terraform](#provision-cloud-infrastructure-with-terraform)
   - [Configure Cloud Credentials for Airflow](#configure-cloud-credentials-for-airflow)
   - [Start the Cloud Stack](#start-the-cloud-stack)
   - [Run the Cloud Airflow DAG](#run-the-cloud-airflow-dag)
   - [Run the BigQuery Transformation DAG](#run-the-bigquery-transformation-dag)
   - [Verify BigQuery in the Google Cloud Console](#verify-bigquery-in-the-google-cloud-console)
6. [Workflow Orchestration](#6-workflow-orchestration)
7. [Data Transformation Logic](#7-data-transformation-logic)
8. [Access & Credentials](#8-access--credentials)
9. [Additional Data Sources](#9-additional-data-sources)

---

## 1. Dataset Overview

- **Source:** [Kaggle - London Bike Share Usage Dataset](https://www.kaggle.com/datasets/kalacheva/london-bike-share-usage-dataset)
- **Description:** Historical trip data from London’s bike-sharing system from Aug 1 to Aug 31, 2023.
- **Scope:** Approximately 776,527 bicycle journeys.

### Main Features

| Feature | Description |
| :--- | :--- |
| **Number** | Unique identifier for each trip, also used as the trip ID |
| **Start Date** | Date and time when the trip began |
| **Start Station** | Name and ID of the starting station |
| **End Date** | Date and time when the trip ended |
| **End Station** | Name and ID of the ending station |
| **Bike Number** | Unique identifier for the bicycle used |
| **Bike Model** | The model of the bicycle used |
| **Total Duration** | Trip length in human-readable format and milliseconds |

---

## 2. Prerequisites

Make sure the following tools are installed on your local machine:

- Docker
- Docker Compose
- Terraform
- Access to a Google Cloud project with billing enabled, required only for the cloud ingestion pipeline
- A Google Cloud service account JSON credentials file, required only for the cloud ingestion pipeline

---

## 3. Project Structure

```bash
.
├── app/
│   ├── local_ingestion/
│   │   ├── Dockerfile
│   │   └── pipeline.py
│   ├── cloud_ingestion/
│   │   ├── Dockerfile
│   │   └── upload_to_gcs.py
│   └── bigquery/
│       └── load_gcs_to_bigquery.py
├── infrastructure/
├── london_bike_share_data/
├── orchestration/
│   └── airflow/
│       ├── dags/
│       │   ├── bike_data_lake_ingestion.py
│       │   ├── bike_bigquery_transformation.py
│       │   └── bike_pipeline_day.py
│       ├── Dockerfile
│       └── simple_auth_manager_passwords.json
├── postgres/
│   └── init_airflow.sql
├── terraform/
│   ├── main.tf
│   ├── outputs.tf
│   ├── provider.tf
│   ├── terraform.tfvars.example
│   └── variables.tf
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

---

## 4. Local Ingestion Pipeline

The local ingestion pipeline loads the London Bike Share CSV data into a local PostgreSQL database. Airflow orchestrates the ingestion and transformation tasks, and pgAdmin can be used to inspect the resulting tables.

### Local Architecture

```text
Kaggle CSV source
    --> Airflow local ingestion DAG
    --> PostgreSQL raw table: london_bike_data
    --> PostgreSQL clean table: bike_trips_clean
    --> PostgreSQL aggregation tables
    --> pgAdmin validation
```

The local stack contains:

| Service | Purpose |
| :--- | :--- |
| PostgreSQL | Stores raw, cleaned, and aggregated local data |
| pgAdmin | Provides a browser-based UI for querying PostgreSQL |
| Airflow API Server | Provides the Airflow UI |
| Airflow Scheduler | Schedules and runs DAG tasks |
| Airflow DAG Processor | Parses DAG files |

### Start the Local Stack

Use the local Docker Compose profile:

```bash
docker compose --profile local up --build
```

This starts the services needed for local development and local ingestion.

To stop the stack:

```bash
docker compose --profile local down
```

### Run the Local Airflow DAG

1. Open the Airflow UI: [http://localhost:8081](http://localhost:8081)
2. Select the DAG `bike_pipeline_day`
3. Click **Trigger DAG**
4. Set the execution date, for example `2023-08-10`
5. Trigger the run

This runs the local pipeline for one specific day.

### Run a Local Backfill

1. Open the DAG `bike_pipeline_day`
2. Click **Trigger DAG**
3. Select **Run Backfills**
4. Set a date range between Aug 1 and Aug 31, 2023

Airflow executes one run per day for the selected range.

**Note:** Only dates in August 2023 contain data.

### Connect pgAdmin to PostgreSQL

Open pgAdmin at [http://localhost:8085](http://localhost:8085), then register a new server.

**General tab**

| Field | Value |
| :--- | :--- |
| Name | London Bike Share DB |

**Connection tab**

| Field | Value |
| :--- | :--- |
| Host name/address | postgres |
| Port | 5432 |
| Maintenance database | london_bike_share |
| Username | root |
| Password | root |

Press **Save**.

### Validate the Local Pipeline

After the Airflow Grid shows successful task runs, open the Query Tool in pgAdmin and run:

```sql
SELECT trip_date, COUNT(*)
FROM bike_trips_clean
GROUP BY trip_date
ORDER BY trip_date ASC;
```

Expected result: row counts for every processed day in August 2023.

---

## 5. Cloud Ingestion Pipeline

The cloud ingestion pipeline loads batch data into Google Cloud Storage and prepares it for analytical use in BigQuery. Terraform is used to provision the required cloud infrastructure.

### Cloud Architecture

```text
Kaggle CSV source
    --> Airflow cloud ingestion DAG
    --> Google Cloud Storage data lake
    --> BigQuery warehouse tables
    --> Analytics or machine learning use case
```

The cloud stack uses:

| Component | Purpose |
| :--- | :--- |
| Google Cloud Storage | Cloud data lake for raw or staged files |
| BigQuery | Cloud data warehouse for transformed analytical tables |
| Terraform | Infrastructure provisioning |
| Airflow | Orchestration of cloud ingestion and transformation tasks |

### Provision Cloud Infrastructure with Terraform

Navigate to the Terraform directory:

```bash
cd terraform
```

Create a `terraform.tfvars` file or rename `terraform.tfvars.example`:

```hcl
project_id       = "your-gcp-project-id"
credentials_file = "/absolute/path/to/your/deng-service-account.json"

region   = "europe-west6"
location = "EU"

bucket_name         = "your-globally-unique-bucket-name"
bigquery_dataset_id = "london_bike_share_warehouse"
```

The bucket name must be globally unique across Google Cloud Storage.

Initialize and apply the Terraform configuration:

```bash
terraform init
terraform apply
```

### Configure Cloud Credentials for Airflow

Create a Google Cloud service account with the permissions required by the pipeline, for example:

- Storage Admin
- BigQuery Admin

Create a JSON key for the service account and store it outside the repository, for example:

```bash
~/.gcp/deng-service-account.json
```

Do not commit this credentials file to GitHub.

Set the credentials path before starting the cloud profile:

```bash
export GCP_CREDENTIALS_PATH=/absolute/path/to/your/deng-service-account.json
export GCS_BUCKET_NAME=your-globally-unique-bucket-name
```

The Docker Compose file mounts the credentials into the Airflow containers at:

```text
/opt/airflow/secrets/gcp_credentials.json
```

Airflow and the Google Cloud Python libraries use this path through:

```bash
GOOGLE_APPLICATION_CREDENTIALS=/opt/airflow/secrets/gcp_credentials.json
```

### Start the Cloud Stack

Use the cloud Docker Compose profile:

```bash
docker compose --profile cloud up --build
```

This starts the services needed to orchestrate the cloud ingestion pipeline.

To stop the stack:

```bash
docker compose --profile cloud down
```

### Run the Cloud Airflow DAG

1. Open the Airflow UI: [http://localhost:8081](http://localhost:8081)
2. Select the cloud ingestion DAG `bike_data_lake_ingestion`
3. Trigger the DAG manually or run the configured schedule
4. Verify in the Google Cloud Console that data has been written to the configured Google Cloud Storage bucket

The cloud ingestion DAG writes raw CSV batches to Google Cloud Storage using this layout:

```text
gs://<bucket-name>/raw/london_bike_share/execution_date=YYYY-MM-DD/batch_00001.csv
```

Example path format:

```text
gs://<bucket-name>/raw/london_bike_share/execution_date=2023-08-17/batch_00001.csv
```

### Run the BigQuery Transformation DAG

After the raw files are available in Google Cloud Storage, run the BigQuery transformation DAG.

1. Open the Airflow UI: [http://localhost:8081](http://localhost:8081)
2. Select the DAG `bike_bigquery_transformation`
3. Trigger the DAG manually or run the configured schedule
4. Check that the DAG run and all tasks finish successfully
5. Verify the resulting warehouse table in the Google Cloud Console

The BigQuery transformation DAG reads the raw CSV batches from Google Cloud Storage, standardizes the columns, converts timestamps, derives analytical fields, removes invalid records, and loads the result into the BigQuery warehouse table.

The final BigQuery table is:

```text
<project-id>.<bigquery-dataset-id>.bike_trips_clean
```

Expected configuration:

| Property | Expected Value |
| :--- | :--- |
| Table name | `bike_trips_clean` |
| Dataset | Value configured as `bigquery_dataset_id` |
| Partitioning | Daily partitioning by `trip_date` |
| Clustering | `start_station_id`, `end_station_id` |

### Verify BigQuery in the Google Cloud Console

Use the Google Cloud Console UI for verification.

1. Open the Google Cloud Console
2. Go to **BigQuery**
3. Select your Google Cloud project
4. Open the dataset configured as `bigquery_dataset_id`
5. Open the table `bike_trips_clean`
6. Check the **Details** tab and confirm that the table contains rows
7. Confirm that partitioning uses `trip_date`
8. Confirm that clustering uses `start_station_id` and `end_station_id`

To validate the loaded data, open the **Query** tab in BigQuery and run:

```sql
SELECT
  trip_date,
  COUNT(*) AS trip_count
FROM `<project-id>.<bigquery-dataset-id>.bike_trips_clean`
GROUP BY trip_date
ORDER BY trip_date;
```

Expected result: one row per processed day in August 2023.

Example analytical query:

```sql
SELECT
  start_station_name,
  start_hour,
  COUNT(*) AS trip_count,
  ROUND(AVG(duration_minutes), 2) AS avg_duration_minutes
FROM `<project-id>.<bigquery-dataset-id>.bike_trips_clean`
GROUP BY start_station_name, start_hour
ORDER BY trip_count DESC
LIMIT 20;
```

---

## 6. Workflow Orchestration

Apache Airflow manages the pipeline execution. It is responsible for:

- Scheduling batch runs
- Running individual pipeline tasks in the correct order
- Supporting backfills for historical data
- Providing observability through the Airflow UI

The local DAG executes the following logic:

```text
ingest_raw_data
    --> create_bike_trips_clean
    --> create_station_hourly_demand
    --> create_route_daily_demand
    --> create_top_routes
```

The cloud ingestion DAG executes the following logic:

```text
read source CSV
    --> filter by Airflow execution date
    --> upload daily batch files to Google Cloud Storage
```

The BigQuery transformation DAG executes the following logic:

```text
read raw CSV batches from Google Cloud Storage
    --> standardize column names
    --> convert timestamps
    --> derive trip_date, start_hour, and duration_minutes
    --> remove invalid records
    --> load bike_trips_clean into BigQuery
```

---

## 7. Data Transformation Logic

The pipeline processes data through three layers:

```text
Raw Layer: london_bike_data
    --> Clean Layer: bike_trips_clean
        --> Aggregation Layer: station_hourly_demand
        --> Aggregation Layer: route_daily_demand
        --> Aggregation Layer: top_routes
        --> Aggregation Layer: station_daily_demand
```

### Raw Layer: `london_bike_data`

The raw layer stores the initial ingestion of CSV data with minimal changes.

### Clean Layer: `bike_trips_clean`

The clean layer standardizes column names, converts timestamp fields, and prepares the data for downstream analytical queries.

In BigQuery, the clean table also includes analytical columns such as:

| Column | Purpose |
| :--- | :--- |
| `trip_date` | Supports daily partitioning and date-based analysis |
| `start_hour` | Supports hourly station demand analysis |
| `duration_minutes` | Supports duration-based analytics |
| `start_station_id` | Supports station and route grouping |
| `end_station_id` | Supports station and route grouping |
| `start_station_name` | Human-readable start station |
| `end_station_name` | Human-readable end station |

The BigQuery table is partitioned by `trip_date` and clustered by `start_station_id` and `end_station_id`.

### Aggregation Layer

| Table | Purpose |
| :--- | :--- |
| `station_hourly_demand` | Identifies hourly station demand patterns and possible maintenance needs |
| `route_daily_demand` | Tracks daily movement patterns between start and end stations |
| `top_routes` | Identifies the highest-traffic route segments |
| `station_daily_demand` | Summarizes daily station-level activity |

These transformations support analysis of station usage, peak demand, and route popularity.

---

## 8. Access & Credentials

| Service | URL | Username | Password |
| :--- | :--- | :--- | :--- |
| Airflow | [http://localhost:8081](http://localhost:8081) | admin | admin |
| pgAdmin | [http://localhost:8085](http://localhost:8085) | admin@admin.com | root |
| PostgreSQL | localhost:5432 | root | root |

---

## 9. Additional Data Sources

London Transport Open Data from TfL:
[https://tfl.gov.uk/info-for/open-data-users/our-open-data](https://tfl.gov.uk/info-for/open-data-users/our-open-data)