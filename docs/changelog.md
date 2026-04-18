# Changelog

All notable changes to Lithos are documented here. The full changelog is maintained in the [main repository](https://github.com/agent-lore/lithos/blob/main/CHANGELOG.md).

---

## v0.2.1

**Released:** 2026-04-18 · [GitHub Release](https://github.com/agent-lore/lithos/releases/tag/v0.2.1) · [PyPI](https://pypi.org/project/lithos-mcp/0.2.1/) · [Docker Hub](https://hub.docker.com/r/davesnowdon/lithos/tags)

Install:
```bash
pip install lithos-mcp==0.2.1
# or
docker pull davesnowdon/lithos:0.2.1
```

### Added

- **`lithos_related` — composite graph tool (PR #188):** New MCP tool that merges wiki-links, provenance chains, and LCMA typed edges into a single response. Eliminates the need to fan out across multiple tools and manually join results.

    ```python
    lithos_related(id="doc-uuid", include=["links", "provenance", "edges"])
    ```

    Response shape:
    ```json
    {
      "id": "<doc>",
      "included": ["links", "provenance", "edges"],
      "links":      { "outgoing": [...], "incoming": [...] },
      "provenance": { "sources": [...], "derived": [...], "unresolved_sources": [...] },
      "edges":      { "outgoing": [...], "incoming": [...] },
      "related_ids": ["<uuid>", ...]
    }
    ```

    - `include` controls which backends are queried — omit a key and it's excluded from the response entirely.
    - `related_ids` is the deduplicated union of all referenced document IDs (excluding the queried doc itself).
    - `depth` is supported (1–3) for the links and provenance sections.
    - `namespace` scopes the `edges` section only.

    → See [Graph Tools Reference](mcp-tools/graph-tools.md)

- **`--telemetry-console` flag on `lithos serve` (PR #187):** DX shortcut that enables in-process OTEL console exporters without a collector. Metrics and spans go to stdout — useful for local debugging.

    ```bash
    lithos serve --telemetry-console
    ```

- **LCMA MVP2 (PR #170, #177, #176):** Second phase of the Layered Cognitive Memory Architecture. Adds OTEL metrics coverage across the full LCMA pipeline and comprehensive structured logging throughout the LCMA codebase.

- **Multiple environment support (PR #180):** Lithos now supports separate named environments (e.g. `prod`, `staging`) with independent OTEL tracking. Useful for running multiple Lithos instances on the same host.

- **`outcome` parameter on `lithos_task_complete` (fix for PR #182):** Tasks can now record a completion outcome string. The value is persisted on the task row and included in the `task.completed` event payload for LCMA consolidation.

    → See [Coordination Tools Reference](mcp-tools/coordination-tools.md)

### Removed

- **`lithos_links` and `lithos_provenance` MCP tools (PR #190):** Both tools are fully superseded by `lithos_related`. Their behaviour is available via:
    - `lithos_related(id=..., include=["links"])` — replaces `lithos_links`
    - `lithos_related(id=..., include=["provenance"])` — replaces `lithos_provenance`

    `lithos_edge_list` is **retained** as it supports global edge queries that don't require a single document centre.

    !!! warning "Breaking change"
        Remove any calls to `lithos_links` or `lithos_provenance` and replace with `lithos_related`. The `include_unresolved` parameter from `lithos_provenance` is dropped — unresolved sources always surface on the composite path.

### Fixed

- **`lithos_task_complete` accepts `outcome` param (PR #182):** Fixes `Unexpected keyword argument` errors when callers passed `outcome=` to `lithos_task_complete`.
- **Rerank weights rebalanced (PR #183):** `vector=0.21, lexical=0.22` (was `0.25`/`0.18`). Exact-term lexical hits can no longer be structurally dominated by vector-only candidates at equal normalised score.
- **OTEL gauge caches primed at startup (PR #184):** Eliminates stale/missing gauge readings at server start.
- **`setup_logging` hardened + handler eviction between tests (PR #185):** Prevents log handler accumulation and test-isolation issues.
- **`lithos_search` tags filter with colons (PR #192):** Tags containing colons (e.g. `type:pattern`) were silently dropped by the FTS filter. Fixed.
- **`lithos_list` content_query pushes tags/author/path_prefix into FTS (PR #211):** Filter fields were not being applied when `content_query` was used.
- **LCMA: snippet against `full_content` (PR #210):** Snippet generation now runs against the full document content, so title-matching passages surface correctly.
- **LCMA: stored salience emitted in `lithos_retrieve` results (PR #209):** Previously salience was not forwarded in result payloads.
- **LCMA: tag filter uses AND semantics across scouts (PR #208):** Tags filter is now applied consistently with AND semantics across all LCMA scouts.
- **Server: search mutations wrapped in `asyncio.to_thread` (PR #213):** Prevents blocking the event loop during write-side search operations.
- **uv commands corrected in README (PR #212):** Dev setup commands updated.

### Refactored

- **`KnowledgeManager.get_cached_meta` public accessor (PR #186):** Exposes the metadata cache via a clean public API for callers that embed lithos as a library.
- **Build: project now uses `uv` exclusively, with Makefile (PR #165):** `uv sync --extra dev` for dev installs; `make check`, `make test`, etc. for common actions.

---

## v0.2.0

**Released:** 2026-04-12 · [GitHub Release](https://github.com/agent-lore/lithos/releases/tag/v0.2.0)

### Added — LCMA MVP1 (Layered Cognitive Memory Architecture)

- **`lithos_retrieve`** — cognitive retrieval tool that orchestrates parallel scouts (vector, lexical, provenance, task-context) with merge-and-normalize, Terrace 1 reranking, and audit receipt logging. Returns `reasons`, `scouts`, `salience`, `temperature`, `terrace_reached`, and `receipt_id` per result. See [lithos_retrieve](mcp-tools/lithos_search.md).
- **`lithos_edge_upsert`** — create or update typed edges in `edges.db`. Upsert key is `(from_id, to_id, type, namespace)`.
- **`lithos_edge_list`** — query edges from `edges.db` by optional filters (`from_id`, `to_id`, `type`, `namespace`).
- **`lithos_write` LCMA fields:** `note_type`, `namespace`, `access_scope`, `summaries`, `schema_version` — all optional and additive; existing documents are unaffected.
- **Receipts logging:** every `lithos_retrieve` call writes an audit receipt (`rcpt_*`) for full observability.

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
