import great_expectations as gx

context = gx.get_context(context_root_dir="gx")

result = context.run_checkpoint(checkpoint_name="silver_checkpoint")

print("\n=== FAILED RULES ===")
for run_result in result.run_results.values():
    validation = run_result["validation_result"]
    for r in validation.results:
        if not r.success:
            print(f"\nFailed: {r.expectation_config.expectation_type}")
            print(f"Column: {r.expectation_config.kwargs}")
            print(f"Result: {r.result}")
