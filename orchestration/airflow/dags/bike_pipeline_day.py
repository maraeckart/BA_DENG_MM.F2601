from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

PROJECT_ROOT = Path("/opt/airflow/project")
TRANSFORMATIONS_DIR = PROJECT_ROOT / "transformations"

with DAG(
    dag_id="bike_pipeline_day",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=True,
    tags=["bike", "pipeline", "midterm"],
) as dag:

    ingest_raw_data = BashOperator(
        task_id="ingest_raw_data",
        bash_command=(
            "python /opt/airflow/project/app/local_ingestion/pipeline.py "
            "--pg-user=root "
            "--pg-pass=root "
            "--pg-host=postgres "
            "--pg-port=5432 "
            "--run-date {{ ds }} "
        ),
    )

    create_bike_trips_clean = PostgresOperator(
        task_id="create_bike_trips_clean",
        postgres_conn_id="postgres_london_bike",
        sql=(TRANSFORMATIONS_DIR / "create_bike_trips_clean.sql").read_text(),
    )

    create_station_hourly_demand = PostgresOperator(
        task_id="create_station_hourly_demand",
        postgres_conn_id="postgres_london_bike",
        sql=(TRANSFORMATIONS_DIR / "create_station_hourly_demand.sql").read_text(),
    )

    create_route_daily_demand = PostgresOperator(
        task_id="create_route_daily_demand",
        postgres_conn_id="postgres_london_bike",
        sql=(TRANSFORMATIONS_DIR / "create_route_daily_demand.sql").read_text(),
    )

    ingest_raw_data >> create_bike_trips_clean >> create_station_hourly_demand >> create_route_daily_demand
