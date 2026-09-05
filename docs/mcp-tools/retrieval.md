# Retrieval Tools (LCMA)

Three tools expose Lithos's cognitive-memory layer: `lithos_retrieve` (scout-based retrieval with audit receipts), `lithos_cache_lookup` (freshness-aware cache check), and `lithos_node_stats` (per-note memory state).

These tools are additive to `lithos_search`/`lithos_read` — they do not replace them. All of them require LCMA to be enabled (`lcma.enabled`, on by default); `lithos_retrieve` returns `{status: "error", code: "lcma_disabled"}` otherwise.

## `lithos_retrieve`

Cognitive retrieval: runs seven scouts in parallel, merges and reranks candidates, and writes an audit receipt. Returns `lithos_search`-compatible results plus LCMA-only metadata.

```python
lithos_retrieve(query: str, limit: int = 10,
                namespace_filter: list[str] | None = None,
                agent_id: str | None = None, task_id: str | None = None,
                surface_conflicts: bool = False,
                max_context_nodes: int | None = None,
                tags: list[str] | None = None, path_prefix: str | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `query` | string | Free-text query |
| `limit` | int | Max results (default 10) |
| `namespace_filter` | string[] | Restrict candidates to these LCMA namespaces |
| `agent_id` | string | Caller agent ID; used for `agent_private` access-scope gating |
| `task_id` | string | Enables `scout_task_context`, `task`-scope gating, and working-memory upserts. A unique ≥6-char prefix of an existing task resolves; other values are used as free-form correlation keys. |
| `surface_conflicts` | bool | Recorded in the receipt (contradiction surfacing activates in a later MVP) |
| `max_context_nodes` | int | Phase B seed size (default: `limit`) |
| `tags` | string[] | Global tag filter applied to every scout |
| `path_prefix` | string | Global path-prefix filter applied to every scout |

**Returns:**

```json
{
  "results": [
    {
      "id": "…", "title": "…", "snippet": "…", "score": 0.42,
      "path": "shared/note.md", "source_url": "", "updated_at": "…",
      "is_stale": false, "derived_from_ids": [],
      "reasons": ["lexical match score 0.91"],
      "scouts": ["scout_lexical"],
      "salience": 0.42,
      "usage_score": 0.18
    }
  ],
  "temperature": 0.5,
  "terrace_reached": 1,
  "receipt_id": "rcpt_<short-uuid>",
  "degraded": false,
  "failed_scouts": []
}
```

- The first nine per-result keys mirror the `lithos_search` shape, so clients that read only those fields work unchanged.
- `reasons` / `scouts` / `salience` / `usage_score` are LCMA-only additive fields: `salience` is the stored learned utility, `usage_score` the live non-decaying popularity signal (retrieval frequency + recency); both feed reranking.
- `degraded` / `failed_scouts` are **always present**: `failed_scouts` lists any scouts whose backend raised (one bad backend degrades rather than kills the retrieve); `degraded` is `true` when non-empty. This lets a caller distinguish partial results from a genuinely empty corpus.

**Receipts:** every call writes a receipt row (`receipt_id`) recording the query, scouts fired, candidates considered, and final nodes. Pass the `receipt_id` back to [`lithos_task_complete`](tasks.md#lithos_task_complete) with `cited_nodes`/`misleading_nodes` to close the reinforcement loop — retrieval learns which notes actually helped.

**Working memory:** when `task_id` is set, each result is upserted into working memory keyed on `(task_id, node_id)`, tracking activation counts across the task.

---

## `lithos_cache_lookup`

Check the knowledge base for a fresh cached answer before performing expensive research.

```python
lithos_cache_lookup(query: str, source_url: str | None = None,
                    max_age_hours: float | None = None,
                    min_confidence: float = 0.5, limit: int = 3,
                    tags: list[str] | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `query` | string | Natural-language query for semantic matching |
| `source_url` | string | Exact URL to check first (fast path) |
| `max_age_hours` | float | Reject documents older than N hours (by `updated_at`) |
| `min_confidence` | float | Minimum confidence score (default 0.5) |
| `limit` | int | Max candidates to evaluate (default 3) |
| `tags` | string[] | Filter by tags |

**Returns (hit):**

```json
{
  "hit": true,
  "document": {"id": "…", "title": "…", "content": "…", "source_url": "…",
               "confidence": 0.9, "updated_at": "…", "expires_at": "…", "tags": ["…"]},
  "stale_exists": false,
  "stale_id": null
}
```

**Returns (miss):** `{"hit": false, "document": null, "stale_exists": <bool>, "stale_id": <id|null>}` — when every candidate failed only on staleness, `stale_id` names the stale document so you can refresh it instead of writing a new one.

**Errors:** `{status: "error", code: "invalid_input" | "search_backend_error", message}`.

**Evaluation pipeline:** exact `source_url` lookup first (fast path) → semantic fallback → per-candidate checks in order: confidence → staleness (`expires_at`) → `max_age_hours`. First passing candidate is the hit.

---

## `lithos_node_stats`

Inspect a single note's cognitive-memory state — salience, retrieval counts, and reinforcement penalties — without querying SQLite directly. Useful to understand why retrieval is (or isn't) surfacing a document.

```python
lithos_node_stats(node_id: str)
```

**Returns:**

```json
{
  "node_id": "…",
  "salience": 0.5,
  "retrieval_count": 12,
  "cited_count": 3,
  "last_retrieved_at": "…",
  "last_used_at": "…",
  "ignored_count": 0,
  "misleading_count": 0,
  "decay_rate": 0.005,
  "spaced_rep_strength": 1.0,
  "last_decay_applied_at": "…"
}
```

Counts and timestamps default to `0` / `null` until the node accrues retrieval activity. Salience decays toward a configurable floor (`lcma.salience_floor`, default 0.3) when unused, and is reinforced when tasks cite the node.

Unknown `node_id` → `{status: "error", code: "doc_not_found", message}`.
