# Phase 4: Cross-Phase Integration Fixes - Research

**Researched:** 2026-03-28
**Domain:** Cross-phase integration gap closure (Python backend, TypeScript frontend)
**Confidence:** HIGH

## Summary

Phase 4 closes three specific cross-phase integration gaps identified in the v1.0 milestone audit. All three gaps are well-understood, precisely located, and have clear fixes. This is a surgical bug-fix phase, not a design phase.

**GAP-1** (AGT-02): The MCP `add_node` tool has a hardcoded `_SLUG_PREFIXES` allowlist that was written in Phase 1, before Phase 2 added `cloud_dns`. Adding `cloud_dns` to this dict (and the identical dict in the REST API handler) enables MCP to create DNS nodes.

**GAP-2** (AGT-11): The frontend `ResourceListPanel` has a `TYPE_LABELS` map missing the `cloud_dns` entry, causing it to render as a raw string instead of "Cloud DNS".

**GAP-3** (OUT-04): The `_parse_terraform_outputs()` function uses `rsplit("_", 1)` to split output keys into `(node_name, attribute)`. This fails for multi-underscore output names like `name_servers` and `connection_name`, because the last underscore is inside the attribute name, not at the node/attribute boundary. The fix requires matching against known node names from the blueprint envelope.

**Primary recommendation:** Three targeted edits across 3 files, plus corresponding test updates. No architectural changes needed.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AGT-02 (gap) | MCP tools for node CRUD must support cloud_dns | GAP-1: Add `"cloud_dns": "dn"` to `_SLUG_PREFIXES` in both `packages/mcp/tools/nodes.py` and `packages/api/handlers/nodes.py` |
| AGT-11 (gap) | Insight board must display cloud_dns with proper label | GAP-2: Add `cloud_dns: "Cloud DNS"` to `TYPE_LABELS` in `ResourceListPanel.tsx` |
| OUT-04 (gap) | by_node output grouping must handle multi-underscore output names | GAP-3: Replace `rsplit("_", 1)` with node-name-aware parsing in `_parse_terraform_outputs()` |
</phase_requirements>

## Standard Stack

No new libraries required. All fixes use existing code patterns in the current stack.

### Existing Code Patterns Used
| Pattern | Location | Purpose |
|---------|----------|---------|
| `_SLUG_PREFIXES` dict | `packages/mcp/tools/nodes.py:35-45` | Maps node types to 2-char slug prefixes |
| `_SLUG_PREFIXES` dict (REST) | `packages/api/handlers/nodes.py:23-33` | Identical map in REST handler |
| `TYPE_LABELS` record | `apps/web/src/components/insight/ResourceListPanel.tsx:13-33` | Maps node type strings to display labels |
| `_parse_terraform_outputs()` | `packages/platform/deploy_orchestrator.py:102-123` | Parses TF output JSON into flat + by_node dicts |
| `_OUTPUT_ATTR_MAP` | `packages/core/terraform/generator.py:49-71` | Maps `(node_type, output_name)` tuples to TF attributes |

## Architecture Patterns

### GAP-1 Fix: Add cloud_dns to slug prefix maps

Two files contain identical `_SLUG_PREFIXES` dicts. Both must be updated in lockstep:

```python
# packages/mcp/tools/nodes.py line ~44, and packages/api/handlers/nodes.py line ~32
# Add after "cloud_sql_table": "st",
"cloud_dns": "dn",
```

The prefix `"dn"` is unused (verified: no existing prefix collisions). This follows the established 2-char abbreviation pattern.

### GAP-2 Fix: Add cloud_dns label to ResourceListPanel

```typescript
// apps/web/src/components/insight/ResourceListPanel.tsx
// Add after third_party_api entry in TYPE_LABELS:
cloud_dns: 'Cloud DNS',
```

This follows the existing pattern where each node type maps to a human-readable label. The fallback on line 129 `{TYPE_LABELS[nodeType] || nodeType}` means missing entries render as raw strings -- adding the entry fixes the display.

### GAP-3 Fix: Node-name-aware output parsing

The current broken approach:
```python
# rsplit("_", 1) on "my-zone_name_servers" gives:
# ("my-zone_name", "servers")  -- WRONG
```

The correct approach: match output keys against known node names from the blueprint. The output naming convention is `{node.name}_{output.name}` (see generator.py line 367). Node names use hyphens (e.g., `my-zone`, `my-db`), while output names can contain underscores (e.g., `name_servers`, `connection_name`).

