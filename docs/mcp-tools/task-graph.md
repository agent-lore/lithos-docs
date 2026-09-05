# Task Graph Tools

Since v0.4.0, task dependencies are **first-class typed edges** — not metadata conventions. Six tools work the graph: edge upsert/list, the ready/blocked frontier, children, and spawn. Lithos stays **passive**: readiness is computed at query time from edges and task status; nothing polls external systems.

!!! warning "Migration from metadata conventions"
    `metadata.depends_on` / `metadata.blocked_on` are **rejected** on task create, update, and spawn with `invalid_metadata_key`. A one-time migration backfilled existing metadata conventions into `blocks` edges when 0.4.0 first started.

## Edge types

| Type | Blocking? | Meaning |
|------|-----------|---------|
| `blocks` | **Yes** | `from` must be `completed` before `to` is ready |
| `waits_on_gate` | **Yes** | `to` waits until the `from` **gate** is resolved (see [Gates](#gates)) |
| `parent_child` | No | Structural hierarchy (`from` = parent). Never blocks the child. |
| `discovered_from` | No | Provenance: `to` was discovered while working `from` |

Cycles in blocking edges are rejected on write (`cycle`), via a bounded traversal — never a full-table walk.

## Readiness

A task is **ready** when it is `open`, is not a `gate` or `epic`, every incoming `blocks` predecessor is `completed`, and no unresolved gate holds it.

- A predecessor still `open` → the dependent is just **waiting** (`kind: "task"` blocker).
- A predecessor that ends **`cancelled`** leaves dependents **permanently blocked** (`kind: "blocker_unsatisfiable"`) rather than spuriously ready — re-open, re-route, or cancel is the orchestrator's call.
- Completing a blocker reports the newly-ready dependents in the completion's `unblocked` list; reopening a completed blocker reports `reblocked`.

---

## `lithos_task_edge_upsert`

Create or update a typed relation between two tasks.

```python
lithos_task_edge_upsert(from_task_id: str, to_task_id: str, type: str,
                        agent: str, metadata: dict | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `from_task_id` | string | Source (blocker / parent / gate / source) |
| `to_task_id` | string | Target (blocked / child / waiter / discovered) |
| `type` | string | `blocks` \| `parent_child` \| `discovered_from` \| `waits_on_gate` |
| `agent` | string | Agent creating the edge |
| `metadata` | object | Optional edge metadata (replaced on conflict) |

**Returns:** `{"success": true, "from_task_id": "…", "from_title": "…", "to_task_id": "…", "to_title": "…"}` (both endpoints resolved to full ids), or an error envelope:

| Code | Meaning |
|------|---------|
| `invalid_edge_type` | Type not accepted |
| `self_edge` | `from` == `to` |
| `task_not_found` | Either endpoint missing |
| `cycle` | Edge would create a blocking or ancestry cycle |
| `parent_exists` | Child already has a different parent (hierarchy is a **forest** — re-parenting requires removing the existing edge first) |
| `not_a_gate` | `waits_on_gate` whose `from` task is not a `gate` |

---

## `lithos_task_edge_list`

List edges touching a task.

```python
lithos_task_edge_list(task_id: str, direction: str = "both",
                      types: list[str] | None = None)
```

`direction` is `incoming` | `outgoing` | `both`, relative to `task_id` (invalid value → `invalid_input`).

**Returns:** `{"edges": [{"from_task_id": "…", "to_task_id": "…", "type": "blocks", "direction": "incoming", "metadata": {}, "created_by": "…", "created_at": "…"}]}`

---

## `lithos_task_ready`

Return open tasks whose blocking predecessors are all satisfied — the **feasible frontier**. `epic` and `gate` tasks are excluded.

```python
lithos_task_ready(project: str | None = None, tags: list[str] | None = None,
                  metadata_match: dict | None = None, limit: int = 50,
                  with_claims: bool = True)
```

| Name | Type | Description |
|------|------|-------------|
| `project` | string | Shorthand for `metadata.project == project` |
| `tags` | string[] | Tasks containing all listed tags |
| `metadata_match` | object | Same semantics as [`lithos_task_list.metadata_match`](tasks.md#lithos_task_list) |
| `limit` | int | Max tasks (default 50) |
| `with_claims` | bool | Attach active claims inline (default `true`) |

**Returns:** `{"tasks": […]}`. Claims are **attached but never used to exclude** a task — collision-correctness comes from the atomic [`lithos_task_claim`](tasks.md#lithos_task_claim), and claims are per-aspect, so the picking agent decides what "taken" means. Query cost scales with the open frontier, not total task count.

---

## `lithos_task_blocked`

Return open tasks that are **not** ready, each with structured blocker reasons. Same filter surface as `lithos_task_ready` (no `with_claims`).

```python
lithos_task_blocked(project: str | None = None, tags: list[str] | None = None,
                    metadata_match: dict | None = None, limit: int = 50)
```

**Returns:** `{"tasks": [{…, "blockers": [{"kind": "…", "task_id": "…", "type": "…", "status": "…", "message": "…"}]}]}`

| `kind` | Meaning |
|--------|---------|
| `task` | Predecessor still `open` — just waiting |
| `gate` | Waiting on an unresolved gate (message names the `gate_type` / `ready_at`) |
| `blocker_unsatisfiable` | Predecessor or gate was `cancelled` — needs intervention (reopen it, or remove the edge) |
| `cycle` | The blocking chain forms a cycle; `message` names the members |

---

## `lithos_task_children`

Return the child tasks of a parent/epic, via outgoing `parent_child` edges.

```python
lithos_task_children(task_id: str, recursive: bool = False,
                     include_closed: bool = False)
```

- `recursive=true` walks the full descendant subtree.
- `include_closed=false` (default) returns open children only — but the subtree is **traversed** in full regardless, so an open grandchild under a closed child is still surfaced.

**Returns:** `{"tasks": […]}` — [task records](tasks.md#the-task-record), ordered by `created_at` within each parent.

---

## `lithos_task_spawn`

Create a follow-on task linked to an existing source task — the idiom for "while doing X I discovered Y needs doing".

```python
lithos_task_spawn(source_task_id: str, title: str, agent: str,
                  description: str | None = None,
                  relation_type: str = "discovered_from",
                  inherit_project: bool = True, inherit_tags: bool = True,
                  inherit_context: bool = True, metadata: dict | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `source_task_id` | string | The task this follow-on came from |
| `relation_type` | string | `discovered_from` (default; provenance) or `blocks` (spawned waits until source completes). The edge is always `source → spawned`. Other values → `invalid_relation_type`. |
| `inherit_project` | bool | Copy `metadata.project` from the source (default `true`) |
| `inherit_tags` | bool | Copy the source's tags (default `true`) |
| `inherit_context` | bool | Copy the scheduling keys `priority`, `parallelizable`, `phase` (default `true`) |
| `metadata` | object | Extra metadata; overrides inherited keys. No `depends_on`/`blocked_on`. |

**Returns:** `{"task_id": "…", "title": "…", "source_task_id": "<resolved>", "updated_at": "…"}` or an error envelope (`invalid_relation_type`, `task_not_found`, `invalid_metadata_key`). The spawned task is always `task_type="task"`. Emits `task.created`.

---

## Epics

An **epic** (`task_type="epic"`) is a roll-up container: give it children via `parent_task_id` on create or `parent_child` edges, and query progress with `lithos_task_children(recursive=True)`. Epics are excluded from `lithos_task_ready`. Hierarchy is a forest (one parent per task, acyclic). There are no epic close rules yet — an epic can complete with open children.

## Gates

A **gate** is an external wait modelled as an ordinary task with `task_type="gate"`, created via [`lithos_task_create`](tasks.md#lithos_task_create) — no dedicated tool. A task waits on it via a `waits_on_gate` edge (`gate → task`).

**Gate metadata** (validated at creation and re-validated on update; invalid → `invalid_input`):

| Key | Required | Description |
|-----|----------|-------------|
| `gate_type` | Yes | `human` \| `timer` \| `ci` \| `pr` \| `external_task` |
| `ready_at` | `timer` only | ISO datetime; the gate auto-resolves once `ready_at <= now` (normalized to UTC second precision at creation) |

Other keys (`approval_required_from`, `provider`, `run_id`, `repo`, `pr_number`, `external_id`, `required_state`, …) are **advisory** — they tell the resolving agent what to check; Lithos never reads them.

**Resolution — Lithos never polls.** A gate is resolved when:

- the gate task is **`completed`** (an agent observed the condition and completed it), or
- it is an open `timer` gate whose `ready_at` has passed (evaluated at query time; no state change).

A **cancelled** gate is unsatisfiable — its waiters show as `blocker_unsatisfiable`. "Proceed anyway" means completing the gate or removing the edge, not cancelling it. Completing a gate reports its newly-ready waiters in `unblocked`.

**Example — hold a deploy behind CI and a human approval:**

```python
ci = lithos_task_create(title="CI green on release branch", agent="orch",
                        task_type="gate", metadata={"gate_type": "ci", "repo": "org/app"})
approval = lithos_task_create(title="Release sign-off", agent="orch",
                              task_type="gate",
                              metadata={"gate_type": "human", "approval_required_from": "dave"})
deploy = lithos_task_create(title="Deploy 1.2.0", agent="orch")
lithos_task_edge_upsert(from_task_id=ci["task_id"], to_task_id=deploy["task_id"],
                        type="waits_on_gate", agent="orch")
lithos_task_edge_upsert(from_task_id=approval["task_id"], to_task_id=deploy["task_id"],
                        type="waits_on_gate", agent="orch")
# later, whichever agent observes CI passing:
lithos_task_complete(task_id=ci["task_id"], agent="ci-watcher", outcome="run 4211 green")
```
