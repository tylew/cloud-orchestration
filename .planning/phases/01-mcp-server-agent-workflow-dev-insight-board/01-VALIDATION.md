---
phase: 1
slug: mcp-server-agent-workflow-dev-insight-board
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
| **Framework** | pytest 7.x with pytest-asyncio |
| **Config file** | `packages/pyproject.toml` |
| **Quick run command** | `python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `python -m pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `python -m pytest tests/ -v --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | AGT-01 | unit | `python -m pytest tests/test_mcp_tools.py -k project` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | AGT-02 | unit | `python -m pytest tests/test_mcp_tools.py -k node` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 1 | AGT-03 | unit | `python -m pytest tests/test_mcp_tools.py -k blueprint` | ❌ W0 | ⬜ pending |
| 01-04-01 | 04 | 1 | AGT-04 | unit | `python -m pytest tests/test_mcp_tools.py -k secret` | ❌ W0 | ⬜ pending |
| 01-05-01 | 05 | 1 | AGT-05 | unit | `python -m pytest tests/test_mcp_tools.py -k code` | ❌ W0 | ⬜ pending |
| 01-06-01 | 06 | 1 | AGT-06 | unit | `python -m pytest tests/test_mcp_tools.py -k build` | ❌ W0 | ⬜ pending |
| 01-07-01 | 07 | 1 | AGT-07 | unit | `python -m pytest tests/test_mcp_tools.py -k deploy` | ❌ W0 | ⬜ pending |
| 01-08-01 | 08 | 2 | AGT-08 | unit | `python -m pytest tests/test_auto_provision.py -k service_account` | ❌ W0 | ⬜ pending |
| 01-09-01 | 09 | 2 | AGT-09 | unit | `python -m pytest tests/test_auto_provision.py -k iam` | ❌ W0 | ⬜ pending |
| 01-10-01 | 10 | 2 | AGT-10 | unit | `python -m pytest tests/test_auto_provision.py -k networking` | ❌ W0 | ⬜ pending |
| 01-11-01 | 11 | 3 | AGT-11 | manual | Browser test | ❌ W0 | ⬜ pending |
| 01-12-01 | 12 | 2 | AGT-12 | unit | `python -m pytest tests/test_mcp_tools.py -k debug` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_mcp_tools.py` — stubs for AGT-01 through AGT-07, AGT-12
- [ ] `tests/test_auto_provision.py` — stubs for AGT-08 through AGT-10
- [ ] `tests/conftest.py` — shared fixtures (mock Firestore, mock GCP clients)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dev insight board renders real-time data | AGT-11 | Requires browser + Firestore real-time subscriptions | Open dashboard, trigger node add via MCP, verify board updates within 2s |
| End-to-end agent workflow | AGT-05 | Full lifecycle spans multiple services | Run MCP tool sequence: add node → configure → set secret → build → deploy → verify |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
