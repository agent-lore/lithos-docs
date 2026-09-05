# Changelog

All notable changes to Lithos are documented here. The full changelog is maintained in the [main repository](https://github.com/agent-lore/lithos/blob/main/CHANGELOG.md).

---

## Unreleased (on `main`)

Shipped on `main` after the v0.4.0 tag; running in source/`main`-built deployments today.

### Added

- **Short ID prefixes accepted everywhere (PR #412):** every task/note id parameter takes an unambiguous git-style prefix (≥ 6 chars). Ambiguity fails loudly with the new `ambiguous_id_prefix` code carrying up to 5 `{id, title}` candidates; mutating responses now echo the resolved full id + title. Behaviour tightened along the way: unknown 6–35-char task prefixes return `task_not_found` on *every* task tool (previously `claim_failed`/`claim_not_found`/silently empty), and `lithos_write` with an unknown `id` returns a `note_not_found` envelope instead of a protocol-level error. See [Envelopes, Errors & IDs](concepts/envelopes.md#short-id-prefixes).
- **`updated_at` on task records (PR #416):** last-modified stamp bumped by every task-row write (create/update/complete/cancel/reopen — claims never bump it), returned by all task-fetching tools, carried in row-mutating events, and echoed by mutating responses. Compare stamps for equality to detect concurrent edits. Existing databases are migrated in place.
- **`lithos_retrieve` degradation signal (PR #397):** responses always carry `degraded` and `failed_scouts`, so callers can distinguish partial results (a backend down) from an empty corpus. New alertable metric `lithos.lcma.scout.failures`.
- **Salience recalibration (PR #402):** decay now bottoms out at `lcma.salience_floor` (default 0.3) instead of zero; new non-decaying `usage_score` result field feeds reranking; new `lithos recalibrate-salience` CLI command backfills collapsed databases; decay/reinforcement constants became config fields.
- **Local/remote LLM synthesis (PRs #405, #406):** new `lcma.llm` config block (any OpenAI-compatible endpoint — Ollama, llama.cpp, vLLM, hosted). The background enrichment worker has the LLM adjudicate typed edges between semantically-close notes, written to `edges.db` as `provenance_type: "inferred"` with rationale and confidence as evidence. **Enabled only when `base_url` is set** — unset is a strict no-op. Token spend bounded by a daily budget.
- **SSE `resync` control event (PR #400):** `GET /events` now tells reconnecting clients when their `Last-Event-ID` fell off the replay ring buffer, instead of silently under-delivering. Consumers must handle `event: resync`.

### Fixed

- **Bare YAML dates in frontmatter broke indexing (PR #411):** an unquoted `created: 2026-07-30` could silently drop notes from search — and after an internal refactor, crash the startup rebuild. Both YAML ingestion points now normalize date objects; hand-edited frontmatter can no longer abort the startup scan.
- **Docker: `LITHOS_LCMA__LLM__*` env vars are now forwarded into the container (PRs #409, #410)**, and `llm.max_output_tokens` default raised 1024 → 4096 for reasoning models.

---

## v0.4.0

**Released:** 2026-07-06 · [GitHub Release](https://github.com/agent-lore/lithos/releases/tag/v0.4.0) · [PyPI](https://pypi.org/project/lithos-mcp/0.4.0/) · [Docker Hub](https://hub.docker.com/r/davesnowdon/lithos/tags)

Install:
```bash
pip install lithos-mcp==0.4.0
# or
docker pull davesnowdon/lithos:0.4.0
```

### Breaking — canonical error envelope (PRs #370, #371)

Every tool **failure** now returns exactly `{"status": "error", "code": "<stable_code>", "message": "..."}`:

- Validation failures use `code: "invalid_input"` — including paths that previously raised protocol-level errors (unparseable datetime filters on `lithos_list`, `lithos_agent_list`, `lithos_finding_list`).
- **Error envelopes no longer include a `warnings` key.**
- Deliberately unchanged: actionable write outcomes keep their own top-level `status` (`version_conflict` with `current_version`, `duplicate`, `slug_collision`, `path_collision`), all success shapes, and the `{"success": ...}` claim envelopes.
- **Migration:** replace `status == "invalid_input"` branches with `status == "error" and code == "invalid_input"` (except on `lithos_write`/`lithos_note_update`, where the code remains the status). This partially reverses 0.3.0's error-status promotion. Full guide: [Envelopes, Errors & IDs](concepts/envelopes.md#migrating-older-clients).

### Added — task graph (Phases 1–3)

Dependencies became first-class edges (`task_edges` table + `task_type` column), adding six tools — [`lithos_task_edge_upsert`](mcp-tools/task-graph.md#lithos_task_edge_upsert), [`lithos_task_edge_list`](mcp-tools/task-graph.md#lithos_task_edge_list), [`lithos_task_ready`](mcp-tools/task-graph.md#lithos_task_ready), [`lithos_task_blocked`](mcp-tools/task-graph.md#lithos_task_blocked), [`lithos_task_children`](mcp-tools/task-graph.md#lithos_task_children), [`lithos_task_spawn`](mcp-tools/task-graph.md#lithos_task_spawn) (PRs #342, #343, #356):

- Edge types `blocks`, `parent_child`, `discovered_from`, `waits_on_gate`; cycle-checked on write.
- `lithos_task_create` gains `task_type` (`task`/`epic`/`gate`), `depends_on`, `parent_task_id`; `lithos_task_complete` returns `unblocked`.
- **Gates** model external waits (`human`/`timer`/`ci`/`pr`/`external_task`) — Lithos never polls; timer gates auto-resolve at query time.
- A cancelled predecessor leaves dependents `blocker_unsatisfiable`, never spuriously ready.
- **Breaking:** `metadata.depends_on`/`blocked_on` are rejected with `invalid_metadata_key`; a one-time migration backfilled existing conventions into `blocks` edges.

### Added — lifecycle & notes

- **[`lithos_task_reopen`](mcp-tools/tasks.md#lithos_task_reopen)** (PR #357): terminal tasks return to `open`, with a `reblocked` list, a durable `[Reopened]` finding, and a `task.reopened` event. `lithos_task_update` now works on terminal tasks (#303).
- **[`lithos_note_update`](mcp-tools/knowledge-write.md#lithos_note_update)** (PR #363): patch a note's frontmatter (tags/metadata/title/status) without resending the body.

With these, the tool count reached **37**.

### Changed

- Python **3.12** is now required (PR #365).

---

## v0.3.3

**Released:** 2026-06-10 · [GitHub Release](https://github.com/agent-lore/lithos/releases/tag/v0.3.3)

Packaging fix (PR #338): the published wheel no longer carries the spaCy model as a direct-URL dependency (which broke `pip install lithos-mcp`). The `en_core_web_sm` model is downloaded on first use instead.

---

## v0.3.2

**Released:** 2026-06-09 · [GitHub Release](https://github.com/agent-lore/lithos/releases/tag/v0.3.2)

### Breaking

- **Transport `sse` renamed to `http` (PR #304)** — no back-compat alias. `lithos serve --transport http` now serves **both** `POST /mcp` (StreamableHTTP, stateless) and `GET /sse` (legacy) on one port; any compliant MCP client connects without a bridge. Update CLI invocations, systemd units, and compose overrides.

### Added

- **Entity extraction (PRs #313, #321, #329):** wiki-links + spaCy NER + corroborated heuristics populate an `entities` frontmatter list, with extractor provenance so agent-curated entities are never clobbered. New CLI command `lithos extract-entities`.
- **`entities` filter on `lithos_search` and `lithos_list` (PRs #316, #319):** exact-match AND filtering, inverted-index backed; entities also boost full-text ranking.

### Fixed

- `lithos_cache_lookup` no longer crashes when a candidate has `confidence: null`; confidence is healed on read and validated on write (PR #314).
- The Docker image bakes in the embedding model and loads it offline — no more HuggingFace rate-limit failures at container start.

---

## v0.3.1

**Released:** 2026-06-05 · [GitHub Release](https://github.com/agent-lore/lithos/releases/tag/v0.3.1) · [PyPI](https://pypi.org/project/lithos-mcp/0.3.1/)

First PyPI release: `pip install lithos-mcp`.

### Added

- **Free-form `metadata` on knowledge notes (PR #305):** arbitrary key/values persisted to frontmatter via `lithos_write(metadata=...)`, returned by `lithos_read`/`lithos_list`. Update semantics: omit preserves, `{}` clears, non-empty merges per key with `null` deleting a key.
- **`metadata_match` filter on `lithos_list` and `lithos_task_list` (PR #306):** AND across keys; matches scalar equality or list containment; index-backed on notes, SQL-pushed on tasks.

---

## v0.3.0

**Released:** 2026-05-27 · [GitHub Release](https://github.com/agent-lore/lithos/releases/tag/v0.3.0)

### Breaking

- **`tasks.completed_at` renamed to `resolved_at` (PR #288)** — now written on *both* terminal transitions (complete and cancel), with an in-place schema migration. `lithos_task_list` gains a `resolved_since` filter; the `task.completed` event field renamed to match.
- **`lithos_task_update(metadata=...)` became an additive per-key merge (PR #291):** `{"key": null}` deletes a key, unmentioned keys are preserved, `{}` is a no-op; there is no wholesale clear. Runs in a single transaction so concurrent writers on different keys can't clobber each other.
- **Write error codes promoted to top-level `status` (PR #217):** `lithos_write` failures became `status="slug_collision"` etc. *(Partially reversed for other tools by 0.4.0's canonical envelope — see above.)*

### Added

- **`lithos_task_get` (PR #294):** single-task fetch with the full record and an explicit `task_not_found` envelope; `lithos_task_status` widened to the same field set.
- **`lithos_task_list(with_claims=true)` (PR #221):** inline active claims per task in one batched query.
- **`metadata` on tasks (PR #216)** — arbitrary JSON at create time.

### Fixed

- `lithos_write(path="a/b.md")` treats a `.md`-terminated path as the complete filename instead of silently creating a directory named `b.md` (PR #301).
- File-watcher events carry the canonical `{id, title, path}` payload, so external Obsidian edits are no longer dropped by id-filtering consumers (PR #298); external renames preserve the document id.
- `task.updated` events are actually emitted (PR #284).

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

    → See [`lithos_related`](mcp-tools/knowledge-read.md#lithos_related)

- **`--telemetry-console` flag on `lithos serve` (PR #187):** DX shortcut that enables in-process OTEL console exporters without a collector. Metrics and spans go to stdout — useful for local debugging.

    ```bash
    lithos serve --telemetry-console
    ```

- **LCMA MVP2 (PR #170, #177, #176):** Second phase of the Layered Cognitive Memory Architecture. Adds OTEL metrics coverage across the full LCMA pipeline and comprehensive structured logging throughout the LCMA codebase.

- **Multiple environment support (PR #180):** Lithos now supports separate named environments (e.g. `prod`, `staging`) with independent OTEL tracking. Useful for running multiple Lithos instances on the same host.

- **`outcome` parameter on `lithos_task_complete` (fix for PR #182):** Tasks can now record a completion outcome string. The value is persisted on the task row and included in the `task.completed` event payload for LCMA consolidation.

    → See [Task Tools Reference](mcp-tools/tasks.md)

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

- **`lithos_retrieve`** — cognitive retrieval tool that orchestrates parallel scouts (vector, lexical, provenance, task-context) with merge-and-normalize, Terrace 1 reranking, and audit receipt logging. Returns `reasons`, `scouts`, `salience`, `temperature`, `terrace_reached`, and `receipt_id` per result. See [`lithos_retrieve`](mcp-tools/retrieval.md#lithos_retrieve).
- **`lithos_edge_upsert`** — create or update typed edges in `edges.db`. Upsert key is `(from_id, to_id, type, namespace)`.
- **`lithos_edge_list`** — query edges from `edges.db` by optional filters (`from_id`, `to_id`, `type`, `namespace`).
- **`lithos_write` LCMA fields:** `note_type`, `namespace`, `access_scope`, `summaries`, `schema_version` — all optional and additive; existing documents are unaffected.
- **Receipts logging:** every `lithos_retrieve` call writes an audit receipt (`rcpt_*`) for full observability.

---

## v0.1.8

!!! note "v0.1.7 skipped"
    v0.1.7 was skipped due to a tag issue. This release covers all changes between v0.1.6 and v0.1.8.

### Added

- **`lithos_search` now supports `mode="graph"` (PR #146):** Traverse the knowledge graph from a starting document and return linked results. Returns documents reachable by wiki-link relationships rather than text/vector similarity. See [`lithos_search`](mcp-tools/knowledge-read.md#lithos_search) for details.

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
