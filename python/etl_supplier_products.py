"""ETL: clean the supplier products in Python using the rules in the data contract, then load."""
import json
import os
import time
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
RAW_DIR = Path(os.getenv("OUTPUT_DIR", "data/raw/supplier_products"))
CONTRACT_PATH = Path(os.getenv("SUPPLIER_CONTRACT", "contracts/supplier_products.yaml"))
engine = create_engine(
    f"postgresql+psycopg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('POSTGRES_DB')}"
)


def latest_folder() -> Path:
    """The newest extract, e.g. data/raw/supplier_products/2026-10-21."""
    folders = sorted(p for p in RAW_DIR.iterdir() if p.is_dir())
    if not folders:
        raise SystemExit("No raw data found. Run fetch_supplier_products.py first.")
    return folders[-1]


def read_products(folder: Path) -> list[dict]:
    products = []
    for page in sorted(folder.glob("page_*.json")):
        products.extend(json.loads(page.read_text(encoding="utf-8"))["products"])
    return products


def apply_contract(df: pd.DataFrame, contract: dict) -> pd.DataFrame:
    """Keep, rename and clean columns exactly as the contract says."""
    keep, drop = contract["keep"], contract["drop"]

    missing = set(keep) - set(df.columns)
    if missing:
        raise SystemExit(f"Contract expects columns the API didn't send: {sorted(missing)}")

    clean = pd.DataFrame()
    for src, rule in keep.items():
        col = df[src]
        if rule.get("strip"):
            col = col.str.strip()
        if "fill_missing" in rule:
            print(f"    {src}: {col.isna().sum()} missing, filled with '{rule['fill_missing']}'")
            col = col.fillna(rule["fill_missing"])
        if "round" in rule:
            col = col.round(rule["round"])
        if rule.get("type") == "datetime":
            col = pd.to_datetime(col, utc=True)
        clean[rule.get("rename", src)] = col

    key = keep[contract["key"]].get("rename", contract["key"])
    clean = clean.drop_duplicates(subset=key)

    print(f"Transform: kept {len(keep)} of {len(df.columns)} columns")
    print("  Kept:")
    for src, rule in keep.items():
        print(f"    {src:<22} -> {rule.get('rename', src):<13} {rule['reason']}")
    print("  Dropped:")
    for col, why in drop.items():
        print(f"    {col:<22} {why}")

    unreviewed = set(df.columns) - set(keep) - set(drop)
    if unreviewed:
        print(f"  WARNING, new columns not in the contract yet: {sorted(unreviewed)}")
    return clean


start = time.perf_counter()
contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))

# 1. Extract: read the JSON pages the API gave us
folder = latest_folder()
products = read_products(folder)
print(f"Extract: {len(products)} products from {folder}")

# 2. Transform: follow the data contract
clean = apply_contract(pd.json_normalize(products), contract)

# 3. Load: only clean data reaches the database
table = contract["target_table"]
clean.to_sql(table, engine, if_exists="replace", index=False)
with engine.connect() as conn:
    loaded = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()

print(f"Load: {loaded} rows in {table}")
print(f"ETL took {time.perf_counter() - start:.2f} s")