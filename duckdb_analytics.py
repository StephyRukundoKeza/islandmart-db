"""Run analytics on IslandMart's files (Parquet, CSV, JSON) with DuckDB, no database server needed."""
import os
import time

import duckdb
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

SALES = "data/formats/sales.parquet"

# Starts DuckDB inside this Python process (in memory, nothing to install or run)
con = duckdb.connect()

# Query a Parquet file directly, as if it were a table
print("--- 1. Query a Parquet file ---")
print(con.sql(f"""
    SELECT COUNT(*)                   AS sales,
           SUM(quantity * unit_price) AS revenue,
           MIN(sale_date)             AS first_day,
           MAX(sale_date)             AS last_day
    FROM '{SALES}'
"""))

# Look at the schema DuckDB read from the Parquet file
print("--- 2. Column types stored in the Parquet file ---")
print(con.sql(f"DESCRIBE SELECT * FROM '{SALES}'"))

# Query a CSV directly (your messy products.csv): what types does DuckDB guess?
print("--- 3. Column types DuckDB guessed from the messy CSV ---")
print(con.sql("DESCRIBE SELECT * FROM 'data/products.csv'"))

# Export the CLEAN products table from Postgres to Parquet, so we can join it
load_dotenv()
engine = create_engine(
    f"postgresql+psycopg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('POSTGRES_DB')}"
)
products = pd.read_sql(
    "SELECT DISTINCT ON (product_id) product_id, name, category FROM products ORDER BY product_id, name",
    engine,
)
products.to_parquet("data/formats/products.parquet", index=False)

# Analytics
print("--- 4. Revenue by category, with each category's share ---")
print(con.sql(f"""
    WITH category_revenue AS (
        SELECT p.category,
               SUM(s.quantity * s.unit_price) AS revenue
        FROM '{SALES}' s
        JOIN 'data/formats/products.parquet' p USING (product_id)
        GROUP BY p.category
    )
    SELECT category,
           revenue,
           ROUND(100 * revenue / SUM(revenue) OVER (), 1) AS pct_of_total,
           RANK() OVER (ORDER BY revenue DESC)           AS rank
    FROM category_revenue
    ORDER BY rank
"""))

# Query JSON files directly: all supplier pages at once, with a wildcard
print("--- 5. Supplier catalog (JSON pages) by category ---")
print(con.sql("""
    WITH items AS (
        SELECT UNNEST(products) AS p
        FROM read_json_auto('data/raw/supplier_products/*/page_*.json')
    )
    SELECT p.category,
           COUNT(*)               AS products,
           ROUND(AVG(p.price), 2) AS avg_price,
           SUM(p.stock)           AS total_stock
    FROM items
    GROUP BY p.category
    ORDER BY products DESC
"""))

# Save a result as a new Parquet file 
con.sql(f"""
    COPY (
        SELECT DATE_TRUNC('month', sale_date) AS month,
               SUM(quantity * unit_price)     AS revenue
        FROM '{SALES}'
        GROUP BY 1
        ORDER BY 1
    ) TO 'data/formats/monthly_revenue.parquet' (FORMAT parquet)
""")
print("--- 6. Saved monthly_revenue.parquet ---")
print(con.sql("SELECT * FROM 'data/formats/monthly_revenue.parquet'"))

# Speed: Among postgres, pandas, and DuckDB, which answers fastest? (DuckDB is in-process, Postgres is over the network)
print("--- 7. Revenue per product: who answers fastest? ---")


def time_it(label, func, repeats=5):
    best = float("inf")
    for _ in range(repeats):
        start = time.perf_counter()
        func()
        best = min(best, time.perf_counter() - start)
    print(f"  {label:<36} {best * 1000:8.1f} ms")


query = "SELECT product_id, SUM(quantity * unit_price) AS revenue FROM {} GROUP BY product_id"
time_it("DuckDB on the Parquet file", lambda: con.sql(query.format(f"'{SALES}'")).fetchall())
time_it("pandas (read Parquet + groupby)", lambda: (
    pd.read_parquet(SALES).assign(revenue=lambda d: d.quantity * d.unit_price)
      .groupby("product_id")["revenue"].sum()
))
time_it("Postgres (query over the network)", lambda: pd.read_sql(query.format("sales"), engine))