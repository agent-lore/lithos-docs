# Changelog

All notable changes to Lithos are documented here. The full changelog is maintained in the [main repository](https://github.com/agent-lore/lithos/blob/main/CHANGELOG.md).

---

## v0.1.8

!!! note "v0.1.7 skipped"
    v0.1.7 was skipped due to a tag issue. This release covers all changes between v0.1.6 and v0.1.8.

### Added

- **`lithos_search` now supports `mode="graph"` (PR #146):** Traverse the knowledge graph from a starting document and return linked results. Returns documents reachable by wiki-link relationships rather than text/vector similarity. See [`lithos_search`](mcp-tools/lithos_search.md) for details.

- **`lithos_stats` extended with health indicators (PR #159):** The stats response now includes a `health` block with pass/warn/fail indicators for each subsystem (index, embedding, coordination). Surfaces the same signal as `GET /health` but in machine-readable per-subsystem form.

- **Observability — OTEL tracing (PRs #148, #151):** OpenTelemetry tracing added to all untraced code paths. An OTEL log bridge enables trace-log correlation — structured log entries now carry `trace_id` and `span_id` fields.

- **Observability — metrics (PRs #87, #89, #96, #97, #99, #101, #149, #150, #155, #156, #157):** Prometheus-compatible metrics exposed across the server:
    - `lithos.knowledge.write_duration_ms` histogram — write latency distribution
    - Resource gauge metrics (documents, chunks, agents, open tasks)
    - Startup duration and file watcher event counters
    - Event bus subscriber drop and buffer utilisation gauges
    - Per-tool call counters and per-tool error counters
    - SSE active clients gauge and events-delivered counter

- **Always-on structured JSON logging (PRs #140, #152, #153):** All log output is now structured JSON (when `LITHOS_LOG_LEVEL` is set to any level). DEBUG traces added for link resolution and slug computation. Coordination and knowledge modules emit structured events for observability pipelines (Loki, CloudWatch, etc.).

- **Read audit logging (PR #147):** `lithos_read` calls are now written to an audit log (append-only `read_audit.jsonl`). Each entry records `timestamp`, `document_id`, `agent`, and `path`. Useful for compliance and debugging access patterns.

### Fixed

- **Preserve incoming edges on document update (PR #139):** Previously, updating a document that other documents linked *to* would silently drop those incoming wiki-link edges from the graph. They are now preserved correctly.

- **Docker healthcheck uses HTTP `/health` (PR #143, closes #72, #77):** The default `docker-compose.yml` healthcheck now calls `GET /health` instead of using a TCP probe. This gives accurate health signals to Compose, Swarm, and Kubernetes.

- **Recover from corrupt ChromaDB stores (PR #160):** If the embedding store is detected as corrupt on startup, Lithos now logs a clear error and attempts an automatic rebuild rather than crashing. Contributed by @peterbrown05 (first contribution 🎉).

- **ChromaDB metadata types (PR #145, closes #42):** Fixed a type error where ChromaDB's `metadatas` list was incorrectly typed, causing failures on some document writes.

### Refactored

- **`KnowledgeManager` now requires explicit config (PR #158, closes #35):** `KnowledgeManager` no longer accepts implicit defaults. All callers must pass a `LithosConfig` instance. This only affects users embedding `lithos` as a Python library — the CLI and MCP server are unaffected.

- **`embed_async()` dead code removed (PR #144, closes #74):** The unused async embedding path was removed to simplify the codebase.

---

## v0.1.6

### Fixed

- **PyPI publish fix.** No functional changes. Re-publish to resolve a packaging issue with the v0.1.5 release.

---

## v0.1.5

### Breaking Changes

- **`lithos_health` MCP tool replaced by HTTP endpoint.** `GET /health` is now a plain HTTP endpoint (returns `200 OK` when healthy, `503` when degraded). It is no longer an MCP tool. Update any callers using `lithos_health()` to use `curl http://<host>:8765/health` or an HTTP client instead.

- **`lithos_semantic` MCP tool removed.** Use `lithos_search` with `mode="semantic"` for pure semantic search, or the new default `mode="hybrid"` for best results.

- **`lithos_search` now defaults to hybrid mode.** Existing callers that relied on `lithos_search` for full-text-only results will now receive hybrid (BM25 + semantic RRF) results. Pass `mode="fulltext"` explicitly to restore the previous behaviour.

- **`similarity` key renamed to `score` in search results.** Callers migrating from `lithos_semantic` that read `result["similarity"]` must update to `result["score"]`. All three modes (`hybrid`, `fulltext`, `semantic`) now use a unified `score` field.

- **`agent` is now required on `lithos_delete`.** Previously optional. Callers that omit it will receive a `TypeError` from the MCP layer.

- **`sort_by_confidence` removed from `lithos_cache_lookup`.** Results are now always sorted by confidence score. Remove the `sort_by_confidence` parameter from any calls that use it.

### Added

- **`lithos_task_list`** — list tasks with optional filters: `agent`, `status` (`"open"` | `"completed"` | `"cancelled"`), `tags` (AND), and `since` (ISO timestamp).

- **`lithos_task_cancel`** — cancel a task, releasing all active claims. Takes `task_id`, `agent`, and an optional `reason`.

- **`lithos_task_update`** — update mutable task metadata (`title`, `description`, `tags`) without closing the task. At least one field must be provided.

- `lithos_search` now accepts a `mode` parameter: `fulltext` | `semantic` | `hybrid` (default: `hybrid`).
- Hybrid search mode merges Tantivy (BM25) and ChromaDB (cosine similarity) results using Reciprocal Rank Fusion (RRF, k=60) for improved ranking quality.
- Unknown `mode` values now return a structured `{ "status": "error", "code": "invalid_mode", ... }` dict instead of raising a `ValueError`.
- `lithos_tags` accepts an optional `prefix` parameter to filter tags by prefix.
- `lithos_list` accepts two new optional filters: `title_contains` (substring match on title) and `content_query` (full-text search within results).

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
    | `lithos_task_cancel` (missing/closed) | `task_not_found` |
    | `lithos_task_update` (missing) | `task_not_found` |

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
