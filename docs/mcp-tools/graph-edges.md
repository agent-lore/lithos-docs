# Graph Edge Tools

Three tools manage **agent-asserted typed edges** between notes, stored in `edges.db` (the authoritative store for asserted edges — distinct from the wiki-link graph, which is derived from `[[wiki-links]]` in note bodies, and from provenance, which is derived from `derived_from_ids` frontmatter).

| Graph | Source of truth | Queried via |
|-------|-----------------|-------------|
| Wiki-links | `[[links]]` in note bodies | [`lithos_related`](knowledge-read.md#lithos_related) (`links`), `lithos_search(mode="graph")` |
| Provenance | `derived_from_ids` frontmatter | [`lithos_related`](knowledge-read.md#lithos_related) (`provenance`) |
| Typed edges | `edges.db` (this page) | `lithos_edge_list`, [`lithos_related`](knowledge-read.md#lithos_related) (`edges`) |

## `lithos_edge_upsert`

Insert or update a typed weighted edge. The unique key is `(from_id, to_id, type, namespace)`.

```python
lithos_edge_upsert(from_id: str, to_id: str, type: str, weight: float,
                   namespace: str, provenance_actor: str | None = None,
                   provenance_type: str | None = None, evidence: Any = None,
                   conflict_state: str | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `from_id` | string | Source node UUID (a unique ≥6-char note prefix resolves; other values pass through for free-form node ids) |
| `to_id` | string | Target node UUID (same lenient resolution) |
| `type` | string | Edge type — e.g. `related_to`, `supports`, `contradicts`, `derived_from` |
| `weight` | float | Edge weight 0–1 |
| `namespace` | string | LCMA namespace this edge belongs to |
| `provenance_actor` | string | Agent or rule ID that authored the edge |
| `provenance_type` | string | `human` \| `agent` \| `rule` \| `frontmatter` |
| `evidence` | object/array | Anchors or snippets supporting the edge; scalars → `invalid_input` |
| `conflict_state` | string | Reserved for `contradicts` edges |

**Returns:** `{"status": "ok", "edge_id": "edge_<short-uuid>"}`. Emits an `edge.upserted` event.

!!! note
    The background enrichment worker can also write edges here when [LLM synthesis](../getting-started/configuration.md) is enabled — those arrive with `provenance_type: "inferred"` and the model's rationale as evidence.

---

## `lithos_edge_list`

Query edges by node, type, or namespace. Filters compose as AND; all are optional. This is the only tool that can express global edge queries (e.g. all `contradicts` edges) — for edges around one document, prefer [`lithos_related`](knowledge-read.md#lithos_related).

```python
lithos_edge_list(from_id: str | None = None, to_id: str | None = None,
                 type: str | None = None, namespace: str | None = None)
```

**Returns:**

```json
{"results": [{"edge_id": "…", "from_id": "…", "to_id": "…", "type": "contradicts",
              "weight": 0.9, "namespace": "shared", "created_at": "…", "updated_at": "…",
              "provenance_actor": "…", "provenance_type": "agent",
              "evidence": [], "conflict_state": "unresolved"}]}
```

---

## `lithos_conflict_resolve`

Resolve a contradiction between two notes by setting the `conflict_state` on a `contradicts` edge. The resolution is recorded so future retrieval reflects it.

```python
lithos_conflict_resolve(edge_id: str, resolution: str, resolver: str,
                        winner_id: str | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `edge_id` | string | Edge ID of the `contradicts` edge |
| `resolution` | string | `accepted_dual` \| `superseded` \| `refuted` \| `merged` |
| `resolver` | string | Agent or user performing the resolution |
| `winner_id` | string | Required when `resolution="superseded"`; must equal the edge's `from_id` or `to_id`. The winner is marked as superseding the loser. |

**Returns:** `{"status": "ok", "edge_id": "…", "conflict_state": "…"}`, or an error envelope:

| Code | Meaning |
|------|---------|
| `invalid_input` | Unknown `resolution`; edge is not a `contradicts` edge; `winner_id` missing or not an endpoint |
| `not_found` | No edge with the given `edge_id` |
| `update_failed` | Edge found but the persistence write failed (e.g. concurrent deletion) |

**Example — find and resolve contradictions:**

```python
edges = lithos_edge_list(type="contradicts")
for edge in edges["results"]:
    if edge["conflict_state"] == "unresolved":
        lithos_conflict_resolve(edge_id=edge["edge_id"],
                                resolution="superseded",
                                resolver="curator-agent",
                                winner_id=edge["to_id"])
```
