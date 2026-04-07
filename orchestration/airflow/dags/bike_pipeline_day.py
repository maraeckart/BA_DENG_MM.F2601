from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator

PROJECT_ROOT = Path("/opt/airflow/project")
TRANSFORMATIONS_DIR = PROJECT_ROOT / "transformations"

with DAG(
    dag_id="bike_pipeline_day",
    start_date=datetime(2023, 8, 1),
    schedule="@daily",
    catchup=False,
    tags=["bike", "pipeline", "midterm"],
    description="Valid run_date range: 2023-08-01 to 2023-09-01",
) as dag:

    ingest_raw_data = BashOperator(
        task_id="ingest_raw_data",
        bash_command=(
            "echo 'Valid run_date range: 2023-08-01 to 2023-09-01'; "
            "echo 'Running for date: {{ ds }}'; "
            "python /opt/airflow/project/app/local_ingestion/pipeline.py "
            "--pg-user=root "
            "--pg-pass=root "
            "--pg-host=postgres "
            "--pg-port=5432 "
            "--run-date {{ ds }} "
        ),
    )

    create_bike_trips_clean = SQLExecuteQueryOperator(
        task_id="create_bike_trips_clean",
        conn_id="postgres_london_bike",
        sql=(TRANSFORMATIONS_DIR / "create_bike_trips_clean.sql").read_text(),
    )

    create_station_hourly_demand = SQLExecuteQueryOperator(
        task_id="create_station_hourly_demand",
        conn_id="postgres_london_bike",
        sql=(TRANSFORMATIONS_DIR / "create_station_hourly_demand.sql").read_text(),
    )

    create_route_daily_demand = SQLExecuteQueryOperator(
        task_id="create_route_daily_demand",
        conn_id="postgres_london_bike",
        sql=(TRANSFORMATIONS_DIR / "create_route_daily_demand.sql").read_text(),
    )

    ingest_raw_data >> create_bike_trips_clean >> create_station_hourly_demand >> create_route_daily_demand
