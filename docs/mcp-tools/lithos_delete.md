# lithos_delete

Delete a knowledge item permanently.

<div class="tool-sig">lithos_delete(id, agent)</div>

!!! warning "Irreversible"
    Deletion is permanent. The Markdown file is removed and the indices are updated. If you need to keep the knowledge but mark it as superseded, prefer updating the document with a note rather than deleting it.

---

## Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `id` | string | ✅ | UUID of the knowledge item to delete |
| `agent` | string | ✅ | Agent performing the deletion (for audit trail) |

---

## Returns

### Success

```json
{ "success": true }
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

### Delete by ID

```python
result = lithos_delete(
    id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
    agent="cleanup-agent"
)

if result.get("success"):
    print("Deleted successfully")
else:
    print(f"Error: {result['code']} — {result['message']}")
```

### Delete outdated research

```python
# Find stale items and remove them
results = lithos_search(query="github api", mode="fulltext")
for r in results["results"]:
    if r["is_stale"]:
        lithos_delete(id=r["id"], agent="maintenance-agent")
        print(f"Deleted stale: {r['title']}")
```

---

## Notes

- `agent` became required in a recent update (see [Changelog](../changelog.md)). Callers that previously omitted it must be updated.
- Deletion removes the Markdown file and updates Tantivy and ChromaDB indices. The knowledge graph is updated to remove any wiki-link edges involving this document.
- Documents that had `derived_from_ids` pointing to the deleted document will retain those IDs in their frontmatter, but `lithos_provenance` will list them under `unresolved_sources`.
- If you need to retain the knowledge but indicate it's been superseded, use `lithos_write` to add a `supersedes` field or update the content with a deprecation notice instead.
