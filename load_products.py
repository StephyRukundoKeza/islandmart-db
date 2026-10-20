"""
IslandMart DB: load data/products.csv into Postgres (ETL: clean in Python, then load).

Cleaning rules:
- Rows without a product_id are dropped (they can't be identified).
- Prices: remove commas and currency text (Rs, MUR). Non-numbers ("free") and
  negative prices become blank, because they are data errors.
- Stock: "out of stock", blank and N/A become 0. Negative stock becomes 0.
- Categories: trimmed, Title Case, typos fixed, blank -> "Uncategorized".
- Dates: year-first formats are read first, then day-first (Mauritian) formats.
  Impossible dates (31/02/2026) become blank.
- Duplicates: same product (name ignoring case/spaces, category, price, stock)
  is kept once, even if it has a different product_id.
- A product_id used for two different products is flagged, not guessed.
"""
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 1. Load credentials from .env
load_dotenv()
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# 2. Build the engine
url = f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{DB_PORT}/{POSTGRES_DB}"
engine = create_engine(url)

# 3. Extract
df = pd.read_csv("data/products.csv")
rows_read = len(df)
print(f"Read {rows_read} rows")

# 4. Transform (clean)

# 4.1 Column names: remove hidden spaces ("price_mur " -> "price_mur")
df.columns = df.columns.str.strip()

# 4.2 Product id: drop rows without one, then make it a whole number (1.0 -> 1)
missing_ids = df["product_id"].isna().sum()
df = df.dropna(subset=["product_id"])
df["product_id"] = df["product_id"].astype(int)

# 4.3 Names: remove spaces at the start and end
df["name"] = df["name"].str.strip()

# 4.4 Categories: trim, Title Case, fix typos, fill blanks
df["category"] = df["category"].str.strip().str.title()
df["category"] = df["category"].replace({"Snaks": "Snacks", "Fruit And Veg": "Fruit & Veg"})
df["category"] = df["category"].fillna("Uncategorized")

# 4.5 Prices: remove commas and currency text, convert to numbers
df["price_mur"] = (
    df["price_mur"]
    .str.replace(",", "")
    .str.replace("Rs", "")
    .str.replace("MUR", "")
    .str.strip()
)
df["price_mur"] = pd.to_numeric(df["price_mur"], errors="coerce")
negative_prices = (df["price_mur"] < 0).sum()
df.loc[df["price_mur"] < 0, "price_mur"] = None

# 4.6 Stock: out of stock / blank / N/A -> 0, negative -> 0, whole numbers
df["stock_qty"] = df["stock_qty"].replace("out of stock", "0")
df["stock_qty"] = pd.to_numeric(df["stock_qty"], errors="coerce").fillna(0)
df.loc[df["stock_qty"] < 0, "stock_qty"] = 0
df["stock_qty"] = df["stock_qty"].astype(int)

# 4.7 Dates: try year-first formats first, then day-first formats
iso = pd.to_datetime(df["last_updated"], format="%Y-%m-%d", errors="coerce")    # 2026-10-01
slash = pd.to_datetime(df["last_updated"], format="%Y/%m/%d", errors="coerce")  # 2026/10/05
other = pd.to_datetime(df["last_updated"], format="mixed", dayfirst=True, errors="coerce")  # 02/10/2026, 4 Oct 2026
df["last_updated"] = iso.fillna(slash).fillna(other)

# 4.8 Duplicates: done last, once everything is clean
rows_before_dedup = len(df)
df["name_key"] = df["name"].str.lower()
df = df.drop_duplicates(subset=["name_key", "category", "price_mur", "stock_qty"])
df = df.drop(columns=["name_key"])
duplicates_removed = rows_before_dedup - len(df)

# 4.9 Flag the same product_id used for different products
conflicts = df[df["product_id"].duplicated(keep=False)]
if not conflicts.empty:
    print("WARNING: same product_id used for different products:")
    print(conflicts.to_string(index=False))

# 5. Load (replace = running the script again gives the same result)
df.to_sql("products", engine, if_exists="replace", index=False)

# 6. Verify: does the database agree with the DataFrame?
with engine.connect() as connection:
    db_count = connection.execute(text("SELECT COUNT(*) FROM products")).scalar()

print(f"Rows in DataFrame: {len(df)} | Rows in database: {db_count}")
print("MATCH" if len(df) == db_count else "MISMATCH")

# 7. Cleaning report
print("--- Cleaning report ---")
print(f"Rows read:            {rows_read}")
print(f"Dropped (no id):      {missing_ids}")
print(f"Duplicates removed:   {duplicates_removed}")
print(f"Negative prices:      {negative_prices} (set to blank)")
print(f"Blank prices:         {df['price_mur'].isna().sum()}")
print(f"Blank dates:          {df['last_updated'].isna().sum()}")
print(f"Id conflicts flagged: {conflicts['product_id'].nunique()}")
print(f"Rows loaded:          {len(df)}")