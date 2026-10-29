"""Incremental load with a watermark: only load products changed since the last successful run."""
import argparse
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import text

from common import apply_contract, column_name, engine, latest_folder, load_contract, read_products

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)   # used when there is no watermark yet

# One bookmark row per source, shared by every incremental pipeline
WATERMARK_TABLE = """
CREATE TABLE IF NOT EXISTS etl_watermarks (
    source      TEXT PRIMARY KEY,
    last_value  TIMESTAMPTZ NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
)"""

# GREATEST: a backfill can load old rows, but it never moves the bookmark backwards
SAVE_WATERMARK = """
INSERT INTO etl_watermarks (source, last_value) VALUES (:source, :value)
ON CONFLICT (source) DO UPDATE SET
    last_value = GREATEST(etl_watermarks.last_value, EXCLUDED.last_value),
    updated_at = now()"""


def build_sql(contract: dict) -> tuple[str, str, str]:
    """Write the CREATE TABLE and UPSERT statements from the contract's columns."""
    table = contract["incremental"]["target_table"]
    key = column_name(contract["key"], contract["keep"][contract["key"]])
    columns = {column_name(src, rule): rule["sql_type"] for src, rule in contract["keep"].items()}

    definitions = ",\n    ".join(
        f"{name} {sql_type}{' PRIMARY KEY' if name == key else ''}" for name, sql_type in columns.items()
    )
    create = (
        f"CREATE TABLE IF NOT EXISTS {table} (\n    {definitions},\n"
        f"    loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)"
    )

    names = ", ".join(columns)
    values = ", ".join(f":{name}" for name in columns)
    updates = ",\n    ".join(f"{name} = EXCLUDED.{name}" for name in columns if name != key)
    upsert = (
        f"INSERT INTO {table} ({names})\nVALUES ({values})\n"
        f"ON CONFLICT ({key}) DO UPDATE SET\n    {updates},\n    loaded_at = now()"
    )
    return table, create, upsert


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", help="Backfill: load everything updated after this date (YYYY-MM-DD)")
    parser.add_argument("--show-sql", action="store_true", help="Print the SQL built from the contract")
    args = parser.parse_args()

    contract = load_contract()
    source = contract["source"]
    watermark_col = contract["incremental"]["watermark"]
    table, create_sql, upsert_sql = build_sql(contract)
    if args.show_sql:
        print(create_sql, "\n")
        print(upsert_sql, "\n")

    with engine.begin() as conn:
        conn.execute(text(WATERMARK_TABLE))
        conn.execute(text(create_sql))
        saved = conn.execute(
            text("SELECT last_value FROM etl_watermarks WHERE source = :s"), {"s": source}
        ).scalar_one_or_none()

    if args.since:
        watermark = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
        print(f"Backfill from {watermark} (saved watermark stays {saved})")
    else:
        watermark = saved or EPOCH
        print(f"Watermark: {watermark}")

    folder = latest_folder()
    clean = apply_contract(pd.json_normalize(read_products(folder)), contract, verbose=False)
    changed = clean[clean[watermark_col] > watermark]
    print(f"Read {len(clean)} products from {folder}: {len(changed)} changed after the watermark")

    if changed.empty:
        print("Nothing new to load.")
        return

    rows = changed.astype(object).where(changed.notna(), None).to_dict("records")

    # Load and move the watermark in ONE transaction: if the load fails, the watermark stays put
    with engine.begin() as conn:
        conn.execute(text(upsert_sql), rows)
        conn.execute(text(SAVE_WATERMARK), {"source": source, "value": changed[watermark_col].max().to_pydatetime()})
        total = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()

    print(f"Upserted {len(changed)} rows. {table} now has {total} rows.")


if __name__ == "__main__":
    main()