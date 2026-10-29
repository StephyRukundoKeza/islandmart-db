"""dlt pipeline: DummyJSON products API -> DuckDB, loading only products that changed since the last run."""
import os
from pathlib import Path

import dlt
from dlt.sources.helpers import requests   # like requests, but with automatic retries
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("API_BASE_URL", "https://dummyjson.com")
PAGE_SIZE = int(os.getenv("PAGE_SIZE", 30))
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "warehouse/islandmart.duckdb")


@dlt.resource(name="products", primary_key="id", write_disposition="merge")
def products(
    updated_at=dlt.sources.incremental("meta.updatedAt", initial_value="1970-01-01T00:00:00Z"),
):
    """Every product, page by page. dlt keeps only the ones newer than the saved cursor."""
    skip, total = 0, None
    while total is None or skip < total:
        response = requests.get(f"{BASE_URL}/products", params={"limit": PAGE_SIZE, "skip": skip})
        response.raise_for_status()
        page = response.json()
        total = page["total"]
        if not page["products"]:
            break
        yield page["products"]
        skip += PAGE_SIZE


@dlt.source(name="dummyjson")
def dummyjson_source():
    return products


if __name__ == "__main__":
    Path(DUCKDB_PATH).parent.mkdir(parents=True, exist_ok=True)
    pipeline = dlt.pipeline(
        pipeline_name="dummyjson",
        destination=dlt.destinations.duckdb(DUCKDB_PATH),
        dataset_name="raw_dummyjson",
    )
    load_info = pipeline.run(dummyjson_source())
    print(load_info)

    normalize = pipeline.last_trace.last_normalize_info
    print("Rows loaded per table:", normalize.row_counts if normalize else {})