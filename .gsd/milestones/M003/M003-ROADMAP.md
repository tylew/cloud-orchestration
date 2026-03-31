# M003: 

## Vision
GCP resource IDs are fully abstracted from users. Every node gets an auto-generated, immutable resource_id at creation. Per-type naming templates in the registry derive GCP-safe resource names. Config-level ID fields are removed. Users only think about display names.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | resource_id on BaseNode + Registry Naming Templates | high | — | ✅ | After this: every node has an auto-generated resource_id; registry entries define naming templates; config-level ID fields removed; resolve_gcp_name uses resource_id; all TF templates produce valid HCL |
| S02 | Explorer UI Cleanup | low | S01 | ✅ | After this: explorer hides resource_id; name preview shows registry-derived name; no config ID fields in UI |
