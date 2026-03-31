---
estimated_steps: 1
estimated_files: 11
skills_used: []
---

# T04: Audit & update Network types (VPC, Subnet, VPC Connector, External LB, Cloud DNS)

Use Terraform MCP to pull full specs for google_compute_network, google_compute_subnetwork, google_vpc_access_connector, google_compute_global_forwarding_rule (or appropriate LB resource), google_dns_managed_zone. VPC and Subnet are very thin (~6 and ~15 lines). Expect gaps.

## Inputs

- `Terraform MCP specs for 5 network resources`

## Expected Output

- `Updated schemas and templates for 5 network types`
- `New tests`

## Verification

pytest packages/tests/test_terraform.py -v
