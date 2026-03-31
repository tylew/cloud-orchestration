# Service Contract Specification

## Overview

A **Service Contract** defines the relationship between a compute node and the resources it depends on. It replaces both the `internalGraph` (ordered action steps) and `WorkflowDefinition` (typed refs) systems with a single, clean abstraction.

The contract answers one question: **what does this service need from the rest of the architecture?**

An AI coding agent reads the contract. A human validates it. The platform enforces it.

## Design Principles

1. **Contracts, not implementations.** Define *what* a service reads/writes, not *how*. The AI agent decides the implementation.
2. **One model, one validation path, one DAG.** No parallel systems.
3. **Field-level precision.** A contract that says "reads from Firestore" is useless. A contract that says "reads `users/{user_id}/orders.status` and `orders.total`" is actionable.
4. **Bidirectional validation.** If a collection is renamed in the data node, every compute node referencing it gets a validation error.
5. **IAM inference.** The platform infers the minimum IAM roles from the contract — no manual role assignment.

## Data Model

### ServiceContract (lives on compute node config)

```python
class ResourceRef(BaseModel):
    """Reference from a compute node to a resource node."""
    node: str                    # target node name (must exist in blueprint)
    access: Literal["read", "write", "read_write"]
    description: str = ""        # human/agent-readable purpose

class DataRef(ResourceRef):
    """Reference to a data node with schema-level detail."""
    collections: list[str] = []  # Firestore: collection paths (e.g. "users", "users/{{user_id}}/orders")
    tables: list[str] = []       # Cloud SQL / BigQuery: table names
    fields: list[str] = []       # specific fields accessed (e.g. "users.email", "orders.total")

class SecretRef(BaseModel):
    """Reference to a secret node, mapped to an env var."""
    node: str                    # secret_manager node name
    env_var: str                 # env var name the secret maps to
    description: str = ""

class EventRef(BaseModel):
    """Reference to a messaging node."""
    node: str                    # pubsub_topic or cloud_task_queue node name
    direction: Literal["publish", "subscribe", "enqueue"]
    description: str = ""

class InvokeRef(BaseModel):
    """Reference to another compute node (service-to-service call)."""
    node: str                    # target compute node name
    description: str = ""

class ServiceContract(BaseModel):
    """Complete dependency contract for a compute node."""
    description: str = ""        # what this service does, in plain language
    data: list[DataRef] = []
    secrets: list[SecretRef] = []
    events: list[EventRef] = []
    invocations: list[InvokeRef] = []
    behavior: str = ""           # free-form behavioral spec for AI codegen agent
```

### Where it lives

```python
class CloudRunConfig(BaseModel):
    # ... existing fields ...
    contract: ServiceContract | None = None
```

Same for `CloudRunJobConfig` and `CloudFunctionConfig`.

### Example

```json
{
  "name": "order-service",
  "type": "cloud_run",
  "config": {
    "image": "...",
    "contract": {
      "description": "Handles order creation and status updates",
      "data": [
        {
          "node": "main-db",
          "access": "read_write",
          "collections": ["users", "users/{{user_id}}/orders"],
          "fields": ["users.email", "users.name", "orders.status", "orders.total", "orders.created_at"]
        },
        {
          "node": "analytics-bq",
          "access": "write",
          "tables": ["order_events"],
          "fields": ["order_events.order_id", "order_events.event_type", "order_events.timestamp"]
        }
      ],
      "secrets": [
        {"node": "stripe-key", "env_var": "STRIPE_API_KEY", "description": "Payment processing"}
      ],
      "events": [
        {"node": "order-events", "direction": "publish", "description": "Emits order.created, order.updated events"}
      ],
      "invocations": [
        {"node": "notification-service", "description": "Sends order confirmation emails"}
      ],
      "behavior": "When POST /orders: validate user exists, create order doc in users/{{user_id}}/orders with status=pending, publish order.created event, call notification-service. When PATCH /orders/{{order_id}}/status: update order.status, write event to analytics BQ, publish order.updated."
    }
  }
}
```

## Validation Rules

### Node existence
- Every `node` reference in every ref type must resolve to an existing node in the blueprint.
- `DataRef.node` must point to a storage type (firestore, cloud_sql, bigquery, bigtable, gcs_bucket).
- `SecretRef.node` must point to a `secret_manager` node.
- `EventRef.node` must point to a `pubsub_topic` or `cloud_task_queue` node.
- `InvokeRef.node` must point to a compute type (cloud_run, cloud_run_job, cloud_function).

