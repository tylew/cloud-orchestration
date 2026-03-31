# M001: 

## Vision
Every resource type fully maps to its Terraform spec, the DAG models logical data flow beyond infrastructure dependencies, data contracts are defined and validated cross-node, and a minimal test UI lets one developer exercise the full workflow.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | Terraform Spec Audit & Schema Completeness | high | — | ✅ | After this: every node type schema covers the full GCP Terraform provider resource fields; updated templates render all fields; audit report documents gaps found and fixed |
| S02 | Deep DAG — Service Contract Model | high | S05 | ✅ | After this: compute nodes define service contracts with typed resource refs; contracts validated against blueprint; DAG surfaces contract edges alongside infra deps |
| S03 | Archive Dead Code & Minimal Test UI | low | S02 | ✅ | After this: dead frontend code archived; minimal UI exercises full workflow |
| S05 | Fix Terraform Template Bugs | high | S01 | ✅ | After this: all 14 terraform validate tests pass — every node type generates valid HCL that terraform accepts |
