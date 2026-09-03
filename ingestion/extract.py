# ingestion/extract.py
"""
NYC Restaurant Inspection API Extractor
---------------------------------------
Fetches all records from the Socrata API using pagination,
exponential backoff retries, and saves each page as a
timestamped JSON batch file ready for S3 upload.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

# Add project root to path so config is importable
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import (
    SOCRATA_APP_TOKEN,
    SOCRATA_DOMAIN,
    SOCRATA_DATASET_ID,
    PAGE_SIZE,
    MAX_PAGES,
    MAX_RETRIES,
    RETRY_WAIT_MIN_SEC,
    RETRY_WAIT_MAX_SEC,
)

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/extract.log"),
    ],
)
log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
BASE_URL = f"https://{SOCRATA_DOMAIN}/resource/{SOCRATA_DATASET_ID}.json"

HEADERS = {
    "X-App-Token": SOCRATA_APP_TOKEN,
    "Accept": "application/json",
}


# ── Retry-wrapped API call ─────────────────────────────────────────────────────
@retry(
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(
        multiplier=1,
        min=RETRY_WAIT_MIN_SEC,
        max=RETRY_WAIT_MAX_SEC,
    ),
    before_sleep=before_sleep_log(log, logging.WARNING),
    reraise=True,
)
def fetch_page(offset: int, limit: int) -> list[dict]:
    """
    Fetch a single page of records from the Socrata API.

    Uses SoQL (Socrata Query Language) parameters:
      $limit  — how many records to return
      $offset — how many records to skip (for pagination)
      $order  — ensures consistent ordering across pages

    Returns a list of record dicts, or raises on HTTP error.
    """
    params = {
        "$limit":  limit,
        "$offset": offset,
        "$order":  "camis,inspection_date",   # stable sort for consistent pages
    }

    log.info(f"Fetching records {offset} → {offset + limit} ...")

    response = requests.get(
        BASE_URL,
        headers=HEADERS,
        params=params,
        timeout=30,          # fail fast if Socrata hangs
    )

    # Surface HTTP errors (4xx, 5xx) as exceptions so tenacity can catch them
    response.raise_for_status()

    records = response.json()
    log.info(f"  ✓ Received {len(records)} records")
    return records


# ── Metadata wrapper ───────────────────────────────────────────────────────────
def wrap_batch(records: list[dict], page_num: int, extracted_at: str) -> dict:
    """
    Wrap raw records in a metadata envelope before writing to S3.
    This makes it easy to audit: when was this batch pulled,
    how many records, which page number?
    """
    return {
        "metadata": {
            "source":        f"https://{SOCRATA_DOMAIN}/resource/{SOCRATA_DATASET_ID}",
            "extracted_at":  extracted_at,
            "page_number":   page_num,
            "record_count":  len(records),
            "pipeline_name": "nyc_restaurant_inspections",
        },
        "data": records,
    }


# ── Main extraction loop ───────────────────────────────────────────────────────
def extract_all() -> list[Path]:
    """
    Paginate through the entire dataset and save each page as a
    local JSON file in output/bronze/year=YYYY/month=MM/day=DD/.

    Returns a list of file paths for the upload step.
    """
    extracted_at = datetime.now(timezone.utc).isoformat()
    now           = datetime.now(timezone.utc)

    # Build date-partitioned output path (matches S3 prefix structure)
    partition = (
        f"year={now.year:04d}/"
        f"month={now.month:02d}/"
        f"day={now.day:02d}"
    )
    output_dir = Path(f"output/bronze/inspections/{partition}")
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[Path] = []
    total_records = 0

    for page_num in range(MAX_PAGES):
        offset = page_num * PAGE_SIZE

        try:
            records = fetch_page(offset=offset, limit=PAGE_SIZE)
        except Exception as e:
            log.error(f"Failed to fetch page {page_num} after {MAX_RETRIES} retries: {e}")
            break

        if not records:
            log.info(f"No more records at offset {offset}. Extraction complete.")
            break

        # Wrap in metadata envelope
        batch = wrap_batch(records, page_num=page_num, extracted_at=extracted_at)

        # Save to local file: batch_0000.json, batch_0001.json, ...
        file_path = output_dir / f"batch_{page_num:04d}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(batch, f, ensure_ascii=False, indent=2)

        saved_files.append(file_path)
        total_records += len(records)

        log.info(
            f"Page {page_num:>3} saved → {file_path} "
            f"(running total: {total_records:,} records)"
        )

        # If we got fewer records than PAGE_SIZE, we've hit the last page
        if len(records) < PAGE_SIZE:
            log.info("Last page reached (partial page received).")
            break

    log.info(
        f"\n{'='*50}\n"
        f"Extraction complete.\n"
        f"  Total pages:   {len(saved_files)}\n"
        f"  Total records: {total_records:,}\n"
        f"  Output dir:    {output_dir}\n"
        f"{'='*50}"
    )

    return saved_files


if __name__ == "__main__":
    files = extract_all()
    print(f"\n✓ Saved {len(files)} batch files locally.")
    print("Next step: run load_to_s3.py to upload these to S3.")