# VPC - Specifics

**Node type:** `vpc`
**Terraform resource:** `google_compute_network`
**Category:** Network
**IAM scope:** None

---

## Overview

VPC (Virtual Private Cloud) is the root network resource. Every other network type (subnet, VPC connector) and many non-network types (Cloud SQL private networking, Cloud Run VPC egress) reference back to a VPC. It is the foundation of the networking layer.

## Field Deep-Dive

### auto_create_subnetworks

- **Type:** `bool`
- **Required:** Yes (no default in Pydantic -- must be explicitly set)
- **Mutable:** Yes
- **Recommendation:** Set to `false` (custom mode) for explicit CIDR control
- **When `true`:** GCP auto-creates one subnet per region with predefined /20 CIDRs. Convenient for prototyping but limits control over IP addressing.
- **When `false`:** No subnets are created. The platform must explicitly create `subnet` nodes for each needed region. This is the production-recommended approach.
- **Gotcha:** Switching from `true` to `false` does not delete auto-created subnets. Switching from `false` to `true` creates subnets in all regions that don't already have one.

### routing_mode

- **Type:** `str`
- **Default:** `"REGIONAL"`
- **Mutable:** Yes
- **Values:** `REGIONAL` or `GLOBAL`
- **REGIONAL:** Routes learned by Cloud Router apply only to the region where the router is deployed. Standard for single-region architectures.
- **GLOBAL:** Routes learned by Cloud Router apply to all regions. Required for multi-region architectures with inter-region routing.
- **Impact:** Changing routing mode is non-destructive but affects all routing behavior within the VPC.

### description

- **Type:** `str | None`
- **Default:** `None`
- **Mutable:** **No (ForceNew)** -- this is a gotcha
- **Impact:** Changing the VPC description requires **full VPC recreation**, which cascades to all dependent resources (subnets, connectors, anything referencing this VPC)
- **Platform UX:** The description field should have a prominent warning in the UI: "Changing this field after deployment will recreate the VPC and all dependent resources."
- **Recommendation:** Set the description correctly before first deploy. If it must change, plan a full network rebuild.

### mtu

- **Type:** `int`
- **Default:** `1460`
- **Range:** 1300-8896 (validated by Pydantic `Field(ge=1300, le=8896)`)
- **Mutable:** Yes
- **Impact:** Changing MTU affects all connected resources. Jumbo frames (8896) can improve throughput for internal traffic but may cause issues with external connectivity.
- **Common values:** 1460 (standard, compatible with all traffic), 8896 (jumbo frames, internal-only optimization)

### delete_default_routes_on_create

- **Type:** `bool`
- **Default:** `False`
- **Mutable:** **No (ForceNew)**
- **When `true`:** Removes the default `0.0.0.0/0` route to the internet gateway. Needed for custom routing tables where all traffic must go through a specific appliance or VPN.
- **When `false`:** The default internet route is preserved (standard behavior).
- **Use case:** Advanced networking scenarios where the platform needs to control all egress routing.

## VPC as Root Dependency

VPC is referenced by multiple resource types:

| Resource | Via Field | Dependency Direction |
|----------|-----------|---------------------|
| `subnet` | `config.network` | subnet -> VPC |
| `vpc_connector` | `config.network` | connector -> VPC |
| `cloud_sql` | `config.ip_configuration.private_network` | Cloud SQL -> VPC (for private IP) |
| `cloud_run` | `config.vpc_access.connector` (indirectly via connector -> VPC) | Cloud Run -> VPC (transitive) |

This means VPC must be deployed first in the network layer and destroyed last.

## Edge Cases

1. **VPC without subnets:** A VPC with `auto_create_subnetworks=false` and no subnet nodes is valid but useless. The platform could warn about this (Phase 2 validation).

2. **Default VPC conflict:** GCP projects may have a "default" VPC auto-created. The platform's VPC uses environment-prefixed names (e.g., `dev-my-vpc`) to avoid conflicts, but the default VPC's auto-created subnets may have overlapping CIDRs.

3. **MTU mismatch:** If VPC MTU is set to jumbo (8896) but a subnet or connected resource expects standard MTU, packet fragmentation may occur. The platform does not currently validate MTU consistency.

4. **Cross-project VPC (Shared VPC):** The current model assumes VPCs are created within the tenant's project. Shared VPC (host project owns VPC, service projects use it) is a Phase 7 architecture concern and is not reflected in the current Pydantic model.

5. **Multiple VPCs:** A blueprint can contain multiple VPC nodes. Each VPC creates an isolated network. Subnets must reference a specific VPC via the `network` field.
