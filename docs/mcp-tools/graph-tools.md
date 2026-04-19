# Graph Tools

Tools for navigating and editing the knowledge graph built from wiki-links, provenance relationships, and LCMA typed edges.

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

---

## lithos_edge_upsert

Create or update a typed LCMA edge between two documents. The upsert key is `(from_id, to_id, type, namespace)` — calling with the same key updates the existing edge.

<div class="tool-sig">lithos_edge_upsert(from_id, to_id, type, weight, namespace, [provenance_actor], [provenance_type], [evidence], [conflict_state])</div>

### Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `from_id` | string | ✅ | Source document UUID |
| `to_id` | string | ✅ | Target document UUID |
| `type` | string | ✅ | Edge type (e.g. `"derived_from"`, `"supports"`, `"contradicts"`, `"related_to"`) |
| `weight` | float | ✅ | Edge weight (higher = stronger relationship) |
| `namespace` | string | ✅ | Namespace for the edge — must be non-empty |
| `provenance_actor` | string | — | Agent or process that created the edge |
| `provenance_type` | string | — | How the edge was derived (e.g. `"inferred"`, `"manual"`) |
| `evidence` | object\|array | — | Supporting evidence; must be a dict or list (scalars rejected) |
| `conflict_state` | string | — | Conflict state marker (see `lithos_conflict_resolve`) |

### Returns

```json
{
  "status": "ok",
  "edge_id": "edge-uuid-abc123"
}
```

### Error Envelope

| Code | Condition |
|------|-----------|
| `invalid_input` | `namespace` is empty, or `evidence` is a scalar (not dict/list) |

### Example

```python
# Record a "supports" relationship between two documents
lithos_edge_upsert(
    from_id="uuid-of-evidence-doc",
    to_id="uuid-of-claim-doc",
    type="supports",
    weight=0.85,
    namespace="research-sprint-4",
    provenance_actor="synthesis-agent",
    provenance_type="inferred"
)
```

!!! note "Edge upsert vs lithos_write provenance"
    `lithos_edge_upsert` writes to `edges.db` (the LCMA typed-edge store). It is separate from `derived_from_ids` in frontmatter, which is set via `lithos_write`. Use `lithos_edge_upsert` for typed, weighted, namespaced relationships; use `derived_from_ids` for simple "this note was synthesised from these sources" provenance.

---

## lithos_conflict_resolve

Resolve a contradiction between two notes by setting the resolution state on a `contradicts` edge. Future retrieval reflects the resolution.

<div class="tool-sig">lithos_conflict_resolve(edge_id, resolution, resolver, [winner_id])</div>

### Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `edge_id` | string | ✅ | The edge ID of the `contradicts` edge to resolve |
| `resolution` | string | ✅ | Resolution strategy — one of `accepted_dual`, `superseded`, `refuted`, `merged` |
| `resolver` | string | ✅ | Agent or user identifier performing the resolution |
| `winner_id` | string | — | Required when `resolution` is `"superseded"` — must be either the `from_id` or `to_id` of the edge |

### Resolution strategies

| Value | Meaning |
|-------|---------|
| `accepted_dual` | Both notes are correct in different contexts |
| `superseded` | One note is newer/more accurate and replaces the other (`winner_id` required) |
| `refuted` | One note has been disproved |
| `merged` | The notes have been combined into a new synthesis document |

### Returns

```json
{
  "status": "ok",
  "edge_id": "edge-uuid-abc123",
  "conflict_state": "superseded"
}
```

### Error Envelope

| Code | Condition |
|------|-----------|
| `invalid_input` | `resolution` is not one of the valid values; `winner_id` is missing for `superseded`; `winner_id` is not one of the edge endpoints; the edge is not of type `contradicts` |
| `not_found` | `edge_id` does not exist |
| `update_failed` | Edge update could not be applied |

### Example

```python
# Find all unresolved contradictions
edges = lithos_edge_list(type="contradicts")
for edge in edges["results"]:
    if edge.get("conflict_state") is None:
        # Resolve: the newer document supersedes the older one
        lithos_conflict_resolve(
            edge_id=edge["id"],
            resolution="superseded",
            resolver="review-agent",
            winner_id=edge["to_id"]
        )
```
