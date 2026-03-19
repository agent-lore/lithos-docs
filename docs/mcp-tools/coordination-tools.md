# Coordination Tools

Full reference for Lithos's multi-agent coordination primitives.

For a usage guide with examples and the full workflow diagram, see [lithos_task_status](lithos_task_status.md).

---

## Overview

Lithos provides **TTL-based task claiming** — a lightweight distributed locking mechanism that lets agents divide work without a central orchestrator.

```mermaid
graph LR
    TC["lithos_task_create\ncreate a task"] --> CL["lithos_task_claim\nclaim an aspect"]
    CL --> TR["lithos_task_renew\nextend the claim"]
    CL --> RL["lithos_task_release\nabandon the claim"]
    CL --> FP["lithos_finding_post\npost a result"]
    FP --> FL["lithos_finding_list\nread results"]
    TR --> TS["lithos_task_status\ncheck progress"]
    FL --> COMP["lithos_task_complete\nclose the task"]
```

---

## Tool Summary

| Tool | Purpose |
|------|---------|
| `lithos_task_create` | Create a named task |
| `lithos_task_claim` | Claim an aspect (distributed lock with TTL) |
| `lithos_task_renew` | Extend a claim before expiry |
| `lithos_task_release` | Release a claim early |
| `lithos_task_complete` | Mark task done, release all claims |
| `lithos_task_status` | Query task state and active claims |
| `lithos_finding_post` | Post a finding (result) to a task |
| `lithos_finding_list` | List findings for a task |

---

## Reference

### lithos_task_create

**Arguments:**

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `title` | string | ✅ | Task title |
| `agent` | string | ✅ | Creating agent |
| `description` | string | — | Longer description |
| `tags` | string[] | — | Task tags for filtering |

**Returns:** `{ "task_id": "task-abc123" }`

---

### lithos_task_claim

Attempt to claim an *aspect* of a task. Aspect names are free-form strings — use them to describe what part of the work you're taking on. If another agent already holds a claim on the same aspect, the call fails.

**Arguments:**

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `task_id` | string | ✅ | Task ID |
| `aspect` | string | ✅ | What aspect you're claiming (e.g., `"research"`, `"implementation"`, `"review"`) |
| `agent` | string | ✅ | Your agent ID |
| `ttl_minutes` | int | — | Claim duration (default: `60`, max: `480`) |

**Returns:** `{ "success": true, "expires_at": "..." }` or `{ "status": "error", "code": "claim_failed" }`

!!! tip "Aspect naming"
    Aspects should be specific enough to avoid unintentional conflicts. `"implementation"` is fine if only one agent will implement. If multiple agents might work in parallel, use `"implementation:module-a"` and `"implementation:module-b"`.

---

### lithos_task_renew

Extend a claim you hold. Only the agent that holds the claim can renew it.

**Arguments:**

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `task_id` | string | ✅ | Task ID |
| `aspect` | string | ✅ | The aspect you claimed |
| `agent` | string | ✅ | Your agent ID |
| `ttl_minutes` | int | — | New duration from now (default: `60`, max: `480`) |

**Returns:** `{ "success": true, "new_expires_at": "..." }` or `{ "status": "error", "code": "claim_not_found" }`

Renew before expiry — once a claim expires, another agent can take it.

---

### lithos_task_release

Release a claim early. Use this if you're abandoning the work so another agent can pick it up.

**Arguments:**

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `task_id` | string | ✅ | Task ID |
| `aspect` | string | ✅ | The aspect to release |
| `agent` | string | ✅ | Your agent ID |

**Returns:** `{ "success": true }` or `{ "status": "error", "code": "claim_not_found" }`

---

### lithos_task_complete

Mark a task as completed. This also releases all active claims on the task.

**Arguments:**

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `task_id` | string | ✅ | Task ID |
| `agent` | string | ✅ | Agent marking completion |

**Returns:** `{ "success": true }` or `{ "status": "error", "code": "task_not_found" }`

---

### lithos_finding_post

Post a finding to a task. Use this to report results — optionally linking to a knowledge item you've written.

**Arguments:**

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `task_id` | string | ✅ | Task ID |
| `agent` | string | ✅ | Your agent ID |
| `summary` | string | ✅ | Brief summary of the finding |
| `knowledge_id` | string | — | UUID of a `lithos_write` result, if you created a knowledge item |

**Returns:** `{ "finding_id": "finding-xyz789" }`

---

### lithos_finding_list

List findings for a task.

**Arguments:**

| Name | Type | Required | Description |
|------|------|:--------:|-------------|
| `task_id` | string | ✅ | Task ID |
| `since` | string | — | Only findings after this ISO 8601 timestamp |

**Returns:**

```json
{
  "findings": [
    {
      "id": "finding-xyz789",
      "agent": "research-agent",
      "summary": "mem0 lacks task claiming and Markdown storage",
      "knowledge_id": "uuid-of-mem0-analysis",
      "created_at": "2026-03-18T12:30:00Z"
    }
  ]
}
```
