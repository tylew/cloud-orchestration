# Phase 2: Implement cloud_dns Node Type - Research

**Researched:** 2026-03-27
**Domain:** GCP Cloud DNS Terraform generation, Pydantic schema design, platform node type registration
**Confidence:** HIGH

## Summary

This phase adds a `cloud_dns` node type to the GCP orchestration platform following the well-established pattern used by all 22 existing node types. The implementation touches exactly 5 files with a clearly defined pattern: enum entry, Pydantic config model, TYPE_TO_CONFIG mapping, registry ComponentDefinition, _NODE_TYPE_APIS mapping, and a Jinja2 Terraform template.

Cloud DNS maps to two Terraform resources: `google_dns_managed_zone` for the DNS zone and `google_dns_record_set` for individual records within it. The required GCP API is `dns.googleapis.com`. Records should support cross-node references (e.g., `node:my-lb.ip_address`) using the existing `resolve_ref` mechanism already used in templates like `external_lb.tf.j2`.

**Primary recommendation:** Follow the exact pattern of existing node types (e.g., `external_lb`, `pubsub_topic`). The codebase has a rigid, well-tested registration pattern -- deviate and existing tests (`test_registry.py`) will fail.

## Project Constraints (from CLAUDE.md)

- Python 3.12 backend, Pydantic >= 2.0 for schemas
- snake_case for Python modules and variables
- Pydantic BaseModel for validated schemas (not dataclass)
- One config file per node type in `packages/core/schemas/configs/`
- Jinja2 templates in `packages/core/terraform/templates/`
- 4-space indentation in Python (PEP 8)
- Module-level docstrings describe purpose
- `# noqa: N815` for intentional camelCase in Pydantic fields matching frontend JSON

## Standard Stack

No new libraries required. This phase uses only existing project dependencies:

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | >= 2.0 | Config schema for CloudDnsConfig | Already used for all 22 node types |
| Jinja2 | (bundled) | Terraform template rendering | Already used for all TF templates |
| pytest | (dev dep) | Unit tests | Already configured in pyproject.toml |

**No new dependencies to install.**

## Architecture Patterns

### File Touchpoints (Exact Pattern from Existing Types)

```
packages/core/schemas/enums.py              # Add CLOUD_DNS to NodeType enum
packages/core/schemas/configs/cloud_dns.py  # NEW: CloudDnsConfig Pydantic model
packages/core/schemas/configs/__init__.py   # Import + TYPE_TO_CONFIG + NodeConfig union
packages/core/registry.py                   # Add ComponentDefinition entry
packages/core/terraform/generator.py        # Add to _NODE_TYPE_APIS mapping
packages/core/terraform/templates/cloud_dns.tf.j2  # NEW: Jinja2 template
packages/core/validation.py                 # Add REQUIRED_FIELDS entry
```

### Pattern 1: NodeType Enum Entry
**What:** Add `CLOUD_DNS = "cloud_dns"` to the NodeType StrEnum
**When to use:** Every new node type
**Example:**
```python
# In packages/core/schemas/enums.py, add to NodeType:
CLOUD_DNS = "cloud_dns"
```
**Placement:** In the Network section, near EXTERNAL_LB (line 24).

### Pattern 2: Pydantic Config Model
**What:** One file per node type in `packages/core/schemas/configs/` with a `BaseModel` subclass
**When to use:** Every node type needs a config model
**Example pattern (from gcs_bucket.py):**
```python
from pydantic import BaseModel

class CloudDnsConfig(BaseModel):
    dns_name: str                    # e.g., "example.com."
    visibility: str = "public"       # "public" or "private"
    description: str = ""
    dnssec_enabled: bool = False
    records: list[DnsRecord] = []
    labels: dict[str, str] = {}
```
**Key:** The config model must be importable as `CloudDnsConfig` from the configs package.

### Pattern 3: TYPE_TO_CONFIG Registration
**What:** Import config in `__init__.py`, add to `TYPE_TO_CONFIG` dict and `NodeConfig` union type
**When to use:** Every new config model
**Example:**
```python
# In packages/core/schemas/configs/__init__.py:
from .cloud_dns import CloudDnsConfig

# Add to TYPE_TO_CONFIG dict:
NodeType.CLOUD_DNS: CloudDnsConfig,

# Add to NodeConfig union:
| CloudDnsConfig
```

