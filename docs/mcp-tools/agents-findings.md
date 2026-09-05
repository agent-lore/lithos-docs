# Agent & Finding Tools

Agents are auto-registered on first use of any tool that takes an `agent` parameter; explicit registration adds a display name, type, and metadata. Findings are lightweight progress notes attached to tasks — the coordination-side complement to knowledge notes.

## `lithos_agent_register`

Explicitly register an agent (optional — agents auto-register on first use).

```python
lithos_agent_register(id: str, name: str | None = None,
                      type: str | None = None, metadata: dict | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `id` | string | Agent identifier (free-form string) |
| `name` | string | Human-friendly display name |
| `type` | string | Agent type, e.g. `"claude-code"`, `"agent-zero"`, `"openclaw"`, `"custom"` |
| `metadata` | object | Additional metadata (capabilities, version, …) |

**Returns:** `{"success": true, "created": true}` for a new agent; `{"success": true, "created": false}` when the agent already existed (metadata updated, `last_seen_at` refreshed). Emits `agent.registered`.

**ID conventions:** pick stable, descriptive ids — `<harness>-<role>` (`claude-code-researcher`) or `<host>-<harness>` work well. The id is your identity across knowledge authorship, claims, and findings.

---

## `lithos_agent_info`

Get information about an agent.

```python
lithos_agent_info(id: str)
```

**Returns:** `{ id, name, type, first_seen_at, last_seen_at, metadata }`, or `null` when the agent is unknown (note: not an error envelope).

---

## `lithos_agent_list`

List all known agents.

```python
lithos_agent_list(type: str | None = None, active_since: str | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `type` | string | Filter by agent type |
| `active_since` | string | Only agents seen since (ISO 8601; unparseable → `invalid_input`) |

**Returns:** `{ "agents": [{ id, name, type, last_seen_at }] }`

---

## `lithos_finding_post`

Post a finding to a task. Findings are the running log of what agents discovered while working a task — post them as you go, not just at the end.

```python
lithos_finding_post(task_id: str, agent: str, summary: str,
                    knowledge_id: str | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `task_id` | string | Task ID (full id or unambiguous ≥6-char prefix) |
| `agent` | string | Your agent identifier |
| `summary` | string | Brief summary of the finding |
| `knowledge_id` | string | Optional link to a knowledge note (unique note prefix resolves; other values stored as given) |

**Returns:** `{"finding_id": "…", "task_id": "<resolved-full-id>", "title": "…"}` — `title` is `null` when a full-length task id is unknown (findings may be posted ahead of their task). Emits `finding.posted`.

!!! tip
    For substantial findings, write a knowledge note first with `lithos_write`, then post the finding with `knowledge_id` linking to it — the finding stays scannable and the detail is searchable.

---

## `lithos_finding_list`

List findings for a task.

```python
lithos_finding_list(task_id: str, since: str | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `task_id` | string | Task ID (full id or unambiguous ≥6-char prefix) |
| `since` | string | Only findings after this time (ISO 8601; unparseable → `invalid_input`) |

**Returns:** `{ "findings": [{ id, agent, summary, knowledge_id, created_at }] }`

Note: [`lithos_task_reopen`](tasks.md#lithos_task_reopen) auto-posts a durable `[Reopened]` finding recording the prior terminal status — it will show up in this list.
