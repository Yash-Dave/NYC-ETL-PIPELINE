# ingestion/load_to_s3.py
"""
S3 Uploader — Bronze Layer
--------------------------
Takes the locally saved JSON batch files from extract.py
and uploads them to S3, preserving the date-partition structure.
"""

import logging
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import AWS_REGION, S3_BUCKET_NAME, S3_BRONZE_PREFIX

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def upload_batches_to_s3(local_files: list[Path]) -> int:
    """
    Upload each local JSON batch file to S3.

    The S3 key mirrors the local path structure:
      local:  output/bronze/inspections/year=2024/month=05/day=17/batch_0000.json
      s3 key: bronze/inspections/year=2024/month=05/day=17/batch_0000.json

    Returns count of successfully uploaded files.
    """
    s3 = boto3.client("s3", region_name=AWS_REGION)
    uploaded = 0

    for local_path in local_files:
        # Build the S3 key by replacing the local 'output/' prefix
        # with our S3 bronze prefix
        relative = local_path.relative_to("output")
        s3_key   = str(relative)          # e.g. bronze/inspections/year=.../batch_0000.json

        try:
            s3.upload_file(
                Filename=str(local_path),
                Bucket=S3_BUCKET_NAME,
                Key=s3_key,
                ExtraArgs={
                    "ContentType": "application/json",
                    "Metadata": {
                        "pipeline": "nyc_restaurant_inspections",
                        "layer":    "bronze",
                    },
                },
            )
            log.info(f"✓ Uploaded: s3://{S3_BUCKET_NAME}/{s3_key}")
            uploaded += 1

        except ClientError as e:
            log.error(f"✗ Failed to upload {local_path}: {e}")

    log.info(f"\nUpload complete: {uploaded}/{len(local_files)} files uploaded.")
    return uploaded


if __name__ == "__main__":
    # Find all batch files saved by extract.py
    output_dir  = Path("output/bronze")
    batch_files = sorted(output_dir.rglob("batch_*.json"))

    if not batch_files:
        print("No batch files found. Run extract.py first.")
        sys.exit(1)

    print(f"Found {len(batch_files)} batch files to upload...")
    upload_batches_to_s3(batch_files)