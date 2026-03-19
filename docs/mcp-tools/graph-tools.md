# Graph Tools

Tools for navigating the knowledge graph built from wiki-links and provenance relationships.

---

## lithos_links

Get the wiki-link relationships for a knowledge item.

<div class="tool-sig">lithos_links(id, [direction], [depth])</div>

### Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `id` | string | ✅ | UUID of the knowledge item |
| `direction` | string | — | `"outgoing"` (default), `"incoming"`, or `"both"` |
| `depth` | int | — | Traversal depth 1–3 (default: `1`) |

### Returns

```json
{
  "outgoing": [
    { "id": "uuid-b", "title": "Python event loop internals" },
    { "id": "uuid-c", "title": "Concurrency patterns" }
  ],
  "incoming": [
    { "id": "uuid-d", "title": "Comprehensive async Python guide" }
  ]
}
```

### Multi-hop traversal

At `depth > 1`, results include all reachable nodes within N hops, deduplicated. For example, with `depth=2`:

```
A → B → C
A → D

depth=1 outgoing from A: [B, D]
depth=2 outgoing from A: [B, C, D]
```

### Example

```python
# What does this document link to?
links = lithos_links(id="uuid-of-asyncio-note", direction="outgoing")

# What documents reference this one?
links = lithos_links(id="uuid-of-asyncio-note", direction="incoming")

# Both, 2 hops
links = lithos_links(id="uuid-of-asyncio-note", direction="both", depth=2)
```

---

## lithos_tags

List all tags in the knowledge base with document counts.

<div class="tool-sig">lithos_tags()</div>

No parameters.

### Returns

```json
{
  "tags": {
    "python": 12,
    "asyncio": 5,
    "patterns": 8,
    "antipattern": 3,
    "research": 20
  }
}
```

### Example

```python
# Get all tags sorted by usage
tags = lithos_tags()
sorted_tags = sorted(tags["tags"].items(), key=lambda x: x[1], reverse=True)
for name, count in sorted_tags[:10]:
    print(f"  {name}: {count} documents")
```

!!! tip "Finding documents by tag"
    `lithos_tags` tells you what tags *exist* and how many documents use each. To find documents *with* a specific tag, use `lithos_list(tags=["tag-name"])` or `lithos_search(query="...", tags=["tag-name"])`.

---

## lithos_provenance

Traverse the provenance (derived-from) lineage graph for a knowledge item.

<div class="tool-sig">lithos_provenance(id, [direction], [depth], [include_unresolved])</div>

### Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `id` | string | ✅ | UUID of the knowledge item |
| `direction` | string | — | `"sources"` (what this was derived from), `"derived"` (what was derived from this), or `"both"` (default) |
| `depth` | int | — | Traversal depth 1–3 (default: `1`) |
| `include_unresolved` | bool | — | Include source IDs that don't resolve to existing documents (default: `true`) |

### Returns

```json
{
  "id": "synthesis-uuid",
  "sources": [
    { "id": "source-a-uuid", "title": "asyncio.gather patterns" },
    { "id": "source-b-uuid", "title": "asyncio event loop internals" }
  ],
  "derived": [
    { "id": "derivative-uuid", "title": "Production async Python cookbook" }
  ],
  "unresolved_sources": []
}
```

`unresolved_sources` contains source UUIDs from `derived_from_ids` that no longer have a corresponding document (e.g., the source was deleted).

### Returns (error)

```json
{
  "status": "error",
  "code": "doc_not_found",
  "message": "No document found with id 'unknown-uuid'"
}
```

### Example

```python
# Trace where a synthesis document came from
prov = lithos_provenance(
    id="synthesis-uuid",
    direction="sources",
    depth=2  # follow chains: synthesis → source → source's sources
)

print(f"Direct sources: {len(prov['sources'])}")
if prov["unresolved_sources"]:
    print(f"⚠️  {len(prov['unresolved_sources'])} source(s) have been deleted")

# Check what documents were derived from a key research note
prov = lithos_provenance(
    id="foundational-research-uuid",
    direction="derived"
)
print(f"Documents built on this research: {[d['title'] for d in prov['derived']]}")
```

---

## The Knowledge Graph

Lithos maintains two overlapping graphs:

| Graph | Built from | Query tool |
|-------|-----------|-----------|
| Wiki-link graph | `[[note-title]]` in Markdown body | `lithos_links` |
| Provenance graph | `derived_from_ids` in frontmatter | `lithos_provenance` |

**Wiki-links** represent semantic relationships — "this note mentions or relies on that note."

**Provenance** represents synthesis — "this note was created by combining those notes."

Both graphs are directed, stored in NetworkX, and rebuilt from Markdown files if needed. Traversal uses BFS with cycle detection.
