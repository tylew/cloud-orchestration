---
id: T01
parent: S01
milestone: M001
provides: []
requires: []
affects: []
key_files: ["packages/core/schemas/configs/cloud_run.py", "packages/core/schemas/configs/cloud_run_job.py", "packages/core/schemas/configs/cloud_function.py", "packages/core/terraform/templates/cloud_run.tf.j2", "packages/core/terraform/templates/cloud_run_job.tf.j2", "packages/core/terraform/templates/cloud_function.tf.j2", "packages/tests/test_env_vars.py"]
key_decisions: ["Added GPU support (nvidia.com/gpu) as a `gpu` field on CloudRun and CloudRunJob configs", "Added all volume types (cloud_sql_instance, gcs, nfs) to CloudRunVolume model shared between Service and Job", "Added readiness_probe as a separate model from liveness/startup probes (different fields per TF spec)", "Container-level fields (name, command, args, working_dir, depends_on) prefixed with `container_` to avoid collision with top-level fields", "Cloud Function `secret_environment_variables` is now a proper schema field matching Terraform spec"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "All 225 unit tests pass. Backward compatibility verified with old and new config payloads."
completed_at: 2026-03-30T23:00:12.477Z
blocker_discovered: false
---

# T01: Audited and updated all 3 compute type schemas (Cloud Run, Cloud Run Job, Cloud Function) to full Terraform provider v7.25.0 spec coverage.

> Audited and updated all 3 compute type schemas (Cloud Run, Cloud Run Job, Cloud Function) to full Terraform provider v7.25.0 spec coverage.

## What Happened
---
id: T01
parent: S01
milestone: M001
key_files:
  - packages/core/schemas/configs/cloud_run.py
  - packages/core/schemas/configs/cloud_run_job.py
  - packages/core/schemas/configs/cloud_function.py
  - packages/core/terraform/templates/cloud_run.tf.j2
  - packages/core/terraform/templates/cloud_run_job.tf.j2
  - packages/core/terraform/templates/cloud_function.tf.j2
  - packages/tests/test_env_vars.py
key_decisions:
  - Added GPU support (nvidia.com/gpu) as a `gpu` field on CloudRun and CloudRunJob configs
  - Added all volume types (cloud_sql_instance, gcs, nfs) to CloudRunVolume model shared between Service and Job
  - Added readiness_probe as a separate model from liveness/startup probes (different fields per TF spec)
  - Container-level fields (name, command, args, working_dir, depends_on) prefixed with `container_` to avoid collision with top-level fields
  - Cloud Function `secret_environment_variables` is now a proper schema field matching Terraform spec
duration: ""
verification_result: passed
completed_at: 2026-03-30T23:00:12.477Z
blocker_discovered: false
---

# T01: Audited and updated all 3 compute type schemas (Cloud Run, Cloud Run Job, Cloud Function) to full Terraform provider v7.25.0 spec coverage.

**Audited and updated all 3 compute type schemas (Cloud Run, Cloud Run Job, Cloud Function) to full Terraform provider v7.25.0 spec coverage.**

## What Happened

Audited all three compute types (Cloud Run Service, Cloud Run Job, Cloud Function) against the Terraform provider v7.25.0 specs using the Terraform MCP.\n\n**Cloud Run Service** had the most gaps: missing service-level description, launch_stage, default_uri_disabled, invoker_iam_disabled, iap_enabled, service-level scaling, encryption_key, node_selector, GPU support, health_check_disabled, gpu_zonal_redundancy_disabled. Container-level gaps: name, command, args, working_dir, base_image_uri, depends_on. Probe gaps: grpc, tcp_socket, readiness_probe, http_headers. Volume gaps: cloud_sql_instance, gcs, nfs, default_mode, sub_path.\n\n**Cloud Run Job** gaps: launch_stage, encryption_key, node_selector, GPU, container name/working_dir/depends_on, startup_probe, direct VPC access, cloud_sql/gcs/nfs volumes.\n\n**Cloud Function** gaps: description, kms_key_name, build_config.service_account/environment_variables/automatic_update_policy/on_deploy_update_policy, available_cpu, all_traffic_on_latest_revision, secret_environment_variables (as proper schema), direct_vpc_network_interface, binary_authorization_policy.\n\nAll gaps filled. Templates updated to render all new fields. All 225 unit tests pass. Backward compatibility verified — existing configs parse unchanged.

## Verification

All 225 unit tests pass. Backward compatibility verified with old and new config payloads.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest packages/tests/ -q --ignore=packages/tests/integration` | 0 | ✅ pass | 4530ms |
| 2 | `python3 -c 'backward compat check for CloudRunConfig, CloudRunJobConfig, CloudFunctionConfig'` | 0 | ✅ pass | 500ms |


## Deviations

CfSecretVolume field renamed from `versions` (was incorrectly inheriting `versions` list internally). Added `CfSecretEnvVar`, `CfDirectVpcNetworkInterface` as new models. Updated one test assertion that was preventing `secret_environment_variables` from existing on CloudFunctionConfig.

## Known Issues

None.

## Files Created/Modified

- `packages/core/schemas/configs/cloud_run.py`
- `packages/core/schemas/configs/cloud_run_job.py`
- `packages/core/schemas/configs/cloud_function.py`
- `packages/core/terraform/templates/cloud_run.tf.j2`
- `packages/core/terraform/templates/cloud_run_job.tf.j2`
- `packages/core/terraform/templates/cloud_function.tf.j2`
- `packages/tests/test_env_vars.py`


## Deviations
CfSecretVolume field renamed from `versions` (was incorrectly inheriting `versions` list internally). Added `CfSecretEnvVar`, `CfDirectVpcNetworkInterface` as new models. Updated one test assertion that was preventing `secret_environment_variables` from existing on CloudFunctionConfig.

## Known Issues
None.
