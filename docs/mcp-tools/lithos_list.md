# lithos_list

List knowledge items with optional filters. Useful for browsing, inventory, and sync operations.

<div class="tool-sig">lithos_list([path_prefix], [tags], [author], [since], [limit], [offset])</div>

---

## Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `path_prefix` | string | — | Return only documents under this path prefix |
| `tags` | string[] | — | Filter to documents with **all** of these tags |
| `author` | string | — | Filter to documents by this author |
| `since` | string | — | Return only documents updated after this ISO 8601 timestamp |
| `limit` | int | — | Max results (default: `50`) |
| `offset` | int | — | Pagination offset (default: `0`) |

---

## Returns

```json
{
  "items": [
    {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "title": "Python asyncio.gather patterns",
      "path": "python-asyncio-gather-patterns.md",
      "updated": "2026-03-18T14:30:00Z",
      "tags": ["python", "asyncio", "patterns"],
      "source_url": null,
      "derived_from_ids": []
    }
  ],
  "total": 1
}
```

`total` is the total number of matching items (before `limit`/`offset` are applied), useful for pagination.

---

## Examples

### List all documents

```python
result = lithos_list()
print(f"Total documents: {result['total']}")
for item in result["items"]:
    print(f"  {item['path']} — {item['title']}")
```

### List by tag

```python
# Find all Python antipatterns
result = lithos_list(tags=["python", "antipattern"])
```

### List documents by a specific agent

```python
# What has research-agent written?
result = lithos_list(author="research-agent")
```

### List recently updated documents

```python
from datetime import datetime, timedelta, timezone

yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
result = lithos_list(since=yesterday)
print(f"Updated since yesterday: {result['total']}")
```

### Paginate through a large KB

```python
page_size = 50
offset = 0
all_items = []

while True:
    result = lithos_list(limit=page_size, offset=offset)
    all_items.extend(result["items"])
    offset += page_size
    if offset >= result["total"]:
        break
```

### List by path prefix

```python
# All documents in the procedures directory
result = lithos_list(path_prefix="procedures/")
```

---

## Notes

- `lithos_list` returns metadata only — titles, paths, tags, dates. Use `lithos_read` to fetch full content.
- Use `lithos_search` when you're looking for documents about a specific topic. Use `lithos_list` when you need to enumerate, audit, or sync.
- For tag discovery (what tags exist?), use `lithos_tags` from the Graph Tools.
