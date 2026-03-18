# lithos_search

Search the knowledge base using full-text, semantic, or hybrid (default) mode.

<div class="tool-sig">lithos_search(query, [mode], [limit], [tags], [author], [path_prefix])</div>

---

## Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `query` | string | ✅ | Search query |
| `mode` | string | — | `"hybrid"` (default), `"fulltext"`, or `"semantic"` |
| `limit` | int | — | Max results (default: `10`, max: `50`) |
| `tags` | string[] | — | Filter results to documents with **all** of these tags |
| `author` | string | — | Filter results to documents by this author |
| `path_prefix` | string | — | Filter results to documents under this path prefix |

---

## Returns

```json
{
  "results": [
    {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "title": "Python asyncio.gather patterns",
      "snippet": "Use asyncio.gather() to run coroutines concurrently. Results are returned in input order...",
      "score": 0.94,
      "path": "python-asyncio-gather-patterns.md",
      "source_url": null,
      "updated_at": "2026-03-18T14:30:00Z",
      "is_stale": false,
      "derived_from_ids": []
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `score` | Relevance score (higher = more relevant). Scale depends on mode. |
| `snippet` | For `fulltext`: terms in context. For `semantic`/`hybrid`: best-matching chunk content. |
| `is_stale` | `true` if `expires_at` has passed. The item still exists and is returned, but may be outdated. |

### Error

```json
{
  "status": "error",
  "code": "invalid_mode",
  "message": "Unknown search mode 'fuzzzy'. Valid modes: hybrid, fulltext, semantic"
}
```

---

## Search Modes

### `hybrid` (default) — Use this for most queries

Merges full-text BM25 and semantic cosine similarity using **Reciprocal Rank Fusion (RRF)**. Gets the precision of keyword search plus the recall of semantic search.

```python
results = lithos_search(
    query="asyncio concurrent patterns",
    mode="hybrid"   # default — same as omitting mode
)
```

### `fulltext` — For exact terms, code, errors

Uses Tantivy's Lucene-compatible query syntax. Best for:
- Exact function or method names (`asyncio.gather`)
- Error messages (`RuntimeError: This event loop is already running`)
- Code snippets
- Known document titles

```python
results = lithos_search(
    query="asyncio.gather return_exceptions",
    mode="fulltext"
)

# Tantivy query syntax — boolean operators, phrases, field search
results = lithos_search(
    query='title:"asyncio patterns" AND tags:python',
    mode="fulltext"
)
```

### `semantic` — For natural language questions

Uses ChromaDB cosine similarity over document chunks. Best for:
- Natural language questions
- Conceptual queries
- Finding related knowledge when you don't know the exact terms

```python
results = lithos_search(
    query="how do I run several tasks at the same time in Python without blocking",
    mode="semantic"
)
```

---

## Examples

### Basic hybrid search

```python
results = lithos_search(query="rate limiting exponential backoff")
for r in results["results"]:
    print(f"{r['score']:.2f}  {r['title']}")
    print(f"  {r['snippet'][:120]}...")
```

### Filter by tags

```python
# Find all antipatterns tagged with 'python'
results = lithos_search(
    query="common mistakes",
    tags=["python", "antipattern"]
)
```

### Filter by path prefix

```python
# Search only within the procedures subdirectory
results = lithos_search(
    query="onboarding steps",
    path_prefix="procedures/"
)
```

### Check staleness

```python
results = lithos_search(query="github api rate limits")
for r in results["results"]:
    if r["is_stale"]:
        print(f"⚠️  '{r['title']}' is stale — consider refreshing")
    else:
        print(f"✅  '{r['title']}' — updated {r['updated_at']}")
```

### Use in a research-cache pattern

```python
# Before doing web research, check what Lithos already knows
results = lithos_search(
    query=research_topic,
    mode="hybrid",
    limit=3
)

if results["results"] and results["results"][0]["score"] > 0.8:
    # High-confidence hit — read the full document
    doc = lithos_read(id=results["results"][0]["id"], max_length=2000)
    return doc["content"]
else:
    # Low confidence or no results — go do the research
    ...
```

---

## Notes

- **Hybrid mode** is the default and recommended mode for most queries. It handles both keyword and conceptual queries well.
- **Semantic search** operates on 500-character chunks internally, then deduplicates to document level before returning results. The `snippet` field shows the best-matching chunk.
- Tags filtering is **AND** — specifying `tags=["python", "asyncio"]` returns only documents tagged with *both*.
- `is_stale` is a soft signal. Stale documents are still returned and may still be correct — the `expires_at` was the author's estimate of freshness, not a hard deletion trigger.
