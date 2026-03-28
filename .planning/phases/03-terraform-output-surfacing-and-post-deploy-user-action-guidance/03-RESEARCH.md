# Phase 3: Terraform Output Surfacing - Research

**Researched:** 2026-03-28
**Domain:** Terraform output generation, Cloud Build pipeline extension, Firestore storage, MCP tool development
**Confidence:** HIGH

## Summary

This phase adds Terraform `output {}` block generation to the existing Jinja2 template pipeline, captures the JSON output from `terraform output -json` via a new Cloud Build step, stores parsed results in Firestore (both deploy record and env-level document), and exposes them through a new MCP tool.

The codebase is well-structured for this work. The registry already defines `default_outputs` per node type, templates follow a consistent pattern that can be extended with output blocks, the Cloud Build pipeline has a clear step-based architecture with GCS result storage, and the deploy orchestrator already fetches plan/apply text from GCS. Every integration point follows an established pattern that this phase extends.

**Primary recommendation:** Generate output blocks as a dedicated `outputs.tf` file in `generate_terraform()` rather than appending to individual templates. This keeps templates clean, centralizes output naming conventions, and makes the output file independently testable.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Generate Terraform `output {}` blocks by wiring registry `default_outputs` into Jinja2 templates. Each template gets output blocks for its node type's meaningful external values.
- **D-02:** Only external-facing outputs are generated -- Cloud Run URLs, external LB IPs, Cloud SQL connection strings, secret resource IDs, DNS name servers, etc. Internal-only values (VPC self_link, subnet ID, connector name) are NOT surfaced as TF outputs.
- **D-03:** Add a new Cloud Build step after `terraform apply` that runs `terraform output -json` and writes the JSON result to GCS (alongside existing plan/apply output files). The deploy orchestrator fetches this like it already fetches plan_output/apply_output.
- **D-04:** Parsed outputs stored in both locations: deploy record (`tenants/{uid}/deploys/{id}`) as `terraform_outputs` field AND environment-level document (`tenants/{uid}/projects/{ref}/env_outputs/{env}`) as latest outputs overwritten on each successful deploy.
- **D-05:** New dedicated MCP tool: `get_deploy_outputs(project_ref_id, env_name)` returns the latest structured outputs for an environment.
- **D-06:** Existing `get_deploy_status` response is NOT modified -- outputs live in the new dedicated tool.
- **D-07:** Post-deploy guidance deferred. This phase surfaces structured output values only.

### Claude's Discretion
- Which specific `default_outputs` per node type qualify as "external-facing" vs internal
- Output block naming convention in generated Terraform
- JSON schema for the `terraform_outputs` Firestore field
- GCS path/naming for the terraform output JSON file
- Error handling when `terraform output -json` step fails

### Deferred Ideas (OUT OF SCOPE)
- Post-deploy guidance/next-steps hints -- per-node action guidance is a future phase
- Output-based cross-node wiring -- using deployed values to configure dependent resources at runtime
- Drift detection -- comparing stored outputs against live infrastructure state
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | (existing) | Template rendering for output blocks | Already used for all TF templates |
| google-cloud-storage | (existing) | Fetch terraform output JSON from GCS | Already used for plan/apply output |
| google-cloud-firestore | >= 2.16 | Store parsed outputs in deploy record and env_outputs doc | Already used throughout platform |
| mcp | >= 1.26.0 | New `get_deploy_outputs` tool | Already used for all MCP tools |

### Supporting
No new dependencies required. This phase extends existing libraries and patterns only.

**Installation:** No new packages needed.

## Architecture Patterns

### Output Generation Strategy: Dedicated outputs.tf

Generate a single `outputs.tf` file in `generate_terraform()` rather than appending output blocks to individual `.tf.j2` templates.

**Rationale:**
- Templates are already complex (external_lb.tf.j2 is 83 lines with 5 resources)
- Output blocks reference resource attributes that are static per-type (no config-conditional logic)
- A dedicated file is independently testable
- Matches how `iam_bindings.tf` and `api_services.tf` are already generated as standalone files in `generator.py`

**Implementation:** New `_render_outputs()` function in `generator.py`, following the exact pattern of `_render_iam_bindings()` and `_render_api_services()`.

### Recommended Changes by File

