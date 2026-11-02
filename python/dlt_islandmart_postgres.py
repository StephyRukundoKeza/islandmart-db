"""dlt pipeline: IslandMart's Postgres app database -> DuckDB raw_islandmart (ELT, raw and uncleaned)."""

import os
import argparse
from pathlib import Path

import dlt
from dlt.sources.sql_database import sql_table
from dotenv import load_dotenv

load_dotenv()
PG_URL = (
    f"postgresql+psycopg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('POSTGRES_DB')}"
)
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "warehouse/islandmart.duckdb")


@dlt.source(name="islandmart")
def islandmart_source():
    # Small table with a known id conflict: reload it fully each run, clean it in dbt
    products = sql_table(credentials=PG_URL, table="products")
    products.apply_hints(write_disposition="replace")

    # Customers change over time: only rows updated since the last run, upserted on customer_id
    customers = sql_table(
        credentials=PG_URL, table="customers", incremental=dlt.sources.incremental("updated_at")
    )
    customers.apply_hints(primary_key="customer_id", write_disposition="merge")

    # Sales are never edited: only new sale_ids, appended
    sales = sql_table(credentials=PG_URL, table="sales", incremental=dlt.sources.incremental("sale_id"))
    sales.apply_hints(write_disposition="append")

    return products, customers, sales

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh", action="store_true",
         help="Drop the raw tables and bookmarks, then reload everything from Postgres",
    )
    args = parser.parse_args()

    Path(DUCKDB_PATH).parent.mkdir(parents=True, exist_ok=True)
    pipeline = dlt.pipeline(
        pipeline_name="islandmart_postgres",
        destination=dlt.destinations.duckdb(DUCKDB_PATH),
        dataset_name="raw_islandmart",
       )
    print(pipeline.run(islandmart_source(), refresh="drop_sources" if args.refresh else None))
    normalize = pipeline.last_trace.last_normalize_info
    print("Rows loaded per table:", normalize.row_counts if normalize else {})