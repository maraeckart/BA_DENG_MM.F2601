import os
import kagglehub
from pathlib import Path
from google.cloud import storage
from pathlib import Path


BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
GCS_PREFIX = os.getenv("GCS_PREFIX", "raw/london_bike_share")


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
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(str(local_file_path))

    print(f"Uploaded {local_file_path} to gs://{bucket_name}/{destination_blob_name}")


def upload_raw_data_to_gcs() -> None:
    if not BUCKET_NAME:
        raise ValueError("Environment variable GCS_BUCKET_NAME is required.")

    csv_file = get_dataset_path()

    execution_date = get_execution_date()

    client = storage.Client()

    if execution_date:
        destination_blob_name = (
            f"{GCS_PREFIX}/execution_date={execution_date}/{csv_file.name}"
        )
    else:
        destination_blob_name = f"{GCS_PREFIX}/{csv_file.name}"

    upload_file_to_gcs(
        client=client,
        bucket_name=BUCKET_NAME,
        local_file_path=csv_file,
        destination_blob_name=destination_blob_name,
    )


if __name__ == "__main__":
    upload_raw_data_to_gcs()
