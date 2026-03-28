# Phase 3: Terraform Output Surfacing and Post-Deploy User Action Guidance - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Surface structured Terraform output values (URLs, IPs, connection strings) after deploys complete, stored in Firestore and accessible via a dedicated MCP tool. Only external-facing outputs are surfaced — internal infrastructure references (VPC self_link, subnet IDs) are excluded.

**Scope narrowing:** The "post-deploy user action guidance" part of the phase name is **deferred**. This phase delivers structured output extraction and storage only. Guidance/next-steps hints will be a future concern.

</domain>

<decisions>
## Implementation Decisions

### Output Generation
- **D-01:** Generate Terraform `output {}` blocks by wiring registry `default_outputs` into Jinja2 templates. Each template gets output blocks for its node type's meaningful external values.
- **D-02:** Only external-facing outputs are generated — Cloud Run URLs, external LB IPs, Cloud SQL connection strings, secret resource IDs, DNS name servers, etc. Internal-only values (VPC self_link, subnet ID, connector name) are NOT surfaced as TF outputs.

### Output Capture from Cloud Build
- **D-03:** Add a new Cloud Build step after `terraform apply` that runs `terraform output -json` and writes the JSON result to GCS (alongside existing plan/apply output files). The deploy orchestrator fetches this like it already fetches plan_output/apply_output.

### Storage
- **D-04:** Parsed outputs stored in **both** locations:
  - **Deploy record** (`tenants/{uid}/deploys/{id}`) — `terraform_outputs` field for deploy-specific history/snapshot
  - **Environment-level document** (`tenants/{uid}/projects/{ref}/env_outputs/{env}`) — latest outputs, overwritten on each successful deploy for quick agent lookup

### Agent Delivery
- **D-05:** New dedicated MCP tool: `get_deploy_outputs(project_ref_id, env_name)` returns the latest structured outputs for an environment. Clean, discoverable interface — agent asks "what's deployed?" without needing a deploy_id.
- **D-06:** Existing `get_deploy_status` response is NOT modified — outputs live in the new dedicated tool.

### Post-Deploy Guidance
- **D-07:** Deferred. This phase surfaces structured output values only. Per-node "next steps" hints (e.g., "run migration", "test at URL") are a future phase concern.

### Claude's Discretion
- Which specific `default_outputs` per node type qualify as "external-facing" vs internal
- Output block naming convention in generated Terraform
- JSON schema for the `terraform_outputs` Firestore field
- GCS path/naming for the terraform output JSON file
- Error handling when `terraform output -json` step fails

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Terraform Generation
- `packages/core/terraform/generator.py` — Main TF generation entry point; output blocks must integrate here
- `packages/core/terraform/templates/*.tf.j2` — All 23 Jinja2 templates; each needs output block additions for external-facing values
- `packages/core/terraform/resolver.py` — Node reference resolution (for understanding TF resource naming)

### Registry & Schema
- `packages/core/registry.py` — REGISTRY dict with `default_outputs` per node type — the source of truth for what each node exposes
- `packages/core/schemas/base.py` — BaseNode model with `outputs` field, NodeOutput schema

### Deploy Pipeline
- `packages/platform/deploy_orchestrator.py` — `_run_deploy()` background task; fetches plan/apply output from GCS; needs to also fetch terraform output JSON
- `packages/platform/gcp/cloud_build.py` — Cloud Build submission and output retrieval; needs new `get_build_terraform_output()` function and Cloud Build step
- `packages/platform/store/deploys.py` — Deploy record CRUD; needs `terraform_outputs` field support

### MCP Tools
- `packages/mcp/tools/deploy.py` — Existing deploy MCP tools; new `get_deploy_outputs` tool lives here or in a new module
- `packages/mcp/tools/builds.py` — Build output retrieval; reference for GCS output fetching pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Registry `default_outputs`** (`packages/core/registry.py`): Already defines output tuples per node type (e.g., Cloud Run: url, service_account_email). Direct source for which TF outputs to generate.
- **GCS output fetching pattern** (`packages/platform/gcp/cloud_build.py`): `get_build_plan_output()` and `get_build_apply_output()` already fetch text from GCS by build ID. Same pattern extends to terraform output JSON.
- **Deploy orchestrator output flow** (`packages/platform/deploy_orchestrator.py`): Already fetches plan/apply text and stores on deploy record. Adding terraform_outputs follows the identical pattern.
- **MCP tool patterns** (`packages/mcp/tools/deploy.py`): Existing deploy tools show the lazy-load, format_json_response, format_error patterns to follow.

### Established Patterns
- **Jinja2 template rendering**: Templates receive `node`, `global_cfg`, `resolve_ref()`, `nodes` as context. Output blocks can be appended to existing templates.
- **Cloud Build step structure**: `submit_terraform_build()` in `cloud_build.py` defines the build steps. A new step for `terraform output -json` follows the existing init/plan/apply pattern.
- **Deploy record fields**: `plan_output` and `apply_output` are stored as nullable strings. `terraform_outputs` will be a JSON dict.

### Integration Points
- **Generator → Templates**: `generate_terraform()` renders each node's template. Output blocks either go in per-node templates or a separate outputs.tf file.
- **Cloud Build → GCS → Orchestrator → Firestore**: Existing pipeline for plan/apply text. Terraform output JSON follows same path.
- **MCP tool → Firestore env_outputs doc**: New read path for the `get_deploy_outputs` tool.

</code_context>

<specifics>
## Specific Ideas

- The registry `default_outputs` is the single source of truth for which values each node type can expose. The researcher should catalog which of these are "external-facing" vs internal.
- Cloud Build step order: init → plan → apply → output. The output step only runs if apply succeeds.
- The env-level output document enables a fast "what's live?" query without scanning deploy history.

</specifics>

<deferred>
## Deferred Ideas

- **Post-deploy guidance/next-steps hints** — Originally part of this phase name, but explicitly deferred. Per-node action guidance (e.g., "run migration", "configure DNS") is a future phase.
- **Output-based cross-node wiring** — Using actual deployed output values to configure dependent resources at runtime (not just Terraform references).
- **Drift detection** — Comparing stored outputs against live infrastructure state.

</deferred>

---

*Phase: 03-terraform-output-surfacing-and-post-deploy-user-action-guidance*
*Context gathered: 2026-03-28*
