# Changelog

All notable changes to Lithos are documented here. The full changelog is maintained in the [main repository](https://github.com/agent-lore/lithos/blob/main/CHANGELOG.md).

---

## Unreleased

### Breaking Changes

- **`lithos_semantic` MCP tool removed.** Use `lithos_search` with `mode="semantic"` for pure semantic search, or the new default `mode="hybrid"` for best results.

- **`lithos_search` now defaults to hybrid mode.** Existing callers that relied on `lithos_search` for full-text-only results will now receive hybrid (BM25 + semantic RRF) results. Pass `mode="fulltext"` explicitly to restore the previous behaviour.

- **`similarity` key renamed to `score` in search results.** Callers migrating from `lithos_semantic` that read `result["similarity"]` must update to `result["score"]`. All three modes (`hybrid`, `fulltext`, `semantic`) now use a unified `score` field.

- **`agent` is now required on `lithos_delete`.** Previously optional. Callers that omit it will receive a `TypeError` from the MCP layer.

### Added

- `lithos_search` now accepts a `mode` parameter: `fulltext` | `semantic` | `hybrid` (default: `hybrid`).
- Hybrid search mode merges Tantivy (BM25) and ChromaDB (cosine similarity) results using Reciprocal Rank Fusion (RRF, k=60) for improved ranking quality.
- Unknown `mode` values now return a structured `{ "status": "error", "code": "invalid_mode", ... }` dict instead of raising a `ValueError`.

### Fixed

- **`lithos_read` returns structured error on missing document** (issue #102): Previously propagated a raw `FileNotFoundError`. Now returns `{ "status": "error", "code": "doc_not_found", "message": "..." }`.

- **Consistent error envelopes across all tools** (issue #85): Coordination tools (`lithos_task_claim`, `lithos_task_renew`, `lithos_task_release`, `lithos_task_complete`) and `lithos_delete` now all return the standard `{ "status": "error", "code": "...", "message": "..." }` envelope on failure paths.

    | Tool | Error code |
    |------|-----------|
    | `lithos_delete` (not found) | `doc_not_found` |
    | `lithos_task_claim` (conflict) | `claim_failed` |
    | `lithos_task_renew` (no claim) | `claim_not_found` |
    | `lithos_task_release` (no claim) | `claim_not_found` |
    | `lithos_task_complete` (missing/closed) | `task_not_found` |

### Schema Changes

- **`version` field in frontmatter** (issue #45, PR #55): All knowledge documents now have a `version: 1` integer field in their YAML frontmatter for optimistic locking. Existing documents without this field are treated as `version: 1` on first read — no migration needed.

    The `lithos_write` tool now accepts an optional `expected_version` parameter. If provided and the document's current version doesn't match, the call returns a `version_conflict` error.

---

## Migration Guide

### From `lithos_semantic` to `lithos_search`

**Before:**

```python
results = lithos_semantic(query="how to run async tasks in python")
# results[0]["similarity"]  ← old key
```

**After:**

```python
results = lithos_search(query="how to run async tasks in python", mode="semantic")
# or use the new default hybrid mode:
results = lithos_search(query="how to run async tasks in python")
# results["results"][0]["score"]  ← new key
```

### Fixing `lithos_delete` calls

**Before:**

```python
lithos_delete(id="uuid-123")  # agent was optional
```

**After:**

```python
lithos_delete(id="uuid-123", agent="my-agent")  # agent now required
```

### Fixing coordination error handling

**Before:**

```python
result = lithos_task_claim(task_id="...", aspect="...", agent="...")
if result.get("success") == False:  # old pattern
    print("Claim failed")
```

**After:**

```python
result = lithos_task_claim(task_id="...", aspect="...", agent="...")
if result.get("status") == "error":  # new pattern
    print(f"Claim failed: {result['code']}")
```
