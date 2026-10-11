# Changelog

Loom has **no tagged release yet**. The package version in `pyproject.toml` is `0.1.0` and the only tags on the repo are `eval/*` baselines for the review eval harness. History lives in the commit log and the closed pull requests of [agent-lore/lithos-loom](https://github.com/agent-lore/lithos-loom); this page describes what `main` currently is, not a release sequence.

---

## Unreleased (`main`)

**What ships today** — everything these pages document:

- **Route-runner.** TOML-configured routes matched by tag superset; server-side readiness through Lithos's task graph; collision-safe claiming; the `result.json` plugin contract; serial admission per project; first-class `pr` and `human` gates with `[NeedsHuman]` escalation, push notifications (`[notifications]`), durable resume after a usage limit, and a `drain` that restarts without spending a round.
- **story-develop.** Persistent coder session + reviewer panel + deterministic check gate in docker; review profiles (`minimal` / `standard` / `thorough`) and canonical personas; explicit-model policy; per-round checkpoints and resume after a host death; PR delivery with fenced untrusted text; brief review at dispatch (opt-in).
- **On-demand develop CLI.** `review`, `converge` (panel, `--from-github`, `--resolve-conflicts`), `merge-gate`, `deliver`, `converge-push`, `resume`, `brief-review`, plus `list` / `attach` / `dump` / `prune` over run state.
- **Obsidian bridge.** Task inbox projection with bidirectional tick / priority / due-date edits, project-context docs with conflict-safe body push, per-project task archive, `project import` / `regenerate-done`, and the `capture-task` / `create-project` Templater macros.
- **GitHub issue watcher.** Bidirectional issue ↔ task mirroring with drift sync and reopen detection; PR-gate resolution on merge; landability, external-review ingestion, budgeted autonomous remediation, base-move re-gate, conflict resolution, and a derived `reconciliation_state` on every delivered PR's gate.
- **Evals.** `eval review` / `rescore` / `triage` / `resolve`.

**Known stubs and gaps** — see [Concepts → What is not implemented](concepts.md#what-is-not-implemented): the `prd-decompose` plugin body, `result.json` fields beyond `status` / `pr_url` / `run_id` / `error` / `escalation` / `resume`, hot reload of the TOML, startup reclaim of stale claims, a persistent event log, a container image.

**Compatibility policy (pre-1.0)** — from `docs/SPECIFICATION.md` §1.3: the TOML schema may change with a documented migration; bus event names are stable; `result.json` carries a `schema_version` (currently `1`) that bumps on incompatible change; the vault file layout (`_lithos/tasks.md`, `_lithos/awaiting-review.md`, `_lithos/projects/<slug>/…`, `_lithos/conflicts/…`) is stable.

!!! note "Requires a recent Lithos"
    Loom's boot gate refuses a Lithos server without the task-graph extension (first-class edges, `lithos_task_ready` / `lithos_task_blocked`, gate tasks). Server-side readiness, `pr` / `human` gates and edge-based `project import` all depend on it; the pre-edge `metadata.depends_on` scheme is gone and the key is rejected by Lithos.

---

## Following changes

Until Loom tags a release, the places that answer "what changed":

| Where | What it tells you |
|-------|-------------------|
| [Commits on `main`](https://github.com/agent-lore/lithos-loom/commits/main) and [merged PRs](https://github.com/agent-lore/lithos-loom/pulls?q=is%3Apr+is%3Amerged) | Every behaviour change lands as a PR; commit subjects follow `type(scope): summary` |
| [`docs/SPECIFICATION.md`](https://github.com/agent-lore/lithos-loom/blob/main/docs/SPECIFICATION.md) | Updated in the same PR as the code; the header carries a date and "Status: Aligned with Implementation" |
| [`docs/adr/`](https://github.com/agent-lore/lithos-loom/tree/main/docs/adr) | Twelve accepted decision records, from where GitHub-watch config lives (0001) to serial-admission release order (0012) |
| `eval/*` tags | Pinned baselines for `eval review`, not releases |

The per-command pages under [CLI](cli.md) are imported from the repo at every site build, so they track `main` automatically; the hand-written pages here are refreshed by hand and may lag a `main` that moves daily.