### Schema validation (DataRef)
- If `collections` are specified and the target is a Firestore node, each collection path must exist in the target's collection definitions.
- If `tables` are specified and the target is Cloud SQL/BigQuery, each table must exist in the target's table definitions.
- If `fields` are specified, each field must resolve against the target's schema using `field_resolution.py`.
- Template paths like `{{user_id}}` are valid Firestore collection path segments.

### Cross-contract consistency
- If service A invokes service B, service B should exist and be a compute node.
- Circular invocation chains should produce warnings (not errors — microservices can legitimately call each other).

## DAG Integration

### New edges
The `BlueprintDAG` gains a `contract_edges()` method that returns logical dependency edges derived from contracts:

```python
def contract_edges(self) -> list[tuple[str, str, str]]:
    """Return (source_node, target_node, access_type) tuples from service contracts."""
```

These edges are **separate from** `depends_on` (infrastructure ordering). They represent logical data flow:
- `depends_on` = "this resource must be provisioned before mine" (Terraform ordering)
- Contract edges = "this service reads/writes that data store at runtime" (logical architecture)

### Visualization
The frontend DAG view should render both edge types:
- Solid lines for `depends_on` (infra)
- Colored/dashed lines for contract edges (data flow), color-coded by access type

## IAM Inference

The existing `IAM_ROLE_MAP` in `iam_mappings.py` is preserved but consumes contract refs instead of `internalGraph` steps:

```python
def infer_iam_roles_from_contract(contract: ServiceContract, all_nodes: list[dict]) -> set[str]:
    """Infer minimum IAM roles from a service contract."""
```

Mapping:
| Ref Type | Access | IAM Role |
|----------|--------|----------|
| DataRef (firestore) | read | roles/datastore.user |
| DataRef (firestore) | write | roles/datastore.user |
| DataRef (cloud_sql) | read | roles/cloudsql.client |
| DataRef (cloud_sql) | write | roles/cloudsql.client |
| DataRef (bigquery) | read | roles/bigquery.dataViewer |
| DataRef (bigquery) | write | roles/bigquery.dataEditor |
| DataRef (gcs_bucket) | read | roles/storage.objectViewer |
| DataRef (gcs_bucket) | write | roles/storage.objectAdmin |
| SecretRef | * | roles/secretmanager.secretAccessor |
| EventRef (publish) | * | roles/pubsub.publisher |
| EventRef (enqueue) | * | roles/cloudtasks.enqueuer |
| InvokeRef (cloud_run) | * | roles/run.invoker |
| InvokeRef (cloud_function) | * | roles/cloudfunctions.invoker |

## AI Codegen Interface

An AI coding agent receives:
1. The `ServiceContract` (structured refs + `behavior` field)
2. The schemas of all referenced data nodes (collection definitions, table columns, field types)
3. The compute node's runtime info (language, framework, entry point)

From this, the agent produces:
1. Application source code implementing the `behavior`
2. Tests
3. Dependency manifest (requirements.txt / package.json)

The platform does NOT generate code itself. It provides the spec. The agent writes the code.

## Migration

### What gets archived
- `InternalGraph`, `InternalStep`, `StepDetails` from `base.py`
- `ActionType`, `GRAPH_TYPES`, `ACTION_VALID_TARGETS` from `enums.py`
- `WorkflowDefinition`, `WorkflowDbRef`, `WorkflowSecretRef`, `WorkflowPubSubRef`, `WorkflowInvokeRef`, `WorkflowTaskDispatch`, `FieldRef` from `cloud_run.py`
- `code_generator.py` and `client_generator.py` from `codegen/`
- `internalGraph` validation in `validation.py`
- `internalGraph` handling in `iam_mappings.py`
- `pipeline.py` code generation endpoint
- `dependencies.py` client generation endpoint

### What stays
- `field_resolution.py` — the resolver logic is solid, just needs new callers
- `dag.py` — gains `contract_edges()` method
- `iam_mappings.py` — keeps `IAM_ROLE_MAP`, gets new `infer_iam_roles_from_contract()`
- `validation.py` — gets new contract validation rules replacing internalGraph validation

### Backward compatibility
- `BaseNode.internalGraph` field removed (breaking change for any blueprints using it)
- `config.workflow` field removed from compute configs
- Existing blueprints that don't use either system are unaffected
- Blueprints using `internalGraph` or `workflow` will fail validation until migrated to `contract`

## Implementation Order (for S02)

1. Archive old code to `archive/`
2. Define `ServiceContract` models in `packages/core/schemas/contracts.py`
3. Add `contract: ServiceContract | None = None` to compute configs
4. Add contract validation to `validation.py`
5. Add `contract_edges()` to `BlueprintDAG`
6. Update `iam_mappings.py` to consume contracts
7. Add API endpoint to retrieve contract + resolved schemas (for AI agent consumption)
8. Tests for all of the above
