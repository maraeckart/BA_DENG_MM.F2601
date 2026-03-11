# BA_DENG_MM.F2601

## 1. Dataset Overview

**Dataset:** London Bike Share Usage Dataset
**Source:** Kaggle
https://www.kaggle.com/datasets/kalacheva/london-bike-share-usage-dataset

This dataset contains historical usage data from the **London bike sharing system**. The dataset includes time-based bike rental information along with environmental and calendar-related variables.

### Main Features

- `Number:` A unique identifier for each trip (Trip ID).
- `Start Date:` The date and time when the trip began.
- `Start Station Number:` The identifier for the starting station.
- `Start Station:` The name of the starting station.
- `End Date:` The date and time when the trip ended.
- `End Station Number:` The identifier for the ending station.
- `End Station:` The name of the ending station.
- `Bike Number:` A unique identifier for the bicycle used.
- `Bike Model:` The model of the bicycle used.
- `Total Duration:` The total time duration of the trip (in a human-readable format).
- `Total Duration (ms):` The total time duration of the trip in milliseconds.

The dataset enables analysis of **rental demands, popular routes, trip durations, etc.**.

## 2. Prerequirements
- Docker is installed on your device
- Some version of Python 3 is installed on your device (we used Python 3.13)
- The package manager uv should be installed on your device

## 3. Running the dockerized local database
mkdir -p london_bike_share_data

Run pg-database and pg-admin:
docker compose up --build postgres pgadmin

Run ingestion pipeline in another terminal:
docker compose --profile ingest up --build bike_ingest

## 4. Connecting to the database in pgadmin

### Fill in the Connection Settings

#### General Tab

```
Name: London Bike Share DB
```

#### Connection Tab

| Field | Value |
|------|------|
| Host name/address | `postgres` |
| Port | `5432` |
| Maintenance database | `london_bike_share` |
| Username | `root` |
| Password | `root` |

#### Save

Click **Save**.


# Transformations:
Aggregation 1) : station-based aggregation
•	Which stations are most used
•	At what time of day demand peaks
•	Where to redistribute bikes
•	Which stations might need maintenance attention
Aggregation 2) : route demant
•	which routes are most popular
•	where bikes move most frequently
•	which station pairs may need redistribution planning

Raw table
london_bike_data
↓
Clean transformation
bike_trips_clean
↓
Aggregations
station_hourly_demand
route_daily_demand
top_routes
station_daily_demand


# Orchestration 
you should already have run: 
docker compose up --build postgres

after that run:
docker compose up --build airflow_init
docker compose up --build airflow_webserver airflow_sheduler

then you can open in your browser: http://localhost:8081/home
| Username | `admin` |
| Password | `admin` |


# Dataset proposals:
https://www.kaggle.com/datasets/kalacheva/london-bike-share-usage-dataset

https://tfl.gov.uk/info-for/open-data-users/our-open-data#on-this-page-5

https://data.stadt-zuerich.ch/dataset/vbz_fahrplandaten_gtfs
