# lithos_node_stats

**Added in v0.2.1** (LCMA MVP2)

View a document's LCMA salience score, retrieval history, and penalty counts. Useful for debugging retrieval quality — understanding why a document ranks high or low in `lithos_retrieve` results.

!!! info "Requires LCMA"
    `lithos_node_stats` queries the LCMA stats store (`stats.db`). The tool is registered regardless of LCMA config, but stats rows are only populated when `lcma.enabled: true`. With LCMA disabled, documents that exist in the knowledge base will return default values (salience `0.5`, all counts `0`).

<div class="tool-sig">lithos_node_stats(node_id)</div>

## Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `node_id` | string | ✅ | Document UUID to look up stats for |

## Returns

```json
{
  "node_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "salience": 0.82,
  "retrieval_count": 14,
  "cited_count": 9,
  "last_retrieved_at": "2026-04-18T11:30:00Z",
  "last_used_at": "2026-04-18T11:30:00Z",
  "ignored_count": 2,
  "misleading_count": 0,
  "decay_rate": 0.05,
  "spaced_rep_strength": 0.76,
  "last_decay_applied_at": "2026-04-17T00:00:00Z"
}
```

## Fields

| Field | Description |
|-------|-------------|
| `node_id` | The document UUID queried |
| `salience` | LCMA salience score (0–1). Higher = more frequently cited; influences reranking in `lithos_retrieve`. Default `0.5` for new documents. |
| `retrieval_count` | Number of times this document has appeared in `lithos_retrieve` results |
| `cited_count` | Number of times an agent cited this document as useful via `lithos_task_complete(cited_nodes=[...])` |
| `last_retrieved_at` | ISO 8601 timestamp of most recent retrieval |
| `last_used_at` | ISO 8601 timestamp of most recent citation |
| `ignored_count` | Times the document was retrieved but not cited (ignored reinforcement signal) |
| `misleading_count` | Times an agent flagged this document as misleading via `lithos_task_complete(misleading_nodes=[...])` |
| `decay_rate` | Current temporal decay rate applied to salience |
| `spaced_rep_strength` | Spaced-repetition strength score (higher = document resurfaces less frequently) |
| `last_decay_applied_at` | When temporal decay was last applied to this document's salience |

## Interpretation

- **High salience + high cited_count** → the document is reliably useful; retrieval is working well
- **High retrieval_count + high ignored_count** → the document matches queries but agents don't find it useful; consider updating or tagging more precisely
- **misleading_count > 0** → agents flagged this document as counterproductive; review and archive or correct it
- **salience well below 0.5** → the document has been penalised by past feedback; it will rank lower in future retrievals

## Error Envelope

```json
{
  "status": "error",
  "code": "doc_not_found",
  "message": "Node 'unknown-uuid' not found in knowledge base."
}
```

Returns `doc_not_found` when `node_id` does not correspond to any document in the knowledge base.

## Example

```python
stats = lithos_node_stats(node_id="f47ac10b-58cc-4372-a567-0e02b2c3d479")
print(f"Salience: {stats['salience']:.2f}")
print(f"Cited {stats['cited_count']}x, ignored {stats['ignored_count']}x, misleading {stats['misleading_count']}x")
```

## Related

- [`lithos_retrieve`](lithos_retrieve.md) — uses salience scores during Terrace 1 reranking
- [`lithos_task_complete`](coordination-tools.md#lithos_task_complete) — the tool that supplies `cited_nodes` / `misleading_nodes` feedback that drives salience updates
