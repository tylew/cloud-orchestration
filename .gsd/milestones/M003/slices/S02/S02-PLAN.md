# S02: Explorer UI Cleanup

**Goal:** Explorer UI hides resource_id, no config ID fields in UI, dead insight code archived
**Demo:** After this: After this: explorer hides resource_id; name preview shows registry-derived name; no config ID fields in UI

## Tasks
- [x] **T01: Archive 9 insight dead-code files, remove insight route from App.tsx, add optional id/resource_id to BaseNode type** — This task does all the work for S02: archives 9 insight-related files to archive/web-insight/, removes the insight route from App.tsx, and adds optional id/resource_id fields to the frontend BaseNode type.

Steps:
1. Create `archive/web-insight/` directory
2. Move these files to `archive/web-insight/`:
   - `apps/web/src/screens/InsightBoard.tsx`
   - `apps/web/src/stores/insight-store.ts`
   - `apps/web/src/components/insight/ActivityFeed.tsx`
   - `apps/web/src/components/insight/DeployPanel.tsx`
   - `apps/web/src/components/insight/ProjectStatePanel.tsx`
   - `apps/web/src/components/insight/ResourceListPanel.tsx`
   - `apps/web/src/components/insight/StatusDot.tsx`
   - `apps/web/src/components/insight/TerraformPanel.tsx`
   - `apps/web/src/components/insight/ValidationPanel.tsx`
3. In `apps/web/src/App.tsx`: remove the InsightBoard import and the `/insight/:projectRefId` route
4. In `apps/web/src/types/node.ts`: add `id?: string` and `resource_id?: string` to the BaseNode type
5. Run `rg "insight" apps/web/src/` — must return zero hits
6. Run `rg "dataset_id|instance_id|account_id|database_id" apps/web/src/` — must return zero hits
7. Run `cd apps/web && npm run build` — must succeed with zero errors

Constraints:
- id and resource_id must be optional (existing data may lack them)
- Do NOT display resource_id anywhere in the UI
- Per D002: archive to archive/ directory, don't delete
  - Estimate: 20m
  - Files: apps/web/src/App.tsx, apps/web/src/types/node.ts, apps/web/src/screens/InsightBoard.tsx, apps/web/src/stores/insight-store.ts, apps/web/src/components/insight/
  - Verify: cd apps/web && npm run build && cd ../.. && test $(rg -c 'insight' apps/web/src/ 2>/dev/null | wc -l) -eq 0 && test -d archive/web-insight && ls archive/web-insight/ | wc -l | grep -q 9
