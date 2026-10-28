# IslandMart DB
IslandMart is a fictional goods shop in Mauritius, so this project was built to practice using Docker to run a database and connect multiple database GUIs to it. In this case, we have pgAdmin and DBeaver, both connected to one PostgreSQL database. It also loads cleaned data in the database using one of the 3 pipeline design types, which is ETL.

Next, I've been able to use a mock API to pull dummy store entries, so as to see practically how to fetch the data page by page (pagination) and save it as JSON files.

## Stack
Postgres 17 and pgAdmin in Docker Compose, Python (pandas + SQLAlchemy + requests + pyarrow), DuckDB, uv.

## Pipeline design: ETL
The reason why I used ETL, instead of Zero-ETL or ELT, was because I was not planning in any way to use the data which I omitted. So, cleaning the data and having it in my database clean seems more convenient for me.

## How to run
1. Copy `.env.example` to `.env` and fill in the values
2. `docker compose up -d`
3. `uv sync`
4. `uv run load_products.py`

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

How to run: `uv run fetch_supplier_products.py`

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

How to run: `uv run compare_formats.py`

## Analytics with DuckDB

`duckdb_analytics.py` uses DuckDB to run SQL directly on the Parquet, CSV and JSON files, without a database server. It joins sales and products, ranks categories by revenue with a window function, reads all the supplier JSON pages at once, and saves a monthly revenue table as a new Parquet file.

I asked the same question (revenue per product) three ways:

| Tool | Time |
|---|---|
| DuckDB on Parquet | 4.8 ms |
| pandas | 14.7 ms |
| Postgres | 25.7 ms |

DuckDB is made for analytics (OLAP), while Postgres is made for an app's day-to-day reads and writes (OLTP), so I'll keep using both for different jobs.

How to run: `uv run duckdb_analytics.py` (run `compare_formats.py` first, since it creates the Parquet file)
