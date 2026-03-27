# Network Category - Rigid Template

**Category:** Network
**Node types:** vpc, subnet, vpc_connector, external_lb
**Lifecycle archetype:** Network with Dependencies (see 00-lifecycle-archetypes.md)

---

## vpc

### Terraform Resource

- Resource: `google_compute_network`
- Provider version: ~5.0
- Last verified: 2026-03-26

### State Machine

Archetype: **Network with Dependencies**

| Current State | Event | Next State | Notes |
|---------------|-------|------------|-------|
| (none) | create | draft | Initial node creation in blueprint |
| draft | deploy | deploying | TF apply submitted |
| deploying | success | deployed | TF apply completed |
| deploying | failure | failed | TF apply errored |
| deployed | update (mutable) | updating | In-place TF apply |
| deployed | update (immutable) | destroying | Destroy-recreate cycle; requires all dependents (subnets, connectors) to be destroyed first |
| updating | success | deployed | |
| updating | failure | failed | |
| deployed | delete | destroying | TF destroy; requires all dependents destroyed first |
| destroying | success | destroyed | |
| destroying | failure | failed | |
| failed | retry | deploying/updating/destroying | Deferred to Phase 3-5 |

**Deletion constraint:** VPC cannot be deleted while subnets, VPC connectors, or other resources reference it. The deploy engine must reverse-order the dependency graph on delete.

### Field Classification

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| auto_create_subnetworks | bool | Yes (explicit) | -- | Yes | `auto_create_subnetworks` | `true` or `false`; recommend `false` for custom mode |
| routing_mode | str | No | `"REGIONAL"` | Yes | `routing_mode` | `REGIONAL` or `GLOBAL` |
| description | str \| None | No | `None` | **No (ForceNew)** | `description` | Free text; changing requires VPC recreation |
| mtu | int | No | `1460` | Yes | `mtu` | 1300-8896 (validated by Pydantic Field) |
| delete_default_routes_on_create | bool | No | `False` | **No (ForceNew)** | `delete_default_routes_on_create` | Removes default 0.0.0.0/0 route |

**Total: 5 fields, 5 TF-mapped, 0 platform-only**

**ForceNew fields:** `description` (surprisingly -- changing VPC description requires recreation), `delete_default_routes_on_create`. Research also notes `network_profile` as ForceNew but it is not in the current Pydantic model. `name` is identity (implicit ForceNew).

### Required Fields (error-level)

None. VPC has sensible defaults (`auto_create_subnetworks` is an explicit bool with no default in Pydantic, so it must be provided, but it is not in REQUIRED_FIELDS).

### Warning Fields

None.

### Notes

- No IAM scope (`iam_scope=None` in REGISTRY); network resources are accessed via network configuration, not IAM bindings
- VPC is the root network resource: subnets, connectors, Cloud SQL private IP, and other resources reference back to VPC
- Default outputs: `self_link`, `id`, `name`
- **Gotcha:** `description` is ForceNew -- this is unusual and should be prominently documented in UI tooltips

---

## subnet

### Terraform Resource

- Resource: `google_compute_subnetwork`
- Provider version: ~5.0
- Last verified: 2026-03-26

### State Machine

Archetype: **Network with Dependencies** (identical to vpc above)

**Deletion constraint:** Subnet cannot be deleted while VPC connectors or compute resources (Cloud Run with VPC connector referencing this subnet) depend on it.

### Field Classification

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| ip_cidr_range | str | **Yes (error)** | -- | **Partially (expand only)** | `ip_cidr_range` | Valid CIDR notation; can expand (e.g., /24 to /20) but CANNOT shrink |
| region | str | **Yes (error)** | -- | **No (ForceNew)** | `region` | GCP region string; subnets are regional (identity field) |
| network | str | **Yes (error)** | -- | **No (ForceNew)** | `network` | Reference to VPC node (resolved via `resolve_ref`); identity field |
| private_ip_google_access | bool | No | `True` | Yes | `private_ip_google_access` | Enables private access to Google APIs |
| secondary_ip_ranges | list[SecondaryIpRange] \| None | No | `None` | Yes | `secondary_ip_range` | Nested: range_name + ip_cidr_range per range |
| log_config | SubnetLogConfig \| None | No | `None` | Yes | `log_config` | Nested: aggregation_interval, flow_sampling, metadata |
| purpose | str | No | `"PRIVATE"` | Yes | `purpose` | `PRIVATE` (standard), `REGIONAL_MANAGED_PROXY`, etc. |

**Nested sub-models (2):**

1. **SecondaryIpRange**: `range_name` (str, required) + `ip_cidr_range` (str, required)
2. **SubnetLogConfig**: `aggregation_interval` (str \| None) + `flow_sampling` (float \| None) + `metadata` (str \| None)

**Total: 7 fields, 7 TF-mapped, 0 platform-only**

**ForceNew fields:** `region` (identity -- subnets cannot move between regions), `network` (identity -- subnets cannot move between VPCs). Research also notes `description` and `ipv6_access_type` as ForceNew but these are not in the current Pydantic model.

