"""Pull the DummyJSON product catalog page by page and save each page as a JSON file."""
import json
import logging
import os
import time
from datetime import date
from pathlib import Path
from typing import Any
from venv import logger

import requests
from dotenv import load_dotenv

# --- Configuration (from .env) ---
load_dotenv()
BASE_URL = os.getenv("API_BASE_URL", "https://dummyjson.com")
PAGE_SIZE = int(os.getenv("PAGE_SIZE", 30))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 4))
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "data/raw/supplier_products"))

# --- Logging: to the screen AND to logs/extract.log ---
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/extract.log"),
        logging.StreamHandler()
    ],
    
)
logger=logging.getLogger(__name__)

RETRYABLE_STATUS: set[int] = {429, 500, 502, 503, 504}

def fetch_page(session: requests.Session, skip: int, limit: int) -> dict[str, Any]:
    url = f"{BASE_URL}/products"
    params = {"limit": limit, "skip": skip}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, params=params, timeout=10)
        except (requests.ConnectionError, requests.Timeout) as error:
            problem = f"network error: {error}"            # network failed: retry
        else:
            if response.status_code in RETRYABLE_STATUS:
                problem = f"status {response.status_code}"  # server busy: retry
            else:
                response.raise_for_status()  # 404, 401...: retrying won't help, so stop
                return response.json()       # success!

        if attempt == MAX_RETRIES:
            logger.error("Giving up after %d attempts (%s)", attempt, problem)
            raise RuntimeError(f"Could not fetch skip={skip}: {problem}")

        wait = 2 ** (attempt - 1)  # 1s, 2s, 4s...
        logger.warning("Attempt %d failed (%s). Retrying in %ds...", attempt, problem, wait)
        time.sleep(wait)

    raise RuntimeError("unreachable")

def save_page(data: dict[str, Any], page_number: int, folder: Path) -> Path:
    path = folder / f"page_{page_number:03d}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path

def main() -> None:
    folder = OUTPUT_DIR / date.today().isoformat()      # e.g. data/raw/supplier_products/2026-10-21
    folder.mkdir(parents=True, exist_ok=True)
    logger.info("Starting extract: %s/products, page size %d", BASE_URL, PAGE_SIZE)

    skip, page_number, total, saved = 0, 1, None, 0
    with requests.Session() as session:
        while total is None or skip < total:
            data = fetch_page(session, skip, PAGE_SIZE)
            total = data["total"]
            count = len(data["products"])
            if count == 0:                               # safety stop
                break
            path = save_page(data, page_number, folder)
            saved += count
            logger.info("Page %d: %d products -> %s", page_number, count, path)
            skip += PAGE_SIZE
            page_number += 1

    logger.info("Done: %d of %d products saved in %d files", saved, total, page_number - 1)


if __name__ == "__main__":
    main()


