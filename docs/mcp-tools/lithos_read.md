# lithos_read

Read a knowledge item by UUID or file path.

<div class="tool-sig">lithos_read(id | path, [max_length])</div>

---

## Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `id` | string | One of* | UUID of the knowledge item |
| `path` | string | One of* | File path relative to `knowledge/` (e.g., `python-asyncio.md`) |
| `max_length` | int | — | Truncate content to N characters. Truncation happens at a sentence or paragraph boundary. |

*Provide either `id` or `path`, not both.

---

## Returns

```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "title": "Python asyncio.gather patterns",
  "content": "Use `asyncio.gather()` to run coroutines concurrently...",
  "truncated": false,
  "metadata": {
    "author": "research-agent",
    "contributors": ["synthesis-agent"],
    "tags": ["python", "asyncio", "patterns"],
    "confidence": 0.95,
    "created_at": "2026-03-18T12:00:00Z",
    "updated_at": "2026-03-18T14:30:00Z",
    "version": 2,
    "source_url": null,
    "derived_from_ids": [],
    "expires_at": null
  },
  "links": {
    "outgoing": ["uuid-of-linked-note"],
    "incoming": []
  }
}
```

### Error

```json
{
  "status": "error",
  "code": "doc_not_found",
  "message": "No document found with id 'f47ac10b-...'"
}
```

---

## Examples

### Read by ID

```python
doc = lithos_read(id="f47ac10b-58cc-4372-a567-0e02b2c3d479")
print(doc["content"])
print(doc["metadata"]["tags"])
```

### Read by path

```python
doc = lithos_read(path="python-asyncio-gather-patterns.md")
```

### Read with truncation (protect context window)

```python
doc = lithos_read(id="f47ac10b-...", max_length=2000)

if doc["truncated"]:
    print("Content was truncated — use lithos_search for a snippet instead")
```

!!! tip "Choose your reading strategy"
    - **Short documents** (< 2000 chars): read in full with no `max_length`
    - **Medium documents**: use `max_length=2000` to get the top and avoid flooding the context window
    - **Very long documents**: use `lithos_search` to get a targeted snippet first, then read by ID with `max_length` if you need more

---

## Notes

- `links` contains the parsed wiki-link graph for this document: `outgoing` = links this document makes, `incoming` = documents that link to this one.
- `truncated: true` means `max_length` was hit. The content ends at the nearest sentence boundary at or before `max_length`.
- Prefer `id` over `path` for stable references. File paths can change if notes are renamed in Obsidian; UUIDs are immutable.
