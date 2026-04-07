# London Bike Share Data Pipeline
### Project Identifier: `BA_DENG_MM.F2601`

This project implements an automated ETL (Extract, Transform, Load) pipeline for the **London Bike Share Usage Dataset**. It utilizes Docker to orchestrate a PostgreSQL database, pgAdmin for visualization, and Apache Airflow for workflow management.

---

## 1. Dataset Overview
* **Source:** [Kaggle - London Bike Share Usage Dataset](https://www.kaggle.com/datasets/kalacheva/london-bike-share-usage-dataset)
* **Description:** Historical trip data from London’s bike-sharing system, including station details, timestamps, and trip durations.

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

## 3. Infrastructure Setup

### Database & Administration

Run the PostgreSQL database and pgAdmin:

```bash
docker compose up -d --build postgres pgadmin
```
### Ingestion Pipeline (If you want to run it manually otherwise use Airflow)

In a separate terminal, run the ingestion service to populate the raw tables:

```bash
docker compose --profile ingest up --build bike_ingest
```
## 4. Data Pipeline Structure
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

## 5. Workflow Orchestration (Airflow)
The pipeline is managed by Apache Airflow to handle task dependencies and scheduling.

### Start Airflow


```bash
# Initialize:
docker compose up --build airflow-init

# Start Services:
docker compose up -d --build airflow-webserver airflow-scheduler airflow-dag-processor
```

### Access & Credentials
|Service| URL | Username | Password |
| :--- | :--- | :--- | :--- |
| Airflow | http://localhost:8081 |admin| admin|
| pgAdmin | http://localhost:8085 |admin@admin.com| root|
| postgres | http://localhost:5432 |root| root|

### Important
To run the pipeline through the airflow UI you need to add a ConnectionId.
For that go to **Admin -> Connections -> +**.
| Field | Value |
| :--- | :--- |
| **Connection Id** | postgres_london_bike |
| **Connection Type** | Postgres |
| **Host** | postgres |
| **Database** | london_bike_share |
| **Login** | root |
| **Password** | root |
| **Port** | 5432 |

The Airflow DAG executes the following logic:

ingest_raw_data

create_bike_trips_clean

create_station_hourly_demand

create_route_daily_demand

## 6. Connecting pgAdmin to Postgres
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

## 7. Additional Data Sources
London Transport Open Data (TfL):
https://tfl.gov.uk/info-for/open-data-users/our-open-data$0
