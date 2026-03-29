---
phase: 4
slug: cross-phase-integration-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| **Config file** | `packages/pyproject.toml` |
| **Quick run command** | `python3 -m pytest packages/tests/test_mcp_nodes.py packages/tests/test_terraform_outputs.py -x --tb=short` |
| **Full suite command** | `python3 -m pytest packages/tests/ --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest packages/tests/test_mcp_nodes.py packages/tests/test_terraform_outputs.py -x --tb=short`
- **After every plan wave:** Run `python3 -m pytest packages/tests/ --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | AGT-02 | unit | `python3 -m pytest packages/tests/test_mcp_nodes.py -x -k cloud_dns` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | AGT-11 | manual | Visual inspection (no frontend test framework) | N/A | ⬜ pending |
| 04-02-01 | 02 | 1 | OUT-04 | unit | `python3 -m pytest packages/tests/test_terraform_outputs.py -x -k by_node` | ✅ (needs new cases) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/tests/test_mcp_nodes.py` — add test: `test_add_node_cloud_dns_accepted` (verifies cloud_dns in _VALID_NODE_TYPES)
- [ ] `packages/tests/test_terraform_outputs.py` — add test: `test_parse_terraform_outputs_by_node_multi_underscore` (verifies name_servers, connection_name parsing)
- [ ] `packages/tests/test_terraform_outputs.py` — add test: `test_parse_terraform_outputs_by_node_with_node_names` (verifies node-name-aware parsing)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ResourceListPanel shows "Cloud DNS" label | AGT-11 | No frontend test framework configured | Open insight board, add cloud_dns node, verify label reads "Cloud DNS" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
