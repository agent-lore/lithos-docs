# lithos_retrieve

**Added in v0.2.0** (LCMA MVP1)

Cognitive retrieval tool that orchestrates multiple parallel scouts, merges and normalises their results, applies Terrace 1 reranking, and logs an audit receipt for every call. Prefer `lithos_retrieve` over `lithos_search` when you need explainability — it tells you *why* each result was returned.

---

## Signature

<div class="tool-sig">lithos_retrieve(query, [tags], [namespace], [limit], [task_id])</div>

## Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `query` | string | ✅ | Natural-language retrieval query |
| `tags` | string[] | — | Filter to documents with **all** of these tags (AND semantics) |
| `namespace` | string | — | Scope retrieval to a specific LCMA namespace |
| `limit` | int | — | Maximum results to return (default: `10`) |
| `task_id` | string | — | Active task ID — enables the task-context scout for better relevance to the current work |

---

## Returns

```json
{
  "results": [
    {
      "id": "doc-uuid",
      "title": "Rate limiting pattern for OpenAI API",
      "path": "rate-limiting-openai.md",
      "score": 0.94,
      "salience": 0.87,
      "temperature": 0.12,
      "terrace_reached": 1,
      "receipt_id": "rcpt_2026...",
      "reasons": ["lexical: exact query term match", "vector: high cosine similarity"],
      "scouts": {
        "scout_vector": 0.91,
        "scout_lexical": 0.97,
        "scout_provenance": 0.0,
        "scout_task_context": 0.0
      }
    }
  ],
  "receipt_id": "rcpt_2026...",
  "query": "openai rate limit backoff"
}
```

### Result fields

| Field | Description |
|-------|-------------|
| `score` | Final reranked score (0–1). Use this for display/ranking. |
| `salience` | Stored salience from prior retrieval history (0–1). High salience = frequently retrieved. |
| `temperature` | Recency signal — lower means accessed more recently. |
| `terrace_reached` | LCMA pipeline stage that produced this result (1 = fast rerank). |
| `receipt_id` | Audit receipt ID. Cross-reference with `<data_dir>/.lithos/receipts/` for full pipeline trace. |
| `reasons` | Human-readable explanation of why this document scored highly. |
| `scouts` | Per-scout scores before merge-and-normalise. |

---

## Scouts

`lithos_retrieve` fans out to four parallel scouts:

| Scout | Description |
|-------|-------------|
| `scout_vector` | ChromaDB cosine similarity search |
| `scout_lexical` | Tantivy BM25 full-text search |
| `scout_provenance` | Graph traversal from known related documents |
| `scout_task_context` | Documents associated with the active task (requires `task_id`) |

Results from all scouts are merged, normalised, and passed through the Terrace 1 reranker which applies configurable per-scout weights. As of v0.2.1 the default weights are `vector=0.21, lexical=0.22` (lexical now has a slight edge to prevent exact-term matches being dominated by vector candidates).

---

## Audit Receipts

Every `lithos_retrieve` call writes an audit receipt file to `<data_dir>/.lithos/receipts/rcpt_<timestamp>.json`. The receipt contains the full pipeline trace: query, all scout raw results, merged scores, rerank weights applied, and final ordering. Use receipts to debug unexpected retrieval behaviour.

---

## Example

```python
# Basic retrieval
results = lithos_retrieve(query="exponential backoff rate limiting")
for r in results["results"]:
    print(f"[{r['score']:.2f}] {r['title']} — {r['reasons'][0]}")

# Task-context retrieval (scouts include task-related documents)
results = lithos_retrieve(
    query="async queue implementation",
    task_id="task-abc123",
    tags=["python", "patterns"]
)

# Scoped to a namespace
results = lithos_retrieve(
    query="deployment patterns",
    namespace="production-runbooks"
)
```

---

## lithos_retrieve vs lithos_search

| | `lithos_retrieve` | `lithos_search` |
|---|---|---|
| **When to use** | Explainability matters; LCMA context active | Simple keyword/semantic/hybrid lookup |
| **Scout model** | 4 parallel scouts + rerank | Single mode (fulltext/semantic/hybrid) |
| **Returns** | Scores + reasons + receipt | Scores + snippets |
| **Audit trail** | ✅ Receipt on every call | ❌ |
| **Task context** | ✅ via `task_id` | ❌ |
| **Speed** | Slightly slower (fan-out + rerank) | Faster |

Use `lithos_retrieve` as the default retrieval tool in LCMA-aware agent pipelines. Use `lithos_search` for simple, fast lookups or when you don't need explainability.
