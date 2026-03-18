# Agent Tools

Tools for managing agent identity within the Lithos knowledge base.

---

## lithos_agent_register

Explicitly register an agent with display metadata. Optional — agents are auto-registered on first use.

<div class="tool-sig">lithos_agent_register(id, [name], [type], [metadata])</div>

### Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `id` | string | ✅ | Agent identifier (free-form string, e.g., `"research-agent"`) |
| `name` | string | — | Human-friendly display name |
| `type` | string | — | Agent type: `"agent-zero"`, `"openclaw"`, `"claude-code"`, `"custom"` |
| `metadata` | object | — | Additional metadata (capabilities, version, etc.) |

### Returns

```json
{ "success": true, "created": true }
```

- `created: true` — new agent registered
- `created: false` — agent already existed; metadata and `last_seen_at` updated

### Example

```python
lithos_agent_register(
    id="research-agent",
    name="Research Agent",
    type="openclaw",
    metadata={"capabilities": ["web_search", "pdf_analysis"], "version": "2.1"}
)
```

---

## lithos_agent_info

Get information about a specific agent.

<div class="tool-sig">lithos_agent_info(id)</div>

### Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `id` | string | ✅ | Agent identifier |

### Returns

```json
{
  "id": "research-agent",
  "name": "Research Agent",
  "type": "openclaw",
  "first_seen_at": "2026-03-01T10:00:00Z",
  "last_seen_at": "2026-03-18T12:00:00Z",
  "metadata": { "capabilities": ["web_search", "pdf_analysis"] }
}
```

Returns `null` if the agent is not found.

---

## lithos_agent_list

List all agents known to Lithos.

<div class="tool-sig">lithos_agent_list([type], [active_since])</div>

### Parameters

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `type` | string | — | Filter by agent type |
| `active_since` | string | — | Only agents seen since this ISO 8601 timestamp |

### Returns

```json
{
  "agents": [
    {
      "id": "research-agent",
      "name": "Research Agent",
      "type": "openclaw",
      "last_seen_at": "2026-03-18T12:00:00Z"
    },
    {
      "id": "claude-code",
      "name": null,
      "type": "claude-code",
      "last_seen_at": "2026-03-17T09:00:00Z"
    }
  ]
}
```

### Example

```python
# Find all active agents in the last 24 hours
from datetime import datetime, timedelta, timezone
since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
result = lithos_agent_list(active_since=since)
print(f"Active agents: {[a['id'] for a in result['agents']]}")
```

---

## Auto-Registration

You don't need to call `lithos_agent_register` before using Lithos. Any operation that requires an agent ID (`lithos_write`, `lithos_task_claim`, etc.) will auto-register the agent if it hasn't been seen before.

Explicit registration is useful when you want to:
- Set a human-readable display name
- Declare the agent type for filtering
- Attach capability metadata

---

## Agent ID Conventions

| Pattern | Example | Use for |
|---------|---------|---------|
| Descriptive slug | `research-agent` | General purpose agents |
| Framework + instance | `claude-code-1` | Multiple instances of the same type |
| Role-based | `orchestrator`, `synthesizer` | Role-specific agents |
| Tool name | `openclaw`, `agent-zero` | Named tools/platforms |

Avoid spaces and special characters. Hyphens are idiomatic.
