# M002 Context: Resource Identity, Reference Contracts & Naming Conventions

## What Was Done in M001

Core package (`packages/core/`) is now a standalone pure-infra layer:
- **20 resource type schemas** audited against Terraform provider v7.25.0 (~100 fields added)
- **Templates produce valid HCL** — 30 terraform validate tests (27 pass, 3 xfail for edge cases)
- **Package restructured** — `packages/core/{pyproject.toml, core/, tests/}` with `from core.X` imports
- **Dead code archived** — internalGraph, WorkflowDefinition, codegen, client_generator all removed
- **BaseNode stripped to 5 fields**: `slug, name, type, depends_on, config` (extra="allow")
- **Core Explorer** built at `packages/core/explorer/` — standalone web UI for testing all core features
- **Service Contract spec** written at `docs/specs/service-contract.md` for future logical dependency layer

## The Problem M002 Solves

Three structural issues in core:

### 1. Identity — name conflation
`BaseNode.name` serves as blueprint identity, TF resource label, GCP name root, AND display name. Renaming breaks `depends_on`, triggers TF destroy/create. Need UUID-based stable identity.

### 2. References — ad-hoc wiring
~30 config fields across 20+ types reference other nodes. Each handled ad-hoc in templates via `resolve_ref()` with two inconsistent patterns (`node:X.Y` prefix check vs bare name). No validation, no UI intelligence, no auto-dependency inference.

Reference fields found (from audit):
- **Subnet**: `config.network` → VPC
- **Cloud Run**: `config.service_account` → SA, `config.vpc_access.connector` → VPC Connector
- **Cloud Run Job**: `config.service_account` → SA, `config.vpc_access.connector` → VPC Connector
- **Cloud Function**: `config.service_account` → SA, `config.vpc_connector` → VPC Connector, `config.event_trigger.pubsub_topic` → PubSub Topic
- **PubSub Subscription**: `config.topic` → PubSub Topic, `config.dead_letter_policy.dead_letter_topic` → PubSub Topic
- **Cloud SQL**: `config.ip_configuration.private_network` → VPC
- **VPC Connector**: `config.network` → VPC, `config.subnet.name` → Subnet
- **Cloud DNS**: `config.peering_config.target_network.network_url` → VPC
- **External LB**: `config.default_backend.cloud_run_service` → Cloud Run
- **Env vars (all compute)**: `env_vars[].secret` → Secret Manager
- **Eventarc triggers**: `transport.pubsub_topic` → PubSub Topic
- **Cloud Task Queue**: `config.http_target.oidc_token.service_account_email` → SA
- **PubSub Subscription**: push/bigquery/cloud_storage service_account_email → SA
- Plus ~10 more nested refs in various configs

### 3. Naming — inconsistent derivation
GCP resource names derived differently per template:
- Most: `${var.environment}-${node.name}` (e.g. `dev-my-service`)
- Firestore: `config.database_id` (e.g. `(default)`)
- Service Account: `config.account_id`
- Bigtable: `config.instance_id`
- BigQuery: `config.friendly_name`

Some names are immutable after creation (Firestore, SA, Cloud SQL, BigQuery). Users need to know this.

## M002 Design

### Phase 1 (S01): UUID Identity
```python
class BaseNode(BaseModel, extra="allow"):
    id: str              # UUID — stable forever, used in depends_on, TF labels, refs
    name: str            # display name — freely renamable
    type: NodeType
    depends_on: list[str] = []  # list of node IDs
    config: dict | BaseModel = Field(default_factory=dict)
```
- Templates use `node.id` for TF resource labels
- Backward compat: old blueprints without `id` auto-generate from name
- `slug` field removed (replaced by `id`)

### Phase 2 (S02): Reference Contract
```python
class FieldRef(BaseModel):
    field: str           # dot-path: "config.network", "config.vpc_access.connector"
    target_type: NodeType
    tf_attribute: str    # what TF attribute to reference: "id", "email", "name"
    format: str = "ref"  # "ref" (TF resource ref) or "string" (quoted value)

RESOURCE_REFS: dict[NodeType, list[FieldRef]] = { ... }  # all ~30 fields
```
- Validation checks refs exist and target correct type
- Generator resolves refs from contract (no more ad-hoc template logic)
- DAG infers auto-dependencies from refs
- API exposes ref metadata for UI dropdowns

### Phase 3 (S03): Naming Convention
```python
class ComponentDefinition:
    # existing fields...
    gcp_name_source: str = "node.name"  # or "config.database_id" etc
    gcp_name_template: str = "${environment}-${name}"
    gcp_name_immutable: bool = False
    gcp_name_sanitize: str = "kebab"  # or "none"
```
- Templates consume naming from registry
- Immutable types flagged for UI warnings

### Phase 4 (S04): Explorer UI Updates
- Ref fields render as dropdowns filtered by target type
- GCP name preview shown per resource
- Rename works without breaking deps
- Immutable name warnings for SA, Firestore, SQL, BigQuery

## Key Decisions (from this session)
- **D005**: UUID id on BaseNode; depends_on uses IDs; name is display-only
- **D006**: RESOURCE_REFS contract for all cross-resource reference fields
- **D007**: Per-type gcp_name_source/template/immutable in ComponentDefinition

## Key Files
- `packages/core/core/schemas/base.py` — BaseNode definition
- `packages/core/core/registry.py` — ComponentDefinition + REGISTRY
- `packages/core/core/terraform/resolver.py` — resolve_node_ref (needs contract rewrite)
- `packages/core/core/terraform/generator.py` — template rendering + output generation
- `packages/core/core/terraform/templates/*.tf.j2` — 22 Jinja2 templates (all need updating)
- `packages/core/core/validation.py` — needs ref validation from contract
- `packages/core/core/dag.py` — needs auto-dep inference from contract
- `packages/core/explorer/` — standalone test UI

## How to Run
- Core tests: `cd packages/core && PYTHONPATH=. python -m pytest tests/ -q`
- TF validate: `cd packages/core && PYTHONPATH=. python -m pytest tests/test_terraform_validate.py -v`
- Explorer: `cd packages/core && PYTHONPATH=. python -m explorer.app` → http://localhost:8100
- Other packages (will break until imports updated): `python -m pytest packages/{platform,api,mcp}/tests/ -q --ignore=packages/platform/tests/integration`
