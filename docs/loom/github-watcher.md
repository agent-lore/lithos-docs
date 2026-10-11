# GitHub watcher

The `github-watcher` child keeps GitHub issues and Lithos tasks aligned in both directions, and — for PRs that `story-develop` delivers — watches them to merge, keeps them landable, and ingests the reviews people leave on them. It runs on **one host only**.

## Enabling it

Two gates, one per host and one per project.

**Per host** — `[github_watcher]` present with `enabled = true`. The watcher resolves a bearer token from `gh auth token` at startup, so `gh` must be on PATH and logged in. There is no election: pick one host and leave the block out (or `false`) everywhere else.

```toml
[github_watcher]
enabled                     = true
poll_interval_seconds       = 60      # incremental issue polls
coord_doc_path              = "projects/_lithos-loom-internal/github-watcher-state.md"  # per-repo cursors, in Lithos
resolved_replay_days        = 7       # replay window for Lithos→GH mirroring at bootstrap; 0 disables
reconcile_interval_minutes  = 60      # the periodic sweep (below); 0 disables
pr_merge_poll_enabled       = true    # resolve `pr` gates on merge
external_reviews_enabled    = true    # ingest PR reviews/comments as [ExternalReview]
external_remediation_budget = 2       # autonomous `converge --from-github` rounds per PR; 0 disables
merge_gate_enabled          = true    # trial-merge re-gate when the base moves
conflict_resolve_enabled    = true    # `converge --resolve-conflicts` on a named conflict
trusted_bots                = ["copilot-pull-request-reviewer[bot]"]
```

**Per project** — metadata on the project-context doc, managed by the CLI (see [`project` GitHub subcommands](cli/project-github-repos.md)):

```bash
lithos-loom project add-github-repo my-project agent-lore/my-repo   # repeatable; a project may map several
lithos-loom project enable-github  my-project                        # sets github_watch_enabled = true
lithos-loom project disable-github my-project                        # keeps the repo list
lithos-loom project migrate-github-tags [--dry-run]                  # one-shot: legacy github-* tags → metadata
```

| Metadata key | Meaning |
|--------------|---------|
| `github_watch_enabled` | `true` enrols the project; takes effect mid-run without a restart |
| `github_repos` | `owner/name` list, each polled independently |
| `github_exclude_labels` / `github_exclude_authors` | Drop an issue **at import time only** (e.g. `dependabot[bot]`); already-linked tasks are never stranded by a later exclude |

---

## GitHub → Lithos

Each poll lists every open issue on the first pass (no cursor) and, thereafter, everything updated since the per-repo `updated_at` cursor — so closes on known issues surface alongside new opens. Pull requests are filtered out at parse time. The link between an issue and its task is a `<!-- lithos:<task_id> -->` marker written into the issue body:

| Situation | Action |
|-----------|--------|
| No marker, no task carries this URL, issue open | `lithos_task_create(title, description=body, tags=labels + ["github-issue"], metadata={project, github_issue_url, github_issue_number, github_labels, github_state_snapshot})`, then write the marker into the issue body (re-fetched immediately before the PATCH so a concurrent edit survives) |
| No marker, no task, issue closed | Skipped — historic closures are not backfilled |
| No marker, but a task carries `metadata.github_issue_url` for it | Re-write the marker; no duplicate task |
| Marker → open task | **Drift sync**: title, body (marker stripped), and labels (diffed against the `github_labels` snapshot, so operator-added Lithos tags survive) — one `task_update` per changed poll, zero round-trips when nothing changed |
| Marker → open task, issue closed as `completed` / `not_planned` | Drift sync + `lithos_task_complete` / `lithos_task_cancel` |
| Marker → terminal task, issue reopened | Post a one-shot `[ReopenRequested]` finding (de-duped on `github_state_snapshot`). Loom does not reopen the task itself. |
| Marker → missing task (force-deleted) | Create a fresh task and overwrite the stale marker |

Cursors and a per-repo set of issues whose dispatch failed persist in the coord doc (CAS-protected), so a restart between a partial reconciliation and its retry loses nothing. A 404 on a repo drops it from the in-memory watch list with a `[Friction]` log line until the metadata is fixed; a rate-limit response sleeps until `X-RateLimit-Reset`.

---

## Lithos → GitHub

The auto-wired `github-issue-push` handler consumes `lithos.task.*` events for tasks carrying `metadata.github_issue_url` (everything else is filtered at entry):

