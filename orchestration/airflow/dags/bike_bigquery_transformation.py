import os
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    "owner": "airflow",
    "retries": 1,
}


with DAG(
    dag_id="bike_bigquery_transformation",
    default_args=default_args,
    description="Transform London Bike Share data from GCS and load it into BigQuery",
    start_date=datetime(2023, 8, 1),
    end_date=datetime(2023, 8, 31),
    schedule="@daily",
    catchup=True,
    tags=["london-bike-share", "gcs", "bigquery", "warehouse"],
) as dag:

    load_clean_data_to_bigquery = BashOperator(
        task_id="load_clean_data_to_bigquery",
        bash_command=(
            "echo GCS_BUCKET_NAME=$GCS_BUCKET_NAME && "
            "echo GCP_PROJECT_ID=$GCP_PROJECT_ID && "
            "echo BIGQUERY_DATASET_ID=$BIGQUERY_DATASET_ID && "
            "python /opt/airflow/project/app/bigquery/load_gcs_to_bigquery.py "
            "--bucket-name $GCS_BUCKET_NAME "
            "--gcs-prefix raw/london_bike_share "
            "--project-id $GCP_PROJECT_ID "
            "--dataset-id $BIGQUERY_DATASET_ID "
            "--table-id bike_trips_clean "
            "--run-date {{ ds }}"
        ),
        env={
            "GOOGLE_APPLICATION_CREDENTIALS": "/opt/airflow/secrets/gcp_credentials.json",
            "GCS_BUCKET_NAME": "deng-bike-data-lake",
            "GCP_PROJECT_ID": "custom-blade-489312-g4",
            "BIGQUERY_DATASET_ID": "bike_data_warehouse",
        },
    )