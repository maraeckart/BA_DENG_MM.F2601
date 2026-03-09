import kagglehub
import pandas as pd
from sqlalchemy import create_engine, Engine
import click

def ingest_data(engine: Engine, chunksize: int, target_table: str):
    cache_path = kagglehub.dataset_download("kalacheva/london-bike-share-usage-dataset")
    dataset_path = cache_path + "/LondonBikeJourneyAug2023.csv"

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

    df_batches = pd.read_csv(dataset_path,
        dtype=dtypes,
        parse_dates=["Start date", "End date"],
        iterator=True,
        chunksize=chunksize,
    )

    first_chunk = next(df_batches)
    first_chunk.head(0).to_sql(
        name=target_table,
        con=engine,
        if_exists="replace"
    )

    print(f"Table {target_table} created")

    for batch in df_batches:
        batch.to_sql(
            name=target_table,
            con=engine,
            if_exists="append"
        )
        print(f"Inserted chunk: {len(batch)}")

    print(f'done ingesting to {target_table}')


@click.command()
@click.option('--pg-user', default='root', help='PostgreSQL username')
@click.option('--pg-pass', default='root', help='PostgreSQL password')
@click.option('--pg-host', default='localhost', help='PostgreSQL host')
@click.option('--pg-port', default='5432', help='PostgreSQL port')
@click.option('--pg-db', default='london_bike_share', help='PostgreSQL database name')
@click.option('--chunksize', default=100000, type=int, help='Chunk size for ingestion')
@click.option('--target-table', default='london_bike_data', help='Target table name')
def main(pg_user, pg_pass, pg_host, pg_port, pg_db, chunksize, target_table):
    engine: Engine = create_engine(f'postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}')

    ingest_data(engine, chunksize, target_table)


if __name__ == "__main__":
    main()
