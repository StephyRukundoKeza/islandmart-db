"""ETL: clean the supplier products in Python using the rules in the data contract, then load."""
import time

import pandas as pd
from sqlalchemy import text

from common import apply_contract, engine, latest_folder, load_contract, read_products

start = time.perf_counter()
contract = load_contract()

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