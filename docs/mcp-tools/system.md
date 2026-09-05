# System Tools & HTTP Endpoints

One MCP tool (`lithos_stats`) plus the three plain HTTP routes the server mounts alongside the MCP transports.

## `lithos_stats`

Knowledge base statistics and health indicators. Cheap to call — use it to understand KB scale before issuing broad queries, or as a health probe from agent code.

```python
lithos_stats()
```

**Returns:**

```json
{
  "documents": 1234,
  "chroma_chunk_count": 5678,
  "agents": 5,
  "active_tasks": 12,
  "open_claims": 8,
  "tags": 89,
  "duplicate_urls": 0,

  "index_drift_detected": false,
  "tantivy_doc_count": 1234,
  "unresolved_links": 3,
  "expired_docs": 2,
  "expired_claims": 0,
  "tantivy_last_updated": "2026-09-01T12:00:00+00:00",
  "chroma_last_updated": "2026-09-01T12:00:00+00:00",

  "graph_node_count": 1240,
  "graph_edge_count": 3100
}
```

| Field | Meaning |
|-------|---------|
| `documents` | Markdown documents in the corpus |
| `chroma_chunk_count` | Semantic chunks in ChromaDB (0 when the store is quarantined) |
| `tantivy_doc_count` | Documents in the full-text index; `null` when the index is unavailable (distinct from 0) |
| `index_drift_detected` | `tantivy_doc_count` disagrees with `documents` — run `lithos reindex` |
| `unresolved_links` | `[[wiki-links]]` pointing at documents that don't exist |
| `expired_docs` | Documents past their `expires_at` freshness deadline |
| `expired_claims` | Task claims past their TTL (cleaned lazily) |
| `graph_edge_count` | All wiki-link graph edges **including** ones to unresolved placeholders (= resolved edges + `unresolved_links`) |

---

## HTTP Endpoints

When run with `--transport http`, one port serves both MCP transports — `POST /mcp` (StreamableHTTP, stateless) and `GET /sse` + `POST /messages/` (legacy SSE) — plus these three routes. They are **not** MCP tools and do not appear in `tools/list`.

There is **no `GET /metrics`** — metrics are pushed via OTLP; see [Observability](../deployment/observability.md).

### `GET /health`

Lightweight health check for Docker `HEALTHCHECK`, load balancers, and monitoring.

**200 OK:**

```json
{
  "status": "ok",
  "timestamp": "2026-09-01T12:00:00+00:00",
  "components": {
    "kb_directory": {"status": "ok"},
    "search": {"status": "ok"},
    "knowledge_base": {"status": "ok"}
  }
}
```

**503 Service Unavailable:** same shape with `"status": "degraded"` and per-component `error` strings.

| Component | Check |
|-----------|-------|
| `kb_directory` | Knowledge base directory exists on disk |
| `search` | `SearchEngine.health()` — composed full-text + semantic + embedding-model signal |
| `knowledge_base` | Can list at least one document |

```bash
curl -f http://localhost:8765/health
```

### `GET /events`

Best-effort Server-Sent Events stream over the in-memory event bus.

**Query parameters / headers:**

| Name | Description |
|------|-------------|
| `types` | Comma-separated event type filter (e.g. `note.created,task.completed`) |
| `tags` | Comma-separated tag filter; any matching tag passes |
| `since` | Replay buffered events strictly after the given event ID |
| `Last-Event-ID` header | Standard SSE reconnect; takes precedence over `since` |

**Event types:** `note.created`, `note.updated`, `note.deleted`, `note.renamed`, `edge.upserted`, `task.created`, `task.updated`, `task.claimed`, `task.released`, `task.completed`, `task.cancelled`, `task.reopened`, `finding.posted`, `agent.registered`.

**Behavior:**

- Replays from the in-memory ring buffer (default 500 events) when `since`/`Last-Event-ID` is supplied, then streams live.
- When the reconnect id is **not** in the ring (evicted, or from a previous server run), the stream emits an **`event: resync`** control message — deliberately with no `id:` line, so it never becomes the client's next `Last-Event-ID` — telling the client to re-fetch current state instead of trusting a truncated replay. Consumers **must** handle `resync`.
- Periodic keepalive comments when idle.
- `503` when `events.sse_enabled=false`; `429` when `events.max_sse_clients` is exceeded; `401` when MCP auth is configured and the request is unauthenticated.
- Delivery is best-effort and **process-local** — events outside the ring buffer cannot be replayed. Treat the stream as a cache-invalidation hint, not a durable log.

### `GET /audit`

Read-only access to the audit log of document reads (search results returned, documents fetched).

**Query parameters:**

| Name | Type | Description |
|------|------|-------------|
| `agent_id` | string | Filter to entries reported by this agent |
| `after` | string | ISO-8601 timestamp; only entries after this time |
| `limit` | int | Max entries (default 100) |
| `doc_id` | string | Filter entries for a specific document |

**Returns:**

- `200` — `{"entries": [{"id": …, "agent_id": "…", "doc_id": "…", "operation": "…", "timestamp": "…"}]}`
- `400` — `{"error": "invalid_after", "message": "…"}` when `after` cannot be parsed
- `503` — `{"error": "audit_log_unavailable", "entries": []}` when the coordination layer fails

!!! warning "Trust boundary"
    The endpoint is **unauthenticated** and `agent_id` values are self-reported by callers. The audit log is advisory-only — never use it for access control. Suitable for trusted-network deployments only.

The same data is available from the CLI: `lithos audit --agent <id> --since <iso> --limit 50`.
