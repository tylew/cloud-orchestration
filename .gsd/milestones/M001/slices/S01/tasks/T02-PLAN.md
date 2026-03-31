---
estimated_steps: 1
estimated_files: 9
skills_used: []
---

# T02: Audit & update Data types (Cloud SQL, Firestore, BigQuery, Bigtable)

Use Terraform MCP to pull full specs for google_sql_database_instance, google_firestore_database, google_bigquery_dataset, google_bigtable_instance. Compare against existing schemas. Add missing fields. Update templates. Firestore is already mature — focus on Cloud SQL, BigQuery, Bigtable gaps.

## Inputs

- `Terraform MCP: google_sql_database_instance, google_firestore_database, google_bigquery_dataset, google_bigtable_instance specs`

## Expected Output

- `Updated schema configs for 4 data types`
- `Updated Jinja2 templates for 4 data types`
- `New/updated tests`

## Verification

pytest packages/tests/test_terraform.py -v && pytest packages/tests/test_validation.py -v
