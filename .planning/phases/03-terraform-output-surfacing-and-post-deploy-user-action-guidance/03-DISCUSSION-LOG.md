# Phase 3: Terraform Output Surfacing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 03-terraform-output-surfacing-and-post-deploy-user-action-guidance
**Areas discussed:** Output extraction strategy, Storage and delivery

---

## Output Extraction Strategy

### Q1: How should we extract structured output values from deploys?

| Option | Description | Selected |
|--------|-------------|----------|
| Generate TF output{} blocks | Wire registry default_outputs into Jinja2 templates. After apply, parse structured output from terraform output -json. | ✓ |
| Parse raw apply text | Regex/pattern-match existing apply_output text. No template changes but fragile. | |
| You decide | Claude picks best technical approach. | |

**User's choice:** Generate TF output{} blocks
**Notes:** Recommended approach — registry already defines default_outputs per node type.

### Q2: Should every node type get output blocks, or only external-facing?

| Option | Description | Selected |
|--------|-------------|----------|
| All node types with default_outputs | Generate output{} for every node type that has default_outputs. | |
| External-facing only | Only Cloud Run URLs, LB IPs, SQL connection strings, secret IDs. Skip internal values. | ✓ |
| You decide | Claude determines based on registry data. | |

**User's choice:** External-facing only
**Notes:** None

### Q3: How should outputs be captured from Cloud Build?

| Option | Description | Selected |
|--------|-------------|----------|
| Add terraform output step to Cloud Build | New CB step runs `terraform output -json`, writes to GCS. Orchestrator fetches like plan/apply output. | ✓ |
| Parse from apply text | Parse output values from existing apply_output. No new step needed. | |
| You decide | Claude picks based on CB pipeline structure. | |

**User's choice:** Add terraform output step to Cloud Build
**Notes:** None

---

## Storage and Delivery

### Q4: Where should parsed Terraform outputs be stored?

| Option | Description | Selected |
|--------|-------------|----------|
| On the deploy record | `terraform_outputs` field on deploy record. Tied to specific deploy. | |
| Separate env-level document | Latest outputs at env level, overwrites on each deploy. | |
| Both | Deploy record for history, env-level for quick lookup. | ✓ |

**User's choice:** Both
**Notes:** None

### Q5: How should the agent access outputs?

| Option | Description | Selected |
|--------|-------------|----------|
| New get_deploy_outputs tool | Dedicated MCP tool returning latest outputs for an env. | ✓ |
| Extend get_deploy_status | Add terraform_outputs to existing response. | |
| You decide | Claude picks based on Phase 1 MCP patterns. | |

**User's choice:** New get_deploy_outputs tool
**Notes:** None

### Q6: Should post-deploy guidance be part of the tool response?

| Option | Description | Selected |
|--------|-------------|----------|
| Include guidance in outputs tool | Per-node next_steps hints alongside output values. | |
| Outputs only, guidance later | Just structured output values. Guidance is a future concern. | ✓ |
| You decide | Claude determines fit. | |

**User's choice:** Outputs only, guidance later
**Notes:** Explicitly narrows phase scope — "post-deploy user action guidance" from the phase name is deferred.

---

## Claude's Discretion

- Which specific default_outputs qualify as "external-facing"
- Output block naming conventions
- JSON schema for terraform_outputs field
- GCS path for output JSON
- Error handling for failed output step

## Deferred Ideas

- Post-deploy guidance/next-steps hints (originally in phase name, explicitly deferred)
- Output-based cross-node wiring
- Drift detection
