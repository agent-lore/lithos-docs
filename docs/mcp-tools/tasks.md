# Task Tools

Eleven tools manage the task lifecycle. Tasks live in SQLite (`.lithos/coordination.db`) and coordinate multi-agent work through **aspect claims** — TTL-based advisory locks on named facets of a task.

## The task record

Every task-returning tool uses the same record shape:

```json
{
  "id": "…", "title": "…", "description": "…",
  "status": "open", "task_type": "task",
  "created_by": "…", "created_at": "…",
  "resolved_at": null, "updated_at": "…",
  "tags": ["…"], "metadata": {}, "outcome": null
}
```

- **Lifecycle:** `open` → `completed` | `cancelled` → (via [`lithos_task_reopen`](#lithos_task_reopen)) → `open`.
- **`task_type`:** `task` (default), `epic` (roll-up container), or `gate` (external wait) — see [Task Graph](task-graph.md).
- **`resolved_at`** is set on both terminal transitions (complete *and* cancel); `null` while open.
- **`outcome`** holds the free-text completion summary; `null` until completed with one.
- **`updated_at`** *(since v0.4.0, unreleased)* is bumped by every task-**row** write — create, update (even a no-op `metadata={}` merge), complete, cancel, reopen. Claim/renew/release never bump it, so lease heartbeats can't masquerade as edits. Mutating responses echo the stamp the write produced; detect "edited since X" by comparing stamps for **equality**, not ordering.

All `task_id` parameters accept an unambiguous ≥6-char [short ID prefix](index.md#short-id-prefixes); an unknown 6–35-char prefix returns `task_not_found` on every task tool.

---

## `lithos_task_create`

```python
lithos_task_create(title: str, agent: str, description: str | None = None,
                   tags: list[str] | None = None, metadata: dict | None = None,
                   task_type: str = "task", depends_on: list[str] | None = None,
                   parent_task_id: str | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `title` | string | Task title |
| `agent` | string | Creating agent |
| `description` | string | Task description |
| `tags` | string[] | Task tags |
| `metadata` | object | Arbitrary JSON persisted at insert time (an **initial set**, not a merge). Must not contain `depends_on`/`blocked_on` → `invalid_metadata_key`; dependencies are edges. |
| `task_type` | string | `task` \| `epic` \| `gate` (default `task`; other values → `invalid_task_type`). A `gate` requires gate metadata — see [Gates](task-graph.md#gates). |
| `depends_on` | string[] | Predecessor task IDs; each creates a `blocks` edge `predecessor → this task`. Predecessors must exist (`task_not_found`). |
| `parent_task_id` | string | Creates a `parent_child` edge `parent → this task` (structural; never blocks). |

**Returns:** `{"task_id": "…", "title": "…", "updated_at": "…"}` (plus resolved `depends_on`/`parent_task_id` when supplied), or an error envelope (`invalid_metadata_key`, `invalid_task_type`, `task_not_found`). Emits `task.created`.

---

## `lithos_task_update`

Update mutable task fields. **Works on terminal tasks too** — useful for annotating an archived task without reviving it; `task_not_found` genuinely means missing.

```python
lithos_task_update(task_id: str, agent: str, title: str | None = None,
                   description: str | None = None, tags: list[str] | None = None,
                   metadata: dict | None = None)
```

At least one of `title`, `description`, `tags`, `metadata` must be provided (`invalid_input` otherwise).

**Metadata is an additive per-key merge:** non-null values overwrite, `{"key": null}` deletes that key, unmentioned keys are preserved. `metadata={}` preserves everything (though it still writes the row and bumps `updated_at`). There is no wholesale clear. The merge runs in a single transaction, so concurrent writers on different keys never clobber each other. `depends_on`/`blocked_on` keys → `invalid_metadata_key`.

**Returns:** `{"success": true, "message": "…", "task_id": "…", "title": "…", "updated_at": "…"}` or an error envelope (`invalid_input`, `invalid_metadata_key`, `task_not_found`). Emits `task.updated`.

---

## `lithos_task_get`

Fetch a single task without claims — with an explicit not-found envelope, unlike `lithos_task_status`.

```python
lithos_task_get(task_id: str)
```

**Returns:** `{"task": {…}}` (the [task record](#the-task-record)), or `{status: "error", code: "task_not_found", message}`.

---

## `lithos_task_list`

```python
lithos_task_list(agent: str | None = None, status: str | None = None,
                 tags: list[str] | None = None, since: str | None = None,
                 resolved_since: str | None = None, with_claims: bool = False,
                 metadata_match: dict | None = None, task_type: str | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `agent` | string | Filter by creating agent |
| `status` | string | `open` \| `completed` \| `cancelled` |
| `task_type` | string | `task` \| `epic` \| `gate` |
| `tags` | string[] | Tasks containing all listed tags |
| `since` | string | `created_at >= since` (ISO) |
| `resolved_since` | string | `resolved_at >= resolved_since` — tasks resolved either way in the window; open tasks excluded |
| `with_claims` | bool | Inline each task's active claims as `claims: [{agent, aspect, expires_at}]` (one batched query — avoids an N+1 of `lithos_task_status` calls). Default `false`. |
| `metadata_match` | object | Same semantics as [`lithos_list.metadata_match`](knowledge-read.md#lithos_list); pushed into SQLite via `json_extract`/`json_each`, never a Python scan |

**Returns:** `{"tasks": […]}` of [task records](#the-task-record) (plus `claims` when `with_claims=true`).

---

## `lithos_task_status`

Full record of one task **with** its active claims.

```python
lithos_task_status(task_id: str)
```

**Returns:** `{"tasks": [{…, "claims": [{"agent": "…", "aspect": "…", "expires_at": "…"}]}]}`. Returns `{"tasks": []}` for an unknown full-length task id (historical behaviour — use [`lithos_task_get`](#lithos_task_get) for an explicit not-found envelope). Expired claims are filtered out lazily at query time.

---

## `lithos_task_claim`

Claim an aspect of a task. Claims are advisory TTL locks — one agent per `(task, aspect)`; the aspect string is free-form (`"research"`, `"implementation"`, `"review"`, …).

```python
lithos_task_claim(task_id: str, aspect: str, agent: str, ttl_minutes: int = 60)
```

`ttl_minutes` defaults to 60, max 480 (configurable via `coordination.*`).

**Returns:** `{"success": true, "expires_at": "…", "task_id": "…", "title": "…"}` or `{status: "error", code: "claim_failed"}` (task closed, or aspect already claimed). A prefix that matches no task → `task_not_found`. Emits `task.claimed`.

---

## `lithos_task_renew`

Extend a claim you hold. Only the claim's agent can renew it.

```python
lithos_task_renew(task_id: str, aspect: str, agent: str, ttl_minutes: int = 60)
```

**Returns:** `{"success": true, "new_expires_at": "…", "task_id": "…", "title": "…"}` or `{status: "error", code: "claim_not_found"}`.

---

## `lithos_task_release`

Release a claim without resolving the task.

```python
lithos_task_release(task_id: str, aspect: str, agent: str)
```

**Returns:** `{"success": true, "task_id": "…", "title": "…"}` or `{status: "error", code: "claim_not_found"}`. Emits `task.released`.

---

## `lithos_task_complete`

Complete a task, optionally closing the LCMA reinforcement loop.

```python
lithos_task_complete(task_id: str, agent: str, outcome: str | None = None,
                     cited_nodes: list[str] | None = None,
                     misleading_nodes: list[str] | None = None,
                     receipt_id: str | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `outcome` | string | Free-text completion summary, persisted on the row and in the `task.completed` event |
| `cited_nodes` | string[] | Note IDs from a [`lithos_retrieve`](retrieval.md#lithos_retrieve) that were genuinely useful — boosts their salience |
| `misleading_nodes` | string[] | Note IDs that misled — penalizes their salience |
| `receipt_id` | string | Bind feedback to a specific retrieve receipt (default: the latest for this `(task_id, agent)`) |

**Returns:** `{"success": true, "unblocked": ["…"], "task_id": "…", "title": "…", "updated_at": "…"}` — `unblocked` lists dependents this completion just made ready, so an orchestrator can pick them up without re-polling [`lithos_task_ready`](task-graph.md#lithos_task_ready). Errors: `task_not_found` (missing or not open), `receipt_not_found`.

**Behavior:** sets `status=completed`, `resolved_at = updated_at = now`, stores `outcome`, releases all claims. Feedback is validated against the bound receipt; with no findable receipt and no explicit `receipt_id`, feedback is silently dropped and the task still completes. Emits `task.completed`.

---

## `lithos_task_cancel`

Cancel a task and delete all its claims.

```python
lithos_task_cancel(task_id: str, agent: str, reason: str | None = None)
```

**Returns:** `{"success": true, "task_id": "…", "title": "…", "updated_at": "…"}` or `task_not_found`. Sets `status=cancelled` and `resolved_at = now`. `reason` is accepted but **not persisted** (it does appear in the `task.cancelled` event payload).

!!! warning
    A cancelled task leaves its `blocks`/`waits_on_gate` dependents **permanently blocked** (`blocker_unsatisfiable`), not spuriously ready. Reopening the cancelled task un-strands them — see below and [Task Graph](task-graph.md#readiness).

---

## `lithos_task_reopen`

Move a terminal (`completed`/`cancelled`) task back to `open` — the inverse of complete/cancel.

```python
lithos_task_reopen(task_id: str, agent: str)
```

**Returns:** `{"success": true, "reblocked": ["…"], "task_id": "…", "title": "…", "updated_at": "…"}`, or an error envelope (`task_not_found`; `task_not_resolved` when the task is already open).

**Behavior:**

- Clears `resolved_at` and `outcome`, sets `status=open`, bumps `updated_at`.
- Posts a durable `[Reopened]` finding recording the prior terminal status, and emits `task.reopened` (payload carries `prior_status`/`prior_outcome`).
- Claims were released at complete/cancel time and are **not** restored.
- `reblocked` lists open dependents this reopen put back under the task's block — non-empty only when reopening a **completed** blocker/gate. Reopening a **cancelled** blocker instead *un-strands* its dependents (`blocker_unsatisfiable` → waiting) and reblocks nothing.
