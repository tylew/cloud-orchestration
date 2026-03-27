# External Category: Rigid Template

**Category:** External
**Types:** third_party_api
**Archetype:** Non-Terraform / Platform-Only (see [00-lifecycle-archetypes.md](../00-lifecycle-archetypes.md))
**Provider version:** N/A -- No Terraform resource
**Last verified:** 2026-03-26

---

## Third-Party API (`third_party_api`)

### Terraform Resource

- Resource: **No Terraform resource** (`terraform_resource=""` in REGISTRY)
- The `third_party_api.tf.j2` template generates only a comment, no actual resources.
- This type exists purely for dependency graph visualization and metadata tracking.

### State Machine

Uses **Non-Terraform (Platform-Only)** lifecycle. See [00-lifecycle-archetypes.md](../00-lifecycle-archetypes.md).

| Current State | Event | Next State | Notes |
|---------------|-------|------------|-------|
| (none) | create | active | Node created in blueprint, saved to Firestore |
| active | update | active | All fields always mutable (Firestore CRUD only) |
| active | delete | deleted | Node removed from Firestore |

No deploying/destroying states -- there is no Terraform resource to deploy or destroy.

### Field Classification

#### Platform-Only Fields (all fields -- no Terraform mapping)

All 7 fields are platform-only metadata. They are always mutable and have no Terraform implications (per D-09).

| Field | Type | Required | Default | Mutable | Purpose |
|-------|------|----------|---------|---------|---------|
| provider | string | No | (required in model, no default) | Yes (always) | Third-party service provider name (e.g., "Stripe", "Twilio") |
| base_url | string | Yes (error) | (required in model, no default) | Yes (always) | Base URL of the API (e.g., "https://api.stripe.com/v1") |
| auth_method | string | No | `"api_key"` | Yes (always) | Authentication method: "api_key", "oauth2", "basic", "none" |
| secret_ref | string or None | No | `None` | Yes (always) | Reference to a secret_manager node storing the API key/credentials |
| rate_limit | ThirdPartyRateLimit or None | No | `None` | Yes (always) | Rate limiting metadata |
| timeout_ms | int or None | No | `None` | Yes (always) | Request timeout in milliseconds |
| description | string or None | No | `None` | Yes (always) | Human-readable description of the API integration |

**No ForceNew fields.** There is no Terraform resource, so the concept of ForceNew does not apply.

### Required Fields (error-level)

- **base_url**: Base URL is required. Per REQUIRED_FIELDS in validation.py.

### Warning Fields

None defined in REQUIRED_FIELDS.

---

*Referenced by: external/02-external-patterns.md, external/03-third-party-api.md*
*Phase: 01-resource-node-specifications*
