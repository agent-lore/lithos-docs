# lithos_stats

**Added in v0.1.1**

Get knowledge base statistics and health indicators. Use this to audit the health of the Lithos instance — document counts, index drift, unresolved links, expired claims, and more.

<div class="tool-sig">lithos_stats()</div>

## Parameters

None.

## Returns

```json
{
  "documents": 142,
  "chroma_chunk_count": 891,
  "agents": 5,
  "active_tasks": 3,
  "open_claims": 7,
  "tags": 38,
  "duplicate_urls": 0,
  "index_drift_detected": false,
  "tantivy_doc_count": 142,
  "unresolved_links": 4,
  "expired_docs": 2,
  "expired_claims": 1,
  "tantivy_last_updated": "2026-04-18T10:00:00Z",
  "chroma_last_updated": "2026-04-18T10:00:00Z",
  "graph_node_count": 150,
  "graph_edge_count": 60
}
```

## Fields

| Field | Description |
|-------|-------------|
| `documents` | Total documents in the knowledge base (in-memory cache count) |
| `chroma_chunk_count` | Number of embedding chunks in ChromaDB |
| `agents` | Number of registered agents |
| `active_tasks` | Number of open coordination tasks |
| `open_claims` | Number of active (non-expired) task claims |
| `tags` | Total distinct tags across all documents |
| `duplicate_urls` | Documents sharing a `source_url` with another document |
| `index_drift_detected` | `true` if Tantivy document count differs from knowledge base count — indicates the index may need rebuilding |
| `tantivy_doc_count` | Documents indexed in Tantivy full-text search (`null` if index unavailable) |
| `unresolved_links` | Wiki-links in the graph pointing to documents that don't exist |
| `expired_docs` | Documents past their `expires_at` freshness deadline |
| `expired_claims` | Claims that have passed their TTL without being explicitly released |
| `tantivy_last_updated` | Filesystem mtime of the Tantivy index directory |
| `chroma_last_updated` | Filesystem mtime of the ChromaDB directory |
| `graph_node_count` | Total nodes in the NetworkX wiki-link graph (includes unresolved placeholders) |
| `graph_edge_count` | Total edges in the graph (includes edges to unresolved nodes; `graph_edge_count - unresolved_links` ≈ resolved edges) |

## Health Signals

| Signal | What to do |
|--------|-----------|
| `index_drift_detected: true` | Restart Lithos with `rebuild_on_start: true` or run `lithos reindex` |
| `unresolved_links > 0` | Wiki-links point to missing documents; create the missing docs or fix the link targets |
| `expired_docs > 0` | Documents have passed freshness deadlines; refresh or delete them |
| `expired_claims > 0` | Task claims are stale — agents may have crashed without releasing claims; use `lithos_task_cancel` to clean up |
| `duplicate_urls > 0` | Multiple documents share a `source_url`; deduplicate with `lithos_delete` |

## Example

```python
stats = lithos_stats()
if stats["index_drift_detected"]:
    print(f"⚠️  Index drift: {stats['tantivy_doc_count']} indexed vs {stats['documents']} in KB")
if stats["expired_docs"] > 0:
    print(f"ℹ️  {stats['expired_docs']} documents need refreshing")
print(f"📚 {stats['documents']} docs | 👥 {stats['agents']} agents | 🏷️ {stats['tags']} tags")
```

!!! note "Difference from GET /health"
    `lithos_stats` returns knowledge base metrics and health *indicators*. For infrastructure liveness (is the server up?), use [`GET /health`](lithos_health.md) instead — it's designed for Docker HEALTHCHECK and load balancers.
