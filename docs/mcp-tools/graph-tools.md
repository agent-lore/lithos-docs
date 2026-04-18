# Graph Tools

Tools for navigating the knowledge graph built from wiki-links, provenance relationships, and LCMA typed edges.

---

## lithos_related

The primary graph-query tool. Merges wiki-links, provenance chains, and LCMA typed edges into a single response.

<div class="tool-sig">lithos_related(id, [include], [depth], [namespace])</div>

### Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `id` | string | ✅ | UUID of the knowledge item |
| `include` | string[] | — | Which backends to query: `"links"`, `"provenance"`, `"edges"` (default: all three) |
| `depth` | int | — | Traversal depth 1–3 (default: `1`); applies to `links` and `provenance` sections |
| `namespace` | string | — | Scope `edges` results to this namespace only (links/provenance ignore this) |

### Returns

```json
{
  "id": "doc-uuid",
  "included": ["links", "provenance", "edges"],
  "links": {
    "outgoing": [
      { "id": "uuid-b", "title": "Python event loop internals" }
    ],
    "incoming": [
      { "id": "uuid-d", "title": "Comprehensive async Python guide" }
    ]
  },
  "provenance": {
    "sources": [
      { "id": "source-a-uuid", "title": "asyncio.gather patterns" }
    ],
    "derived": [],
    "unresolved_sources": []
  },
  "edges": {
    "outgoing": [
      { "from_id": "doc-uuid", "to_id": "uuid-b", "type": "supports", "namespace": "default" }
    ],
    "incoming": []
  },
  "related_ids": ["uuid-b", "uuid-d", "source-a-uuid"]
}
```

Sections not in `include` are **omitted entirely** (not emitted as empty objects). `related_ids` is the deduplicated union of all referenced document IDs across all included sections, excluding the queried document's own ID.

### Migration from `lithos_links` / `lithos_provenance`

!!! warning "lithos_links and lithos_provenance removed in v0.2.1"
    `lithos_links` and `lithos_provenance` were removed in v0.2.1. Use `lithos_related` instead:

    ```python
    # Before (lithos_links)
    links = lithos_links(id="doc-uuid", direction="both", depth=2)

    # After
    related = lithos_related(id="doc-uuid", include=["links"], depth=2)
    links = related["links"]  # same outgoing/incoming structure
    ```

    ```python
    # Before (lithos_provenance)
    prov = lithos_provenance(id="doc-uuid", direction="both")

    # After
    related = lithos_related(id="doc-uuid", include=["provenance"])
    prov = related["provenance"]  # sources, derived, unresolved_sources
    ```

    Note: the `include_unresolved` parameter from `lithos_provenance` is dropped — unresolved sources always surface in the composite response.

### Multi-hop traversal

`depth` controls traversal depth for the `links` and `provenance` sections (1–3). For example, with `depth=2`:

```
A → B → C
A → D

depth=1 outgoing from A: [B, D]
depth=2 outgoing from A: [B, C, D]
```

### Examples

```python
# Everything related to a document
related = lithos_related(id="doc-uuid")

# Just wiki-links, 2 hops
related = lithos_related(id="doc-uuid", include=["links"], depth=2)

# Just provenance chain
related = lithos_related(id="doc-uuid", include=["provenance"])

# Typed edges in a specific namespace
related = lithos_related(id="doc-uuid", include=["edges"], namespace="research")

# Walk the full graph neighbourhood
for related_id in related["related_ids"]:
    neighbour = lithos_read(id=related_id)
```

### Returns (error)

```json
{
  "status": "error",
  "code": "doc_not_found",
  "message": "No document found with id 'unknown-uuid'"
}
```

---

## lithos_edge_list

Query typed LCMA edges globally (not anchored to a single document). Use this when you need cross-collection edge queries that `lithos_related` can't express.

<div class="tool-sig">lithos_edge_list([from_id], [to_id], [type], [namespace])</div>

### Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `from_id` | string | — | Filter edges by source document ID |
| `to_id` | string | — | Filter edges by target document ID |
| `type` | string | — | Filter by edge type (e.g. `"supports"`, `"contradicts"`, `"derived_from"`) |
| `namespace` | string | — | Filter by namespace |

### Returns

```json
{
  "edges": [
    {
      "from_id": "uuid-a",
      "to_id": "uuid-b",
      "type": "supports",
      "namespace": "default",
      "created_at": "2026-04-18T10:00:00Z"
    }
  ]
}
```

### Examples

```python
# All edges of type "contradicts" across the entire knowledge base
edges = lithos_edge_list(type="contradicts")

# All edges in a namespace (for an audit/review pass)
edges = lithos_edge_list(namespace="research-sprint-4")

# Outgoing edges from a specific document
edges = lithos_edge_list(from_id="doc-uuid")
```

!!! tip "lithos_related vs lithos_edge_list"
    Use `lithos_related` when you have a **specific document** and want to see all its relationships at once.
    Use `lithos_edge_list` when you need **global queries** across all edges (e.g. "find all `contradicts` edges", "audit an entire namespace").

---

## lithos_tags

List all tags in the knowledge base with document counts.

<div class="tool-sig">lithos_tags([prefix])</div>

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `prefix` | string | — | Return only tags starting with this prefix (e.g. `"py"` returns `python`, `pytest`, …) |

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

## The Knowledge Graph

Lithos maintains overlapping graph structures:

| Graph | Built from | Query tool |
|-------|-----------|-----------|
| Wiki-link graph | `[[note-title]]` in Markdown body | `lithos_related` (include=["links"]) |
| Provenance graph | `derived_from_ids` in frontmatter | `lithos_related` (include=["provenance"]) |
| LCMA edge graph | `lithos_edge_upsert` | `lithos_related` (include=["edges"]) / `lithos_edge_list` |

**Wiki-links** represent semantic relationships — "this note mentions or relies on that note."

**Provenance** represents synthesis — "this note was created by combining those notes."

**LCMA edges** are typed, namespaced relationships managed by the Layered Cognitive Memory Architecture pipeline.

All graph structures are queryable via `lithos_related` for per-document neighbourhood traversal, or `lithos_edge_list` for global edge queries.
