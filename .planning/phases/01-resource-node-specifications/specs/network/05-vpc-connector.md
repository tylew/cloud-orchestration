# VPC Connector - Specifics

**Node type:** `vpc_connector`
**Terraform resource:** `google_vpc_access_connector`
**Category:** Network
**IAM scope:** None

---

## Overview

VPC Connector is **entirely immutable after creation**. It is the only resource type in the platform where every single field is ForceNew. Any configuration change -- even changing `min_instances` from 2 to 3 -- requires full destroy-recreate. This has significant implications for platform UX, deploy safety, and connected service availability.

VPC Connectors bridge serverless services (Cloud Run, Cloud Functions, App Engine) to VPC networks, enabling private IP access to resources like Cloud SQL, Memorystore, and internal services.

## Total Immutability

**Every field in VpcConnectorConfig is ForceNew:**

| Field | Why ForceNew |
|-------|-------------|
| region | Identity field -- connector is regional |
| network | Infrastructure binding -- connector is bound to specific VPC |
| ip_cidr_range | Network allocation -- /28 block is reserved in VPC |
| min_throughput | Infrastructure sizing -- determines internal resource allocation |
| max_throughput | Infrastructure sizing -- determines internal resource allocation |
| machine_type | Infrastructure sizing -- determines VM instance type for connector |
| min_instances | Infrastructure sizing -- determines minimum VM count |
| max_instances | Infrastructure sizing -- determines maximum VM count |

This is because VPC Connectors are implemented as managed instance groups (MIGs) of small VMs. Changing any parameter requires rebuilding the underlying VM infrastructure.

## Impact on Connected Cloud Run Services

When a VPC Connector is recreated:

1. **Terraform destroys the old connector** -- the internal VMs are terminated
2. **Connected Cloud Run services lose VPC connectivity** -- any in-flight requests to private IPs may fail
3. **Terraform creates a new connector** -- new VMs are provisioned
4. **Cloud Run services must be redeployed** to pick up the new connector (the connector resource ID changes)

### Downtime window

The gap between destroy and recreate is typically 1-3 minutes. During this window:
- Cloud Run services referencing the old connector cannot reach private VPC resources
- External HTTP requests to Cloud Run still work (public ingress is unaffected)
- Database connections via private IP will fail

### Mitigation strategies

1. **Blue-green connector:** Create a new connector (with a different name), update Cloud Run services to reference it, then delete the old connector. This requires the platform to support multiple connectors.
2. **Maintenance window:** Schedule connector changes during low-traffic periods.
3. **Cloud Run Direct VPC Egress:** A newer GCP feature that allows Cloud Run to directly connect to VPC without a connector. This eliminates the connector entirely but requires Cloud Run v2 and may not be GA for all regions.

## Field Details

### machine_type

| Value | Description | Max Throughput | Use Case |
|-------|-------------|---------------|----------|
| `e2-micro` (default) | Minimal compute | ~200 Mbps | Low-traffic services, development |
| `e2-standard-4` | Standard compute | ~3 Gbps | Production workloads |
| `f1-micro` | Legacy micro | ~100 Mbps | Cost-sensitive workloads |

Choosing the machine type is a permanent decision. Changing it requires full recreation.

### min_instances / max_instances

- **min_instances:** 2-9 (default 2). The minimum number of VMs backing the connector. Setting higher values provides more consistent throughput at higher cost.
- **max_instances:** 3-10 (default 10). The maximum scale-up limit. Must be >= min_instances + 1.
- Both are ForceNew -- cannot be adjusted after creation.
- **Recommendation:** For production, start with `min_instances=2, max_instances=10` (defaults). Only increase min_instances if consistent throughput is critical.

### min_throughput / max_throughput

- **Range:** 200-1000 Mbps each
- **Alternative to instance-based scaling:** These fields control throughput-based autoscaling. When set, the connector scales instances to maintain throughput between min and max.
- Both are ForceNew.

### ip_cidr_range

- **Format:** /28 CIDR range (e.g., `10.8.0.0/28` = 16 IPs)
- **Constraint:** Must be within the referenced VPC's address space and must NOT overlap with any subnet CIDRs
- **ForceNew:** The CIDR block is permanently reserved. Changing it requires recreation.
- **Address planning:** The platform should track allocated /28 blocks to prevent overlap (Phase 7).

### network

- **Format:** Reference to a VPC node (resolved via `resolve_ref`)
- **ForceNew:** Connector is permanently bound to a VPC.
- **Dependency:** Creates a hard edge from connector to VPC in the blueprint DAG.

## Cloud Run Direct VPC Egress (Future Alternative)

The existing codebase includes a `CloudRunVpcAccessDirect` model, suggesting awareness of Cloud Run Direct VPC Egress:

- **How it works:** Cloud Run instances connect directly to the VPC using the subnet's IP range, without requiring a VPC Connector.
- **Benefits:** No connector to manage, no connector-level bottleneck, no immutability concerns.
- **Current status:** Available in Cloud Run v2 but not yet reflected in the platform's TF templates.
- **Phase 7 consideration:** The networking architecture phase should evaluate whether to adopt Direct VPC Egress as the default, relegating VPC Connectors to legacy support.

## Edge Cases

1. **Connector name reuse:** Like Cloud Tasks queues, deleted VPC Connector names may be retained by GCP briefly. Immediate recreation with the same name may fail.

2. **CIDR overlap with subnets:** If the connector's /28 CIDR overlaps with a subnet's CIDR, Terraform will fail. The platform must validate non-overlap.

3. **Region mismatch:** The connector's region must match the region of the Cloud Run services that use it. Cross-region connector usage is not supported.

4. **Maximum connectors per VPC:** GCP limits the number of VPC Connectors per project and per VPC. The platform should be aware of these quotas.

5. **Throughput vs instances:** Both `min/max_throughput` and `min/max_instances` control scaling. The current Pydantic model includes both, and both are set in the TF template. In practice, instance-based scaling is more predictable.

6. **Cost:** VPC Connectors run always-on VMs (minimum 2). Even idle connectors incur compute costs. This is relevant for cost estimation and free-tier limits.
