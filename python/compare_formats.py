"""Compare CSV and Parquet: file size, read speed, and data types, using the sales table."""
import os
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()
url = (
    f"postgresql+psycopg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('POSTGRES_DB')}"
)
engine = create_engine(url)

# Export the sales table from Postgres into pandas
df = pd.read_sql("SELECT * FROM sales", engine)
df["sale_date"] = pd.to_datetime(df["sale_date"])   # make it a real pandas date type
print(f"Rows from Postgres: {len(df):,}")

# Write the same data in both formats

out = Path("data/formats")
out.mkdir(parents=True, exist_ok=True)
csv_path = out / "sales.csv"
parquet_path = out / "sales.parquet"

df.to_csv(csv_path, index=False)
df.to_parquet(parquet_path, index=False)  

# Compare file sizes

def size_mb(path: Path) -> float:
    return path.stat().st_size / 1_000_000


def time_it(label: str, func, repeats: int = 5) -> float:
    """Run func several times and keep the fastest time (in milliseconds)."""
    best = float("inf")
    for _ in range(repeats):
        start = time.perf_counter()
        func()
        best = min(best, time.perf_counter() - start)
    print(f"  {label:<38} {best * 1000:8.1f} ms")
    return best


# File size
csv_mb, parquet_mb = size_mb(csv_path), size_mb(parquet_path)
print("\n--- File size ---")
print(f"  CSV:     {csv_mb:6.2f} MB")
print(f"  Parquet: {parquet_mb:6.2f} MB  ({csv_mb / parquet_mb:.1f}x smaller)")

# Read speed: the whole file
print("\n--- Read the whole file ---")
time_it("CSV, all columns", lambda: pd.read_csv(csv_path))
time_it("Parquet, all columns", lambda: pd.read_parquet(parquet_path))

# Read speed: only the 2 columns we need
cols = ["product_id", "quantity"]
print("\n--- Read only 2 columns ---")
time_it("CSV, 2 columns (usecols)", lambda: pd.read_csv(csv_path, usecols=cols))
time_it("Parquet, 2 columns (columns)", lambda: pd.read_parquet(parquet_path, columns=cols))

# Data types: what survives the round trip?
print("\n--- Data types after reading back ---")
types = pd.DataFrame({
    "postgres -> pandas": df.dtypes.astype(str),
    "from CSV": pd.read_csv(csv_path).dtypes.astype(str),
    "from Parquet": pd.read_parquet(parquet_path).dtypes.astype(str),
})
print(types.to_string())