# Phase 5: End-to-End User Acceptance Testing Suite - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 05-end-to-end-user-acceptance-testing-suite
**Areas discussed:** Test approach, Bug fix scope, UI/MCP requirements

---

## Combined Discussion

User was presented with three gray areas (test approach, bug fix scope, test coverage boundary) and responded with a single directive covering all:

**User's choice:** "Make the necessary assumptions so we have a dead basic path to either agent or user deploying, meaning we need the MCP available, and the UI available for the whole pipeline, UI needs to expose debug"

**Interpretation:**
- Both MCP (agent) and UI (human) deploy paths must work end-to-end
- Fix whatever blocks the critical path (the two pre-existing bugs)
- UI insight board must expose debug views of the pipeline
- Keep it minimal -- no exhaustive testing, just prove the pipeline works
- Claude should make reasonable assumptions rather than asking more questions

## Claude's Discretion

- Test data strategy (reuse existing fixtures vs new ones)
- Specific field name fix for list_deploys query
- Whether to wire or remove deployStatus store field
- Integration test timeouts and skip conditions

## Deferred Ideas

None
