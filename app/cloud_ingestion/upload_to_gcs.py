import os
from datetime import datetime
from pathlib import Path

import click
import kagglehub
import pandas as pd
from google.cloud import storage

MIN_DATE = datetime(2023, 8, 1).date()
MAX_DATE = datetime(2023, 8, 31).date()


def get_dataset_path() -> Path:
    """
    Retrieve the dataset file path.

    This function first checks whether the dataset already exists locally.
    If not, it downloads the dataset from Kaggle and returns the file path.

    Returns:
        Path: Local path to the dataset CSV file.

    Raises:
        FileNotFoundError: If the dataset cannot be found after download.
    """
    dataset_file = "LondonBikeJourneyAug2023.csv"
    local_data_path = Path("/opt/airflow/project/data") / dataset_file

    if local_data_path.exists():
        print(f"Using existing local dataset at {local_data_path}")
        return local_data_path

    print("Local dataset not found. Downloading dataset from Kaggle...")
    cache_path = Path(kagglehub.dataset_download("kalacheva/london-bike-share-usage-dataset"))
    dataset_path = cache_path / dataset_file

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Dataset file not found after Kaggle download: {dataset_path}"
        )

    return dataset_path

def validate_run_date(run_date: str) -> None:
    """Validate that the run date is available in the source dataset."""
    try:
        run_dt = datetime.strptime(run_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("EXECUTION_DATE must be in YYYY-MM-DD format.") from exc

    if not (MIN_DATE <= run_dt <= MAX_DATE):
        raise ValueError(
            f"EXECUTION_DATE must be between {MIN_DATE} and {MAX_DATE}, got {run_date}"
        )


def filter_batch_for_run_date(batch: pd.DataFrame, run_date: str) -> pd.DataFrame:
    """
    Filter a CSV batch for the Airflow logical run date.

    This mirrors the local PostgreSQL ingestion pipeline and ensures each cloud
    DAG run only uploads data for its own execution date.
    """
    target_date = pd.to_datetime(run_date).date()
    filtered_batch = batch[batch["Start date"].dt.date == target_date].copy()
    return filtered_batch


def upload_dataframe_to_gcs(
    client: storage.Client,
    bucket_name: str,
    batch: pd.DataFrame,
    destination_blob_name: str,
) -> None:
    """Upload one DataFrame batch to Google Cloud Storage as CSV."""
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    csv_data = batch.to_csv(index=False)
    blob.upload_from_string(csv_data, content_type="text/csv")

    print(f"Uploaded batch to gs://{bucket_name}/{destination_blob_name}")

def upload_filtered_csv_to_gcs_in_batches(
    client: storage.Client,
    bucket_name: str,
    csv_file_path: Path,
    destination_prefix: str,
    chunksize: int,
    output_batch_size: int,
    run_date: str,
) -> None:
    """
    Read the source CSV in chunks, filter by run date, and upload CSV batches to GCS.

    This follows the same batch-oriented pattern as the local ingestion pipeline:
    read a source chunk, filter rows for the logical run date, and persist only
    the matching rows for that run.
    """
    if chunksize <= 0:
        raise ValueError("INGESTION_CHUNKSIZE must be greater than 0.")
    if output_batch_size <= 0:
        raise ValueError("INGESTION_OUTPUT_BATCH_SIZE must be greater than 0.")

    dtypes = {
        "Number": "int64",
        "Start Station Number": "int64",
        "Start Station": "string",
        "End Station Number": "int64",
        "End Station": "string",
        "Bike Number": "string",
        "Bike Model": "string",
        "Total Duration": "string",
        "Total Duration (ms)": "int64",
    }

    df_batches = pd.read_csv(
        str(csv_file_path),
        dtype=dtypes,
        parse_dates=["Start date", "End date"],
        iterator=True,
        chunksize=chunksize,
    )

    uploaded_rows = 0
    batch_number = 1
    pending_rows = pd.DataFrame()

    for source_batch in df_batches:
        filtered_batch = filter_batch_for_run_date(source_batch, run_date)

        if filtered_batch.empty:
            continue

        pending_rows = pd.concat([pending_rows, filtered_batch], ignore_index=True)

        while len(pending_rows) >= output_batch_size:
            output_batch = pending_rows.iloc[:output_batch_size].copy()
            pending_rows = pending_rows.iloc[output_batch_size:].copy()

            upload_dataframe_to_gcs(
                client=client,
                bucket_name=bucket_name,
                batch=output_batch,
                destination_blob_name=(
                    f"{destination_prefix}/batch_{batch_number:05d}.csv"
                ),
            )
            uploaded_rows += len(output_batch)
            batch_number += 1

    if not pending_rows.empty:
        upload_dataframe_to_gcs(
            client=client,
            bucket_name=bucket_name,
            batch=pending_rows,
            destination_blob_name=f"{destination_prefix}/batch_{batch_number:05d}.csv",
        )
        uploaded_rows += len(pending_rows)

    print(f"Uploaded {uploaded_rows} rows to GCS for run_date={run_date}")



@click.command()
@click.option(
    "--bucket-name",
    required=True,
    help="Google Cloud Storage bucket name for the raw data lake.",
)
@click.option(
    "--gcs-prefix",
    default="raw/london_bike_share",
    show_default=True,
    help="GCS prefix where raw batches are uploaded.",
)
@click.option(
    "--chunksize",
    default=100000,
    type=int,
    show_default=True,
    help="Number of source CSV rows to read per pandas chunk.",
)
@click.option(
    "--output-batch-size",
    default=10000,
    type=int,
    show_default=True,
    help="Maximum number of filtered rows per uploaded CSV file.",
)
@click.option(
    "--run-date",
    required=True,
    help="Airflow logical run date in YYYY-MM-DD format.",
)
def upload_raw_data_to_gcs(
    bucket_name: str,
    gcs_prefix: str,
    chunksize: int,
    output_batch_size: int,
    run_date: str,
) -> None:
    validate_run_date(run_date)

    csv_file = get_dataset_path()
    client = storage.Client()
    destination_prefix = f"{gcs_prefix}/execution_date={run_date}"

    print(f"Starting cloud ingestion for run_date={run_date}")
    upload_filtered_csv_to_gcs_in_batches(
        client=client,
        bucket_name=bucket_name,
        csv_file_path=csv_file,
        destination_prefix=destination_prefix,
        chunksize=chunksize,
        output_batch_size=output_batch_size,
        run_date=run_date,
    )


if __name__ == "__main__":
    upload_raw_data_to_gcs()
