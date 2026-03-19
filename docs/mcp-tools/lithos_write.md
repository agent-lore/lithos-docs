# lithos_write

Create or update a knowledge item in the Lithos knowledge base.

<div class="tool-sig">lithos_write(title, content, agent, [tags], [confidence], [path], [id], [source_task], [source_url], [derived_from_ids], [ttl_hours], [expires_at], [expected_version])</div>

---

## Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `title` | string | ✅ | Title of the knowledge item |
| `content` | string | ✅ | Markdown content (without YAML frontmatter) |
| `agent` | string | ✅ | Your agent identifier |
| `tags` | string[] | — | List of tags for filtering and discovery |
| `confidence` | float | — | Confidence score 0–1 (default: `1.0`) |
| `path` | string | — | Subdirectory path (e.g., `"procedures"`, `"research/python"`) |
| `id` | string | — | UUID of existing document to **update**; omit to **create** |
| `source_task` | string | — | Task ID or provenance note (stored as `source` in frontmatter) |
| `source_url` | string | — | Canonical URL provenance. Normalised before storage; used for deduplication. Pass `""` on update to clear. |
| `derived_from_ids` | string[] | — | UUIDs of source documents this item was derived from |
| `ttl_hours` | float | — | Relative freshness window; converted to `expires_at` |
| `expires_at` | string | — | Absolute ISO 8601 freshness deadline (e.g., `"2026-04-01T00:00:00Z"`) |
| `expected_version` | int | — | Optimistic-lock guard for updates. If provided and the current version doesn't match, returns `version_conflict`. |

---

## Returns

### Created

```json
{
  "status": "created",
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "path": "python-asyncio-gather-patterns.md",
  "version": 1,
  "warnings": []
}
```

### Updated

```json
{
  "status": "updated",
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "path": "python-asyncio-gather-patterns.md",
  "version": 2,
  "warnings": []
}
```

### Duplicate (same `source_url` already exists)

```json
{
  "status": "duplicate",
  "duplicate_of": {
    "id": "existing-uuid",
    "title": "Existing note title",
    "source_url": "https://example.com/article"
  },
  "message": "A document with this source_url already exists",
  "warnings": []
}
```

### Error

```json
{
  "status": "error",
  "code": "version_conflict",
  "message": "Expected version 3 but current version is 4",
  "current_version": 4,
  "warnings": []
}
```

| Error code | When |
|-----------|------|
| `invalid_input` | Bad argument values |
| `content_too_large` | Content exceeds size limit |
| `slug_collision` | A different document has the same title slug |
| `version_conflict` | `expected_version` mismatch on update |

---

## Examples

### Create a new knowledge item

```python
result = lithos_write(
    title="Python asyncio.gather patterns",
    content="""
Use `asyncio.gather()` to run coroutines concurrently.
Results are returned in input order regardless of completion order.

## Basic usage

```python
results = await asyncio.gather(fetch(url1), fetch(url2))
```

## Error handling

Use `return_exceptions=True` to prevent one failure from cancelling others.
""",
    tags=["python", "asyncio", "patterns"],
    confidence=0.95,
    agent="research-agent"
)
```

### Update an existing item

```python
# First, read to get the current version
doc = lithos_read(id="f47ac10b-...")
current_version = doc["metadata"]["version"]

# Update with version guard
lithos_write(
    id="f47ac10b-...",
    title="Python asyncio.gather patterns",
    content="Updated content...",
    expected_version=current_version,
    agent="research-agent"
)
```

### Write with provenance

```python
# After synthesising from multiple sources
lithos_write(
    title="Comprehensive async Python guide",
    content="...",
    derived_from_ids=[
        "uuid-of-asyncio-gather-note",
        "uuid-of-asyncio-run-note",
        "uuid-of-event-loop-note"
    ],
    tags=["python", "async", "synthesis"],
    confidence=0.85,
    agent="synthesis-agent"
)
```

### Write with freshness TTL

```python
# This note expires in 24 hours
lithos_write(
    title="Current GitHub API rate limits",
    content="5000 requests/hour for authenticated requests...",
    source_url="https://docs.github.com/en/rest/overview/rate-limits-for-the-rest-api",
    ttl_hours=24,
    tags=["github", "api", "rate-limits"],
    agent="research-agent"
)
```

### Write to a subdirectory

```python
lithos_write(
    title="Customer onboarding runbook",
    content="...",
    path="procedures/onboarding",
    tags=["runbook", "onboarding"],
    agent="ops-agent"
)
# Creates: knowledge/procedures/onboarding/customer-onboarding-runbook.md
```

---

## Update Semantics

- Omitted optional fields on update **preserve** their existing values.
- `source_url=""` (empty string) explicitly **clears** the source URL.
- `derived_from_ids=[]` (empty list) explicitly **clears** the lineage.
- Omitting `derived_from_ids` preserves the existing lineage.
- `author` is immutable — set once on creation, never changed by updates.
- `contributors` is append-only — the updating agent is added automatically if not already present.

---

## Notes

- The `agent` parameter is always required, even on updates. This is for audit-trail consistency.
- Slug collisions occur when two *different* documents would produce the same filename (e.g., `"Python Asyncio"` and `"python-asyncio"` both resolve to `python-asyncio.md`). Resolve by using a more specific title or specifying a `path`.
- `source_url` is normalised before storage (scheme lowercased, trailing slash removed, fragment stripped). The same URL with minor variations is treated as the same source.
