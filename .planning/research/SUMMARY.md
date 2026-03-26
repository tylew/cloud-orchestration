# Research Summary: GCP Orchestration Platform - Design Specification

**Domain:** Multi-tenant GCP infrastructure orchestration
**Researched:** 2026-03-26
**Overall confidence:** MEDIUM-HIGH

## Executive Summary

The GCP Orchestration Platform has a solid foundation -- 22 node types in the registry, working Terraform generation via Jinja2, Cloud Build deploys, per-environment GCP project provisioning, and a dependency DAG with topological sorting. What is missing is the theoretical framework that ties these pieces together: how resources interact across layers, how IAM flows from dependency edges, how deploys work incrementally, and how tenant networking is isolated.

The design specification phase should produce complete specifications for six subsystems: networking (Shared VPC with CIDR-managed tenant subnets), deploy ordering (layered Terraform state with change-set-based incremental apply), IAM inference (deterministic role mapping from ActionType x NodeType edges), database schema lifecycle (instance provisioning via TF, schema management via Cloud Build migration steps), multi-environment lifecycle (promotion with env-specific overrides, drift detection), and billing pass-through (BigQuery billing export aggregated into Stripe meters).

The most architecturally significant decision is adopting **layered Terraform state** -- separating network, data, IAM, compute, and messaging into independent state files per tenant environment. This enables incremental deploys (only apply layers with changes), reduces blast radius (network changes cannot destroy compute), and isolates failure modes. The existing `BlueprintDAG.parallel_batches()` method already computes dependency layers; extending it to drive layer selection is natural.

The highest-risk area is **IAM inference**. The platform already has `ActionType` and `ACTION_VALID_TARGETS` mappings, but the complete mapping from (ActionType, NodeType) pairs to specific GCP IAM roles needs exhaustive specification and testing. A wrong role mapping means either broken deploys (insufficient permissions) or security vulnerabilities (excessive permissions). This must be the most rigorously specified subsystem.

## Key Findings

**Stack:** Existing stack is correct. Add Shared VPC, Cloud Asset Inventory (drift detection), BigQuery billing export (cost tracking), and Stripe Meters API (invoicing). No framework changes needed.

**Architecture:** Layered Terraform state per tenant environment, with change-set-based incremental deploys. IAM inference engine as a pure function of the dependency graph. Blueprint snapshot (not TF state) as source of truth.

**Critical pitfall:** Terraform destroy-recreate on immutable Cloud SQL fields -- can cause catastrophic data loss. Must lock immutable fields after first deploy and parse `terraform plan` output for `forces replacement` before applying.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Resource Lifecycle Specification** - Document create/update/delete behavior for all 22 node types
   - Addresses: Foundation needed by every other design
   - Avoids: Destroy-recreate pitfall by identifying immutable fields upfront
   - Output: Per-type lifecycle document with mutable/immutable fields, state machine

2. **Deploy Engine Design** - Layered TF state, deploy ordering, change set computation
   - Addresses: Incremental deploy, deploy ordering
   - Avoids: Monolithic deploy anti-pattern, blast radius issues
   - Output: Sequence diagrams for full and incremental deploys, layer definitions

3. **IAM Inference Specification** - Complete (ActionType, NodeType) -> Role mapping
   - Addresses: Zero-IAM-knowledge deploys
   - Avoids: Permission accumulation, over-permissive bindings
   - Output: Role mapping table, inference algorithm, override mechanism

4. **Networking Architecture** - Shared VPC design, CIDR allocation, VPC connectors
   - Addresses: Tenant network isolation
   - Avoids: VPC sprawl, CIDR exhaustion, subnet overlaps
   - Output: Network topology diagram, CIDR allocation algorithm

5. **Database & Schema Lifecycle** - Instance provisioning + schema management separation
   - Addresses: Cloud SQL DDL, Firestore indexes, BigQuery schemas
   - Avoids: Using Terraform for schema DDL
   - Output: Per-database-type lifecycle spec, migration pipeline design

6. **Environment & Billing** - Multi-env promotion, drift detection, cost pass-through
   - Addresses: Promotion workflow, billing integration
   - Avoids: Billing export lag surprises
   - Output: Promotion state machine, billing pipeline architecture

**Phase ordering rationale:**
- Resource lifecycle is foundational -- every other spec references it
- Deploy engine must be designed before IAM because IAM bindings are deployed as a layer
- IAM inference must be specified before networking because network resources have their own IAM
- Networking can proceed after deploy engine because it IS a deploy layer
- Database lifecycle depends on deploy engine (schema migrations are post-TF steps)
- Environment and billing are least coupled to other designs and can be last

**Research flags for phases:**
- Phase 3 (IAM): Needs deeper research to validate every role mapping against current GCP docs
- Phase 4 (Networking): Needs validation of Private Service Connect vs VPC peering for cross-project connectivity
- Phase 6 (Billing): Needs validation of BigQuery billing export lag and Stripe meter event limits
- Phases 1, 2, 5: Standard patterns, well-documented, unlikely to need additional research

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing stack is solid. Additions (Shared VPC, billing export) are well-documented GCP features. |
| Features | HIGH | Feature landscape is clear from existing codebase analysis and project requirements. |
| Architecture | MEDIUM-HIGH | Layered TF state is well-established pattern. IAM inference model is novel -- needs rigorous validation. |
| Pitfalls | MEDIUM-HIGH | Critical pitfalls identified from GCP and Terraform documentation. May miss edge cases specific to this platform's node type mix. |

## Gaps to Address

- **Complete IAM role mapping validation**: Need to verify every (ActionType, NodeType) -> GCP role mapping against current GCP documentation. Training data may have stale role names.
- **Cloud Run Direct VPC Egress**: May eliminate the need for VPC connectors entirely. Need to evaluate current GA status and limitations.
- **Stripe Meters API version requirements**: Stripe's 2025-03-31.basil API version requires meters for all metered prices. Verify backward compatibility.
- **Cloud Build concurrent build quotas**: Default is 10. Need to determine actual quota for the host project and plan for growth.
- **Firestore database limits**: Firestore has a 100-database limit per project. If each tenant env needs a separate database, this could be a scaling concern.
- **GCP Organization Policy constraints**: Some org policies may restrict what tenant projects can do. Need to audit current org policy set.

---

*Research summary: 2026-03-26*