**Special mutability: `ip_cidr_range`** -- This field has one-way mutability. The CIDR range can be **expanded** (e.g., /24 to /20 to accommodate more IP addresses) but can **NEVER be shrunk**. This is unique among all field types in the platform. The platform should validate that any CIDR change is an expansion, not a contraction.

### Required Fields (error-level)

- `ip_cidr_range`: IP CIDR range is required
- `region`: Region is required
- `network`: Network reference is required (must reference a VPC node)

### Warning Fields

None.

### Notes

- No IAM scope (`iam_scope=None` in REGISTRY)
- Default outputs: `self_link`, `id`, `gateway_address`
- `network` field creates a hard dependency edge from subnet to VPC in the blueprint graph

---

## vpc_connector

> **ENTIRELY IMMUTABLE:** VPC Connectors are entirely immutable after creation. ANY configuration change requires full recreation. This is the only resource type in the platform where every field is ForceNew. See specifics doc (05-vpc-connector.md) for full implications.

### Terraform Resource

- Resource: `google_vpc_access_connector`
- Provider version: ~5.0
- Last verified: 2026-03-26

### State Machine

Archetype: **Network with Dependencies** (modified -- ALL updates are destroy-recreate)

| Current State | Event | Next State | Notes |
|---------------|-------|------------|-------|
| (none) | create | draft | Initial node creation in blueprint |
| draft | deploy | deploying | TF apply submitted |
| deploying | success | deployed | TF apply completed |
| deploying | failure | failed | TF apply errored |
| deployed | update (ANY field) | destroying | **ALL fields are ForceNew** -- any change = destroy-recreate |
| destroying (recreate) | success | deploying | New connector created |
| deployed | delete | destroying | TF destroy submitted |
| destroying | success | destroyed | |
| destroying | failure | failed | |
| failed | retry | deploying/destroying | Deferred to Phase 3-5 |

**Critical:** There is no "updating" state for VPC Connectors. Any change goes through destroy-recreate.

### Field Classification

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| region | str | **Yes (error)** | -- | **No (ForceNew)** | `region` | GCP region string |
| network | str | **Yes (error)** | -- | **No (ForceNew)** | `network` | Reference to VPC node (resolved via `resolve_ref`) |
| ip_cidr_range | str | **Yes (error)** | -- | **No (ForceNew)** | `ip_cidr_range` | /28 CIDR range within the VPC's address space |
| min_throughput | int | No | `200` | **No (ForceNew)** | `min_throughput` | 200-1000 Mbps (validated by Pydantic Field) |
| max_throughput | int | No | `1000` | **No (ForceNew)** | `max_throughput` | 200-1000 Mbps (validated by Pydantic Field) |
| machine_type | str | No | `"e2-micro"` | **No (ForceNew)** | `machine_type` | `e2-micro`, `e2-standard-4`, `f1-micro` |
| min_instances | int | No | `2` | **No (ForceNew)** | `min_instances` | 2-9 (validated by Pydantic Field) |
| max_instances | int | No | `10` | **No (ForceNew)** | `max_instances` | 3-10 (validated by Pydantic Field) |

**Total: 8 fields, 8 TF-mapped, 0 platform-only**

**ForceNew fields: ALL 8 fields are ForceNew.** VPC Connectors are entirely immutable after creation. Any configuration change requires full recreation.

### Required Fields (error-level)

- `region`: Region is required
- `ip_cidr_range`: IP CIDR range is required
- `network`: Network reference is required

### Warning Fields

None.

### Notes

- No IAM scope (`iam_scope=None` in REGISTRY)
- Default outputs: `id`, `self_link`, `state`
- **Platform UX implication:** Must show a strong warning when ANY VPC Connector field is modified. Recreation causes downtime for ALL connected Cloud Run services.
- The connector consumes a /28 CIDR block from the VPC's address space -- this CIDR must not overlap with any subnet CIDRs

---

## external_lb

> **COMPOSITE RESOURCE:** External LB is a composite of multiple Terraform resources. The REGISTRY maps it to `google_compute_global_address` as the base resource, but the actual load balancer requires 5-7 Terraform resources working together. See specifics doc (06-external-lb.md) for the full sub-resource list and per-sub-resource mutability.

### Terraform Resource

- Base resource: `google_compute_global_address`
- Composite sub-resources: `google_compute_managed_ssl_certificate`, `google_compute_region_network_endpoint_group`, `google_compute_backend_service`, `google_compute_url_map`, `google_compute_target_https_proxy`, `google_compute_global_forwarding_rule`
- Provider version: ~5.0
- Last verified: 2026-03-26

### State Machine

Archetype: **Network with Dependencies** (composite variant -- sub-resources have individual lifecycles)

