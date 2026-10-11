# Concepts

Loom is structured as **sources → bus → subscribers**. Sources (the Lithos event stream, vault file watchers, the GitHub poller) publish typed events onto an in-process async bus; subscribers consume them. The route-runner is a special *claim-bound* subscriber that owns a task's lifecycle from claim to `result.json`.

```
lithos-loom run  (supervisor: one TOML, forks children, relays SIGTERM / SIGUSR1)
├── route-runner     ← [[routes]]            LithosEventStream → one RouteRunner per route
├── obsidian-sync    ← [obsidian_sync]       Lithos streams + vault watchers → projection / push handlers
└── github-watcher   ← [github_watcher]      LithosNoteStream + GitHubIssueWatcher → issue sync / PR-gate sweep
```

---

## Routes and tag matching

A `[[routes]]` stanza is a claim-bound subscriber. A task **matches** a route when it carries *every* tag in `match.tags` (superset semantics — extra tags are fine).

```toml
[[routes]]
name = "story-develop"
command = "uv run python -m lithos_loom.plugins.story_develop --task-json {{task_json}} --work-dir {{work_dir}} --result-file {{result_file}} --repo {{repo}}"
max_runtime_seconds = 28800   # SIGTERM, grace, SIGKILL, then a `timeout` escalation
completes_task = false        # default true; false = success raises a `pr` gate instead of completing
human_blocking = false        # true = the claimed task still shows in the Obsidian inbox

[routes.match]
tags = ["trigger:story-develop"]
```

| Token in `command` | Replaced with |
|--------------------|---------------|
| `{{task_json}}` | Path to a read-only JSON file: `{"task": <Lithos task envelope>}` (plus a `resume` block on a resume dispatch) |
| `{{work_dir}}` | `<orchestrator.work_dir>/<task_id>/` — the plugin owns the tree |
| `{{result_file}}` | The path the plugin must write atomically on exit |
| `{{repo}}` | `[projects.<slug>].repo` for the task's `metadata.project` — one route serves every registered project. A task with no project, or a slug this host has not mapped, is released with a `[BlockerFailed]` finding and never run. |

Routes listen to `lithos.task.created`, `lithos.task.updated` and `lithos.task.released`. Because `updated` is treated as "re-evaluate the match", **adding a trigger tag to an existing open task dispatches it without a daemon restart**; a plugin's own end-of-run metadata write cannot re-trigger itself because the task is already in the runner's in-process claim set.

The repo ships three plugin entry points: `story_develop` (the real one, see [story-develop](story-develop.md)), `echo` (a zero-cost smoke test that writes `status="succeeded"` and exits — wire it to `trigger:echo` to exercise claim → run → complete) and `prd_decompose`, whose body is a **stub** that raises `NotImplementedError`.

---

## Readiness, claiming and admission

On a match the runner does not derive readiness itself. It asks Lithos's server-side ready frontier — `lithos_task_ready` narrowed to the route's tags and the task's project, with `lithos_task_blocked` as the other half of the partition when the page is full — so a task behind an open `blocks` predecessor, an unmet gate or a cancelled blocker is simply deferred. Undetermined answers are re-checked with backoff (60 s → 15 min) rather than dropped; nothing dispatches on a guess.

!!! note "Dependencies are edges, not metadata"
    Lithos rejects `metadata.depends_on` / `metadata.blocked_on` (`invalid_metadata_key`). Parallelism is the *absence* of a `blocks` edge. `project import` builds the graph from indentation; the runner reads it only through `lithos_task_ready`.

Once ready, the runner claims via `lithos_task_claim` (Lithos guarantees collision safety across hosts), spawns the plugin, renews the claim periodically, and waits for `result.json`. **Serial admission** applies to PR-producing routes (`completes_task = false`): a project's ready stories are admitted only while its open `pr` gates are under `[orchestrator].max_open_delivered_prs` (default 1; `max_open_delivered_prs_total`, default 3, is the backstop that posts `[AdmissionHeld]`). Held stories are released by `metadata.priority`, then first-asked order (ADR 0012). Both dials can be overridden per project in the project-context doc's metadata; `0` = unlimited.

Multiple hosts can run route-runners against one Lithos: each has its own `agent_id`, its own TOML (so its own `[projects.*]` checkouts) and claims competitively. There is no cross-host coordination.

---

## The plugin contract

A plugin is any subprocess that accepts three flags and writes one file:

```
<command> --task-json <path> --work-dir <path> --result-file <path>
```