### Pattern 4: Registry ComponentDefinition
**What:** Add entry to REGISTRY dict in `packages/core/registry.py`
**When to use:** Every new node type
**Example:**
```python
NodeType.CLOUD_DNS: ComponentDefinition(
    node_type=NodeType.CLOUD_DNS,
    label="Cloud DNS",
    category="Network",
    is_compute=False,
    config_model=TYPE_TO_CONFIG[NodeType.CLOUD_DNS],
    terraform_resource="google_dns_managed_zone",
    default_outputs=(
        {"name": "name_servers", "type": "connection_string"},
        {"name": "dns_name", "type": "connection_string"},
    ),
),
```
**Notes:** Cloud DNS does not have resource-level IAM in the typical sense, so `iam_scope` and `iam_terraform_resource` should be omitted (defaulting to None). Category is "Network" to match `external_lb`, `vpc`, `subnet`, `vpc_connector`.

### Pattern 5: _NODE_TYPE_APIS Mapping
**What:** Map node type string to required GCP API(s) in `generator.py`
**When to use:** Every node type that needs a GCP API enabled
**Example:**
```python
# In _NODE_TYPE_APIS dict in generator.py:
"cloud_dns": ["dns.googleapis.com"],
```

### Pattern 6: Jinja2 Terraform Template
**What:** `cloud_dns.tf.j2` renders `google_dns_managed_zone` + `google_dns_record_set` resources
**When to use:** The template is auto-loaded by the generator using `f"{node.type.value}.tf.j2"`
**Key considerations:**
- Template receives: `node`, `config`, `global_`, `resolve_ref`, `defn`, `api_depends_on`
- Use `resolve_ref()` for cross-node references in record data (e.g., `node:my-lb.ip_address`)
- Resource naming: `"${var.environment}-{{ node.name }}-zone"` (matches existing patterns)
- Each record in `config.records` generates a separate `google_dns_record_set`

### Pattern 7: Validation REQUIRED_FIELDS
**What:** Add entry to `REQUIRED_FIELDS` dict in `validation.py`
**When to use:** Every node type must have an entry (even if empty list)
**Example:**
```python
"cloud_dns": [
    FieldRequirement("dns_name", "error", "DNS name (domain) is required"),
],
```

### Anti-Patterns to Avoid
- **Forgetting the NodeConfig union update:** The `NodeConfig` type in `__init__.py` must include `CloudDnsConfig` or type checking breaks.
- **Missing REQUIRED_FIELDS entry:** Validation iterates over node types; a missing entry causes no validation rather than explicit pass.
- **Trailing dot on dns_name:** The Terraform `google_dns_managed_zone.dns_name` requires a trailing dot (e.g., `"example.com."`). The Pydantic model should accept the domain but the template should ensure the trailing dot.
- **Not using resolve_ref for record targets:** Record rrdatas that reference other nodes (e.g., LB IP) must go through `resolve_ref()` in the template, not be hardcoded.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-node reference resolution | Custom ref parser | `resolve_ref()` from resolver.py | Already handles `node:X.attr` -> TF interpolation |
| API enablement | Manual API enable | `_NODE_TYPE_APIS` mapping | Generator auto-creates `google_project_service` resources |
| Config validation | Custom validators | Pydantic model + `REQUIRED_FIELDS` | Consistent with all other node types |

**Key insight:** The entire node type registration pipeline is mechanical -- follow the pattern exactly and existing infrastructure handles everything (template loading, API enablement, validation, preview).

## Common Pitfalls

### Pitfall 1: google_dns_managed_zone dns_name trailing dot
**What goes wrong:** Terraform requires `dns_name` to end with a `.` (e.g., `"example.com."` not `"example.com"`)
**Why it happens:** Users naturally type domains without trailing dots
**How to avoid:** Either enforce trailing dot in the Pydantic validator or append it in the Jinja2 template
**Warning signs:** Terraform plan errors about invalid dns_name format
**Recommendation:** Handle in template with `{{ config.dns_name if config.dns_name.endswith('.') else config.dns_name ~ '.' }}`

### Pitfall 2: Record set name must be fully qualified
**What goes wrong:** `google_dns_record_set.name` must be a FQDN ending in dot, relative to the zone
**Why it happens:** Users think of records as "www" not "www.example.com."
**How to avoid:** Template should construct FQDN from record name + zone dns_name
**Warning signs:** Terraform apply errors about record name format

