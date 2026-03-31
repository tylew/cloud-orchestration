# M002: 

## Vision
Every resource has a stable UUID identity. Cross-resource references are declared in a typed contract that drives validation, template generation, and UI intelligence. GCP naming conventions are explicit per type. The explorer UI leverages all of this for an intelligent configuration experience.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | Resource Identity — UUID Foundation | high | — | ✅ | After this: every node has a UUID id; depends_on uses IDs; TF resource labels are UUIDs; existing blueprints auto-migrate; all tests pass |
| S02 | Reference Contract — Type-Safe Cross-Resource Wiring | high | S01 | ✅ | After this: every cross-resource reference field is declared in a contract; validation catches broken refs with type checking; templates resolve refs from the contract; auto-depends_on inferred from refs |
| S03 | Naming Convention Contract | medium | S01 | ✅ | After this: each resource type has a declared GCP naming convention in the registry; templates derive names from registry rules; immutable names flagged; naming is consistent across all types |
| S04 | Explorer UI — Reference Dropdowns, Naming Preview, Rename | low | S01, S02, S03 | ✅ | After this: explorer UI renders ref fields as dropdowns filtered by target type; GCP name preview shown per resource; rename works without breaking anything; immutable name warnings shown |