**Fix strategy:** Pass the list of node names to `_parse_terraform_outputs()`. For each output key, try to match against known node names (longest match first to handle edge cases). If a node name is found as a prefix followed by `_`, the remainder is the attribute name.

```python
def _parse_terraform_outputs(raw: dict, node_names: list[str] | None = None) -> dict:
    flat = {}
    by_node = {}
    # Sort node names longest-first to match greedily
    sorted_names = sorted(node_names or [], key=len, reverse=True)
    for key, entry in raw.items():
        value = entry.get("value") if isinstance(entry, dict) else entry
        flat[key] = value
        # Match against known node names
        matched = False
        for name in sorted_names:
            prefix = f"{name}_"
            if key.startswith(prefix) and len(key) > len(prefix):
                attr = key[len(prefix):]
                if name not in by_node:
                    by_node[name] = {}
                by_node[name][attr] = value
                matched = True
                break
        # Fallback: rsplit for unknown nodes (backward compat)
        if not matched:
            parts = key.rsplit("_", 1)
            if len(parts) == 2:
                node_name, attr = parts
                if node_name not in by_node:
                    by_node[node_name] = {}
                by_node[node_name][attr] = value
    return {"outputs": flat, "by_node": by_node}
```

The call site in `_run_deploy()` line 202 has access to `envelope` and can extract node names:

```python
# Extract node names for output parsing
node_names = [n.get("name", n.get("slug", "")) for n in envelope.get("nodes", [])]
tf_outputs = _parse_terraform_outputs(tf_outputs_raw, node_names=node_names) if tf_outputs_raw else None
```

### Anti-Patterns to Avoid
- **Regex-only parsing:** Don't try to parse `{node_name}_{attr}` with regex alone -- node names can contain hyphens and underscores in theory, making regex fragile without the node name list.
- **Modifying the output naming convention:** Don't change the TF output naming pattern (e.g., to use `__` as separator). This would require migration of existing stored outputs and break backward compatibility.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Node type validation | A new validation layer | Add to existing `_SLUG_PREFIXES` dict | The dict IS the allowlist; extending it is the pattern |
| Output key parsing | Custom regex parser | Node name prefix matching from blueprint | The blueprint is the authoritative source of node names |

## Common Pitfalls

### Pitfall 1: Forgetting the REST API handler
**What goes wrong:** Updating `_SLUG_PREFIXES` in MCP tools but not in `packages/api/handlers/nodes.py`
**Why it happens:** The dict is duplicated across two files (acknowledged tech debt -- see comment on MCP file line 34)
**How to avoid:** Update BOTH files in the same task. Search for `_SLUG_PREFIXES` across the codebase.
**Warning signs:** REST API rejects cloud_dns but MCP accepts it (or vice versa)

### Pitfall 2: Backward compatibility of _parse_terraform_outputs
**What goes wrong:** Changing the function signature breaks existing callers
**Why it happens:** The function is called in `_run_deploy()` which passes no node_names currently
**How to avoid:** Make `node_names` parameter optional with default `None`. When `None`, fall back to the existing `rsplit` behavior. This ensures any other callers (tests, future code) still work.
**Warning signs:** Existing `test_parse_terraform_outputs_by_node` test fails

### Pitfall 3: Existing test expectations for by_node parsing
**What goes wrong:** Existing tests in `test_terraform_outputs.py` test by_node with simple output names (e.g., `my-service_endpoint`, `my-db_ip`) that work with rsplit. These tests should still pass after the fix.
**Why it happens:** The fix changes parsing logic
**How to avoid:** Keep backward compat (rsplit fallback when no node_names), and add NEW tests for multi-underscore cases
**Warning signs:** `TestOutputStorage::test_parse_terraform_outputs_by_node` fails

### Pitfall 4: Node names with underscores
**What goes wrong:** If a node name itself contains underscores (unlikely but theoretically possible via REST API), prefix matching could be ambiguous
**Why it happens:** Node slugs use hyphens (`cr-abc123`) but node names are user-defined
**How to avoid:** The longest-match-first strategy handles this -- longer node names match first. The existing tests use hyphenated names which is the convention enforced by slug generation.
**Warning signs:** A node named `my_db` with output `connection_name` would produce key `my_db_connection_name` which could match as `my_db` + `connection_name` or `my_db_connection` + `name`

