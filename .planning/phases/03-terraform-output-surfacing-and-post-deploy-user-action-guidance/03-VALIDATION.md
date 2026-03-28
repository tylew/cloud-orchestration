---
phase: 3
slug: terraform-output-surfacing-and-post-deploy-user-action-guidance
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x with pytest-asyncio |
| **Config file** | `packages/pyproject.toml` |
| **Quick run command** | `python -m pytest packages/ -x -q --timeout=10` |
| **Full suite command** | `python -m pytest packages/ -q --timeout=30` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest packages/ -x -q --timeout=10`
- **After every plan wave:** Run `python -m pytest packages/ -q --timeout=30`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 1 | TF output gen | unit | `python -m pytest packages/core/terraform/ -x -q` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | CB step | integration | `python -m pytest packages/platform/ -x -q` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | MCP tool | unit | `python -m pytest packages/mcp/ -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test stubs for output generation in `packages/core/terraform/`
- [ ] Test stubs for Cloud Build output step
- [ ] Test stubs for MCP `get_deploy_outputs` tool
- [ ] Shared fixtures for mock registry, mock nodes, mock deploy records

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cloud Build step runs terraform output -json | D-03 | Requires live GCP project | Deploy to dev env, verify GCS blob exists |
| Env output doc written to Firestore | D-04 | Requires Firestore emulator or live | Check Firestore after deploy |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