| Current State | Event | Next State | Notes |
|---------------|-------|------------|-------|
| (none) | create | draft | Initial node creation in blueprint |
| draft | deploy | deploying | TF apply submitted for ALL sub-resources |
| deploying | success | deployed | All sub-resources created |
| deploying | failure | failed | Any sub-resource creation failed |
| deployed | update (mutable sub-resource) | updating | Partial TF apply |
| deployed | update (ForceNew sub-resource) | destroying | Destroy-recreate of affected sub-resources |
| updating | success | deployed | |
| updating | failure | failed | |
| deployed | delete | destroying | TF destroy of all sub-resources |
| destroying | success | destroyed | |
| destroying | failure | failed | |
| failed | retry | deploying/updating/destroying | Deferred to Phase 3-5 |

**Composite lifecycle note:** Different ExternalLbConfig fields map to different sub-resources with different mutability. Changing `domains` recreates the SSL certificate (15+ min provisioning). Changing backend weights is an in-place update.

### Field Classification

| Field | Type | Required | Default | Mutable | TF Argument | Validation | Sub-Resource |
|-------|------|----------|---------|---------|-------------|------------|-------------|
| scheme | str | No | `"EXTERNAL_MANAGED"` | **No (ForceNew)** | `load_balancing_scheme` | `EXTERNAL_MANAGED` or `EXTERNAL` | backend_service, forwarding_rule |
| ssl_policy | LbSslPolicy \| None | No | `None` | Yes | ssl_policy block | Nested: min_tls_version, profile | target_https_proxy |
| managed_ssl_certificate | LbManagedSslCertificate \| None | No | `None` | **Partially (ForceNew on domains)** | managed block | Nested: domains list | managed_ssl_certificate |
| custom_ssl_certificate | str \| None | No | `None` | Yes | `ssl_certificates` | Certificate resource name | target_https_proxy |
| default_backend | LbDefaultBackend \| None | No | `None` | Yes (backend mutable) | backend block | Nested: type, cloud_run_service, region | backend_service, serverless_neg |
| cdn_policy | LbCdnPolicy \| None | No | `None` | Yes | cdn_policy block | Nested: cache_mode, TTLs, negative_caching | backend_service |
| security_policy | str \| None | No | `None` | Yes | `security_policy` | Cloud Armor policy resource name | backend_service |
| logging | LbLogging \| None | No | `None` | Yes | log_config block | Nested: enable, sample_rate | backend_service |
| custom_request_headers | list[str] | No | `[]` | Yes | `custom_request_headers` | Header strings | backend_service |
| custom_response_headers | list[str] | No | `[]` | Yes | `custom_response_headers` | Header strings | backend_service |
| iap | LbIap \| None | No | `None` | Yes | iap block | Nested: oauth2_client_id, oauth2_client_secret | backend_service |
| domain | str \| None | No | `None` | -- | -- | Legacy flat field | (legacy) |
| ssl | bool | No | `True` | -- | -- | Legacy flat field | (legacy) |
| backend_service | str \| None | No | `None` | -- | -- | Legacy flat field | (legacy) |
| cdn_enabled | bool | No | `False` | -- | -- | Legacy flat field | (legacy) |
| cloud_armor_policy | str \| None | No | `None` | -- | -- | Legacy flat field | (legacy) |

**Nested sub-models (6):**

1. **LbSslPolicy**: `min_tls_version` (str, default `"TLS_1_2"`) + `profile` (str, default `"MODERN"`)
2. **LbManagedSslCertificate**: `domains` (list[str], required)
3. **LbDefaultBackend**: `type` (str, default `"serverless_neg"`) + `cloud_run_service` (str \| None) + `region` (str \| None)
4. **LbNegativeCachingPolicy**: `code` (int, required) + `ttl` (str, required)
5. **LbCdnPolicy**: `cache_mode` (str, default `"CACHE_ALL_STATIC"`) + `default_ttl` + `max_ttl` + `client_ttl` + `negative_caching` (bool) + `negative_caching_policy` (list) + `serve_while_stale` + `signed_url_cache_max_age`
6. **LbLogging**: `enable` (bool, default `True`) + `sample_rate` (float, default `1.0`)
7. **LbIap**: `oauth2_client_id` (str, required) + `oauth2_client_secret` (str, required)

**Total: 16 fields (11 active + 5 legacy), 16 TF-mapped, 0 platform-only**

**Note:** The 5 legacy flat fields (`domain`, `ssl`, `backend_service`, `cdn_enabled`, `cloud_armor_policy`) appear to be from an older config schema. The structured fields (`managed_ssl_certificate`, `ssl_policy`, `default_backend`, `cdn_policy`, `security_policy`) are the current approach.

### Required Fields (error-level)

- `backend_service`: Backend service reference is required (from REQUIRED_FIELDS -- refers to the legacy flat field; structured equivalent is `default_backend`)

### Warning Fields

None.

### Notes

- No IAM scope (`iam_scope=None` in REGISTRY); load balancers are accessed via network routing, not IAM bindings
- Default outputs: `ip_address`, `self_link`
- This is the most complex resource type in the platform -- downstream phases must handle each sub-resource independently
- See 06-external-lb.md for complete sub-resource lifecycle documentation
