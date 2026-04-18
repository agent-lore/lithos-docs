# lithos_retrieve

**Added in v0.2.0** (LCMA MVP1)

Cognitive retrieval tool that runs a two-phase scout pipeline, merges and normalises results, applies Terrace 1 reranking (weighted scores, note-type priors, salience, MMR diversity), and writes an audit receipt on every call.

Prefer `lithos_retrieve` over `lithos_search` when you need explainability, multi-signal recall, or LCMA context — it tells you *why* each result was returned and which scouts found it.

---

## Signature

<div class="tool-sig">lithos_retrieve(query, [limit], [namespace_filter], [agent_id], [task_id], [surface_conflicts], [max_context_nodes], [tags], [path_prefix])</div>

## Parameters

| Name | Type | Required | Default | Description |
|------|------|:--------:|---------|-------------|
| `query` | string | ✅ | — | Natural-language retrieval query |
| `limit` | int | — | `10` | Maximum results to return |
| `namespace_filter` | string[] | — | `null` | Restrict results to documents in these namespaces (OR semantics) |
| `agent_id` | string | — | `null` | Caller identity for access-scope gating and audit trail |
| `task_id` | string | — | `null` | Active task ID — enables the `scout_task_context` scout and records results in working memory |
| `surface_conflicts` | bool | — | `false` | Reserved for MVP 2 — when `true`, the response envelope includes a `conflicts` list of contradiction edges |
| `max_context_nodes` | int | — | `limit` | Number of Phase A candidates to use as seeds for Phase B scouts (provenance, graph, coactivation) |
| `tags` | string[] | — | `null` | Filter to documents with **all** of these tags (AND semantics) |
| `path_prefix` | string | — | `null` | Filter by document path prefix |

!!! note "LCMA must be enabled"
    `lithos_retrieve` requires `lcma.enabled: true` in your config. If LCMA is disabled it returns `{"status": "error", "code": "lcma_disabled", ...}`.

---

## Returns

```json
{
  "results": [
    {
      "id": "doc-uuid",
      "title": "Rate limiting pattern for OpenAI API",
      "snippet": "Use exponential backoff with jitter. Base delay 1s…",
      "score": 0.94,
      "path": "rate-limiting-openai.md",
      "source_url": "https://example.com/article",
      "updated_at": "2026-04-01T12:00:00",
      "is_stale": false,
      "derived_from_ids": [],
      "reasons": ["lexical: exact query term match", "vector: high cosine similarity"],
      "scouts": ["scout_vector", "scout_lexical"],
      "salience": 0.87
    }
  ],
  "temperature": 0.5,
  "terrace_reached": 1,
  "receipt_id": "rcpt_2026..."
}
```

### Top-level envelope fields

| Field | Description |
|-------|-------------|
| `results` | Ranked list of matching documents (up to `limit`). |
| `temperature` | Pipeline temperature (MVP 1: always `lcma.temperature_default`, typically `0.5`). High temperature (≥ 0.5) indicates a cold-start graph — insufficient typed edges to compute coherence. Low temperature will indicate a well-connected graph in a future release. |
| `terrace_reached` | LCMA pipeline stage reached — `1` = Terrace 1 (fast rerank). |
| `receipt_id` | Audit receipt ID. Full pipeline trace written to `<data_dir>/.lithos/receipts/` in `stats.db`. |
| `conflicts` | *(Only present when `surface_conflicts=true`)* List of contradiction edges from the knowledge graph. Reserved for MVP 2. |

### Per-result fields

| Field | Description |
|-------|-------------|
| `id` | Document UUID. |
| `title` | Document title. |
| `snippet` | Short excerpt generated from document content matching the query. |
| `score` | Final reranked composite score (higher = better). |
| `path` | Relative path of the Markdown file within the data directory. |
| `source_url` | Original source URL, if set in frontmatter; empty string otherwise. |
| `updated_at` | ISO 8601 timestamp of last update; empty string if unset. |
| `is_stale` | `true` if the document is past its `expires_at` freshness deadline. |
| `derived_from_ids` | List of document IDs this document was derived from (provenance chain). |
| `reasons` | Human-readable explanations of why this document scored highly (from each contributing scout). |
| `scouts` | Names of the scouts that retrieved this document. |
| `salience` | Stored salience value from retrieval history (0–1). High = frequently retrieved. |

---

## Scout Pipeline