### Pitfall 3: Test suite enforces completeness
**What goes wrong:** `test_registry.py::TestRegistryCompleteness::test_all_node_types_registered` fails if CLOUD_DNS is in NodeType enum but not in REGISTRY
**Why it happens:** Adding to enum without adding to all registration points
**How to avoid:** Touch ALL 5+ files in a single atomic change
**Warning signs:** `assert nt in REGISTRY` failure for `cloud_dns`

### Pitfall 4: MX record rdata format
**What goes wrong:** MX records require priority prefix (e.g., `"10 mail.example.com."`)
**Why it happens:** Different record types have different rdata formats
**How to avoid:** MX records need a `priority` field; model should handle this explicitly
**Warning signs:** Terraform apply errors about invalid MX rdata

### Pitfall 5: Multiple records per type per name
**What goes wrong:** A single `google_dns_record_set` resource can hold multiple rrdatas for the same name+type
**Why it happens:** Users expect one record per `google_dns_record_set`
**How to avoid:** Group records by (name, type) in the template, combining rrdatas into a single resource
**Warning signs:** Terraform errors about duplicate record sets

## Code Examples

### DnsRecord Sub-Model Design
```python
from pydantic import BaseModel, Field
from typing import Literal


class DnsRecord(BaseModel):
    """A single DNS record entry within a Cloud DNS zone."""
    name: str = "@"                              # "@" for apex, or subdomain like "www"
    type: Literal["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SRV", "PTR"] = "A"
    ttl: int = 300
    rrdatas: list[str] = []                      # Raw rdata values
    target: str | None = None                    # Cross-node ref like "node:my-lb.ip_address"
    priority: int | None = None                  # For MX records
```

### Terraform Template Pattern (cloud_dns.tf.j2)
```jinja2
resource "google_dns_managed_zone" "{{ node.name }}" {
  name        = "${var.environment}-{{ node.name }}"
  dns_name    = "{{ config.dns_name if config.dns_name.endswith('.') else config.dns_name ~ '.' }}"
  description = "{{ config.description }}"
  visibility  = "{{ config.visibility }}"
  project     = var.gcp_project_id

{% if config.dnssec_enabled %}
  dnssec_config {
    state = "on"
  }
{% endif %}

{% if config.labels %}
  labels = {
{% for key, value in config.labels.items() %}
    "{{ key }}" = "{{ value }}"
{% endfor %}
  }
{% endif %}
}

{% for record in config.records %}
resource "google_dns_record_set" "{{ node.name }}_{{ record.name | replace('@', 'apex') | replace('.', '-') }}_{{ record.type | lower }}" {
  managed_zone = google_dns_managed_zone.{{ node.name }}.name
  name         = {% if record.name == '@' %}google_dns_managed_zone.{{ node.name }}.dns_name{% else %}"{{ record.name }}.${google_dns_managed_zone.{{ node.name }}.dns_name}"{% endif %}

  type    = "{{ record.type }}"
  ttl     = {{ record.ttl }}
  project = var.gcp_project_id

{% if record.target and record.target.startswith('node:') %}
  rrdatas = [{{ resolve_ref(record.target) }}]
{% elif record.rrdatas %}
  rrdatas = {{ record.rrdatas | tojson }}
{% endif %}
}
{% endfor %}
```

### Cross-Node Reference Usage (how resolve_ref works)
```python
# In resolver.py, resolve_node_ref handles:
# "node:my-lb.ip_address" -> "google_compute_global_address.my-lb.address"
# This is passed as resolve_ref to templates, already working for external_lb
```

## Terraform Resources Reference

### google_dns_managed_zone
| Argument | Required | Type | Description |
|----------|----------|------|-------------|
| name | Yes | string | Unique zone name (resource label) |
| dns_name | Yes | string | FQDN with trailing dot |
| description | No | string | Zone description |
| visibility | No | string | "public" (default) or "private" |
| dnssec_config | No | block | DNSSEC configuration |
| labels | No | map | Resource labels |
| project | No | string | GCP project ID |

**Exported attributes:** `name_servers`, `zone_id`, `dns_name`, `id`

