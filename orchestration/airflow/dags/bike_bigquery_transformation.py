import os
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator


print("DAG_VERSION_MARKER: BIGQUERY_DAG_2026_05_19_FINAL")


default_args = {
    "owner": "airflow",
    "retries": 1,
}


with DAG(
    dag_id="bike_bigquery_transformation",
    default_args=default_args,
    description="Transform London Bike Share data from GCS and load it into BigQuery",
    start_date=datetime(2023, 8, 1),
    schedule="@daily",
    catchup=False,
    tags=["london-bike-share", "gcs", "bigquery", "warehouse"],
) as dag:

    load_clean_data_to_bigquery = BashOperator(
        task_id="load_clean_data_to_bigquery",
        bash_command=(
            "echo 'Starting BigQuery transformation DAG' && "
            "echo GCS_BUCKET_NAME=$GCS_BUCKET_NAME && "
            "echo GCP_PROJECT_ID=$GCP_PROJECT_ID && "
            "echo BIGQUERY_DATASET_ID=$BIGQUERY_DATASET_ID && "
            "echo AIRFLOW_DS={{ ds }} && "
            "echo RUN_DATE={{ ds if '2023-08-01' <= ds <= '2023-08-31' else 'all' }} && "
            "python /opt/airflow/project/app/bigquery/load_gcs_to_bigquery.py "
            "--bucket-name $GCS_BUCKET_NAME "
            "--gcs-prefix raw/london_bike_share "
            "--project-id $GCP_PROJECT_ID "
            "--dataset-id $BIGQUERY_DATASET_ID "
            "--table-id bike_trips_clean "
            "--run-date {{ ds if '2023-08-01' <= ds <= '2023-08-31' else 'all' }}"
        ),
        env={
            "GOOGLE_APPLICATION_CREDENTIALS": "/opt/airflow/secrets/gcp_credentials.json",
            "GCS_BUCKET_NAME": os.environ.get("GCS_BUCKET_NAME", ""),
            "GCP_PROJECT_ID": os.environ.get("GCP_PROJECT_ID", ""),
            "BIGQUERY_DATASET_ID": os.environ.get("BIGQUERY_DATASET_ID", ""),
        },
        append_env=True,
    )