`lithos_retrieve` runs a two-phase scout pipeline:

### Phase A — Parallel scouts

All five (or six) Phase A scouts fire concurrently via `asyncio.gather`:

| Scout | Description |
|-------|-------------|
| `scout_vector` | ChromaDB cosine similarity search against the semantic index |
| `scout_lexical` | Tantivy BM25 full-text search |
| `scout_exact_alias` | Graph-based exact alias and title lookup |
| `scout_tags_recency` | Tag-weighted recency scoring — surfaces recently-updated documents whose tags match the query context |
| `scout_freshness` | Freshness boost for documents with time-sensitive keywords in the query |
| `scout_task_context` | Documents associated with the active task *(only fires when `task_id` is provided)* |

Phase A results are merged and normalised into a ranked pool. The top `max_context_nodes` documents become **seeds** for Phase B.

### Phase B — Sequential scouts (seeded from Phase A)

Phase B scouts run sequentially, seeded from the top Phase A candidates:

| Scout | Description |
|-------|-------------|
| `scout_provenance` | Documents in the provenance chain of the Phase A seeds (derived-from relationships) |
| `scout_graph` | Neighbours via typed LCMA edges (`edges.db`) and wiki-link graph traversal |
| `scout_coactivation` | Documents frequently retrieved alongside the seeds in past sessions |
| `scout_source_url` | Documents sharing a source URL with Phase A seeds (URL-cluster expansion) |

A scout appears in the receipt as "fired" if it ran without error — even if it returned zero candidates.

### Merge, Rerank, and Diversity

All Phase A and Phase B candidates are merged with `merge_and_normalize` into a unified pool. Terrace 1 reranking applies a weighted combination of:

- **Scout weights** — configurable per-scout contribution via `lcma.rerank_weights`
- **Note-type priors** — document type bias (e.g., `reference` notes weighted differently than `observation`)
- **Salience** — historical retrieval frequency from `stats.db`

After reranking, a greedy **MMR (Maximal Marginal Relevance)** pass over the top 30 candidates promotes diversity by penalising near-duplicates (Jaccard similarity on title tokens, λ=0.7).

---

## Audit Receipts

Every `lithos_retrieve` call writes a receipt row to `stats.db` under `<data_dir>/.lithos/`. The receipt captures: query, limit, namespace filter, scouts fired, candidates considered, final nodes with reasons, temperature, and terrace reached. Receipts are written even when the call errors.

---

## Working Memory

When `task_id` is provided, each result document is upserted into working memory (`stats_store.upsert_working_memory`), linking the document to the active task for use by subsequent `scout_task_context` calls.

---

## Example

```python
# Basic retrieval
results = lithos_retrieve(query="exponential backoff rate limiting")
for r in results["results"]:
    print(f"[{r['score']:.2f}] {r['title']}")
    print(f"  Scouts: {', '.join(r['scouts'])}")
    print(f"  Why: {r['reasons'][0]}")

# Task-context retrieval (activates scout_task_context + working memory)
results = lithos_retrieve(
    query="async queue implementation",
    task_id="task-abc123",
    tags=["python", "patterns"],
    agent_id="my-agent"
)

# Namespace-scoped retrieval
results = lithos_retrieve(
    query="deployment patterns",
    namespace_filter=["production-runbooks", "ops"]
)

# Widen provenance seeding beyond the default limit
results = lithos_retrieve(
    query="rate limiting",
    limit=5,
    max_context_nodes=20  # seed Phase B from top 20 Phase A candidates
)
```

---

## lithos_retrieve vs lithos_search

| | `lithos_retrieve` | `lithos_search` |
|---|---|---|
| **When to use** | Multi-signal recall, explainability, LCMA context | Simple keyword, semantic, or hybrid lookup |
| **Scout model** | 10 scouts in two phases + rerank + MMR | Single mode (fulltext / semantic / hybrid / graph) |
| **Returns** | Score + reasons + scouts + salience + provenance | Score + snippet |
| **Audit trail** | ✅ Receipt on every call | ❌ |
| **Task context** | ✅ via `task_id` | ❌ |
| **Speed** | Slightly slower (fan-out + rerank) | Faster |
| **LCMA required** | ✅ (`lcma.enabled: true`) | ❌ |

Use `lithos_retrieve` as the default retrieval tool in LCMA-aware agent pipelines. Use `lithos_search` for simple, fast lookups where explainability and multi-signal recall are not required.
