# London Bike Share Data Pipeline

### Project Identifier: `BA_DENG_MM.F2601`

This project implements an automated batch data pipeline for the **London Bike Share Usage Dataset**.

It supports two reproducible pipeline paths:

- **Local pipeline**: ingestion into PostgreSQL, transformation with SQL, and validation through pgAdmin.
- **Cloud pipeline**: ingestion into Google Cloud Storage, transformation into BigQuery, and validation with analytical SQL queries.

Apache Airflow is used for workflow orchestration, Docker Compose is used for reproducibility, Terraform provisions the Google Cloud infrastructure, Google Cloud Storage acts as the cloud data lake, and BigQuery acts as the analytical data warehouse.

---

## Table of Contents

1. [Dataset Overview](#1-dataset-overview)
2. [Prerequisites](#2-prerequisites)
3. [Project Structure](#3-project-structure)
4. [Local Ingestion Pipeline](#4-local-ingestion-pipeline)
5. [Cloud Pipeline](#5-cloud-pipeline)
   - [Cloud Architecture](#cloud-architecture)
   - [Create Local Configuration Files](#create-local-configuration-files)
   - [Provision Cloud Infrastructure with Terraform](#provision-cloud-infrastructure-with-terraform)
   - [Start the Cloud Stack](#start-the-cloud-stack)
   - [Run the Cloud Data Lake Ingestion DAG](#run-the-cloud-data-lake-ingestion-dag)
   - [Run the BigQuery Transformation DAG](#run-the-bigquery-transformation-dag)
   - [Verify GCS and BigQuery](#verify-gcs-and-bigquery)
6. [Workflow Orchestration](#6-workflow-orchestration)
7. [Data Transformation Logic](#7-data-transformation-logic)
8. [Access & Credentials](#8-access--credentials)
9. [Security Notes](#9-security-notes)
10. [Additional Data Sources](#10-additional-data-sources)

---

## 1. Dataset Overview

- **Source:** [Kaggle - London Bike Share Usage Dataset](https://www.kaggle.com/datasets/kalacheva/london-bike-share-usage-dataset)
- **Description:** Historical trip data from London’s bike-sharing system from August 1 to August 31, 2023.
- **Scope:** Approximately 776,527 bicycle journeys.

### Main Features

| Feature | Description |
| :--- | :--- |
| `Number` | Unique identifier for each trip, also used as the trip ID |
| `Start date` | Date and time when the trip began |
| `Start station number` | ID of the starting station |
| `Start station` | Name of the starting station |
| `End date` | Date and time when the trip ended |
| `End station number` | ID of the ending station |
| `End station` | Name of the ending station |
| `Bike number` | Unique identifier for the bicycle used |
| `Bike model` | Bicycle model |
| `Total duration` | Trip duration in human-readable format |
| `Total duration (ms)` | Trip duration in milliseconds |

---

## 2. Prerequisites

Make sure the following tools are installed locally:

- Docker
- Docker Compose
- Terraform
- Google Cloud CLI
- BigQuery CLI, included with the Google Cloud CLI
- Access to a Google Cloud project with billing enabled
- A Google Cloud service account JSON key

For the cloud pipeline, the service account should have permissions for:

- Google Cloud Storage
- BigQuery

For this class project, roles such as `Storage Admin` and `BigQuery Admin` are sufficient. In a production setup, permissions should be narrowed according to the principle of least privilege.

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
├── docker-compose.yaml
├── pyproject.toml
├── .env.example
└── README.md
```

---

# London Bike Share Data Pipeline

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

```bash
docker compose --profile local up --build
```

To stop the local stack:

```bash
docker compose --profile local down
```

### Run the Local Airflow DAG

Open Airflow:

```text
http://localhost:8081
```

Select the DAG:

```text
bike_pipeline_day
```

Trigger the DAG for an execution date between:

```text
2023-08-01 and 2023-08-31
```

Only August 2023 contains source data.

### Run a Local Backfill

Use Airflow backfill for:

```text
2023-08-01 to 2023-08-31
```

Airflow executes one run per day for the selected range.

### Connect pgAdmin to PostgreSQL

Open pgAdmin:

```text
http://localhost:8085
```

Register a new server.

#### General tab

| Field | Value |
| :--- | :--- |
| Name | Local PostgreSQL |

#### Connection tab

| Field | Value |
| :--- | :--- |
| Host name/address | postgres |
| Port | 5432 |
| Maintenance database | postgres |
| Username | airflow |
| Password | airflow |

### Validate the Local Pipeline

After the Airflow Grid shows successful task runs, open the Query Tool in pgAdmin and run:

```sql
SELECT trip_date, COUNT(*)
FROM bike_trips_clean
GROUP BY trip_date
ORDER BY trip_date ASC;
```

Expected result: row counts for every processed August 2023 date.

---

## 5. Cloud Pipeline

The cloud pipeline has two stages:

### Step 2: Data Lake Ingestion

```text
Kaggle CSV source
    --> Airflow DAG
    --> Google Cloud Storage raw data lake
```

### Step 3: Data Warehouse Transformation

```text
Google Cloud Storage raw data lake
    --> Airflow DAG
    --> BigQuery partitioned and clustered warehouse table
```

### Cloud Architecture

```text
Kaggle CSV source
    --> Airflow DAG: bike_data_lake_ingestion
    --> GCS bucket: raw/london_bike_share/execution_date=YYYY-MM-DD/
    --> Airflow DAG: bike_bigquery_transformation
    --> BigQuery table: bike_data_warehouse.bike_trips_clean
    --> Analytics / reporting / machine learning use case
```

### Cloud Components

| Component | Purpose |
| :--- | :--- |
| Google Cloud Storage | Stores raw CSV batches in a data lake layout |
| BigQuery | Stores the cleaned warehouse table |
| Terraform | Provisions cloud infrastructure |
| Airflow | Orchestrates ingestion and transformation DAGs |
| Docker Compose cloud profile | Runs the cloud-enabled Airflow stack locally |

### Create Local Configuration Files

Two local configuration files are required:

```text
terraform/terraform.tfvars
.env
```

These files contain project-specific values and must not be committed to GitHub.

The repository should contain only template files:

```text
terraform/terraform.tfvars.example
.env.example
```

### 1. Create `terraform/terraform.tfvars`

Copy the example file:

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

Example content:

```hcl
project_id = "your-gcp-project-id"

region   = "europe-west6"
location = "EU"

bucket_name         = "your-globally-unique-bucket-name"
bigquery_dataset_id = "bike_data_warehouse"

credentials_file = "/absolute/path/to/your/service-account.json"
```

Example project-specific version:

```hcl
project_id = "custom-blade-489312-g4"

region   = "europe-west6"
location = "EU"

bucket_name         = "deng-bike-data-lake"
bigquery_dataset_id = "bike_data_warehouse"

credentials_file = "/Users/your-username/.gcp/deng-london-bike-share.json"
```

The bucket name must be globally unique across Google Cloud Storage.

### 2. Create `.env`

Copy the example file:

```bash
cp .env.example .env
```

Example content:

```env
GCP_CREDENTIALS_PATH=/absolute/path/to/your/service-account.json
GCS_BUCKET_NAME=your-gcs-bucket-name
GCP_PROJECT_ID=your-gcp-project-id
BIGQUERY_DATASET_ID=your-bigquery-dataset-id
```

Example project-specific version:

```env
GCP_CREDENTIALS_PATH=/Users/your-username/.gcp/deng-london-bike-share.json
GCS_BUCKET_NAME=deng-bike-data-lake
GCP_PROJECT_ID=custom-blade-489312-g4
BIGQUERY_DATASET_ID=bike_data_warehouse
```

Docker Compose automatically reads `.env` from the project root.

The credentials file is mounted into the Airflow containers at:

```text
/opt/airflow/secrets/gcp_credentials.json
```

Airflow and the Google Cloud Python libraries use:

```text
GOOGLE_APPLICATION_CREDENTIALS=/opt/airflow/secrets/gcp_credentials.json
```

### 3. Create the Service Account Key

Create or use an existing service account in Google Cloud.

The service account should have access to:

| Google Cloud Service | Required Access |
| :--- | :--- |
| Google Cloud Storage | Read and write raw CSV files |
| BigQuery | Create, load, and query warehouse tables |

Store the JSON key outside the repository, for example:

```text
~/.gcp/deng-london-bike-share.json
```

Do not commit service account keys to GitHub.

### Provision Cloud Infrastructure with Terraform

Navigate to the Terraform folder:

```bash
cd terraform
```

Initialize Terraform:

```bash
terraform init
```

Preview the infrastructure changes:

```bash
terraform plan
```

Apply the infrastructure:

```bash
terraform apply
```

Terraform provisions:

| Resource | Purpose |
| :--- | :--- |
| Google Cloud Storage bucket | Raw data lake storage |
| BigQuery dataset | Warehouse dataset |

After Terraform completes, return to the project root:

```bash
cd ..
```

Verify the bucket:

```bash
gcloud storage buckets list
```

Verify the BigQuery dataset:

```bash
bq ls your-gcp-project-id:
```

Example:

```bash
bq ls custom-blade-489312-g4:
```

### Start the Cloud Stack

From the project root:

```bash
docker compose --profile cloud up --build
```

To stop the cloud stack:

```bash
docker compose --profile cloud down
```

To restart cleanly after changing DAGs, environment variables, or Docker configuration:

```bash
docker compose --profile cloud down -v
docker compose --profile cloud up --build
```

### Run the Cloud Data Lake Ingestion DAG

The data lake ingestion DAG is:

```text
bike_data_lake_ingestion
```

It runs:

```text
app/cloud_ingestion/upload_to_gcs.py
```

The DAG uploads raw filtered daily CSV batches to Google Cloud Storage using this layout:

```text
gs://<bucket-name>/raw/london_bike_share/execution_date=YYYY-MM-DD/batch_00001.csv
```

Example:

```text
gs://deng-bike-data-lake/raw/london_bike_share/execution_date=2023-08-17/batch_00001.csv
```

#### Run for One Date

In Airflow:

```text
Open http://localhost:8081
Select bike_data_lake_ingestion
Trigger or backfill for a date between 2023-08-01 and 2023-08-31
```

#### Backfill Full Month

Use Airflow backfill for:

```text
2023-08-01 to 2023-08-31
```

Only August 2023 is valid because the source dataset only contains that month.

### Run the BigQuery Transformation DAG

The BigQuery transformation DAG is:

```text
bike_bigquery_transformation
```

It runs:

```text
app/bigquery/load_gcs_to_bigquery.py
```

This DAG reads raw files from GCS, transforms them, and loads them into a native BigQuery warehouse table:

```text
bike_data_warehouse.bike_trips_clean
```

The final BigQuery table is:

| Property | Value |
| :--- | :--- |
| Partitioned by | `trip_date` |
| Clustered by | `start_station_id`, `end_station_id` |

### User-Friendly Manual Trigger

The BigQuery DAG supports manual triggering.

If the Airflow logical date is within the dataset range:

```text
2023-08-01 to 2023-08-31
```

the DAG processes that single date.

If the DAG is triggered manually with a current date outside the dataset range, the script processes all available `execution_date=YYYY-MM-DD` folders in GCS.

This makes the DAG easier to use during demos and peer review.

### Recommended Cloud Run Order

For the complete cloud pipeline:

1. Provision infrastructure with Terraform.
2. Start the cloud Docker Compose profile.
3. Run or backfill `bike_data_lake_ingestion`.
4. Trigger `bike_bigquery_transformation`.
5. Validate GCS and BigQuery outputs.

### Verify GCS and BigQuery

#### Verify GCS Raw Files

List all raw files:

```bash
gcloud storage ls --recursive gs://deng-bike-data-lake/raw/london_bike_share/
```

Check one date:

```bash
gcloud storage ls --long --recursive gs://deng-bike-data-lake/raw/london_bike_share/execution_date=2023-08-17/
```

Inspect a raw CSV header:

```bash
gcloud storage cat gs://deng-bike-data-lake/raw/london_bike_share/execution_date=2023-08-17/batch_00001.csv | head -n 1
```

Expected header:

```csv
Number,Start date,Start station number,Start station,End date,End station number,End station,Bike number,Bike model,Total duration,Total duration (ms)
```

#### Verify BigQuery Table Exists

```bash
bq show custom-blade-489312-g4:bike_data_warehouse.bike_trips_clean
```

Expected table properties:

| Property | Expected Value |
| :--- | :--- |
| Time Partitioning | DAY field `trip_date` |
| Clustered Fields | `start_station_id`, `end_station_id` |
| Total Rows | Greater than 0 |

Replace `custom-blade-489312-g4` with your own Google Cloud project ID if using a different project.

#### Verify Row Counts by Date

```bash
bq query --use_legacy_sql=false \
"SELECT
   trip_date,
   COUNT(*) AS trip_count
 FROM `custom-blade-489312-g4.bike_data_warehouse.bike_trips_clean`
 GROUP BY trip_date
 ORDER BY trip_date"
```

Expected output: one row per processed date.

#### Example Analytics Query: Station Demand by Hour

```bash
bq query --use_legacy_sql=false \
"SELECT
   start_station_name,
   start_hour,
   COUNT(*) AS trip_count,
   ROUND(AVG(duration_minutes), 2) AS avg_duration_minutes
 FROM `custom-blade-489312-g4.bike_data_warehouse.bike_trips_clean`
 GROUP BY start_station_name, start_hour
 ORDER BY trip_count DESC
 LIMIT 20"
```

#### Example Analytics Query: Popular Routes

```bash
bq query --use_legacy_sql=false \
"SELECT
   start_station_name,
   end_station_name,
   COUNT(*) AS trip_count,
   ROUND(AVG(duration_minutes), 2) AS avg_duration_minutes
 FROM `custom-blade-489312-g4.bike_data_warehouse.bike_trips_clean`
 GROUP BY start_station_name, end_station_name
 ORDER BY trip_count DESC
 LIMIT 20"
```

---

## 6. Workflow Orchestration

Apache Airflow manages pipeline execution. It is responsible for:

- Scheduling batch runs
- Running pipeline tasks in the correct order
- Supporting historical backfills
- Supporting manual demo runs
- Providing observability through the Airflow UI

### Local DAG

```text
bike_pipeline_day
```

Local flow:

```text
ingest_raw_data
    --> create_bike_trips_clean
    --> create_station_hourly_demand
    --> create_route_daily_demand
    --> create_top_routes
```

### Cloud Data Lake DAG

```text
bike_data_lake_ingestion
```

Cloud data lake flow:

```text
Kaggle CSV source
    --> filter by Airflow logical date
    --> upload CSV batches to GCS
```

### Cloud BigQuery DAG

```text
bike_bigquery_transformation
```

Cloud warehouse flow:

```text
Read GCS raw CSV batches
    --> standardize column names
    --> convert timestamps
    --> derive trip_date
    --> derive start_hour
    --> derive duration_minutes
    --> remove invalid records
    --> load into BigQuery bike_trips_clean
```

---

## 7. Data Transformation Logic

The pipeline processes data through the following layers:

### Raw Layer

| Environment | Storage |
| :--- | :--- |
| Local | PostgreSQL table `london_bike_data` |
| Cloud | GCS raw CSV batches |

### Clean Layer

| Environment | Storage |
| :--- | :--- |
| Local | PostgreSQL table `bike_trips_clean` |
| Cloud | BigQuery table `bike_trips_clean` |

### Aggregation / Analytics Layer

| Environment | Storage |
| :--- | :--- |
| Local | `station_hourly_demand`, `route_daily_demand`, `top_routes` |
| Cloud | BigQuery analytical queries over `bike_trips_clean` |

### BigQuery Clean Table: `bike_trips_clean`

The BigQuery transformation creates analytical columns such as:

| Column | Purpose |
| :--- | :--- |
| `trip_date` | Supports daily partitioning and date-based analysis |
| `start_hour` | Supports hourly station demand analysis |
| `duration_minutes` | Supports duration-based analytics |
| `start_station_id` | Supports station and route grouping |
| `end_station_id` | Supports station and route grouping |
| `start_station_name` | Human-readable start station |
| `end_station_name` | Human-readable end station |

### Partitioning and Clustering

The BigQuery table is partitioned by:

```text
trip_date
```

This supports time-based analysis such as daily trip counts and daily demand trends.

The table is clustered by:

```text
start_station_id, end_station_id
```

This supports station-demand and route-demand analysis, because common queries filter or group by station and route fields.

---

## 8. Access & Credentials

Google Cloud credentials are not stored in the repository. They are passed locally through `.env` and mounted into the Airflow containers.

---

## 9. Security Notes

Do not commit the following files:

```text
.env
terraform/terraform.tfvars
*.json
orchestration/airflow/secrets/
```

The repository should include only safe templates:

```text
.env.example
terraform/terraform.tfvars.example
```

Recommended `.gitignore` entries:

```gitignore
.env
terraform/terraform.tfvars
*.json
orchestration/airflow/secrets/
```

Service account JSON keys must be stored outside the repository, for example:

```text
~/.gcp/deng-london-bike-share.json
```

---

## 10. Additional Data Sources

London Transport Open Data from TfL:

```text
https://tfl.gov.uk/info-for/open-data-users/our-open-data
```




