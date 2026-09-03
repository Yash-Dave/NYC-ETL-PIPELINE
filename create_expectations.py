import os
import sys
from dotenv import load_dotenv
load_dotenv()

import great_expectations as gx
from great_expectations.core.batch import BatchRequest

context = gx.get_context(context_root_dir="gx")

batch_request = BatchRequest(
    datasource_name="nyc_pipeline_postgres",
    data_connector_name="default_inferred_data_connector_name",
    data_asset_name="public_silver.silver_inspections",
)

suite_name = "silver_inspections_suite"

try:
    context.delete_expectation_suite(expectation_suite_name=suite_name)
except:
    pass

context.add_expectation_suite(expectation_suite_name=suite_name)

validator = context.get_validator(
    batch_request=batch_request,
    expectation_suite_name=suite_name,
)

print("Building expectations...")

for col in ["camis", "dba", "borough", "inspection_date",
            "grade", "inspection_score", "critical_flag",
            "violation_code", "department_category"]:
    validator.expect_column_to_exist(column=col)

for col in ["camis", "inspection_date", "borough"]:
    validator.expect_column_values_to_not_be_null(column=col)

validator.expect_column_values_to_be_in_set(
    column="borough",
    value_set=["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"],
    mostly=0.99,
)

validator.expect_column_values_to_be_in_set(
    column="grade",
    value_set=["A", "B", "C", "Z", "P", "N", "UNKNOWN"],
    mostly=0.99,
)

validator.expect_column_values_to_be_between(
    column="inspection_score",
    min_value=0,
    max_value=250,      # updated to 250 to reflect real NYC data
    mostly=0.99,
)

validator.expect_column_values_to_match_regex(
    column="zipcode",
    regex=r"^\d{5}$",
    mostly=0.95,
)

validator.expect_column_values_to_match_regex(
    column="camis",
    regex=r"^\d+$",
    mostly=0.99,
)

# Updated max to 250 to match real data
validator.expect_column_max_to_be_between(
    column="inspection_score",
    min_value=0,
    max_value=250,
)

validator.expect_table_row_count_to_be_between(
    min_value=100000,
    max_value=1000000,
)

validator.expect_column_values_to_be_in_set(
    column="critical_flag",
    value_set=["Critical", "Not Critical", "Not Applicable"],
    mostly=0.99,
)

validator.expect_column_values_to_be_in_set(
    column="department_category",
    value_set=[
        "Food Safety & Hygiene",
        "Sanitary Conditions",
        "Compliance & Permits",
        "No Violation",
        "General",
    ],
)

validator.expect_column_values_to_not_match_regex(
    column="dba",
    regex=r"^\s+|\s+$",
    mostly=0.99,
)

validator.expect_column_values_to_not_match_regex(
    column="borough",
    regex=r"^\s*$",
    mostly=0.99,
)

from datetime import datetime
validator.expect_column_values_to_be_between(
    column="inspection_date",
    min_value="1990-01-01",
    max_value=datetime.today().strftime("%Y-%m-%d"),
    mostly=0.99,
)

validator.expect_compound_columns_to_be_unique(
    column_list=["camis", "inspection_date", "violation_code"],
    mostly=0.99,
)

validator.save_expectation_suite(discard_failed_expectations=False)
print("✓ Suite updated with corrected max score of 250")
