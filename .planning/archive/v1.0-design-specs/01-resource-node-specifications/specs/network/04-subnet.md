# Subnet - Specifics

**Node type:** `subnet`
**Terraform resource:** `google_compute_subnetwork`
**Category:** Network
**IAM scope:** None

---

## Overview

Subnet is a regional network segment within a VPC. It defines an IP address range (CIDR) from which compute resources (Cloud Run, Cloud SQL, etc.) receive IP addresses. Subnets are the primary mechanism for IP address management and network segmentation.

## Field Deep-Dive

### ip_cidr_range (one-way mutable)

- **Type:** `str`
- **Required:** Yes (error severity)
- **Format:** CIDR notation (e.g., `10.0.0.0/24`)
- **Mutable:** **Partially -- expand only, NEVER shrink**
- **This is the most unusual mutability behavior in the entire platform.**

#### Expansion behavior

| Current Range | New Range | Result | Description |
|---------------|-----------|--------|-------------|
| `10.0.0.0/24` | `10.0.0.0/20` | In-place update | 256 -> 4,096 IPs. Non-destructive. |
| `10.0.0.0/24` | `10.0.0.0/16` | In-place update | 256 -> 65,536 IPs. Non-destructive. |
| `10.0.0.0/20` | `10.0.0.0/24` | **ERROR** | Cannot shrink. Requires destroy-recreate. |
| `10.0.0.0/24` | `10.1.0.0/24` | **ForceNew** | Different network address = new subnet. |

The ratchet effect means the platform must:
1. Compare old and new CIDR ranges before applying
2. Validate the new range contains the old range (same network address, smaller prefix)
3. Warn users that expansion is permanent

### region (ForceNew -- identity)

- **Type:** `str`
- **Required:** Yes (error severity)
- **Mutable:** No (ForceNew -- identity field)
- **Impact:** Subnets are regional resources. A subnet in `us-central1` cannot be moved to `us-east1`. Changing region requires a new subnet with new CIDR, migrating all connected resources, and deleting the old subnet.

### network (ForceNew -- identity)

- **Type:** `str`
- **Required:** Yes (error severity)
- **Mutable:** No (ForceNew -- identity field)
- **Format:** Reference to a VPC node (resolved via `resolve_ref` in TF template)
- **Dependency:** Creates a hard dependency edge from this subnet to the referenced VPC
- **Impact:** Subnets cannot be moved between VPCs. Changing the VPC reference requires recreating the subnet and all dependent resources.

### private_ip_google_access

- **Type:** `bool`
- **Default:** `True`
- **Mutable:** Yes
- **Purpose:** Enables VM instances (and Cloud Run services via VPC Connector) to reach Google APIs and services using internal IP addresses instead of external IPs.
- **Critical for:** Cloud SQL private networking, accessing Google Cloud Storage from internal-only instances, any service that should not have a public IP.
- **Recommendation:** Keep enabled (`True`) unless there is a specific reason to disable.

### secondary_ip_ranges

- **Type:** `list[SecondaryIpRange] | None`
- **Default:** `None`
- **Mutable:** Yes (can add/remove secondary ranges)
- **Purpose:** Additional IP ranges for GKE pod and service IPs, or other specialized addressing needs.
- **Each range:** `range_name` (str) + `ip_cidr_range` (str) -- must not overlap with primary CIDR or other secondary ranges.
- **Note:** While the platform does not currently support GKE, secondary ranges may be needed for future integrations or advanced networking.

### log_config (VPC Flow Logs)

- **Type:** `SubnetLogConfig | None`
- **Default:** `None` (logging disabled)
- **Mutable:** Yes
- **Purpose:** Enables VPC Flow Logs for network traffic monitoring and debugging.

**SubnetLogConfig fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| aggregation_interval | str \| None | `None` | Log aggregation interval (e.g., `"INTERVAL_5_SEC"`, `"INTERVAL_1_MIN"`) |
| flow_sampling | float \| None | `None` | Sampling rate: 0.0 to 1.0 (1.0 = log all traffic) |
| metadata | str \| None | `None` | What metadata to include (`"INCLUDE_ALL_METADATA"`, `"EXCLUDE_ALL_METADATA"`, etc.) |

- **Cost implication:** Flow logs at high sampling rates generate significant log volume and cost. Use low sampling rates (0.1-0.5) in production.

### purpose

- **Type:** `str`
- **Default:** `"PRIVATE"`
- **Mutable:** Yes
- **Values:**
  - `PRIVATE`: Standard subnet for VM and service IP allocation
  - `REGIONAL_MANAGED_PROXY`: Reserved for proxy-only subnets used by regional load balancers
  - `INTERNAL_HTTPS_LOAD_BALANCER`: (Legacy) Same as REGIONAL_MANAGED_PROXY
- **Note:** Most subnets in the platform will use `PRIVATE`. Proxy-only subnets are specialized for internal load balancing.

## Network Reference Dependency

The `network` field creates the primary dependency edge:

```
subnet.config.network --> vpc (node reference)
```

This is resolved via `resolve_ref()` in the TF template to produce the VPC's `self_link` output. The dependency is enforced in the blueprint DAG -- subnet cannot be deployed before its VPC.

## Edge Cases

1. **Overlapping CIDRs:** Two subnets in the same VPC cannot have overlapping primary CIDRs. The platform should validate this (Phase 2). GCP will reject the Terraform apply if CIDRs overlap.

2. **CIDR exhaustion:** If a subnet's CIDR is fully allocated (all IPs in use), new resources cannot be placed in it. The only option is to expand the CIDR (if the surrounding address space allows it) or create a new subnet.

3. **Subnet without consumers:** A subnet with no resources using it is valid but wasteful. The platform could warn about unused subnets.

4. **Regional mismatch:** If a compute resource (Cloud Run) is in a different region than the subnet it needs to access, a VPC Connector in the correct region is needed. The platform should validate region alignment between subnets and connectors.

5. **Cross-region subnets:** A single VPC can have subnets in multiple regions. This is the standard pattern for multi-region architectures. Each subnet defines the IP range for its specific region.

6. **Secondary range overlap:** Secondary IP ranges must not overlap with the primary CIDR or with each other, both within the same subnet and across subnets in the same VPC.
