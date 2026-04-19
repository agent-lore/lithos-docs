# lithos_cache_lookup

**Added in v0.1.3**

Check for fresh cached knowledge before doing expensive research. Returns a full cache hit, a stale reference (update instead of duplicate), or a clean miss.

!!! tip "Always check the cache first"
    Call `lithos_cache_lookup` before any external research. If `hit` is `true`, use the cached document. If `stale_exists` is `true`, update the stale document with `lithos_write(id=stale_id, ...)` instead of creating a duplicate.

<div class="tool-sig">lithos_cache_lookup(query, [source_url], [max_age_hours], [min_confidence], [limit], [tags])</div>

## Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `query` | string | ✅ | What you are about to research |
| `source_url` | string | — | Canonical URL for exact dedup-aware lookup. When provided, a fast exact match is tried first before falling back to semantic search. Default: `null`. |
| `max_age_hours` | float | — | Reject documents older than N hours (based on `updated_at`). Must be positive. Default: `null` (no age limit). |
| `min_confidence` | float | — | Skip candidates whose `metadata.confidence` is strictly below this value. Range: 0.0–1.0. Default: `0.5`. |
| `limit` | int | — | Maximum candidate documents to evaluate during semantic fallback. Must be ≥ 1. Default: `3`. |
| `tags` | string[] | — | Restrict to documents with all of these tags (AND semantics). Default: `null`. |

## Returns

### Cache hit

```json
{
  "hit": true,
  "document": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "title": "GitHub API rate limits",
    "content": "5000 requests/hour for authenticated requests...",
    "confidence": 0.95,
    "updated_at": "2026-04-01T12:00:00Z",
    "expires_at": "2026-04-02T12:00:00Z",
    "tags": ["github", "api", "rate-limits"],
    "source_url": "https://docs.github.com/en/rest/overview/rate-limits-for-the-rest-api"
  },
  "stale_exists": false,
  "stale_id": null
}
```

### Cache miss (clean)

```json
{
  "hit": false,
  "document": null,
  "stale_exists": false,
  "stale_id": null
}
```

### Cache miss (stale exists)

```json
{
  "hit": false,
  "document": null,
  "stale_exists": true,
  "stale_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

When `stale_exists` is `true`, refresh the knowledge with `lithos_write(id=stale_id, ...)` rather than creating a new document.

## Lookup Strategy

`lithos_cache_lookup` uses a two-path strategy:

1. **Fast path (source_url)** — if `source_url` is provided, an exact URL lookup is performed first. If the URL matches a document and all other filters pass, that document is used as the sole candidate.
2. **Semantic fallback** — if no exact URL match, semantic search retrieves up to `limit` candidate documents ranked by embedding similarity.

Candidates are then filtered by `min_confidence`, explicit expiry (`expires_at`), and `max_age_hours`. The passing document with the highest confidence is returned as the hit.

## Examples

```python
# Basic: check before researching
cache = lithos_cache_lookup(query="GitHub API rate limits")
if cache["hit"]:
    print(cache["document"]["content"])
else:
    # ... do research, then write
    lithos_write(title="...", content="...", agent="my-agent")
```

```python
# URL-dedup: exact lookup by source URL
cache = lithos_cache_lookup(
    query="GitHub API rate limits",
    source_url="https://docs.github.com/en/rest/overview/rate-limits-for-the-rest-api"
)
```

```python
# With freshness window: only accept docs updated in the last week
cache = lithos_cache_lookup(
    query="OpenAI pricing",
    max_age_hours=168,
    tags=["pricing", "openai"]
)
if not cache["hit"]:
    if cache["stale_exists"]:
        # Update the stale doc rather than creating a duplicate
        lithos_write(
            id=cache["stale_id"],
            title="OpenAI API pricing",
            content="...",
            agent="my-agent"
        )
    else:
        lithos_write(title="OpenAI API pricing", content="...", agent="my-agent")
```

## Error Envelope

| Code | Condition |
|------|-----------|
| `invalid_input` | `max_age_hours` ≤ 0, `limit` < 1, or `min_confidence` out of 0–1 range |
| `search_backend_error` | Semantic search backend unavailable during fallback |
