# MCP Tools Reference

Lithos exposes **28 MCP tools** across five categories. All tools are available via both SSE and stdio transports.

!!! info "v0.2.1"
    This reference reflects v0.2.1. `lithos_conflict_resolve` and `lithos_node_stats` were added in v0.2.1 (LCMA MVP2). `lithos_links` and `lithos_provenance` were removed in v0.2.1 — use [`lithos_related`](graph-tools.md#lithos_related) instead.

## Tool Categories

=== "Knowledge (7)"

    | Tool | Description |
    |------|-------------|
    | [`lithos_write`](lithos_write.md) | Create or update a knowledge item |
    | [`lithos_read`](lithos_read.md) | Read a knowledge item by ID or path |
    | [`lithos_search`](lithos_search.md) | Full-text, semantic, hybrid, or graph traversal search |
    | [`lithos_list`](lithos_list.md) | List items with filters |
    | [`lithos_delete`](lithos_delete.md) | Delete a knowledge item |
    | [`lithos_cache_lookup`](lithos_cache_lookup.md) | Check for a cached answer before researching |
    | [`lithos_retrieve`](lithos_retrieve.md) | LCMA cognitive retrieval (multi-scout, reranked, with audit receipts) |

=== "Graph (5)"

    | Tool | Description |
    |------|-------------|
    | [`lithos_related`](graph-tools.md#lithos_related) | Composite graph tool — wiki-links, provenance, and LCMA edges in one call |
    | [`lithos_tags`](graph-tools.md#lithos_tags) | List all tags with document counts |
    | [`lithos_edge_upsert`](graph-tools.md#lithos_edge_upsert) | Create or update a typed LCMA edge |
    | [`lithos_edge_list`](graph-tools.md#lithos_edge_list) | Query LCMA edges by filters (global edge queries) |
    | [`lithos_conflict_resolve`](graph-tools.md#lithos_conflict_resolve) | Resolve a contradiction between two notes |

    → [Graph Tools Reference](graph-tools.md)

=== "Agent (3)"

    | Tool | Description |
    |------|-------------|
    | [`lithos_agent_register`](lithos_agent_register.md#lithos_agent_register) | Explicitly register an agent |
    | [`lithos_agent_info`](lithos_agent_register.md#lithos_agent_info) | Get info about a specific agent |
    | [`lithos_agent_list`](lithos_agent_register.md#lithos_agent_list) | List all known agents |

    → [Agent Tools Reference](lithos_agent_register.md)

=== "Coordination (11)"

    | Tool | Description |
    |------|-------------|
    | [`lithos_task_create`](coordination-tools.md#lithos_task_create) | Create a coordination task |
    | [`lithos_task_update`](coordination-tools.md#lithos_task_update) | Update task metadata (title, description, tags) |
    | [`lithos_task_claim`](coordination-tools.md#lithos_task_claim) | Claim an aspect of a task |
    | [`lithos_task_renew`](coordination-tools.md#lithos_task_renew) | Extend a task claim |
    | [`lithos_task_release`](coordination-tools.md#lithos_task_release) | Release a task claim |
    | [`lithos_task_complete`](coordination-tools.md#lithos_task_complete) | Mark a task complete |
    | [`lithos_task_cancel`](coordination-tools.md#lithos_task_cancel) | Cancel a task, releasing all claims |
    | [`lithos_task_list`](coordination-tools.md#lithos_task_list) | List tasks with optional filters |
    | [`lithos_task_status`](lithos_task_status.md) | Get task status and active claims |
    | [`lithos_finding_post`](coordination-tools.md#lithos_finding_post) | Post a finding to a task |
    | [`lithos_finding_list`](coordination-tools.md#lithos_finding_list) | List findings for a task |

    → [Coordination Tools Reference](coordination-tools.md)

=== "System (2)"

    | Tool | Description |
    |------|-------------|
    | [`lithos_stats`](lithos_stats.md) | Knowledge base statistics and health indicators |
    | [`lithos_node_stats`](lithos_node_stats.md) | View a document's LCMA salience score and retrieval history |

---

## HTTP Endpoints

In addition to MCP tools, Lithos exposes HTTP endpoints for infrastructure use:

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Server health check — returns `200 OK` or `503`. Use with Docker `HEALTHCHECK` and load balancers. |
| `GET /events` | Server-Sent Events stream for real-time event delivery. |
| `GET /audit` | Read-access audit log — filterable by agent, document, and start time. |
| `GET /metrics` | Prometheus-compatible metrics (added v0.1.8). |

→ [Health Endpoint Reference](lithos_health.md)

→ [Observability Reference](../deployment/observability.md)

---

## Common Patterns

### Always check before researching

```python
cache = lithos_cache_lookup(query="...", max_age_hours=168)
if not cache["hit"]:
    # do research
    lithos_write(title="...", content="...", agent="...")
```

### Truncate reads to protect context windows

```python
doc = lithos_read(id="...", max_length=2000)
```

### Tag aggressively

Tags are your primary filtering mechanism. Be consistent. Examples:

- Technology: `python`, `rust`, `docker`
- Type: `pattern`, `antipattern`, `reference`, `decision`
- Status: `draft`, `verified`, `stale`
- Source: `research`, `production`, `test`

---

## Error Envelope

All tools that can fail return a structured error envelope:

```json
{
  "status": "error",
  "code": "<error_code>",
  "message": "Human-readable description"
}
```

| Code | Tool | Meaning |
|------|------|---------|
| `doc_not_found` | `lithos_read`, `lithos_delete`, `lithos_node_stats` | Document with given ID/path does not exist |
| `version_conflict` | `lithos_write` | `expected_version` did not match current version |
| `content_too_large` | `lithos_write` | Content exceeds configured size limit |
| `slug_collision` | `lithos_write` | A different document already has this slug |
| `duplicate` | `lithos_write` | A document with the same `source_url` already exists |
| `claim_failed` | `lithos_task_claim` | Task missing, closed, or aspect already claimed |
| `claim_not_found` | `lithos_task_renew`, `lithos_task_release` | No active claim for this agent/aspect |
| `task_not_found` | `lithos_task_complete`, `lithos_task_cancel`, `lithos_task_update` | Task missing or already closed |
| `receipt_not_found` | `lithos_task_complete` | Specified `receipt_id` not found for this task |
| `invalid_mode` | `lithos_search` | Unknown search mode |
| `lcma_disabled` | `lithos_retrieve` | LCMA is not enabled in config |
| `not_found` | `lithos_conflict_resolve` | Edge ID does not exist |
| `invalid_input` | various | Bad argument values |
