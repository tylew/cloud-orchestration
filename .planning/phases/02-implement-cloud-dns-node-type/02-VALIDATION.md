---
phase: 2
slug: implement-cloud-dns-node-type
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x with pytest-asyncio |
| **Config file** | `packages/pyproject.toml` |
| **Quick run command** | `python -m pytest packages/ -x -q --tb=short` |
| **Full suite command** | `python -m pytest packages/ -v --tb=short` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest packages/ -x -q --tb=short`
- **After every plan wave:** Run `python -m pytest packages/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | cloud_dns enum + schema | unit | `python -m pytest packages/ -k "cloud_dns or registry" -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | registry entry | unit | `python -m pytest packages/ -k "registry" -x` | ✅ | ⬜ pending |
| 02-01-03 | 01 | 1 | TF template | unit | `python -m pytest packages/ -k "terraform" -x` | ✅ | ⬜ pending |
| 02-01-04 | 01 | 1 | validation + refs | unit | `python -m pytest packages/ -k "validation" -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/tests/test_cloud_dns.py` — cloud_dns schema validation, record types, cross-node refs
- [ ] Existing `test_registry.py` already enforces all enum values have registry entries

*Existing test infrastructure covers framework needs. Only cloud_dns-specific test stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TF template renders valid HCL | cloud_dns template | HCL syntax validation requires terraform CLI | Run `terraform fmt -check` on generated output |

*Most behaviors have automated verification via existing test patterns.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
