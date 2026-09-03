import json
import logging
import os
import sys
from pathlib import Path

# ── Load .env using absolute path ─────────────────────────
from dotenv import load_dotenv
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

import boto3
import psycopg2
import psycopg2.extras
from botocore.exceptions import ClientError

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import AWS_REGION, S3_BUCKET_NAME, S3_BRONZE_PREFIX

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def get_db_connection():
    host     = os.getenv("DB_HOST")
    port     = int(os.getenv("DB_PORT", 5432))
    dbname   = os.getenv("DB_NAME")
    user     = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    log.info(f"Connecting to {host}:{port}/{dbname} as {user}")

    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=10,
    )

FIELD_MAP = {
    "camis":                "camis",
    "dba":                  "dba",
    "boro":                 "boro",
    "building":             "building",
    "street":               "street",
    "zipcode":              "zipcode",
    "phone":                "phone",
    "cuisine_description":  "cuisine_description",
    "inspection_date":      "inspection_date",
    "action":               "action",
    "violation_code":       "violation_code",
    "violation_description":"violation_description",
    "critical_flag":        "critical_flag",
    "score":                "score",
    "grade":                "grade",
    "grade_date":           "grade_date",
    "record_date":          "record_date",
    "inspection_type":      "inspection_type",
    "latitude":             "latitude",
    "longitude":            "longitude",
    "community_board":      "community_board",
    "council_district":     "council_district",
    "census_tract":         "census_tract",
    "bin":                  "bin",
    "bbl":                  "bbl",
    "nta":                  "nta",
}

UPSERT_SQL = """
INSERT INTO public.inspections_bronze (
    camis, dba, boro, building, street, zipcode, phone,
    cuisine_description, inspection_date, action,
    violation_code, violation_description, critical_flag,
    score, grade, grade_date, record_date, inspection_type,
    latitude, longitude, community_board, council_district,
    census_tract, bin, bbl, nta,
    dbt_loaded_at, pipeline_batch_id
)
VALUES (
    %(camis)s, %(dba)s, %(boro)s, %(building)s, %(street)s,
    %(zipcode)s, %(phone)s, %(cuisine_description)s,
    %(inspection_date)s, %(action)s, %(violation_code)s,
    %(violation_description)s, %(critical_flag)s, %(score)s,
    %(grade)s, %(grade_date)s, %(record_date)s, %(inspection_type)s,
    %(latitude)s, %(longitude)s, %(community_board)s,
    %(council_district)s, %(census_tract)s, %(bin)s, %(bbl)s, %(nta)s,
    NOW(), %(pipeline_batch_id)s
)
ON CONFLICT DO NOTHING;
"""

def process_s3_file(s3_client, bucket, key, conn):
    log.info(f"Processing s3://{bucket}/{key}")
    response = s3_client.get_object(Bucket=bucket, Key=key)
    raw      = response["Body"].read().decode("utf-8")
    payload  = json.loads(raw)
    records  = payload.get("data", [])
    batch_id = key

    if not records:
        log.warning(f"No records in {key}")
        return 0

    normalized = []
    for rec in records:
        row = {db_col: rec.get(api_key) for api_key, db_col in FIELD_MAP.items()}
        row["pipeline_batch_id"] = batch_id
        normalized.append(row)

    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, UPSERT_SQL, normalized, page_size=1000)
    conn.commit()

    log.info(f"✓ Upserted {len(normalized):,} records from {key}")
    return len(normalized)

def load_all_from_s3():
    s3   = boto3.client("s3", region_name=AWS_REGION)
    conn = get_db_connection()

    log.info(f"Listing files in s3://{S3_BUCKET_NAME}/{S3_BRONZE_PREFIX}/")

    paginator     = s3.get_paginator("list_objects_v2")
    pages         = paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=S3_BRONZE_PREFIX)
    total_records = 0
    total_files   = 0

    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".json"):
                continue
            try:
                count          = process_s3_file(s3, S3_BUCKET_NAME, key, conn)
                total_records += count
                total_files   += 1
            except Exception as e:
                log.error(f"Failed to process {key}: {e}")
                conn.rollback()

    conn.close()
    log.info(f"Load complete. Files: {total_files}, Records: {total_records:,}")

if __name__ == "__main__":
    load_all_from_s3()
