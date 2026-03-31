# S02: Explorer UI Cleanup — UAT

**Milestone:** M003
**Written:** 2026-03-31T17:14:17.969Z

# S02: Explorer UI Cleanup — UAT

**Milestone:** M003
**Written:** 2026-03-31

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: This slice only moves files, removes routes, and adds type fields — no runtime behavior to test

## Preconditions

- Working tree has apps/web/ source code
- Node.js 20 and npm available for builds

## Smoke Test

Run `cd apps/web && npm run build` — must exit 0 with no errors.

## Test Cases

### 1. No insight references in source

1. Run `rg 'insight' apps/web/src/`
2. **Expected:** Zero matches (exit code 1)

### 2. Insight files archived

1. Run `ls archive/web-insight/ | wc -l`
2. **Expected:** Exactly 9 files
3. Verify files include: InsightBoard.tsx, insight-store.ts, ActivityFeed.tsx, DeployPanel.tsx, ProjectStatePanel.tsx, ResourceListPanel.tsx, StatusDot.tsx, TerraformPanel.tsx, ValidationPanel.tsx

### 3. BaseNode type has id and resource_id

1. Run `grep -E 'id\?:|resource_id\?:' apps/web/src/types/node.ts`
2. **Expected:** Both `id?: string` and `resource_id?: string` present

### 4. Frontend builds clean

1. Run `cd apps/web && npm run build`
2. **Expected:** tsc and vite both exit 0

### 5. Tests pass

1. Run `python -m pytest -m "not integration" --ignore=packages/platform/tests/integration -q`
2. **Expected:** All non-integration tests pass (210+)

## Edge Cases

### App.tsx has no orphaned imports

1. Run `grep -i 'insight' apps/web/src/App.tsx`
2. **Expected:** Zero matches

## Failure Signals

- `npm run build` fails with missing imports (insight components referenced somewhere)
- `rg insight apps/web/src/` returns matches
- archive/web-insight/ has fewer than 9 files

## Not Proven By This UAT

- Runtime behavior of the app (no dev server tested)
- That resource_id is correctly hidden in UI rendering (no UI components display it)
- Integration test suite health (pre-existing GCP credential failures)

## Notes for Tester

- Pre-existing integration tests fail due to GCP credentials — not related to this slice
- scroll-area.tsx unused React import was fixed as part of this slice (pre-existing TS6133)
