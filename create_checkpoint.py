import great_expectations as gx

context = gx.get_context(context_root_dir="gx")

checkpoint_config = {
    "name": "silver_checkpoint",
    "config_version": 1.0,
    "class_name": "SimpleCheckpoint",
    "run_name_template": "%Y%m%d-%H%M%S-silver-validation",
    "validations": [
        {
            "batch_request": {
                "datasource_name": "nyc_pipeline_postgres",
                "data_connector_name": "default_inferred_data_connector_name",
                "data_asset_name": "public_silver.silver_inspections",
            },
            "expectation_suite_name": "silver_inspections_suite",
        }
    ],
}

context.add_checkpoint(**checkpoint_config)
print("✓ Checkpoint created successfully")

# Run it immediately
result = context.run_checkpoint(checkpoint_name="silver_checkpoint")
print(f"\nValidation result: {'PASS ✅' if result.success else 'FAIL ❌'}")

# Print individual rule results
for run_result in result.run_results.values():
    validation = run_result["validation_result"]
    total   = len(validation.results)
    passed  = sum(1 for r in validation.results if r.success)
    print(f"Rules passed: {passed}/{total}")