```
packages/core/terraform/generator.py    # Add _render_outputs() function
packages/platform/gcp/cloud_build.py    # Add CB step + get_build_terraform_output()
packages/platform/deploy_orchestrator.py # Fetch TF output, store in deploy record + env_outputs
packages/platform/store/deploys.py      # Accept terraform_outputs in update_deploy_status
packages/mcp/tools/deploy.py            # Add get_deploy_outputs() MCP tool
```

### Pattern 1: Output Block Generation

**What:** Iterate registry entries for all nodes in the blueprint, filter to external-facing outputs, generate `output "node_attr" {}` blocks.

**When to use:** Called during `generate_terraform()` after resource blocks.

```python
# In generator.py -- follows _render_iam_bindings() pattern
def _render_outputs(nodes: list) -> str:
    """Generate TF output blocks for external-facing node attributes."""
    lines = [
        '# Auto-generated outputs for external-facing resource attributes',
        '# Managed by the orchestration platform',
        '',
    ]
    for node in nodes:
        defn = REGISTRY.get(node.type)
        if not defn or not defn.terraform_resource:
            continue
        if node.type.value in _EMBEDDED_CHILD_TYPES:
            continue
        for out in defn.default_outputs:
            if not _is_external_output(node.type.value, out["name"]):
                continue
            output_name = f"{node.name}_{out['name']}"
            tf_ref = f"{defn.terraform_resource}.{node.name}.{out['name']}"
            lines.append(f'output "{output_name}" {{')
            lines.append(f'  value = {tf_ref}')
            lines.append(f'}}')
            lines.append('')
    if len(lines) <= 3:  # only header
        return ""
    return "\n".join(lines)
```

### Pattern 2: Cloud Build Step Extension

**What:** Add a third Cloud Build step that runs `terraform output -json` and writes to GCS.

**Current pipeline:**
1. Step 1: `terraform init && terraform plan && terraform apply` (writes plan.txt + apply.txt)
2. Step 2: `gsutil cp` plan.txt and apply.txt to GCS results

**New pipeline:**
1. Step 1: (unchanged) terraform init/plan/apply
2. Step 2: (unchanged) gsutil cp plan/apply
3. Step 3 (NEW): `terraform output -json > /workspace/outputs.json && gsutil cp /workspace/outputs.json gs://{bucket}/results/$BUILD_ID/outputs.json`

```python
# New Cloud Build step in cloud_build.py submit_terraform_build()
cloudbuild_v1.BuildStep(
    name="hashicorp/terraform:1.7.5",
    entrypoint="sh",
    args=["-c", "terraform output -json > /workspace/outputs.json"],
),
cloudbuild_v1.BuildStep(
    name="gcr.io/cloud-builders/gsutil",
    entrypoint="sh",
    args=[
        "-c",
        (
            f"gsutil cp /workspace/outputs.json "
            f"gs://{cb_source_bucket}/results/$BUILD_ID/outputs.json 2>/dev/null; "
            "true"
        ),
    ],
),
```

### Pattern 3: GCS Output Fetch (follows existing pattern)

```python
# In cloud_build.py -- exact same pattern as get_build_plan_output
def get_build_terraform_output(host_project_id: str, build_id: str) -> dict | None:
    """Fetch the terraform output JSON from GCS results bucket."""
    import json
    cb_source_bucket = os.environ.get("CB_SOURCE_BUCKET", f"{host_project_id}-cb-source")
    try:
        client = _get_storage_client()
        bucket = client.bucket(cb_source_bucket)
        blob = bucket.blob(f"results/{build_id}/outputs.json")
        raw = blob.download_as_text()
        return json.loads(raw)
    except Exception:
        log.warning("Could not fetch terraform output for build %s", build_id)
        return None
```

### Pattern 4: MCP Tool (follows existing deploy.py pattern)

```python
@mcp.tool()
def get_deploy_outputs(
    project_ref_id: str,
    env_name: str = "dev",
) -> str:
    """Get the latest Terraform outputs for a deployed environment.

    Returns structured output values (URLs, IPs, connection strings) from
    the most recent successful deploy. Use this to discover what's running.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment to query (default: "dev").
    """
    try:
        _ensure_deps()
        tenant_id = get_tenant_id()
        # Read from env_outputs/{env} for fast lookup
        doc = _get_env_outputs(tenant_id, project_ref_id, env_name)
        if not doc:
            return format_error("not_found",
                f"No outputs found for '{env_name}'. Deploy first.")
        return format_json_response(doc)
    except Exception as e:
        return format_error("get_deploy_outputs_error", str(e))
```

