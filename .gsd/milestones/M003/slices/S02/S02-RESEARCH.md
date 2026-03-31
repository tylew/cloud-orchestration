# S02 — Explorer UI Cleanup — Research

**Date:** 2026-03-31

## Summary

The frontend TypeScript `BaseNode` type (`apps/web/src/types/node.ts`) has no `id`, `resource_id`, or `gcp_name` fields — it still only knows `slug`, `name`, `type`, `depends_on`, `config`, `env_vars`. The backend now returns these new fields (added in S01), but the frontend silently ignores them. No UI component renders config-level ID fields (`dataset_id`, `instance_id`, `account_id`, `database_id`) — those were already backend-only concerns.

The slice scope is: (1) update the TS `BaseNode` type to include `id` and `resource_id` (so they're available but not displayed), (2) optionally show a GCP name preview derived from the node type, and (3) archive the dead insight code (InsightBoard, insight-store, insight/* components) per D002/R006. The insight code is a self-contained island — only referenced internally and from one route in App.tsx.

## Recommendation

This is light, low-risk work. Three independent tasks: update the TypeScript type, archive the insight dead code, and verify the app builds and runs. No new libraries, no complex integration.

## Implementation Landscape

### Key Files

- `apps/web/src/types/node.ts` — Add `id`, `resource_id` to `BaseNode` type (optional fields, since existing data may lack them)
- `apps/web/src/components/resources/ResourceList.tsx` — Currently shows `node.name` and `node.type`. Could add a GCP name preview subtitle, but not strictly required
- `apps/web/src/App.tsx` — Remove `InsightBoard` import and `/insight/:projectRefId` route
- `apps/web/src/screens/InsightBoard.tsx` — Archive to `archive/`
- `apps/web/src/stores/insight-store.ts` — Archive to `archive/`
- `apps/web/src/components/insight/` — Entire directory (7 files: DeployPanel, TerraformPanel, StatusDot, ResourceListPanel, ProjectStatePanel, ActivityFeed, ValidationPanel) — Archive to `archive/`
- `apps/web/src/stores/blueprint-store.ts` — No changes needed (already handles BaseNode generically)

### Build Order

1. **Archive insight dead code** — remove route from App.tsx, move 9 files to `archive/web-insight/`. This is the largest chunk of file moves but zero risk.
2. **Update TypeScript BaseNode type** — add `id?: string` and `resource_id?: string` fields. Optional because the API may return nodes without them (pre-migration data).
3. **Verify** — `npm run build` in `apps/web/` passes with no errors and no dead imports.

### Verification Approach

- `cd apps/web && npm run build` — must succeed with zero errors
- `rg "insight" apps/web/src/` — must return zero hits (all archived)
- `rg "dataset_id\|instance_id\|account_id\|database_id" apps/web/src/` — must return zero hits (confirms no config ID fields in UI)
- Confirm `archive/web-insight/` contains all moved files
