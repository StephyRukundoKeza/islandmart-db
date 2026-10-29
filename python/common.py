"""Shared helpers for the supplier pipelines: database connection, raw files and the data contract."""
import json
import os
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine

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
        raise SystemExit("No raw data found. Run python/fetch_supplier_products.py first.")
    return folders[-1]


def read_products(folder: Path) -> list[dict]:
    products = []
    for page in sorted(folder.glob("page_*.json")):
        products.extend(json.loads(page.read_text(encoding="utf-8"))["products"])
    return products


def load_contract() -> dict:
    return yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


def column_name(src: str, rule: dict) -> str:
    """The name a column gets after cleaning (its rename, or its original name)."""
    return rule.get("rename", src)


def apply_contract(df: pd.DataFrame, contract: dict, verbose: bool = True) -> pd.DataFrame:
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
            if verbose:
                print(f"    {src}: {col.isna().sum()} missing, filled with '{rule['fill_missing']}'")
            col = col.fillna(rule["fill_missing"])
        if "round" in rule:
            col = col.round(rule["round"])
        if rule.get("type") == "datetime":
            col = pd.to_datetime(col, utc=True)
        clean[column_name(src, rule)] = col

    key = column_name(contract["key"], keep[contract["key"]])
    clean = clean.drop_duplicates(subset=key)

    unreviewed = set(df.columns) - set(keep) - set(drop)
    if verbose:
        print(f"Transform: kept {len(keep)} of {len(df.columns)} columns")
        print("  Kept:")
        for src, rule in keep.items():
            print(f"    {src:<22} -> {column_name(src, rule):<13} {rule['reason']}")
        print("  Dropped:")
        for col, why in drop.items():
            print(f"    {col:<22} {why}")
    if unreviewed:
        print(f"  WARNING, new columns not in the contract yet: {sorted(unreviewed)}")
    return clean