import great_expectations as gx

context = gx.get_context(context_root_dir="gx")

# Just run the existing checkpoint
result = context.run_checkpoint(checkpoint_name="silver_checkpoint")
print(f"\nValidation result: {'PASS ✅' if result.success else 'FAIL ❌'}")

for run_result in result.run_results.values():
    validation = run_result["validation_result"]
    total  = len(validation.results)
    passed = sum(1 for r in validation.results if r.success)
    print(f"Rules passed: {passed}/{total}")

    if not result.success:
        print("\n=== FAILED RULES ===")
        for r in validation.results:
            if not r.success:
                print(f"  ✗ {r.expectation_config.expectation_type}")
                print(f"    {r.expectation_config.kwargs}")