### google_dns_record_set
| Argument | Required | Type | Description |
|----------|----------|------|-------------|
| managed_zone | Yes | string | Zone name this record belongs to |
| name | Yes | string | FQDN of the record |
| type | Yes | string | DNS record type (A, AAAA, CNAME, etc.) |
| ttl | Yes | int | Time-to-live in seconds |
| rrdatas | Yes* | list(string) | Record data values |
| project | No | string | GCP project ID |

**Required GCP API:** `dns.googleapis.com`

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| google provider < 5.0 | google provider >= 5.0 | 2023 | google_dns_record_set uses rrdatas (not rrdatas + routing_policy split) |

**No deprecated resources:** `google_dns_managed_zone` and `google_dns_record_set` are stable, GA resources with no deprecation notices.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio |
| Config file | `packages/pyproject.toml` |
| Quick run command | `python -m pytest packages/tests/test_registry.py packages/tests/test_terraform.py packages/tests/test_validation.py -x` |
| Full suite command | `python -m pytest packages/tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DNS-01 | NodeType enum includes CLOUD_DNS | unit | `pytest packages/tests/test_registry.py::TestRegistryCompleteness -x` | Existing (auto-passes when enum+registry updated) |
| DNS-02 | CloudDnsConfig validates correctly | unit | `pytest packages/tests/test_cloud_dns.py::TestCloudDnsConfig -x` | Wave 0 |
| DNS-03 | Registry entry exists with correct fields | unit | `pytest packages/tests/test_registry.py -x` | Existing (auto-passes) |
| DNS-04 | TF template generates valid HCL | unit | `pytest packages/tests/test_cloud_dns.py::TestCloudDnsTerraform -x` | Wave 0 |
| DNS-05 | Cross-node ref resolution in records | unit | `pytest packages/tests/test_cloud_dns.py::TestCloudDnsCrossRef -x` | Wave 0 |
| DNS-06 | Required field validation | unit | `pytest packages/tests/test_validation.py -x` | Existing (auto-checks REQUIRED_FIELDS) |

### Sampling Rate
- **Per task commit:** `python -m pytest packages/tests/test_registry.py packages/tests/test_terraform.py packages/tests/test_validation.py -x`
- **Per wave merge:** `python -m pytest packages/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `packages/tests/test_cloud_dns.py` -- covers DNS-02, DNS-04, DNS-05
- [ ] No new fixtures needed in conftest.py (test file creates its own envelope data)

## Open Questions

1. **Private zones and VPC binding**
   - What we know: Private DNS zones require binding to one or more VPCs
   - What's unclear: Should the config model support `private_visibility_config` with VPC references now, or defer?
   - Recommendation: Include optional `networks` field (list of VPC node refs) for private zones. This follows the cross-node reference pattern already used by subnet (network field). Defer to implementation.

2. **Record grouping strategy**
   - What we know: Multiple rrdatas for the same (name, type) must be in a single `google_dns_record_set`
   - What's unclear: Should grouping happen in the Pydantic model (one DnsRecord per unique name+type with multiple rrdatas) or in the template?
   - Recommendation: Model stores individual records; template groups by (name, type). This keeps the user-facing API simple.

3. **SOA and NS records**
   - What we know: GCP auto-creates SOA and NS records for the zone
   - What's unclear: Should the model allow users to override NS records?
   - Recommendation: Don't expose SOA/NS management initially. Let GCP manage them automatically.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `packages/core/registry.py`, `packages/core/schemas/enums.py`, `packages/core/schemas/configs/__init__.py`, `packages/core/terraform/generator.py` -- exact patterns for adding new node types
- Codebase analysis: `packages/core/terraform/templates/external_lb.tf.j2` -- reference template with cross-node resolution
- Codebase analysis: `packages/core/terraform/resolver.py` -- resolve_ref mechanism

### Secondary (MEDIUM confidence)
- [Terraform google_dns_managed_zone resource docs](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/dns_managed_zone) -- resource arguments
- [Terraform google_dns_record_set resource docs](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/dns_record_set) -- record set arguments
- [Google Cloud DNS overview](https://docs.cloud.google.com/dns/docs/overview) -- managed zones, DNSSEC, visibility

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, exact pattern replication
- Architecture: HIGH - 22 existing node types establish the pattern precisely
- Pitfalls: HIGH - trailing dot, FQDN, and MX format are well-documented DNS requirements
- Terraform resources: MEDIUM - registry.terraform.io pages require JS (content verified via WebSearch + training data)

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable -- Cloud DNS and Terraform google provider are GA and rarely change)