`result.json` must be written atomically (temp file + fsync + rename) and validate against [`docs/result-schema.json`](https://github.com/agent-lore/lithos-loom/blob/main/docs/result-schema.json). Required: `schema_version` (const `1`), `task_id`, `status` (`succeeded` | `failed` | `interrupted`), `exit_code`.

```json
{
  "schema_version": 1,
  "task_id": "…",
  "status": "failed",
  "exit_code": 1,
  "run_id": "abc12345",
  "rounds": 5,
  "pr_url": null,
  "error": { "category": "agent", "message": "round 5: NOT approved (max_rounds)", "retriable": false },
  "escalation": { "reason": "max_rounds", "summary": "round 5: NOT approved (max_rounds)",
                  "brief": { "branch": "loom/us42", "rounds": 5, "cost_usd": 48.53 } }
}
```

What the runner does with `status`:

| `status` | Route default | Runner action |
|----------|---------------|---------------|
| `succeeded` | `completes_task = true` | `lithos_task_complete`; every task that completion unblocked is republished onto the bus so the next link in a chain dispatches immediately |
| `succeeded` | `completes_task = false` | Raise a **`pr` gate** from `pr_url` (a gate task joined to the story by a `waits_on_gate` edge), record `metadata.pr_gate_id`, release the claim and leave the story **open**. A success with no `pr_url` posts a loud `[Friction]` — nothing else guards against a re-run. |
| `failed` | — | Raise a **`human` gate** (`Needs human: <title>`, `metadata.escalation_reason` from the `escalation` block or `error.category`), write `metadata.loom_last_attempt:<route>`, post `[NeedsHuman]`, fire `[notifications]`, release. The story is structurally blocked until the operator completes the gate (= retry) or cancels the story (= abandon). |
| `interrupted` | — | Release with no finding. With a `resume.resume_after` block (a provider usage limit) the runner records `metadata.loom_resume:<route>` and re-dispatches at that time, up to 3 times, then escalates `resume_exhausted`. |
| missing / unknown | — | Escalate as `contract_violation`. A plugin killed on `max_runtime_seconds` escalates as `timeout`. |

Only `status`, `pr_url`, `run_id`, `error`, `escalation` and `resume` are acted on today; `artifacts`, `commits`, `spawned_tasks`, `metadata_updates`, `exit_code` and `error.retriable` are schema-validated but ignored by the runner. `retain_failed_workdirs = true` (default) keeps a failed run's work dir for triage; successful work dirs are reaped. The `loom_last_attempt:*` and `loom_resume:*` metadata namespaces are runner-owned — plugins must not repurpose them.

---

## Gates: how work waits for a human or a merge

Loom never parks state in private markers when Lithos can express it structurally. Two gate kinds, both `task_type="gate"` tasks joined to their story by a `waits_on_gate` edge, so the story is absent from `lithos_task_ready` until the gate resolves:

| Gate | `metadata.gate_type` | Raised when | Resolved by |
|------|----------------------|-------------|-------------|
| PR gate | `pr` | A `completes_task = false` run delivers a PR; `develop deliver` delivers a stopped run's branch | The [GitHub watcher](github-watcher.md#pr-gate-resolution) sees the PR merge: story completed first, then the gate, `[GateResolved]` posted. A PR closed unmerged or deleted converts into a `human` gate. |
| Needs-human gate | `human` (`raised_by="loom"`) | A run ends without delivering; a remediation budget is exhausted; a conflict cannot be resolved; a delivered PR dies | The operator **completes** the gate (tick in Obsidian, Lens, or `lithos_task_complete`) — that is the retry gesture; the route-runner's escalation resolver re-dispatches the story live. Cancelling the *gate* strands the story; cancel the *story* to abandon. |

`lithos-loom gates` lists every open gate with its type, the PR or escalation reason, the waiting story, and a health word (`ok` / `orphan` / `malformed` / `waiter-gone` / `waiter-resolved`). A delivered-but-unmerged PR's live state is derived onto the `pr` gate as `reconciliation_state` (`awaiting_review` · `reconciling` · `behind` · `resolving_conflict` · `gate_failed` · `needs_human` · `ready_to_merge`) by the watcher's sweep alone; Lens and the CLI only read it.

A restart replays every open task as `created`. A delivered story is deferred by its `pr` gate; a failed story is declined while its `loom_last_attempt` marker still matches an unedited task — edit the task (any write) or delete the marker key to re-dispatch.

---

## The event bus

Each child owns one `EventBus`. Events are frozen `(type, timestamp, payload)` records; payloads are the Lithos envelope (tasks) or `{id, title, path}` (note bootstrap — handlers re-fetch what they need).

| Event | Source |
|-------|--------|
| `lithos.task.{created,updated,claimed,released,completed,cancelled}` | `LithosEventStream` — bootstraps from `lithos_task_list(status='open')`, then streams `GET /events` with `Last-Event-ID` resume; cursor persisted under `<work_dir>/<child>/sse_cursors.json` |
| `lithos.note.{created,updated,deleted}` | `LithosNoteStream` — bootstraps from `lithos_list(path_prefix='projects/', tags=['project-context'])` |
| `obsidian.task.{status_changed,priority_changed,due_date_changed}` | `ObsidianFSWatcher` (250 ms poll of `tasks_file`) |
| `obsidian.note.modified` | `ObsidianDirWatcher` (body-only hash of `<projects_dir>/**/*.md`) |
| `github.issue.seen` | `GitHubIssueWatcher` (one per issue per poll) |

Event names are stable pre-1.0 (renaming one is a breaking change). Bootstrap-replayed events carry `origin="bootstrap"`; the runner's own synthetic nudges carry `resume`, `gate-resolved`, `ready-recheck` or `admission-recheck`.

**Subscriptions** are fire-and-forget handlers declared in TOML, each with a bounded queue, per-subscription retry (`attempts`, `exponential` | `linear` backoff) and a `[Friction]` finding on persistent failure (`on_persistent_failure = "friction"` | `"ignore"`). Filters: a structural `match.tags` superset test, then an optional `where` Python expression over `event` / `task`. Actions are **hand-wired by name** in the hosting child (ADR 0007), not discovered:

| Action | Child | Effect |
|--------|-------|--------|
| `obsidian-projection`, `obsidian-awaiting-review`, `obsidian-status-transition`, `obsidian-priority-changed`, `obsidian-due-date-changed`, `project-context-projection`, `note-push`, `task-archive` | obsidian-sync | See [Obsidian bridge](obsidian-bridge.md) |
| `github-issue-sync`, `github-issue-push` | github-watcher | Auto-wired; not declared in TOML. See [GitHub watcher](github-watcher.md) |
| `noop` | any | Logs at DEBUG — useful for tracing a filter |

---

## Finding prefixes

Every finding Loom posts starts with a stable bracketed prefix so operators and Lens can grep them:

| Prefix | Posted by | Meaning |
|--------|-----------|---------|
| `[Friction]` | any | A side effect failed past its retries, or a notable event (note-push conflict, a sink that could not fire) |
| `[NeedsHuman]` | route-runner, github-watcher | A `human` gate now blocks the story: reason, summary, run facts, gate id, the actions (and the `develop deliver <run>` command when a branch exists) |
| `[BlockerFailed]` | route-runner | Marker-only failure path: a misconfigured route, or an exit where the gate could not be raised |
| `[DevelopResult]`, `[ReviewDispute]`, `[BriefReview]` | story-develop plugin | The run's own outcome; a deadlocked coder/reviewer dispute; a brief recheck that appended facts |
| `[GateResolved]`, `[DeliveredPRClosed]` | github-watcher | PR merged (story completed); PR closed unmerged / deleted (converted to a `human` gate) |
| `[PRConflicted]`, `[MergeGateFailed]`, `[ConflictResolved]`, `[ExternalReview]` | github-watcher | PR maintenance on a delivered PR — see [GitHub watcher](github-watcher.md#pr-gate-resolution) |
| `[AdmissionHeld]` | route-runner | The project hit `max_open_delivered_prs_total`; dispatch is held |
| `[ManualDelivery]`, `[ConvergePushed]` | `develop deliver`, `develop converge-push` | A human-driven delivery or push, recorded on the story |
| `[ReopenRequested]` | obsidian-sync, github-watcher | A completed task was unticked in Obsidian, or its closed GitHub issue was reopened. Loom does not reopen tasks itself; this signals the intent. |
| `[LinkedIssueGone]` | github-watcher | The linked GitHub issue was deleted; pushes to it stop until the task is re-linked |

---

## What is not implemented

Stated so you do not go looking: the `prd-decompose` plugin body; application of `result.json` fields beyond those listed above; the resolved project entry inside `task.json`; startup reclaim of stale claims (they age out via Lithos's claim TTL); hot reload of the TOML; a persistent event log; a containerised daemon. PRDs for queued work live under [`docs/prd/`](https://github.com/agent-lore/lithos-loom/tree/main/docs/prd) in the repo and are not documented here.
