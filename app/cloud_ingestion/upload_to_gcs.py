import os
import kagglehub
from pathlib import Path
from google.cloud import storage


BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
GCS_PREFIX = os.getenv("GCS_PREFIX", "raw/london_bike_share")
BATCH_SIZE = int(os.getenv("INGESTION_BATCH_SIZE", "10000"))


def get_execution_date() -> str:
    """
    Returns the Airflow execution date if provided.
    Otherwise uploads the full dataset without date filtering.
    """
    return os.getenv("EXECUTION_DATE", "")

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

def upload_file_to_gcs(
    client: storage.Client,
    bucket_name: str,
    local_file_path: Path,
    destination_blob_name: str,
) -> None:
    """Upload one local file to Google Cloud Storage."""
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(str(local_file_path))

    print(f"Uploaded {local_file_path} to gs://{bucket_name}/{destination_blob_name}")


def upload_csv_to_gcs_in_batches(
    client: storage.Client,
    bucket_name: str,
    csv_file_path: Path,
    destination_prefix: str,
    batch_size: int,
) -> None:
    """
    Split a CSV file into row-based batches and upload each batch to GCS.

    Each uploaded object contains the original CSV header plus up to `batch_size`
    data rows. This keeps the pipeline batch-based while avoiding one large raw
    file upload.
    """
    if batch_size <= 0:
        raise ValueError("INGESTION_BATCH_SIZE must be greater than 0.")

    with csv_file_path.open("r", encoding="utf-8") as source_file:
        header = source_file.readline()
        if not header:
            raise ValueError(f"CSV file is empty: {csv_file_path}")

        batch_number = 1
        current_batch_rows = []

        for row in source_file:
            current_batch_rows.append(row)

            if len(current_batch_rows) >= batch_size:
                batch_file_path = write_batch_file(
                    source_file_path=csv_file_path,
                    header=header,
                    rows=current_batch_rows,
                    batch_number=batch_number,
                )
                upload_file_to_gcs(
                    client=client,
                    bucket_name=bucket_name,
                    local_file_path=batch_file_path,
                    destination_blob_name=(
                        f"{destination_prefix}/batch_{batch_number:05d}.csv"
                    ),
                )
                batch_file_path.unlink()
                batch_number += 1
                current_batch_rows = []

        if current_batch_rows:
            batch_file_path = write_batch_file(
                source_file_path=csv_file_path,
                header=header,
                rows=current_batch_rows,
                batch_number=batch_number,
            )
            upload_file_to_gcs(
                client=client,
                bucket_name=bucket_name,
                local_file_path=batch_file_path,
                destination_blob_name=f"{destination_prefix}/batch_{batch_number:05d}.csv",
            )
            batch_file_path.unlink()


def write_batch_file(
    source_file_path: Path,
    header: str,
    rows: list[str],
    batch_number: int,
) -> Path:
    """Write one temporary CSV batch file and return its path."""
    batch_file_path = source_file_path.with_name(
        f"{source_file_path.stem}_batch_{batch_number:05d}{source_file_path.suffix}"
    )

    with batch_file_path.open("w", encoding="utf-8") as batch_file:
        batch_file.write(header)
        batch_file.writelines(rows)

    return batch_file_path


def upload_raw_data_to_gcs() -> None:
    if not BUCKET_NAME:
        raise ValueError("Environment variable GCS_BUCKET_NAME is required.")

    csv_file = get_dataset_path()

    execution_date = get_execution_date()

    client = storage.Client()

    if execution_date:
        destination_prefix = f"{GCS_PREFIX}/execution_date={execution_date}"
    else:
        destination_prefix = GCS_PREFIX

    upload_csv_to_gcs_in_batches(
        client=client,
        bucket_name=BUCKET_NAME,
        csv_file_path=csv_file,
        destination_prefix=destination_prefix,
        batch_size=BATCH_SIZE,
    )


if __name__ == "__main__":
    upload_raw_data_to_gcs()
