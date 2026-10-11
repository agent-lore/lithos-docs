# CLI Reference

The `lithos-loom` binary is one [Typer](https://typer.tiangolo.com/) app. Every command accepts `--config / -c <path>` to bypass [config discovery](installation.md#configure); commands that emit data accept `--format / -f text|json`. Exit codes follow one convention: `0` success, `1` operational failure (Lithos unreachable, config failed to load, slug collision, partial import), `2` input validation failure (bad flag combination, unknown project, malformed input). Every command has `--help`.

This page is the map. The commands marked **→ reference** have a full per-command page pulled from the Loom repo's `docs/cli/` at build time, so it cannot lag the code.

---

## Daemon

| Command | What it does |
|---------|--------------|
| `lithos-loom run [--dry-run]` | Start the daemon: pidfile lock, task-graph boot gate, orphan-container reap, then the supervisor and its children. `--dry-run` is shorthand for `validate-config --dry-run`. |
| `lithos-loom drain [--timeout S]` | Signal the running daemon to finish in-flight runs and exit — the restart that spends nothing. Exit `0` daemon gone, `1` nothing to signal, `2` timed out still draining. |
| `lithos-loom doctor` | PASS / FAIL probes: vault writability, the Lithos task-graph extension (the same probe `run` gates on), and TOML projects vs Lithos project-context docs. |
| `lithos-loom validate-config [--dry-run]` | Parse and typecheck the TOML; list projects, routes and subscriptions. `--dry-run` polls Lithos and shows, per open task, which route would claim it, which are `deferred (<reason>)`, plus orphan tasks and dead config. |
| `lithos-loom config --show` | Print the merged effective config (confirms which file discovery picked). |
| `lithos-loom gates [--shadow]` | Read-only inventory of every open gate: type, PR or escalation reason, waiting story, and health (`ok` / `orphan` / `malformed` / `waiter-gone` / `waiter-resolved`). `--shadow` reports the shadow auto-merge record instead. |

---

## `task`

| Command | What it does |
|---------|--------------|
| `lithos-loom task create --project S --title T [--brief] [--scheduled YYYY-MM-DD] [--priority] [--tags a,b] [--target-file P \| --no-insert]` | Create a Lithos task and print its projected Tasks-plugin line (default), append it to a file, or print only the id (`--no-insert`, what the capture macro uses). |

---

## `project`

| Command | What it does |
|---------|--------------|
| `lithos-loom project list [--source lithos\|toml]` | Projects with status overlay: slug, `active` / `archived`, repo path. `-f json` emits the slug array the capture macro consumes. |
| `lithos-loom project create --title T [--slug S] [--tags] [--body \| --body-file]` | Create a project-context doc at `projects/<slug>/<slug>-project-context.md`. |
| `lithos-loom project import <file> [--slug] [--tasks-only] [--no-tasks] [--force-tasks] [--dry-run] [--yes]` | Adopt an existing Markdown file as a project and extract its `- [ ]` lines as a task graph. **→ reference:** [`project import`](cli/project-import.md) |
| `lithos-loom project regenerate-done --slug S [--dry-run] [--yes]` | Rebuild `<slug>-done.md` from every resolved task in Lithos. **→ reference:** [`project regenerate-done`](cli/project-regenerate-done.md) |
| `lithos-loom project add-github-repo S owner/name` / `remove-github-repo` | Map / unmap a repo for the issue watcher (a project may map several). **→ reference:** [`project` GitHub subcommands](cli/project-github-repos.md) |
| `lithos-loom project enable-github S` / `disable-github S` | Toggle `github_watch_enabled`; disabling keeps the repo list. **→ reference:** same page |
| `lithos-loom project migrate-github-tags [--dry-run]` | One-shot migration of legacy `github-*` tags to metadata. **→ reference:** same page |

---

## `obsidian-sync`

| Command | What it does |
|---------|--------------|
| `lithos-loom obsidian-sync show` | Print the resolved `[obsidian_sync]` block. The macros call it with `-f json` to find `tasks_file` and `projects_dir`. |

---

## `develop`

Observability and on-demand entry points for [story-develop](story-develop.md) runs. Everything below `prune` needs `docker`, the agent CLIs and `gh` on the host.

| Command | What it does |
|---------|--------------|
| `lithos-loom develop list` | Table of inspectable runs under `work_dir`: run id, task, current round, active agent, PR, last activity. |
| `lithos-loom develop attach <run\|task> [--once\|--wait\|--stream]` | Follow a live run, printing each handoff as it lands, through PR delivery to a one-line outcome. |
| `lithos-loom develop dump <run\|task>` | Print the assembled conversation log. |
| `lithos-loom develop prune [--dry-run]` | Delete the run dirs and on-demand worktrees of **finished** runs; anything it cannot classify is kept and named. |
| `lithos-loom develop review <pr\|range\|branch>` | Review-only mode: panel + gate on an existing change, no coder. **→ reference:** [`develop review`](cli/review.md) |
| `lithos-loom develop converge <pr> [--from-github] [--resolve-conflicts]` | Converge an existing PR to review-green with a coder fix loop, then push. **→ reference:** [`develop converge`](cli/converge.md) |
| `lithos-loom develop merge-gate <pr>` | Trial-merge the base's current tip and run the current check-set; zero agent tokens. **→ reference:** [`develop merge-gate`](cli/merge-gate.md) |
| `lithos-loom develop deliver <run\|task> [--converge] [--no-gate] [--dry-run]` | Push a stopped run's branch, open or adopt its PR, raise the `pr` gate, retire the needs-human gate. **→ reference:** [`develop deliver`](cli/deliver.md) |
| `lithos-loom develop converge-push <run\|pr> [--yes] [--complete-gate]` | Report an exhausted converge run's rounds and, on `--yes`, push them. **→ reference:** [`develop converge-push`](cli/converge-push.md) |
| `lithos-loom develop resume <run\|task> [--dry-run]` | Continue a run whose host died mid-loop from its checkpoint. **→ reference:** [`develop resume`](cli/resume.md) |
| `lithos-loom develop brief-review <story> [--delta-from REF]` | Draft a story's brief-review addendum with one read-only agent turn. **→ reference:** [`develop brief-review`](cli/brief-review.md) |

---

## `eval`

Benchmarks for the review and remediation machinery, all host-only and on demand. Cases live under `evals/` in the repo; see [`docs/SPECIFICATION.md` §4.16–§4.19](https://github.com/agent-lore/lithos-loom/blob/main/docs/SPECIFICATION.md) and [ADR 0005](https://github.com/agent-lore/lithos-loom/blob/main/docs/adr/0005-review-correctness-eval-harness.md).

| Command | What it does |
|---------|--------------|
| `lithos-loom eval review [--case ID] [-k N] [--bar F]` | Seeded-defect benchmark of the reviewer panel: catch rate, severity correctness and false-positive rate over K runs, each with a Wilson 95% CI. |
| `lithos-loom eval rescore <report-dir> [--judge-repeats N]` | Re-score a retained report dir offline (judge calls only, no reviewer runs); measures judge variance. |
| `lithos-loom eval triage [--case ID] [-k N]` | Benchmark the external-review triage step on known verdicts. |
| `lithos-loom eval resolve [--case ID] [-k N]` | Benchmark `converge --resolve-conflicts` on real conflicting merges against an executable oracle. |

---

## Plugin entry points

Not `lithos-loom` subcommands, but the modules a route's `command` invokes:

| Module | Status |
|--------|--------|
| `python -m lithos_loom.plugins.story_develop` | Shipped. Daemon mode with `--task-json`; standalone with `--repo … --task-id <uuid>`. |
| `python -m lithos_loom.plugins.echo` | Shipped smoke test: writes `status="succeeded"` and exits. |
| `python -m lithos_loom.plugins.prd_decompose` | **Stub** — raises `NotImplementedError`. |
