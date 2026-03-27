# Network Category - Patterns & Shared Behaviors

**Category:** Network
**Node types:** vpc, subnet, vpc_connector, external_lb

---

## Dependency Ordering

Network resources form infrastructure layers with strict dependency ordering:

```
VPC --> Subnet --> VPC Connector
                        |
                        v
                   Cloud Run / Cloud Function (consumers)

VPC -----> External LB (references backend services)
```

### Deploy Order (Phase 3 Critical)

1. **Layer 0:** Deploy VPC first (root network resource)
2. **Layer 1:** Deploy Subnets (depend on VPC via `network` field)
3. **Layer 2:** Deploy VPC Connectors (depend on VPC via `network` field, consume /28 from VPC address space)
4. **Layer 3:** Deploy External LBs (reference compute backends via serverless NEGs)

### Delete Order (Reverse)

Deletion must proceed in reverse dependency order:
1. Remove External LBs
2. Remove VPC Connectors (requires Cloud Run services to first release the connector reference)
3. Remove Subnets
4. Remove VPC

**Critical:** Attempting to delete a VPC while subnets or connectors still reference it will fail with a dependency error in Terraform.

## Network with Dependencies Archetype

All four network types follow the "Network with Dependencies" archetype, which differs from Simple CRUD in two ways:

1. **Deletion requires reverse-dependency checking:** Unlike data or messaging resources that can be deleted independently, network resources are infrastructure layers. Other resources depend on them, and deletion fails if dependents still exist.

2. **Changes cascade to dependents:** Modifying network resources can affect all resources that reference them:
   - Changing VPC `mtu` affects all subnets and connected resources
   - Recreating a VPC Connector requires redeploying all connected Cloud Run services
   - Changing External LB `domains` triggers SSL certificate reprovisioning (15+ min)

## VPC Connector Total Immutability (Pitfall 3)

VPC Connector is the **one resource where ANY change requires full recreation**. All 8 fields are ForceNew.

### Why this matters

Unlike most resources that have 1-3 ForceNew fields (typically name and location), VPC Connector has zero mutable fields. Even changing `min_instances` from 2 to 3 triggers a full destroy-recreate cycle.

### Impact on dependents

When a VPC Connector is recreated:
1. The old connector is destroyed
2. A new connector is created (new internal resource ID)
3. **ALL Cloud Run services referencing the old connector must be redeployed** to use the new connector
4. During the gap between old destroy and new create, connected Cloud Run services lose VPC connectivity

### Platform UX implications

- Show a strong warning when any VPC Connector field is modified
- Display the list of affected Cloud Run services
- Consider a two-phase approach: create new connector, update services to point to new connector, then destroy old connector (blue-green pattern for connectors)
- Document Cloud Run Direct VPC Egress as a future alternative that avoids connectors entirely (see RESEARCH.md State of the Art)

## External LB Composite Nature (Pitfall 5)

External LB is unlike every other type in the platform. While other types map 1:1 to a Terraform resource, External LB is a **composite of 6-7 Terraform resources**:

| # | Sub-Resource | TF Resource | ForceNew Fields | Mutable Fields |
|---|-------------|-------------|-----------------|----------------|
| 1 | Static IP | `google_compute_global_address` | Most fields (name, address type) | -- |
| 2 | SSL Certificate | `google_compute_managed_ssl_certificate` | `domains` (changing triggers reprovision) | -- |
| 3 | Serverless NEG | `google_compute_region_network_endpoint_group` | `network_endpoint_type`, `region` | cloud_run service reference |
| 4 | Backend Service | `google_compute_backend_service` | `name` | backends, cdn_policy, security_policy, logging, IAP |
| 5 | URL Map | `google_compute_url_map` | `name` | default_service, routing rules |
| 6 | HTTPS Proxy | `google_compute_target_https_proxy` | `name` | url_map, ssl_certificates |
| 7 | Forwarding Rule | `google_compute_global_forwarding_rule` | `ip_address`, `port_range` | target |

### Lifecycle implications

- Adding/removing backends is an in-place update to the backend service (fast)
- Changing `domains` triggers SSL certificate recreation (15+ min for provisioning)
- Changing `scheme` (EXTERNAL_MANAGED vs EXTERNAL) affects backend_service and forwarding_rule (likely requires recreation)
- CDN policy, logging, security policy changes are all in-place updates to the backend service

### Phase 3 impact

The deploy engine must handle External LB as multiple Terraform resources with individual lifecycles. A single ExternalLbConfig change may affect only one sub-resource or multiple.

## CIDR Management

CIDR range management is critical for network types and feeds into Phase 7 (Networking Architecture).

### Subnet CIDR Rules

- `ip_cidr_range` is required and must be a valid CIDR notation
- CIDRs must not overlap within the same VPC
- **One-way mutability:** Subnet CIDR can be **expanded** (e.g., /24 to /20) but can **NEVER be shrunk**
  - Expanding is a non-destructive in-place update
  - Shrinking requires destroy-recreate, losing all connected resources
- Secondary IP ranges have their own non-overlapping CIDRs (used for GKE pod/service ranges)

### VPC Connector CIDR Rules

- VPC Connectors consume a /28 CIDR block from the VPC's address space
- This /28 must not overlap with any subnet CIDRs or other connector CIDRs
- The CIDR is ForceNew -- changing it requires connector recreation

### Platform Validation (Phase 2)

The platform should validate:
1. No CIDR overlap between subnets within the same VPC
2. No CIDR overlap between VPC Connector ranges and subnet ranges
3. Subnet CIDR changes are expansions, not contractions

## ip_cidr_range One-Way Expansion

Subnet `ip_cidr_range` has a unique mutability behavior not seen in any other field:

| Change Type | Allowed | Terraform Behavior | Example |
|------------|---------|-------------------|---------|
| Expand (larger range) | Yes | In-place update | /24 -> /20 |
| Same (no change) | Yes | No-op | /24 -> /24 |
| Shrink (smaller range) | **No** | **Error / ForceNew** | /24 -> /28 |

This creates a ratchet effect: once a CIDR is expanded, it cannot be reduced. The platform should:
- Validate that any ip_cidr_range change is an expansion
- Warn users that expansion is permanent
- Show the old and new range clearly in the UI before confirming

## No IAM Scope

None of the four network types have IAM scope in the REGISTRY:

| Type | iam_scope | Why |
|------|-----------|-----|
| vpc | None | VPCs are accessed via network configuration, not IAM |
| subnet | None | Subnets are VPC sub-resources, access via VPC |
| vpc_connector | None | Connectors are used by referencing their name |
| external_lb | None | LBs are accessed via IP/DNS routing |

Network resources provide connectivity, not data access. IAM bindings are applied to the resources that use the network (Cloud Run, Cloud SQL, etc.), not to the network resources themselves.

## Shared Characteristics

- All 4 types have only TF-mapped fields (0 platform-only fields)
- All 4 types produce `self_link` or `id` as default outputs
- All 4 types follow the "Network with Dependencies" archetype
- None have IAM scope -- access is via network configuration
- Network types are typically deployed once and rarely modified (unlike compute types which are updated frequently)
