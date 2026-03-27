# Third-Party API: Specifics

**Type:** third_party_api
**Terraform Resource:** None
**Archetype:** Non-Terraform / Platform-Only
**Complexity:** Lowest of all types (7 config fields, 1 sub-model)

---

## Overview

Third-Party API is the simplest node type in the entire platform. It has no Terraform resource, no deploy lifecycle, no ForceNew fields, and no required fields with error severity beyond `base_url`. It exists purely as a metadata node for dependency graph visualization and future AI agent context.

## Field Details

### provider

| Property | Value |
|----------|-------|
| Type | string |
| Default | (required in model -- no default) |
| Purpose | Human-readable name of the third-party service |
| Examples | "Stripe", "Twilio", "SendGrid", "OpenAI", "Auth0" |
| Validation | None beyond basic string type |

The `provider` field is the display label for the node in the visual editor. It identifies which third-party service this node represents.

### base_url

| Property | Value |
|----------|-------|
| Type | string |
| Default | (required in model -- no default) |
| Required | Yes (error severity in REQUIRED_FIELDS) |
| Purpose | Base URL for API requests |
| Examples | "https://api.stripe.com/v1", "https://api.twilio.com/2010-04-01" |
| Validation | Non-empty string (could add URL format validation) |

The base_url is the only field with error-level validation. It is essential for documenting the API endpoint and for future code generation.

### auth_method

| Property | Value |
|----------|-------|
| Type | string |
| Default | `"api_key"` |
| Purpose | Documents how the API authenticates requests |
| Values | "api_key", "oauth2", "basic", "none" |
| Enforcement | Purely informational -- no platform enforcement |

This field is metadata for documentation and code generation. The platform does not validate or enforce the authentication method.

### secret_ref

| Property | Value |
|----------|-------|
| Type | string or None |
| Default | `None` |
| Purpose | Reference to a secret_manager node storing API credentials |
| Format | Node reference (e.g., "node:stripe-api-key") or secret name |
| Validation | If set, should reference a valid secret_manager node |

Links the API node to its credentials. This is the primary integration point with the security layer.

### rate_limit

| Property | Value |
|----------|-------|
| Type | ThirdPartyRateLimit or None |
| Default | `None` |
| Purpose | Documents the API's rate limits |

#### ThirdPartyRateLimit Sub-Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| requests_per_second | int or None | `None` | Maximum requests per second |

**Note on current model:** The Pydantic model currently only has `requests_per_second`. The plan referenced `requests_per_minute` and `daily_limit` as additional fields, but these do not exist in the current codebase. The sub-model is minimal.

The rate_limit field is purely informational:
- It documents the API's rate limits for developer reference.
- It could be used by future code generation to implement client-side rate limiting.
- It does not enforce any limits at the platform level.

### timeout_ms

| Property | Value |
|----------|-------|
| Type | int or None |
| Default | `None` |
| Purpose | Default request timeout in milliseconds |
| Validation | If set, should be a positive integer |

Informational field for code generation -- suggests a default timeout for HTTP requests to this API.

### description

| Property | Value |
|----------|-------|
| Type | string or None |
| Default | `None` |
| Purpose | Human-readable description of the API integration |

Free-form text describing what this API is used for, any special considerations, or links to documentation.

## No Validation Constraints

Beyond the `base_url` being required (error severity in REQUIRED_FIELDS), there are no validation constraints on this type:

- All fields are optional except `provider` and `base_url` (which are required by the Pydantic model but `provider` is not in REQUIRED_FIELDS).
- No cross-field validation.
- No format validation on URLs, auth methods, or rate limits.
- No reference validation on `secret_ref` (though the validation module could add this).

## Template Output

The `third_party_api.tf.j2` template generates:

```hcl
# my-stripe-api (Stripe) -- third-party API
# No Terraform resources generated. Exists for dependency tracking and documentation.
# Base URL: https://api.stripe.com/v1
# Auth method: api_key
```

Four lines of comments. No resources. This is intentional -- the node exists for the graph, not for infrastructure.

## Interaction with Compute Nodes

Compute nodes can reference third_party_api nodes via the `internalGraph` workflow:

```yaml
# Cloud Run internalGraph step
steps:
  - id: "call-stripe"
    targetNodeName: "stripe-api"
    targetNodeType: "third_party_api"
    action: "Invoke"
    details:
      description: "Create payment intent"
```

This creates a visible edge in the architecture graph. The `ActionType.INVOKE` action is valid for `third_party_api` targets per ACTION_VALID_TARGETS.

## Future Enhancements

As the platform evolves, this type may gain:

| Enhancement | Phase | Description |
|-------------|-------|-------------|
| URL format validation | Implementation | Validate base_url is a valid HTTPS URL |
| secret_ref validation | Phase 2 | Cross-node validation that secret_ref points to a valid secret_manager node |
| Extended rate_limit model | Future | Add requests_per_minute, daily_limit, burst_limit |
| OpenAPI spec reference | Future | Link to the API's OpenAPI/Swagger spec for code generation |
| Health check endpoint | Future | URL to check if the API is available |

---

*References: [01-external-template.md](01-external-template.md), [02-external-patterns.md](02-external-patterns.md)*
*Phase: 01-resource-node-specifications*
