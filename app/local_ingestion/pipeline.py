from datetime import datetime
from pathlib import Path

import click
import kagglehub
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.types import BigInteger, DateTime, Text

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


def filter_batch_for_run_date(batch: pd.DataFrame, run_date: str) -> pd.DataFrame:
    """
    Filter a batch of data for a specific run date.

    This enables batch-based ingestion by only processing rows
    corresponding to the Airflow execution date.

    Args:
        batch (pd.DataFrame): A chunk of the dataset.
        run_date (str): Target date in format YYYY-MM-DD.

    Returns:
        pd.DataFrame: Filtered DataFrame containing only rows for the given date.
    """
    target_date = pd.to_datetime(run_date).date()
    filtered_batch = batch[batch["Start date"].dt.date == target_date].copy()
    return filtered_batch

def ingest_data(engine: Engine, chunksize: int, target_table: str, run_date: str):
    """
    Ingest data into PostgreSQL in a batch-oriented manner.

    The dataset is processed in chunks to ensure scalability and memory efficiency.
    Each batch is filtered by the provided run_date before being written to the database.

    Args:
        engine (Engine): SQLAlchemy database engine.
        chunksize (int): Number of rows per batch.
        target_table (str): Destination table in PostgreSQL.
        run_date (str): Date used to filter the dataset (YYYY-MM-DD).
    """
    dataset_path = get_dataset_path()

    dtypes = {
        "Number": "int64",
        "Start Station Number": "int64",
        "Start Station": "string",
        "End Station Number": "int64",
        "End Station": "string",
        "Bike Number": "string",
        "Bike Model": "string",
        "Total Duration": "string",
        "Total Duration (ms)": "int64"
    }

    sql_dtypes = {
        "Number": BigInteger(),
        "Start date": DateTime(),
        "End date": DateTime(),
        "Start Station Number": BigInteger(),
        "Start Station": Text(),
        "End Station Number": BigInteger(),
        "End Station": Text(),
        "Bike Number": Text(),
        "Bike Model": Text(),
        "Total Duration": Text(),
        "Total Duration (ms)": BigInteger(),
    }

    df_batches = pd.read_csv(str(dataset_path),
        dtype=dtypes,
        parse_dates=["Start date", "End date"],
        iterator=True,
        chunksize=chunksize,
    )
    table_initialized = False
    inserted_rows = 0

    for batch in df_batches:
        filtered_batch = filter_batch_for_run_date(batch, run_date)

        if filtered_batch.empty:
            continue

        if not table_initialized:
            filtered_batch.head(0).to_sql(
                name=target_table,
                con=engine,
                if_exists="append",
                index=False,
                dtype=sql_dtypes,
            )
            print(f"Table {target_table} created for run_date={run_date}")
            table_initialized = True

        filtered_batch.to_sql(
            name=target_table,
            con=engine,
            if_exists="append",
            index=False,
            dtype=sql_dtypes,
        )
        inserted_rows += len(filtered_batch)
        print(f"Inserted {len(filtered_batch)} rows for run_date={run_date}")

    if not table_initialized:
        empty_df = pd.read_csv(
            str(dataset_path),
            dtype=dtypes,
            parse_dates=["Start date", "End date"],
            nrows=0,
        )
        empty_df.to_sql(
            name=target_table,
            con=engine,
            if_exists="replace",
            index=False,
            dtype=sql_dtypes,
        )
        print(f"No rows found for run_date={run_date}. Created empty table {target_table}")
    else:
        print(f"done ingesting {inserted_rows} rows to {target_table} for run_date={run_date}")


@click.command()
@click.option('--pg-user', default='root', help='PostgreSQL username')
@click.option('--pg-pass', default='root', help='PostgreSQL password')
@click.option('--pg-host', default='localhost', help='PostgreSQL host')
@click.option('--pg-port', default='5432', help='PostgreSQL port')
@click.option('--pg-db', default='london_bike_share', help='PostgreSQL database name')
@click.option('--chunksize', default=100000, type=int, help='Chunk size for ingestion')
@click.option('--target-table', default='london_bike_data', help='Target table name')
@click.option('--run-date', default="2023-08-01", show_default='current UTC date', help='Airflow logical run date in YYYY-MM-DD format')
def main(pg_user, pg_pass, pg_host, pg_port, pg_db, chunksize, target_table, run_date):
    engine: Engine = create_engine(f'postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}')

    print(f"Starting ingestion for run_date={run_date}")
    try:
        run_dt = datetime.strptime(run_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise click.BadParameter("run-date must be in YYYY-MM-DD format") from exc

    # Restrict ingestion to dataset availability range
    min_date = datetime(2023, 8, 1).date()
    max_date = datetime(2023, 8, 31).date()

    if not (min_date <= run_dt <= max_date):
        raise click.BadParameter(
            f"run-date must be between {min_date} and {max_date}, got {run_date}"
        )

    ingest_data(engine, chunksize, target_table, run_date)


if __name__ == "__main__":
    main()
