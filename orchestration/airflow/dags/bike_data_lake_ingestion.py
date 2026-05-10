import os
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    "owner": "airflow",
    "retries": 1,
}


with DAG(
    dag_id="bike_data_lake_ingestion",
    default_args=default_args,
    description="Upload raw London Bike Share data to Google Cloud Storage data lake",
    start_date=datetime(2023, 8, 1),
    end_date=datetime(2023, 8, 31),
    schedule="@daily",
    catchup=True,
    tags=["london-bike-share", "gcs", "data-lake"],
) as dag:

    upload_raw_data_to_gcs = BashOperator(
        task_id="upload_raw_data_to_gcs",
        bash_command="""
        python /opt/airflow/project/app/cloud_ingestion/upload_to_gcs.py
        """,
        env={
            "GOOGLE_APPLICATION_CREDENTIALS": "/opt/airflow/secrets/gcp_credentials.json",
            "GCS_BUCKET_NAME": os.environ["GCS_BUCKET_NAME"],
            "GCS_PREFIX": "raw/london_bike_share",
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
