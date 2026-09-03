# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

# Socrata
SOCRATA_APP_TOKEN  = os.getenv("SOCRATA_APP_TOKEN")
SOCRATA_DOMAIN     = os.getenv("SOCRATA_DOMAIN")
SOCRATA_DATASET_ID = os.getenv("SOCRATA_DATASET_ID")

# S3
AWS_REGION        = os.getenv("AWS_REGION", "eu-north-1")
S3_BUCKET_NAME    = os.getenv("S3_BUCKET_NAME")
S3_BRONZE_PREFIX  = os.getenv("S3_BRONZE_PREFIX", "bronze/inspections")

# Pagination
PAGE_SIZE = 50_000      # records per API call (Socrata max is 50,000)
MAX_PAGES = 20          # safety ceiling: 20 × 50,000 = 1,000,000 max records

# Retry
MAX_RETRIES        = 5
RETRY_WAIT_MIN_SEC = 2
RETRY_WAIT_MAX_SEC = 60