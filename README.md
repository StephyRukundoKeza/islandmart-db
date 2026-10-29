# IslandMart DB
IslandMart is a fictional goods shop in Mauritius, so this project was built to practice using Docker to run a database and connect multiple database GUIs to it. In this case, we have pgAdmin and DBeaver, both connected to one PostgreSQL database. It also loads cleaned data in the database using one of the 3 pipeline design types, which is ETL.

Next, I've been able to use a mock API to pull dummy store entries, so as to see practically how to fetch the data page by page (pagination) and save it as JSON files.

## Stack
Postgres 17 and pgAdmin in Docker Compose, Python (pandas + SQLAlchemy + requests + pyarrow + PyYAML), DuckDB, uv.

## Pipeline design: ETL
The reason why I used ETL, instead of Zero-ETL or ELT, was because I was not planning in any way to use the data which I omitted. So, cleaning the data and having it in my database clean seems more convenient for me.

## How to run
1. Copy `.env.example` to `.env` and fill in the values
2. `docker compose up -d`
3. `uv sync`
4. `uv run python/load_products.py`

## Cleaning results
59 rows read, 54 loaded: 1 row without an id dropped, 4 duplicates removed,
1 conflicting product_id flagged for review.

## What confused me
- The port 5432 clashed with my Windows PostgreSQL 18, and hence I had to change my port to another port that was not in use.
- Before, I didn't understand why pgAdmin uses `db`, but DBeaver uses `localhost`, but I later
understood that it's because DBeaver is the one that is installed on the PC, while pgAdmin runs inside its own Docker container, so it reaches Postgres by the service name `db`.

## Supplier feed (API extract)

A new file called `fetch_supplier_products.py` was created to help in fetching, and creating the JSON files to keep the data in segments.

I have added a retry function to ensure that if an error code which is retryable happens, instead of crashing it tries again, until it either succeeds or reaches the maximum number of tries. If the error code is not retryable (like 404), it stops straight away.

How to run: `uv run python/fetch_supplier_products.py`

## What I learned in SQL

I used an SQL Lab artifact, which allowed me to learn SQL for Data Engineers. I practiced using window functions like ROW_NUMBER, RANK vs. DENSE_RANK, etc. 

I learned the necessity of using upserts; they are needed in case a person needs to update information in a row, or add new data if it doesn't exist, while ensuring no duplicates are made mistakenly. 

I also learned the usage of indexes. Indexes allow a system to make queries with a lower execution time because, when there is no index, the computer is forced to do a sequential scan, which is a complete scan of the rows present.

## CSV vs Parquet

`compare_formats.py` exports the sales table from Postgres and saves the same data as CSV and as Parquet, then compares file size, read speed and data types.

| Format | Size |
|---|---|
| CSV | 5.54 MB |
| Parquet (snappy) | 1.68 MB (3.3x smaller) |
| Parquet (zstd) | 1.06 MB |

Parquet also kept the column types (like dates), while the CSV came back with dates as plain text. Parquet can also read only the columns I need, which makes it faster.

How to run: `uv run python/compare_formats.py`

## Analytics with DuckDB

`duckdb_analytics.py` uses DuckDB to run SQL directly on the Parquet, CSV and JSON files, without a database server. It joins sales and products, ranks categories by revenue with a window function, reads all the supplier JSON pages at once, and saves a monthly revenue table as a new Parquet file.

I asked the same question (revenue per product) three ways:

| Tool | Time |
|---|---|
| DuckDB on Parquet | 4.8 ms |
| pandas | 14.7 ms |
| Postgres | 25.7 ms |

DuckDB is made for analytics (OLAP), while Postgres is made for an app's day-to-day reads and writes (OLTP), so I'll keep using both for different jobs.

How to run: `uv run python/duckdb_analytics.py` (run `compare_formats.py` first, since it creates the Parquet file)

## Star schema

I designed a star schema for IslandMart's sales: one fact table (FACT_SALES) and four dimensions (date, product, store and customer, where customer keeps its history with SCD Type 2). See [docs/star_schema.md](docs/star_schema.md).

## ETL vs ELT (same supplier data, loaded twice)

I loaded the same 194 supplier products two ways:
- `python/etl_supplier_products.py`: cleaned in Python with pandas, following the rules in `contracts/supplier_products.yaml`, then loaded only the clean table.
- `python/elt_supplier_products.py`: loaded every product as raw JSON (JSONB) into `raw.supplier_products`, then cleaned it with SQL in `sql/elt_supplier_products.sql`.

Both gave 194 rows, and comparing them with `EXCEPT` found 0 differences.

| | ETL | ELT |
|---|---|---|
| Time (194 rows) | 0.22 s | 0.14 s |
| Where the cleaning lives | Python + data contract | SQL |
| Raw data kept? | No (16 of 27 columns dropped) | Yes, every field |
| Re-clean without calling the API? | No | Yes, rerun the SQL |
| Privacy | Sensitive fields never stored | Everything is stored first |

What I noticed:
- The ELT pipeline looked faster than the ETL, but I have done some research and found that ETL can be faster when one only needs a small part of the data, because less data is moved and stored. With only 194 rows, most of the time here is fixed overhead.

When I'd pick each one:
- ETL when the data has sensitive fields (like phone numbers) that should never be stored, or when I know exactly which columns I need.
- ELT when I want to keep everything and might want to clean it differently later.

How to run: `uv run python/etl_supplier_products.py` and `uv run python/elt_supplier_products.py`

## Incremental loader (watermark)

`python/incremental_supplier_products.py` only loads products whose `updatedAt` is newer than the last successful run. The bookmark (watermark) is saved in the `etl_watermarks` table, and it only moves forward after the load succeeds, in the same transaction. Loading uses upserts, so re-runs and backfills never create duplicates.

The table and the upsert are built from `contracts/supplier_products.yaml`, so adding a column to the contract is enough; the Python code doesn't change.

| Test | Result |
|---|---|
| First run | 194 rows loaded |
| Second run | 0 rows (nothing new) |
| One product changed | 1 row upserted, still 194 rows |
| Backfill from 2026-08-01 | rows reloaded, 0 duplicates, watermark not moved back |

How to run:
- `uv run python/incremental_supplier_products.py`
- `uv run python/incremental_supplier_products.py --since 2026-08-01` (backfill)
- `uv run python/incremental_supplier_products.py --show-sql` (see the SQL built from the contract)