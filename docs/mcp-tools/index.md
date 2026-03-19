# MCP Tools Reference

Lithos exposes **22 MCP tools** across five categories. All tools are available via both SSE and stdio transports.

## Tool Categories

=== "Knowledge (7)"

    | Tool | Description |
    |------|-------------|
    | [`lithos_write`](lithos_write.md) | Create or update a knowledge item |
    | [`lithos_read`](lithos_read.md) | Read a knowledge item by ID or path |
    | [`lithos_search`](lithos_search.md) | Full-text, semantic, or hybrid search |
    | [`lithos_list`](lithos_list.md) | List items with filters |
    | [`lithos_delete`](lithos_delete.md) | Delete a knowledge item |
    | `lithos_cache_lookup` | Check for a cached answer before researching |
    | `lithos_health` | Knowledge base health check |

=== "Graph (3)"

    | Tool | Description |
    |------|-------------|
    | `lithos_links` | Get wiki-link relationships for a document |
    | `lithos_tags` | List all tags with document counts |
    | `lithos_provenance` | Traverse derived-from lineage |

    → [Graph Tools Reference](graph-tools.md)

=== "Agent (3)"

    | Tool | Description |
    |------|-------------|
    | [`lithos_agent_register`](lithos_agent_register.md) | Explicitly register an agent |
    | `lithos_agent_info` | Get info about a specific agent |
    | `lithos_agent_list` | List all known agents |

    → [Agent Tools Reference](lithos_agent_register.md)

=== "Coordination (8)"

    | Tool | Description |
    |------|-------------|
    | `lithos_task_create` | Create a coordination task |
    | `lithos_task_claim` | Claim an aspect of a task |
    | `lithos_task_renew` | Extend a task claim |
    | `lithos_task_release` | Release a task claim |
    | `lithos_task_complete` | Mark a task complete |
    | [`lithos_task_status`](lithos_task_status.md) | Get task status and active claims |
    | `lithos_finding_post` | Post a finding to a task |
    | `lithos_finding_list` | List findings for a task |

    → [Coordination Tools Reference](coordination-tools.md)

=== "System (1)"

    | Tool | Description |
    |------|-------------|
    | `lithos_stats` | Knowledge base statistics |

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
| `doc_not_found` | `lithos_read`, `lithos_delete` | Document with given ID/path does not exist |
| `version_conflict` | `lithos_write` | `expected_version` did not match current version |
| `content_too_large` | `lithos_write` | Content exceeds configured size limit |
| `slug_collision` | `lithos_write` | A different document already has this slug |
| `duplicate` | `lithos_write` | A document with the same `source_url` already exists |
| `claim_failed` | `lithos_task_claim` | Task missing, closed, or aspect already claimed |
| `claim_not_found` | `lithos_task_renew`, `lithos_task_release` | No active claim for this agent/aspect |
| `task_not_found` | `lithos_task_complete` | Task missing or already closed |
| `invalid_mode` | `lithos_search` | Unknown search mode |
| `invalid_input` | various | Bad argument values |