## Code Examples

### GAP-1: _SLUG_PREFIXES addition (verified pattern)
```python
# Source: packages/mcp/tools/nodes.py lines 35-45
# Current dict ends with:
    "cloud_sql_database": "sd", "cloud_sql_table": "st",
}
# Add:
    "cloud_dns": "dn",
# Before the closing brace
```

### GAP-2: TYPE_LABELS addition (verified pattern)
```typescript
// Source: apps/web/src/components/insight/ResourceListPanel.tsx lines 13-33
// Current map ends with:
  third_party_api: 'Third Party API',
}
// Add:
  cloud_dns: 'Cloud DNS',
```

### GAP-3: Fixed _parse_terraform_outputs (new implementation)
```python
# Source: packages/platform/deploy_orchestrator.py lines 102-123
# See Architecture Patterns section above for full implementation
```

### GAP-3: Updated call site
```python
# Source: packages/platform/deploy_orchestrator.py line 202
# Before:
tf_outputs = _parse_terraform_outputs(tf_outputs_raw) if tf_outputs_raw else None
# After:
node_names = [n.get("name", n.get("slug", "")) for n in envelope.get("nodes", [])]
tf_outputs = _parse_terraform_outputs(tf_outputs_raw, node_names=node_names) if tf_outputs_raw else None
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `packages/pyproject.toml` |
| Quick run command | `python3 -m pytest packages/tests/ -x --tb=short` |
| Full suite command | `python3 -m pytest packages/tests/ --tb=short` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGT-02 (gap) | add_node accepts cloud_dns type | unit | `python3 -m pytest packages/tests/test_mcp_nodes.py -x -k cloud_dns` | Needs new test |
| AGT-11 (gap) | ResourceListPanel shows "Cloud DNS" label | manual | Visual inspection (no frontend test framework) | N/A |
| OUT-04 (gap) | by_node parses multi-underscore output names correctly | unit | `python3 -m pytest packages/tests/test_terraform_outputs.py -x -k by_node` | Exists (needs new cases) |

### Sampling Rate
- **Per task commit:** `python3 -m pytest packages/tests/test_mcp_nodes.py packages/tests/test_terraform_outputs.py -x --tb=short`
- **Per wave merge:** `python3 -m pytest packages/tests/ --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `packages/tests/test_mcp_nodes.py` -- add test: `test_add_node_cloud_dns_accepted` (verifies cloud_dns in _VALID_NODE_TYPES)
- [ ] `packages/tests/test_terraform_outputs.py` -- add test: `test_parse_terraform_outputs_by_node_multi_underscore` (verifies name_servers, connection_name parsing)
- [ ] `packages/tests/test_terraform_outputs.py` -- add test: `test_parse_terraform_outputs_by_node_with_node_names` (verifies node-name-aware parsing)

## Open Questions

1. **Should _SLUG_PREFIXES be derived from a single source?**
   - What we know: The dict is duplicated in `packages/mcp/tools/nodes.py` and `packages/api/handlers/nodes.py`. Both must be updated when adding node types.
   - What's unclear: Whether this tech debt should be addressed now or deferred.
   - Recommendation: **Defer.** Fix the immediate gap (add cloud_dns to both). Consolidation is a separate refactor task, not blocking for Phase 4.

## Sources

### Primary (HIGH confidence)
- `packages/mcp/tools/nodes.py` -- direct code inspection of _SLUG_PREFIXES (line 35-45)
- `packages/api/handlers/nodes.py` -- direct code inspection of _SLUG_PREFIXES (line 23-33)
- `apps/web/src/components/insight/ResourceListPanel.tsx` -- direct code inspection of TYPE_LABELS (line 13-33)
- `packages/platform/deploy_orchestrator.py` -- direct code inspection of _parse_terraform_outputs (line 102-123)
- `packages/core/terraform/generator.py` -- output naming convention (line 367)
- `.planning/v1.0-MILESTONE-AUDIT.md` -- gap definitions (lines 118-137)
- `packages/tests/test_terraform_outputs.py` -- existing test coverage (26 tests passing)
- `packages/tests/test_mcp_nodes.py` -- existing test coverage (8 tests)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, all existing patterns
- Architecture: HIGH -- all three fixes are precisely scoped with clear implementations
- Pitfalls: HIGH -- edge cases identified through direct code analysis

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable -- fixes are deterministic code changes)
