"""ELT: load the raw JSON into Postgres untouched, then clean it with SQL inside the database."""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
RAW_DIR = Path(os.getenv("OUTPUT_DIR", "data/raw/supplier_products"))
TRANSFORM_SQL = Path(os.getenv("SUPPLIER_ELT_SQL", "sql/elt_supplier_products.sql"))
engine = create_engine(
    f"postgresql+psycopg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('POSTGRES_DB')}"
)


def latest_folder() -> Path:
    folders = sorted(p for p in RAW_DIR.iterdir() if p.is_dir())
    if not folders:
        raise SystemExit("No raw data found. Run fetch_supplier_products.py first.")
    return folders[-1]


def read_products(folder: Path) -> list[dict]:
    products = []
    for page in sorted(folder.glob("page_*.json")):
        products.extend(json.loads(page.read_text(encoding="utf-8"))["products"])
    return products


start = time.perf_counter()

# 1. Extract
folder = latest_folder()
products = read_products(folder)
print(f"Extract: {len(products)} products from {folder}")

# 2. Load: every product exactly as the API sent it, in one JSONB column
with engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS raw.supplier_products (
            product_id  INT NOT NULL,
            data        JSONB NOT NULL,
            source_file TEXT NOT NULL,
            loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))
    conn.execute(text("TRUNCATE raw.supplier_products"))   # full load: replace what was there
    conn.execute(
        text("INSERT INTO raw.supplier_products (product_id, data, source_file) "
             "VALUES (:product_id, CAST(:data AS JSONB), :source_file)"),
        [{"product_id": p["id"], "data": json.dumps(p), "source_file": str(folder)} for p in products],
    )
load_done = time.perf_counter()
print(f"Load: {len(products)} raw rows in raw.supplier_products ({load_done - start:.2f} s)")

# 3. Transform in SQL
sql = TRANSFORM_SQL.read_text(encoding="utf-8")
with engine.begin() as conn:
    for statement in sql.split(";"):
        if statement.strip():
            conn.execute(text(statement))
    cleaned = conn.execute(text("SELECT COUNT(*) FROM supplier_products_elt")).scalar_one()

print(f"Transform: {cleaned} rows in supplier_products_elt ({time.perf_counter() - load_done:.2f} s)")
print(f"ELT took {time.perf_counter() - start:.2f} s")