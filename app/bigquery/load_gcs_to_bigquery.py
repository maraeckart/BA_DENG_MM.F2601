import argparse
import os
import tempfile
from pathlib import Path

import pandas as pd
from google.cloud import storage
from google.cloud import bigquery

import re
from datetime import datetime

MIN_DATE = datetime(2023, 8, 1).date()
MAX_DATE = datetime(2023, 8, 31).date()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket-name", required=True)
    parser.add_argument("--gcs-prefix", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--table-id", default="bike_trips_clean")
    parser.add_argument("--run-date", required=True)
    return parser.parse_args()

def resolve_run_dates(bucket_name: str, gcs_prefix: str, run_date: str):
    if run_date != "all":
        run_dt = datetime.strptime(run_date, "%Y-%m-%d").date()

        if not (MIN_DATE <= run_dt <= MAX_DATE):
            raise ValueError(
                f"run_date must be between {MIN_DATE} and {MAX_DATE}, got {run_date}"
            )

        return [run_date]

    storage_client = storage.Client()

    blobs = storage_client.list_blobs(
        bucket_name,
        prefix=f"{gcs_prefix}/execution_date=",
    )

    available_dates = set()

    for blob in blobs:
        match = re.search(r"execution_date=(\d{4}-\d{2}-\d{2})/", blob.name)

        if match:
            date_value = match.group(1)
            date_obj = datetime.strptime(date_value, "%Y-%m-%d").date()

            if MIN_DATE <= date_obj <= MAX_DATE:
                available_dates.add(date_value)

    if not available_dates:
        raise FileNotFoundError(
            f"No available execution_date folders found in gs://{bucket_name}/{gcs_prefix}"
        )

    return sorted(available_dates)

def list_gcs_files(bucket_name: str, gcs_prefix: str, run_date: str):
    storage_client = storage.Client()
    prefix = f"{gcs_prefix}/execution_date={run_date}"

    blobs = list(storage_client.list_blobs(bucket_name, prefix=prefix))

    files = [
        blob.name
        for blob in blobs
        if blob.name.endswith(".csv")
    ]

    if not files:
        raise FileNotFoundError(
            f"No CSV files found in gs://{bucket_name}/{prefix}"
        )

    return files


def download_gcs_file(bucket_name: str, blob_name: str, local_path: str):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(local_path)


def transform_chunk(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(
        columns={
            "Number": "trip_id",
            "Start date": "start_datetime",
            "Start station number": "start_station_id",
            "Start station": "start_station_name",
            "End date": "end_datetime",
            "End station number": "end_station_id",
            "End station": "end_station_name",
            "Bike number": "bike_id",
            "Bike model": "bike_model",
            "Total duration": "duration_text",  
            "Total duration (ms)": "duration_ms",
        }
    )

    print("Columns after rename:", list(df.columns))

    required_columns = [
        "trip_id",
        "start_datetime",
        "end_datetime",
        "start_station_id",
        "end_station_id",
        "duration_ms",
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise KeyError(
            f"Missing columns after rename: {missing_columns}. "
            f"Available columns: {list(df.columns)}"
        )

    df["start_datetime"] = pd.to_datetime(df["start_datetime"], errors="coerce")
    df["end_datetime"] = pd.to_datetime(df["end_datetime"], errors="coerce")

    df["trip_date"] = df["start_datetime"].dt.date
    df["start_hour"] = df["start_datetime"].dt.hour

    df["duration_ms"] = pd.to_numeric(df["duration_ms"], errors="coerce")
    df["duration_minutes"] = df["duration_ms"] / 60000

    before = len(df)

    df = df.dropna(
        subset=[
            "trip_id",
            "trip_date",
            "start_datetime",
            "end_datetime",
            "start_station_id",
            "end_station_id",
            "duration_ms",
        ]
    )

    df = df[df["duration_ms"] > 0]

    after = len(df)
    print(f"Transformed rows: before={before}, after={after}")

    return df[
        [
            "trip_id",
            "trip_date",
            "start_hour",
            "start_datetime",
            "end_datetime",
            "start_station_id",
            "start_station_name",
            "end_station_id",
            "end_station_name",
            "bike_id",
            "bike_model",
            "duration_ms",
            "duration_minutes",
        ]
    ]


def create_table_if_needed(project_id: str, dataset_id: str, table_id: str):
    client = bigquery.Client(project=project_id)

    full_table_id = f"{project_id}.{dataset_id}.{table_id}"

    schema = [
        bigquery.SchemaField("trip_id", "STRING"),
        bigquery.SchemaField("trip_date", "DATE"),
        bigquery.SchemaField("start_hour", "INTEGER"),
        bigquery.SchemaField("start_datetime", "TIMESTAMP"),
        bigquery.SchemaField("end_datetime", "TIMESTAMP"),
        bigquery.SchemaField("start_station_id", "STRING"),
        bigquery.SchemaField("start_station_name", "STRING"),
        bigquery.SchemaField("end_station_id", "STRING"),
        bigquery.SchemaField("end_station_name", "STRING"),
        bigquery.SchemaField("bike_id", "STRING"),
        bigquery.SchemaField("bike_model", "STRING"),
        bigquery.SchemaField("duration_ms", "INTEGER"),
        bigquery.SchemaField("duration_minutes", "FLOAT"),
    ]

    table = bigquery.Table(full_table_id, schema=schema)

    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="trip_date",
    )

    table.clustering_fields = [
        "start_station_id",
        "end_station_id",
    ]

    client.create_table(table, exists_ok=True)

    print(f"Table ready: {full_table_id}")


def delete_existing_partition(project_id: str, dataset_id: str, table_id: str, run_date: str):
    client = bigquery.Client(project=project_id)

    query = f"""
    DELETE FROM `{project_id}.{dataset_id}.{table_id}`
    WHERE trip_date = DATE(@run_date)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("run_date", "STRING", run_date)
        ]
    )

    client.query(query, job_config=job_config).result()

    print(f"Deleted existing rows for {run_date}")


def load_csv_to_bigquery(
    csv_path: str,
    project_id: str,
    dataset_id: str,
    table_id: str,
):
    client = bigquery.Client(project=project_id)

    full_table_id = f"{project_id}.{dataset_id}.{table_id}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        autodetect=False,
    )

    with open(csv_path, "rb") as file_obj:
        load_job = client.load_table_from_file(
            file_obj,
            full_table_id,
            job_config=job_config,
        )

    load_job.result()

    print(f"Loaded transformed data into {full_table_id}")


def main():
    args = parse_args()

    create_table_if_needed(
        project_id=args.project_id,
        dataset_id=args.dataset_id,
        table_id=args.table_id,
    )

    run_dates = resolve_run_dates(
        bucket_name=args.bucket_name,
        gcs_prefix=args.gcs_prefix,
        run_date=args.run_date,
    )

    print(f"Processing run dates: {run_dates}")

    for current_run_date in run_dates:
        print(f"Starting BigQuery transformation for {current_run_date}")

        delete_existing_partition(
            project_id=args.project_id,
            dataset_id=args.dataset_id,
            table_id=args.table_id,
            run_date=current_run_date,
        )

        gcs_files = list_gcs_files(
            bucket_name=args.bucket_name,
            gcs_prefix=args.gcs_prefix,
            run_date=current_run_date,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            transformed_csv_path = Path(tmpdir) / f"bike_trips_clean_{current_run_date}.csv"

            wrote_header = False

            for index, blob_name in enumerate(gcs_files):
                local_raw_path = Path(tmpdir) / f"raw_{index}.csv"

                print(f"Downloading gs://{args.bucket_name}/{blob_name}")

                download_gcs_file(
                    bucket_name=args.bucket_name,
                    blob_name=blob_name,
                    local_path=str(local_raw_path),
                )

                for chunk in pd.read_csv(local_raw_path, chunksize=100000):
                    transformed = transform_chunk(chunk)

                    transformed.to_csv(
                        transformed_csv_path,
                        mode="a",
                        header=not wrote_header,
                        index=False,
                    )

                    wrote_header = True

            if not wrote_header:
                raise RuntimeError(
                    f"No transformed rows were produced for run_date={current_run_date}"
                )

            load_csv_to_bigquery(
                csv_path=str(transformed_csv_path),
                project_id=args.project_id,
                dataset_id=args.dataset_id,
                table_id=args.table_id,
            )


if __name__ == "__main__":
    main()