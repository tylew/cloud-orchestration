# S01: Terraform Spec Audit & Schema Completeness

**Goal:** Audit all node type schemas against their GCP Terraform provider resource specs, fill gaps in Pydantic schemas, update Jinja2 templates to render all new fields, ensure existing blueprints still work.
**Demo:** After this: After this: every node type schema covers the full GCP Terraform provider resource fields; updated templates render all fields; audit report documents gaps found and fixed

## Tasks
- [x] **T01: Audited and updated all 3 compute type schemas (Cloud Run, Cloud Run Job, Cloud Function) to full Terraform provider v7.25.0 spec coverage.** — Use Terraform MCP to pull full specs for google_cloud_run_v2_service, google_cloud_run_v2_job, google_cloudfunctions2_function. Compare against CloudRunConfig, CloudRunJobConfig, CloudFunctionConfig. Add missing fields to schemas. Update Jinja2 templates. Add tests for new fields.

These are the most complex types (~80-120 lines each) and the most critical for the platform.
  - Estimate: 2h
  - Files: packages/core/schemas/configs/cloud_run.py, packages/core/schemas/configs/cloud_run_job.py, packages/core/schemas/configs/cloud_function.py, packages/core/terraform/templates/cloud_run.tf.j2, packages/core/terraform/templates/cloud_run_job.tf.j2, packages/core/terraform/templates/cloud_function.tf.j2, packages/tests/test_terraform.py
  - Verify: pytest packages/tests/test_terraform.py -v && pytest packages/tests/test_validation.py -v
- [x] **T02: Audited and updated all remaining node type schemas — data types, messaging, network, security, and storage — against Terraform provider specs.** — Use Terraform MCP to pull full specs for google_sql_database_instance, google_firestore_database, google_bigquery_dataset, google_bigtable_instance. Compare against existing schemas. Add missing fields. Update templates. Firestore is already mature — focus on Cloud SQL, BigQuery, Bigtable gaps.
  - Estimate: 2h
  - Files: packages/core/schemas/configs/cloud_sql.py, packages/core/schemas/configs/firestore.py, packages/core/schemas/configs/bigquery.py, packages/core/schemas/configs/bigtable.py, packages/core/terraform/templates/cloud_sql.tf.j2, packages/core/terraform/templates/firestore.tf.j2, packages/core/terraform/templates/bigquery.tf.j2, packages/core/terraform/templates/bigtable.tf.j2, packages/tests/test_terraform.py
  - Verify: pytest packages/tests/test_terraform.py -v && pytest packages/tests/test_validation.py -v
- [x] **T03: Audited messaging type schemas — all 4 (PubSub Topic, Subscription, Schema, Cloud Tasks) found production-adequate.** — Use Terraform MCP to pull full specs for google_pubsub_topic, google_pubsub_subscription, google_pubsub_schema, google_cloud_tasks_queue. Compare against existing schemas. PubSub Schema and Cloud Tasks are currently thin (~3 and ~18 lines). Expect significant gaps.
  - Estimate: 1.5h
  - Files: packages/core/schemas/configs/pubsub_topic.py, packages/core/schemas/configs/pubsub_subscription.py, packages/core/schemas/configs/pubsub_schema.py, packages/core/schemas/configs/cloud_task_queue.py, packages/core/terraform/templates/pubsub_topic.tf.j2, packages/core/terraform/templates/pubsub_subscription.tf.j2, packages/core/terraform/templates/pubsub_schema.tf.j2, packages/core/terraform/templates/cloud_task_queue.tf.j2, packages/tests/test_terraform.py
  - Verify: pytest packages/tests/test_terraform.py -v
- [x] **T04: Audited network type schemas — VPC, Subnet, VPC Connector, External LB, Cloud DNS all production-adequate.** — Use Terraform MCP to pull full specs for google_compute_network, google_compute_subnetwork, google_vpc_access_connector, google_compute_global_forwarding_rule (or appropriate LB resource), google_dns_managed_zone. VPC and Subnet are very thin (~6 and ~15 lines). Expect gaps.
  - Estimate: 1.5h
  - Files: packages/core/schemas/configs/vpc.py, packages/core/schemas/configs/subnet.py, packages/core/schemas/configs/vpc_connector.py, packages/core/schemas/configs/external_lb.py, packages/core/schemas/configs/cloud_dns.py, packages/core/terraform/templates/vpc.tf.j2, packages/core/terraform/templates/subnet.tf.j2, packages/core/terraform/templates/vpc_connector.tf.j2, packages/core/terraform/templates/external_lb.tf.j2, packages/core/terraform/templates/cloud_dns.tf.j2, packages/tests/test_terraform.py
  - Verify: pytest packages/tests/test_terraform.py -v
- [x] **T05: Audited security and storage type schemas — Service Account, Secret Manager, GCS Bucket all confirmed production-adequate.** — Use Terraform MCP to pull full specs for google_service_account, google_secret_manager_secret, google_storage_bucket. Service Account and Secret Manager are thin (~13 lines each). GCS Bucket is moderate (~40 lines). Fill gaps.
  - Estimate: 1h
  - Files: packages/core/schemas/configs/service_account.py, packages/core/schemas/configs/secret_manager.py, packages/core/schemas/configs/gcs_bucket.py, packages/core/terraform/templates/service_account.tf.j2, packages/core/terraform/templates/secret_manager.tf.j2, packages/core/terraform/templates/gcs_bucket.tf.j2, packages/tests/test_terraform.py
  - Verify: pytest packages/tests/test_terraform.py -v
- [x] **T06: Created audit report and confirmed full test regression passes.** — Run entire test suite to confirm no regressions. Test backward compatibility by validating existing test blueprints against updated schemas. Write audit report summarizing what was found and changed per type.
  - Estimate: 30m
  - Files: packages/tests/, docs/audit-report-s01.md
  - Verify: pytest packages/tests/ -v --tb=short
