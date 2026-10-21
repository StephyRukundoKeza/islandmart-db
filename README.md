# IslandMart DB
IslandMart is a fictional goods shop in Mauritius, so this project was built to practice using Docker to run a database and connect multiple database GUIs to it. In this case, we have pgAdmin and DBeaver, both connected to one PostgreSQL database. It also loads cleaned data in the database using one of the 3 pipeline design types, which is ETL.

Next, I've been able to use a mock API to pull dummy store entries, so as to see practically how to fetch the data page by page (pagination) and save it as JSON files.

## Stack
Postgres 17 and pgAdmin in Docker Compose, Python (pandas + SQLAlchemy + requests), uv.

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
