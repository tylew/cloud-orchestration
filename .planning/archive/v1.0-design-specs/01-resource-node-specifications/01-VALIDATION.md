---
phase: 1
slug: resource-node-specifications
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with pytest-asyncio |
| **Config file** | `packages/pyproject.toml` |
| **Quick run command** | `python -m pytest tests/ -x --tb=short` |
| **Full suite command** | `python -m pytest tests/` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Manual review — verify spec covers all fields from Pydantic model
- **After every plan wave:** Cross-reference field counts between spec and config model
- **Before `/gsd:verify-work`:** All 19 top-level types + 4 child types have complete specs
- **Max feedback latency:** N/A (documentation-only phase)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | RSLC-01 | manual-only | N/A — documentation review | N/A | ⬜ pending |
| 01-02-01 | 02 | 1 | RSLC-02 | manual-only | N/A — documentation review | N/A | ⬜ pending |
| 01-03-01 | 03 | 1 | RSLC-03 | manual-only | N/A — documentation review | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. This is a documentation-only phase — no test infrastructure needed. Validation is structural review (all types covered, all fields listed, all mutability classified).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| State machines documented for all 22+ types | RSLC-01 | Documentation content review | Verify each spec has create/update/delete state transitions matching D-03 platform states |
| Mutable vs immutable fields classified | RSLC-02 | Documentation content review | Verify every Terraform-mapped field has mutability tag; cross-reference against Pydantic model field count |
| Default values and validation constraints defined | RSLC-03 | Documentation content review | Verify defaults match Pydantic model defaults; constraints include type, range/pattern, required/optional |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < N/A (docs only)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
