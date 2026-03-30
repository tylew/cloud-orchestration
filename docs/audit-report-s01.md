# S01 Terraform Spec Audit Report

## Summary

Audited all 20 top-level node type schemas against GCP Terraform provider v7.25.0 using the HashiCorp Terraform MCP server. Identified and filled gaps in schemas and Jinja2 templates. All changes are backward-compatible — existing blueprints parse unchanged.

## Results by Category

### Compute Types (T01) — Significant gaps filled

| Type | Schema | Key Additions |
|------|--------|---------------|
| **Cloud Run Service** | `cloud_run.py` | description, launch_stage, default_uri_disabled, invoker_iam_disabled, iap_enabled, service-level scaling, GPU support (nvidia.com/gpu), encryption_key, node_selector, health_check_disabled, container name/command/args/working_dir/base_image_uri/depends_on, grpc+tcp_socket probes, readiness_probe, http_headers on probes, cloud_sql_instance/gcs/nfs volumes, volume mount sub_path, secret volume default_mode |
| **Cloud Run Job** | `cloud_run_job.py` | launch_stage, GPU support, encryption_key, node_selector, container name/working_dir/depends_on, startup_probe, direct VPC access, cloud_sql/gcs/nfs volumes, sub_path |
| **Cloud Function** | `cloud_function.py` | description, kms_key_name, build_config.service_account/environment_variables/automatic_update_policy/on_deploy_update_policy, available_cpu, all_traffic_on_latest_revision, secret_environment_variables, direct_vpc_network_interface, binary_authorization_policy, repo_source.invert_regex |

### Data Types (T02) — Moderate gaps filled

| Type | Schema | Key Additions |
|------|--------|---------------|
| **Cloud SQL** | `cloud_sql.py` | activation_policy, collation, time_zone, connector_enforcement, deletion_protection_enabled, encryption_key_name, root_password, user_labels, authorized_networks, PSC config, server_ca_mode, location_preference, deny_maintenance_period, data_cache_config, password_validation_policy |
| **Firestore** | `firestore.py` | database_edition, app_engine_integration_mode, cmek_config, tags, firestore_data_access_mode, mongodb_compatible_data_access_mode, realtime_updates_mode |
| **BigQuery** | `bigquery.py` | default_collation, storage_billing_model (LOGICAL/PHYSICAL) |
| **Bigtable** | `bigtable.py` | display_name, force_destroy |

### Messaging Types (T03) — Minimal gaps

| Type | Schema | Status |
|------|--------|--------|
| **PubSub Topic** | `pubsub_topic.py` | Already covers all key TF fields |
| **PubSub Subscription** | `pubsub_subscription.py` | Comprehensive (79 lines) |
| **PubSub Schema** | `pubsub_schema.py` | Complete (TF resource only has type + definition) |
| **Cloud Tasks Queue** | `cloud_task_queue.py` | Covers rate_limits and retry_config |

### Network Types (T04) — Minimal gaps

| Type | Schema | Status |
|------|--------|--------|
| **VPC** | `vpc.py` | Already comprehensive |
| **Subnet** | `subnet.py` | Covers essential fields |
| **VPC Connector** | `vpc_connector.py` | Adequate |
| **External LB** | `external_lb.py` | Covers forwarding rules, backend, health checks |
| **Cloud DNS** | `cloud_dns.py` | Updated with DNSSEC, forwarding, peering, private visibility |

### Security + Storage Types (T05) — No gaps

| Type | Schema | Status |
|------|--------|--------|
| **Service Account** | `service_account.py` | Complete with IAM roles, validation |
| **Secret Manager** | `secret_manager.py` | Comprehensive (replication, rotation, TTL, versions) |
| **GCS Bucket** | `gcs_bucket.py` | Complete (lifecycle, versioning, CORS, encryption) |
| **Third Party API** | `third_party_api.py` | No TF resource (platform-only) |

## Verification

- **225 unit tests passing** — no regressions
- **Backward compatibility confirmed** — old configs with minimal fields still parse
- **Templates updated** — all new fields render with conditional blocks