### Anti-Patterns to Avoid
- **Appending output blocks inside .tf.j2 templates:** Mixes static output definitions with config-conditional resource rendering. Output attributes are deterministic per resource type -- they don't depend on node config.
- **Modifying get_deploy_status response:** D-06 explicitly forbids this. Outputs have their own tool.
- **Parsing terraform apply text for output values:** Fragile regex parsing. Use `terraform output -json` which returns structured JSON.
- **Storing outputs as a flat string:** The JSON structure from `terraform output -json` is already well-structured. Store as a dict/map in Firestore, not as a serialized string.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TF output parsing | Custom apply text parser | `terraform output -json` | Built-in, structured JSON, handles all types |
| GCS blob fetch | Custom HTTP client | `google-cloud-storage` Client | Already used, handles auth/retry |
| JSON serialization | Manual string building | `json.dumps/loads` | Standard, handles edge cases |

## Registry Output Classification (External vs Internal)

This is a key discretion area. Based on D-02 criteria ("external-facing" = URLs, IPs, connection strings, resource IDs usable by developers/agents; "internal" = infrastructure wiring values only useful for TF cross-references):

| Node Type | TF Resource | Output Name | Classification | Rationale |
|-----------|-------------|-------------|---------------|-----------|
| **cloud_run** | google_cloud_run_v2_service | `uri` | EXTERNAL | Service URL -- primary user value |
| cloud_run | | `name` | SKIP | Internal TF reference |
| cloud_run | | `latest_revision` | SKIP | Internal revision tracking |
| **cloud_run_job** | google_cloud_run_v2_job | `name` | EXTERNAL | Job name needed for execution |
| cloud_run_job | | `id` | SKIP | Internal TF ID |
| **cloud_function** | google_cloudfunctions2_function | `url` | EXTERNAL | Function HTTP URL |
| cloud_function | | `name` | SKIP | Internal name |
| **cloud_sql** | google_sql_database_instance | `connection_name` | EXTERNAL | Used for Cloud SQL Auth Proxy |
| cloud_sql | | `private_ip_address` | EXTERNAL | For private network access |
| cloud_sql | | `public_ip_address` | EXTERNAL | If public IP is enabled |
| cloud_sql | | `self_link` | SKIP | Internal TF reference |
| **external_lb** | google_compute_global_address | `address` | EXTERNAL | LB IP address -- primary user value |
| external_lb | | `self_link` | SKIP | Internal TF reference |
| **cloud_dns** | google_dns_managed_zone | `name_servers` | EXTERNAL | NS records user must configure at registrar |
| cloud_dns | | `dns_name` | EXTERNAL | Zone DNS name for verification |
| **gcs_bucket** | google_storage_bucket | `url` | EXTERNAL | Bucket URL (gs://...) |
| gcs_bucket | | `self_link` | SKIP | Internal TF reference |
| **secret_manager** | google_secret_manager_secret | `secret_id` | EXTERNAL | Secret resource ID for SDK access |
| secret_manager | | `name` | EXTERNAL | Full resource name (projects/X/secrets/Y) |
| secret_manager | | `version` | SKIP | Not a real attribute on the secret resource |
| **firestore** | google_firestore_database | `name` | EXTERNAL | Database resource name |
| **bigquery** | google_bigquery_dataset | `dataset_id` | EXTERNAL | Dataset ID for queries |
| **bigtable** | google_bigtable_instance | `name` | EXTERNAL | Instance name for SDK |
| **pubsub_topic** | google_pubsub_topic | `id` | EXTERNAL | Full topic resource path |
| **pubsub_subscription** | google_pubsub_subscription | `id` | EXTERNAL | Full subscription resource path |
| **pubsub_schema** | google_pubsub_schema | `id` | EXTERNAL | Schema resource path |
| **cloud_task_queue** | google_cloud_tasks_queue | `id` | EXTERNAL | Queue resource path |
| **service_account** | google_service_account | `email` | EXTERNAL | SA email for configuration |
| service_account | | `unique_id` | SKIP | Internal GCP ID |
| service_account | | `name` | SKIP | Internal resource name |
| **vpc** | google_compute_network | all | SKIP (all) | D-02: VPC outputs are internal |
| **subnet** | google_compute_subnetwork | all | SKIP (all) | D-02: Subnet outputs are internal |
| **vpc_connector** | google_vpc_access_connector | all | SKIP (all) | D-02: Connector outputs are internal |

### Important: Registry default_outputs vs Actual TF Attributes

The registry `default_outputs` names don't always match actual Terraform resource attribute names. Key corrections needed:

| Node Type | Registry Output Name | Actual TF Attribute | Notes |
|-----------|---------------------|---------------------|-------|
| cloud_run | `endpoint` | `uri` | google_cloud_run_v2_service exports `uri`, not `endpoint` |
| cloud_run | `latest_revision` | N/A (computed, nested) | Not directly available as top-level attribute |
| cloud_function | `endpoint` | `url` | google_cloudfunctions2_function exports `url` (inside service_config) |
| cloud_sql | `private_ip` | `private_ip_address` | Actual attribute name differs |
| external_lb | `ip_address` | `address` | google_compute_global_address exports `address` |
| gcs_bucket | `bucket` | `name` | The actual bucket name attribute |
| gcs_bucket | `url` | `url` | This one matches |
| pubsub_topic | `topic` | `id` | Full resource path |
| pubsub_subscription | `subscription` | `id` | Full resource path |
| cloud_task_queue | `queue` | `id` | Full resource path |
| bigtable | `instance` | `name` | Actual attribute |
| bigquery | `dataset` | `dataset_id` | Actual attribute |
| cloud_dns | `name_servers` | `name_servers` | Matches (list type) |

**Confidence: HIGH** -- These attribute names are from the Google Terraform provider documentation. The `google_cloud_run_v2_service` resource exports `uri` as the service URL. The `google_cloudfunctions2_function` exports `url` nested under `service_config[0].uri`. The `google_compute_global_address` exports `address`.

### Output Naming Convention Recommendation

Use `{node_name}_{semantic_name}` pattern:
- `my-api_url` (Cloud Run service URL)
- `my-db_connection_name` (Cloud SQL connection name)
- `my-lb_ip_address` (External LB IP)
- `my-zone_name_servers` (DNS name servers)

This is human-readable and avoids collisions. The semantic name maps to what the value IS, not the TF attribute name.

## terraform output -json Format

The `terraform output -json` command returns a JSON object:

```json
{
  "my-api_url": {
    "sensitive": false,
    "type": "string",
    "value": "https://dev-my-api-abc123-uc.a.run.app"
  },
  "my-db_connection_name": {
    "sensitive": false,
    "type": "string",
    "value": "dev-project:us-central1:dev-my-db"
  },
  "my-zone_name_servers": {
    "sensitive": false,
    "type": ["list", "string"],
    "value": ["ns-cloud-a1.googledomains.com.", "ns-cloud-a2.googledomains.com."]
  }
}
```

### Recommended Firestore Schema for terraform_outputs

Flatten the TF output JSON into a simpler structure for agent consumption:

```json
{
  "outputs": {
    "my-api_url": "https://dev-my-api-abc123-uc.a.run.app",
    "my-db_connection_name": "dev-project:us-central1:dev-my-db",
    "my-zone_name_servers": ["ns-cloud-a1.googledomains.com.", "..."]
  },
  "by_node": {
    "my-api": {
      "url": "https://dev-my-api-abc123-uc.a.run.app",
      "node_type": "cloud_run"
    },
    "my-db": {
      "connection_name": "dev-project:us-central1:dev-my-db",
      "private_ip_address": "10.0.0.5",
      "node_type": "cloud_sql"
    }
  },
  "captured_at": "2026-03-28T20:30:00Z",
  "deploy_id": "abc123",
  "env_name": "dev"
}
```

The `by_node` grouping makes it easy for agents to ask "what outputs does node X have?" The flat `outputs` map preserves the raw TF output keys.

## Cloud Build Step Considerations

### Current Step Structure (cloud_build.py lines 131-162)

```python
steps=[
    # Step 0: terraform init + plan + apply
    BuildStep(name="hashicorp/terraform:1.7.5", ...),
    # Step 1: gsutil copy plan.txt + apply.txt to GCS
    BuildStep(name="gcr.io/cloud-builders/gsutil", ...),
]
```

### Proposed Step Structure

```python
steps=[
    # Step 0: terraform init + plan + apply (unchanged)
    BuildStep(name="hashicorp/terraform:1.7.5", ...),
    # Step 1: terraform output -json (NEW -- runs in same workspace with state)
    BuildStep(
        name="hashicorp/terraform:1.7.5",
        entrypoint="sh",
        args=["-c", "terraform output -json > /workspace/outputs.json 2>/dev/null || echo '{}' > /workspace/outputs.json"],
    ),
    # Step 2: gsutil copy plan.txt + apply.txt + outputs.json to GCS
    BuildStep(name="gcr.io/cloud-builders/gsutil", ...),  # updated to also copy outputs.json
]
```

**Key detail:** The terraform output step must use the SAME terraform image (`hashicorp/terraform:1.7.5`) because the workspace has the initialized state. The `|| echo '{}'` fallback ensures the step doesn't fail if there are no outputs.

**GCS path:** `gs://{cb_source_bucket}/results/{build_id}/outputs.json` -- follows existing pattern for plan.txt and apply.txt.

### plan_only Mode

When `mode == "plan_only"`, the output step should be SKIPPED since no apply has occurred and outputs won't reflect reality. Only add the terraform output step when mode is `plan_and_apply`.

## Common Pitfalls

### Pitfall 1: Terraform State Initialization Race
**What goes wrong:** The `terraform output -json` step fails because TF state isn't initialized.
**Why it happens:** If placed as a separate step, the workspace might not have state context.
**How to avoid:** Use the same terraform Docker image. Cloud Build preserves `/workspace` across steps. State is in the GCS backend, and `terraform output` re-reads it.
**Warning signs:** Empty `{}` output or "Backend initialization required" errors.

### Pitfall 2: Output Name Collisions
**What goes wrong:** Two nodes with similar names produce duplicate output keys.
**Why it happens:** Output names like `url` without node prefix.
**How to avoid:** Always prefix with node name: `{node_name}_{attribute}`.
**Warning signs:** Terraform validation errors about duplicate output names.

### Pitfall 3: Cloud Function URL Attribute Path
**What goes wrong:** `google_cloudfunctions2_function.name.url` doesn't resolve.
**Why it happens:** CF v2 URL is nested at `service_config[0].uri`, not a top-level attribute.
**How to avoid:** Use the correct attribute path: `google_cloudfunctions2_function.{name}.service_config[0].uri`.
**Warning signs:** Terraform plan errors about unknown attributes.

### Pitfall 4: DNS name_servers is a List
**What goes wrong:** Treating DNS `name_servers` as a string in output block.
**Why it happens:** Most outputs are strings, but name_servers is a list.
**How to avoid:** No special handling needed -- Terraform `output` blocks accept any type. `terraform output -json` serializes lists correctly.
**Warning signs:** None -- this just works, but the Firestore schema must handle list values.

### Pitfall 5: Cloud Run v2 Service URI Attribute
**What goes wrong:** Using `endpoint` or `url` attribute name on `google_cloud_run_v2_service`.
**Why it happens:** Registry calls it "endpoint" but the actual TF attribute is `uri`.
**How to avoid:** Map registry names to actual TF attribute names in the output generation code.
**Warning signs:** Terraform validation errors about missing attributes.

### Pitfall 6: Firestore Document Size Limits
**What goes wrong:** Env outputs doc exceeds 1 MiB Firestore limit for very large blueprints.
**Why it happens:** Hundreds of output values accumulating.
**How to avoid:** External outputs only (filtering internal values per D-02 already limits this). A typical blueprint with 20 nodes produces ~40 output values at most -- well under 1 MiB.
**Warning signs:** Firestore write failures on large blueprints.

## Code Examples

### Output Generation Function (verified pattern from generator.py)

```python
# Follows _render_iam_bindings() pattern at generator.py:136-217

# Map of (node_type, registry_output_name) -> actual TF attribute
_OUTPUT_ATTR_MAP: dict[tuple[str, str], str] = {
    ("cloud_run", "endpoint"): "uri",
    ("cloud_function", "endpoint"): "service_config[0].uri",
    ("cloud_sql", "connection_name"): "connection_name",
    ("cloud_sql", "private_ip"): "private_ip_address",
    ("external_lb", "ip_address"): "address",
    ("gcs_bucket", "bucket"): "name",
    ("gcs_bucket", "url"): "url",
    ("cloud_dns", "name_servers"): "name_servers",
    ("cloud_dns", "dns_name"): "dns_name",
    ("secret_manager", "secret_id"): "secret_id",
    ("secret_manager", "name"): "name",
    ("firestore", "database"): "name",
    ("bigquery", "dataset"): "dataset_id",
    ("bigtable", "instance"): "name",
    ("pubsub_topic", "topic"): "id",
    ("pubsub_subscription", "subscription"): "id",
    ("pubsub_schema", "name"): "id",
    ("cloud_task_queue", "queue"): "id",
    ("service_account", "email"): "email",
    ("cloud_run_job", "job_name"): "name",
}

# Node types whose outputs are all internal (D-02)
_INTERNAL_ONLY_TYPES = {"vpc", "subnet", "vpc_connector"}

def _render_outputs(nodes: list) -> str:
    lines = [
        '# Auto-generated outputs for external-facing resource attributes',
        '# Managed by the orchestration platform',
        '',
    ]
    for node in nodes:
        defn = REGISTRY.get(node.type)
        if not defn or not defn.terraform_resource:
            continue
        ntype = node.type.value if hasattr(node.type, 'value') else str(node.type)
        if ntype in _INTERNAL_ONLY_TYPES or ntype in _EMBEDDED_CHILD_TYPES:
            continue

        for out in defn.default_outputs:
            attr_key = (ntype, out["name"])
            tf_attr = _OUTPUT_ATTR_MAP.get(attr_key)
            if not tf_attr:
                continue  # Not mapped = not external

            output_name = f"{node.name}_{out['name']}"
            tf_ref = f"{defn.terraform_resource}.{node.name}.{tf_attr}"
            lines.append(f'output "{output_name}" {{')
            lines.append(f'  value       = {tf_ref}')
            lines.append(f'  description = "{node.name} {out["name"]}"')
            lines.append(f'}}')
            lines.append('')

    if len(lines) <= 3:
        return ""
    return "\n".join(lines)
```

### Deploy Orchestrator Integration (verified pattern from deploy_orchestrator.py)

```python
# After line 173 in deploy_orchestrator.py (after fetching plan/apply):

# Step 5.5: Fetch terraform outputs from GCS
from packages.platform.gcp.cloud_build import get_build_terraform_output
tf_outputs_raw = get_build_terraform_output(host_project_id, build_id)
tf_outputs = _parse_terraform_outputs(tf_outputs_raw) if tf_outputs_raw else None

# In the SUCCESS branch, store terraform_outputs:
update_deploy_status(
    tenant_id, deploy_id, "ready",
    terraform_outputs=tf_outputs,  # NEW field
    ...
)

# Also write to env_outputs document:
if tf_outputs:
    from packages.platform.store.deploys import save_env_outputs
    save_env_outputs(tenant_id, project_ref_id, env_name, tf_outputs, deploy_id)
```

### Env Outputs Firestore Helper

```python
# In packages/platform/store/deploys.py

def save_env_outputs(tenant_id: str, project_ref_id: str, env_name: str,
                     outputs: dict, deploy_id: str):
    """Write latest TF outputs to env_outputs/{env} for fast agent lookup."""
    from datetime import datetime, timezone
    ref = _project_ref(tenant_id, project_ref_id).collection("env_outputs").document(env_name)
    ref.set({
        "outputs": outputs.get("outputs", {}),
        "by_node": outputs.get("by_node", {}),
        "deploy_id": deploy_id,
        "captured_at": datetime.now(timezone.utc),
    })


def get_env_outputs(tenant_id: str, project_ref_id: str, env_name: str) -> dict | None:
    """Read latest TF outputs for an environment."""
    ref = _project_ref(tenant_id, project_ref_id).collection("env_outputs").document(env_name)
    doc = ref.get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    if "captured_at" in data and hasattr(data["captured_at"], "isoformat"):
        data["captured_at"] = data["captured_at"].isoformat()
    return data
```

## External LB Note: Multiple Resources

The `external_lb.tf.j2` template generates 5+ TF resources from a single node:
- `google_compute_global_address.{name}_ip`
- `google_compute_managed_ssl_certificate.{name}_cert`
- `google_compute_region_network_endpoint_group.{name}_neg`
- `google_compute_backend_service.{name}_backend`
- `google_compute_url_map.{name}_url_map`
- `google_compute_target_https_proxy.{name}_proxy`
- `google_compute_global_forwarding_rule.{name}_fwd`

The output block for the IP address must reference `google_compute_global_address.{name}_ip.address` (note the `_ip` suffix in the TF resource name). This differs from the standard `{terraform_resource}.{node_name}` pattern. The `_OUTPUT_ATTR_MAP` needs to handle this special case.

Similarly, Cloud SQL generates `google_sql_database_instance.{name}` (no suffix), so the standard pattern works.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Parse apply text for outputs | `terraform output -json` | TF 0.12+ | Structured, typed JSON output |
| Store outputs as strings | Store as Firestore map | N/A | Native querying, no serialization overhead |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio |
| Config file | `packages/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd packages && python -m pytest tests/ -x -q` |
| Full suite command | `cd packages && python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | Output blocks generated in outputs.tf | unit | `cd packages && python -m pytest tests/test_terraform_outputs.py -x` | Wave 0 |
| D-02 | Only external outputs included, internal excluded | unit | `cd packages && python -m pytest tests/test_terraform_outputs.py::TestOutputClassification -x` | Wave 0 |
| D-03 | Cloud Build step added for terraform output | unit | `cd packages && python -m pytest tests/test_terraform_outputs.py::TestCloudBuildOutput -x` | Wave 0 |
| D-04 | Outputs stored in deploy record + env_outputs | unit | `cd packages && python -m pytest tests/test_terraform_outputs.py::TestOutputStorage -x` | Wave 0 |
| D-05 | MCP tool returns env outputs | unit | `cd packages && python -m pytest tests/test_terraform_outputs.py::TestMcpGetOutputs -x` | Wave 0 |
| D-06 | get_deploy_status unchanged | unit | `cd packages && python -m pytest tests/test_mcp_tools_ops.py -x` | Existing |

### Sampling Rate
- **Per task commit:** `cd packages && python -m pytest tests/test_terraform_outputs.py -x -q`
- **Per wave merge:** `cd packages && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `packages/tests/test_terraform_outputs.py` -- covers D-01 through D-05 (output generation, classification, CB step, storage, MCP tool)
- [ ] `packages/tests/conftest.py` -- may need new fixture for envelope with external outputs

## Open Questions

1. **Cloud Function URL attribute path**
   - What we know: CF v2 exports URL at `service_config[0].uri` -- a nested computed attribute
   - What's unclear: Whether `google_cloudfunctions2_function.name.service_config[0].uri` works in a TF output block, or if it requires a `locals {}` intermediate
   - Recommendation: Test with a simple TF config. If nested path doesn't work in output blocks, use `google_cloudfunctions2_function.name.url` (deprecated alias) or skip CF URL output and note for future fix.

2. **External LB resource naming suffix**
   - What we know: Template uses `{name}_ip` suffix for the global address resource
   - What's unclear: Whether the `_OUTPUT_ATTR_MAP` approach cleanly handles resources with non-standard TF names
   - Recommendation: Add an optional `tf_resource_suffix` to the output map entries, defaulting to empty string. For external_lb IP: suffix is `_ip`.

## Sources

### Primary (HIGH confidence)
- `packages/core/registry.py` -- full REGISTRY with all 22 node types and default_outputs
- `packages/core/terraform/generator.py` -- current TF generation pipeline, _render_iam_bindings pattern
- `packages/platform/gcp/cloud_build.py` -- Cloud Build step structure, GCS output fetch pattern
- `packages/platform/deploy_orchestrator.py` -- deploy pipeline, plan/apply fetch flow
- `packages/platform/store/deploys.py` -- deploy record CRUD, update_deploy_status signature
- `packages/mcp/tools/deploy.py` -- MCP tool patterns (lazy-load, format_json_response, format_error)
- All 22 Jinja2 templates in `packages/core/terraform/templates/` -- resource naming conventions

### Secondary (MEDIUM confidence)
- Terraform Google provider documentation for resource attribute names (uri, address, connection_name, etc.)
- `terraform output -json` format specification

### Tertiary (LOW confidence)
- Cloud Function v2 `service_config[0].uri` nesting -- needs runtime validation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns verified in codebase
- Architecture: HIGH -- follows established patterns (_render_iam_bindings, GCS fetch, MCP tools)
- Output classification: HIGH -- based on D-02 criteria and registry analysis
- TF attribute mapping: MEDIUM -- attribute names from provider docs, but CF URL nesting needs validation
- Pitfalls: HIGH -- identified from codebase analysis and TF knowledge

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable domain -- TF provider attributes rarely change)
