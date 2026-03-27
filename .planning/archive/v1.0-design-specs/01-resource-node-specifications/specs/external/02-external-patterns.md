# External Category: Shared Patterns

**Category:** External
**Types:** third_party_api
**Archetype:** Non-Terraform / Platform-Only

---

## No Terraform Resource

The `third_party_api` is the only node type in the entire platform with no Terraform resource (`terraform_resource=""` in REGISTRY). This has several implications:

### Skipped During TF Generation

The Terraform generator skips this type entirely during HCL output. The `third_party_api.tf.j2` template generates only a descriptive comment:

```hcl
# my-stripe-api (Stripe) -- third-party API
# No Terraform resources generated. Exists for dependency tracking and documentation.
# Base URL: https://api.stripe.com/v1
# Auth method: api_key
```

This comment provides human-readable context in the generated Terraform files without creating any resources.

### No Deploy States

Since there is no Terraform resource, the node never enters `deploying`, `updating`, `destroying`, or `failed` states. It is either `active` or `deleted`. The deploy engine should skip these nodes entirely during deployment orchestration.

### No IAM Implications

- No `iam_scope` in REGISTRY.
- No IAM bindings needed.
- No service account permissions required to "access" a third-party API (the SA needs internet egress, not GCP IAM).

## Purpose: Dependency Graph Visualization

The primary purpose of third_party_api nodes is to make outbound API dependencies visible in the architecture graph:

- A Cloud Run service that calls the Stripe API can have an `Invoke` edge to a `third_party_api` node.
- This makes the dependency explicit and visible in the visual editor.
- Per ACTION_VALID_TARGETS in enums.py: `ActionType.INVOKE` targets include `NodeType.THIRD_PARTY_API`.

### Graph Integration

```
[Cloud Run: payment-service] --Invoke--> [3rd Party API: stripe-api]
[Cloud Run: notification-service] --Invoke--> [3rd Party API: twilio-api]
```

These edges are informational -- they document the architecture but don't affect deployment ordering (since there's nothing to deploy for the third-party API).

## Secret Reference Pattern

The `secret_ref` field can reference a `secret_manager` node to indicate where API credentials are stored:

```yaml
type: third_party_api
config:
  provider: "Stripe"
  base_url: "https://api.stripe.com/v1"
  auth_method: "api_key"
  secret_ref: "node:stripe-api-key"  # Reference to a secret_manager node
```

This creates a documentation link between the API and its credentials, which is useful for:
- Understanding which secrets are used by which external services.
- Future AI agent integration -- an agent generating code to call Stripe can look up the secret reference.
- Audit and compliance -- tracking where API keys are stored.

## Future Significance

The third_party_api type is currently the simplest in the system, but it may gain significance in future phases:

### MCP Tool Integration (Post-Platform)

When MCP tools and AI agents are added:
- Agents generating service code can read third_party_api nodes to understand what external APIs are available.
- The `base_url`, `auth_method`, and `rate_limit` fields provide context for code generation.
- The `secret_ref` tells the agent where to find credentials.
- The `description` and `headers` fields provide API documentation.

### Code Generation Context

AI agents with access to the infrastructure graph can:
- Generate HTTP client code with the correct base URL.
- Configure authentication based on `auth_method`.
- Implement rate limiting based on the `rate_limit` field.
- Reference the correct secret for API key injection.

---

*References: [01-external-template.md](01-external-template.md), [00-lifecycle-archetypes.md](../00-lifecycle-archetypes.md)*
*Phase: 01-resource-node-specifications*