| Lithos event | GitHub action |
|--------------|---------------|
| `task.completed` | `PATCH state=closed, state_reason=completed` (unless already so) |
| `task.cancelled` | `PATCH state=closed, state_reason=not_planned` |
| `task.updated` (and bootstrap-replayed `task.created`) | `PATCH title` when it differs |

Pushes re-fetch the issue before every PATCH, so they are idempotent. Transient errors retry with exponential backoff (up to 8 attempts, ~3 minutes); auth and repo-404 errors are logged as `[Friction]` and dropped. Outages longer than the retry budget are caught by the **reconciliation sweep**: every `reconcile_interval_minutes` the child re-dispatches every open task plus those resolved within `resolved_replay_days` through the push handler. A linked issue that was deleted posts `[LinkedIssueGone]` once and writes a `github_issue_gone_url` marker that silences further pushes until the task is re-linked.

---

## PR-gate resolution

The same sweep is the home of every PR-maintenance behaviour on the `pr` gates the route-runner (or `develop deliver`) raises. For each still-open gate it reads `repo` / `pr_number`, finds the gated story through the `waits_on_gate` edge, fetches the PR and acts:

| PR state | Action |
|----------|--------|
| **Merged** | Complete the **story first**, then the gate; post `[GateResolved]`; nudge every task the story's completion unblocked so the route-runner picks it up |
| **Closed unmerged / deleted** | Convert the stranding into a loom `human` gate on the story (`pr_closed_unmerged` / `pr_gone`), post `[DeliveredPRClosed]` and `[NeedsHuman]` with the three choices (work landed elsewhere → complete the story; re-develop → complete the gate; abandon → cancel the story), then complete the `pr` gate — never cancel it |
| **Story already terminal** (completed by hand or via the issue mirror) | Complete the gate; the PR is the operator's now |
| **Still open** | Run the dispatchers below, then write `reconciliation_state` / `reconciliation_detail` / `reconciliation_since` on the gate — the one place Lens, `lithos-loom gates` and you read "where is this PR right now" |

The dispatchers, each gated by a host dial and a per-project `develop_*` opt-out on the context doc, each spawning a Loom CLI command as a crash-isolated subprocess and recording a URL-scoped marker on the gate so nothing runs twice on the same inputs:

| Behaviour | Trigger | Host dial / project key | Outcome |
|-----------|---------|-------------------------|---------|
| **Landability** | every sweep | — | GitHub reports a conflict → one-shot `[PRConflicted]` per `(head, base)` |
| **External-review ingestion** | new reviews, inline comments or Conversation-tab comments | `external_reviews_enabled` | `[ExternalReview]` on the story; pure approvals are listed but never remediated; high-water marks on the gate de-dup |
| **Autonomous remediation** | a batch with at least one **trusted** item (allowlisted bot, or a human with repo write/admin) | `external_remediation_budget`, `trusted_bots` / `develop_external_review_converge` | `develop converge <pr> --from-github --story <id>`; one in flight globally; the per-PR round counter never resets on Loom's own pushes and resets on a human push; exhaustion raises a `remediation_exhausted` human gate |
| **Base-move re-gate** | `(head, base, settings)` changed | `merge_gate_enabled` / `develop_merge_gate` | `develop merge-gate <pr> --story <id>`: green and behind → merge commit pushed (append-only); red → `[MergeGateFailed]`; conflict → paths added to `[PRConflicted]` |
| **Conflict resolver** | the re-gate named a conflict | `conflict_resolve_enabled` / `develop_conflict_resolve` | `develop converge <pr> --resolve-conflicts` once per sha pair; pushed → `[ConflictResolved]`; unresolved → `conflict_unresolved` human gate |

All of them hold each other per PR (any one may push to the branch), are refused before any subprocess when the mapped checkout's `origin` does not match the gate's repo, and fail **closed** on an unreadable project doc. `lithos-loom drain` lets a sweep in flight finish and refuses new dispatch; a round the daemon itself kills at shutdown is refunded.

!!! note "Where the state lives"
    Findings are history. The current state of a delivered PR is the set of flat, `metadata_match`-queryable keys the sweep alone writes on its `pr` gate (`reconciliation_state`, `pr_landability`, `merge_gate`, `conflict_resolve`, `external_remediation`, `external_review_seen`, …). The route-runner, Lens and the CLI read them; a webhook could too.
