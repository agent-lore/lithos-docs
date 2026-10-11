# story-develop

`story-develop` is the one shipped plugin body: it turns a Lithos task ("story") into a reviewed branch and an open pull request. It replaces the Ralph++ fresh-process-per-turn loop with a **persistent, dialogue-based cycle** — one coder session that both implements and fixes, an N-reviewer panel, and a deterministic check gate, all running in docker containers from a sandbox image.

```
claim → worktree off origin/main → round 1: coder implements, commits
      → gate: check-set on the committed tree (test, lint, typecheck, …)
      → panel: each reviewer writes a handoff with addressable findings
      → round n: coder fixes / disputes, commits → gate → panel …
      → approved (every reviewer LGTM, or only findings below its threshold)
      → push branch, open PR, request operator review → result.json {succeeded, pr_url}
```

Every state the loop needs is on disk under `<work_dir>/<task_id>/<run_id>/` (per-round `handoff/` files, a per-round `checkpoint` in `state.json`, `conversation.md` at the end) and on the Lithos task (`develop_*` metadata, a `[DevelopResult]` finding).

---

## Invocation

In daemon mode the route passes the runner's tokens; `--repo {{repo}}` resolves per task from `[projects.<slug>].repo`, so one route serves every project:

```
uv run python -m lithos_loom.plugins.story_develop \
    --task-json {{task_json}} --work-dir {{work_dir}} --result-file {{result_file}} --repo {{repo}}
```

The task's title, body and `metadata.acceptance_criteria` are the brief. The same module runs standalone against a task id (`--repo … --task-id <uuid>`) for hand-driven runs; the on-demand CLI surfaces below reuse its loop.

**Idempotency.** A daemon run that ends `succeeded` records its `result.json` under the task id; a later run under the same key replays that payload and exits 0 without a second agent loop or a second PR.

---

## Configuration layering

Reviewer and gate settings live on the **project-context doc's metadata** (`projects/<slug>/<slug>-project-context.md` in Lithos), overridable per task on the task's `metadata`, with route flags and the host TOML as fallbacks. Resolution is first match wins:

| Knob | Order |
|------|-------|
| coder model | `task.develop_model` → `develop_coder.model` → `--coder-model` → `[story_develop].default_models[<tool>]` → **error** |
| coder effort | `task.develop_effort` → `develop_coder.effort` → `--coder-effort` → agent default |
| reviewer model | `develop_reviewers[].model` → `--reviewer-model` → `default_models[<tool>]` → **error** |
| sandbox image | `task.develop_image` → `develop_image` → `--image` → `ralph-sandbox:latest` |
| test command | `task.develop_test_command` → `develop_test_command` → `--test-command` → per-ecosystem auto-detection |
| review profile | `task.develop_review_profile` → `develop_review_profile` → `[story_develop].default_review_profile` → `standard` |

!!! warning "Models must be explicit"
    An agent still on `model=None` after every layer **fails the run closed before any container starts** — there is no fallback to the sandbox CLI's built-in default, which is recorded nowhere and drifts with image rebuilds. Set `[story_develop.default_models]` for every tool (`claude`, `codex`) your agents run on.

A project doc's frontmatter, by example:

```yaml
develop_image: ghcr.io/acme/dev:2026-06
develop_test_command: make check            # trusted verbatim; no probing
develop_review_profile: thorough
develop_coder: { model: sonnet, effort: medium }
develop_default_reviewers: [correctness, security, architecture]
develop_check_commands: { typecheck: "make typecheck" }
develop_generated_paths: ["docs/generated"]
develop_regenerate_command: make diagrams
develop_max_rounds: 8
develop_max_cost_usd: 60
```

`effort` is a level (`low` / `medium` / `high` / `xhigh` / `max`), not a token budget; each engine maps it onto its own flag. Each agent's `tool` is `claude` or `codex`, choosable independently per coder and per reviewer.

---

## Review profiles and personas

A **Review Profile** bundles a reviewer panel, a deterministic check-set (each check `required` / `informational` / `off`) and the blocking policy — the one dial for review strength:

| Profile | Panel | Required checks | Informational |
|---------|-------|-----------------|---------------|
| `minimal` | gate only | `format`, `lint`, `test` | — |
| `standard` (default) | correctness + security | + `typecheck` | `sast` |
| `thorough` | + architecture, test-quality, dependency-hygiene | + `sast`, `dep-audit`, `coverage` | `semgrep` |

Check commands are auto-detected per ecosystem (Python / Node / Rust / Go) unless the project declares them; a code repo whose ecosystem *expects* a check it cannot run is **expected-but-absent** and a required check there blocks rather than passes silently. `develop_parity_command` (e.g. `make check`) adds a required `repo-parity` check that runs the repo's aggregate verification once on the approval candidate.

Canonical reviewer personas are opt-in by name in `develop_default_reviewers` (or a task's `metadata.reviewers`) and carry their own engine, severity floor and focused prompt: `correctness` (codex, blocks on major), `security` (claude at `xhigh`, blocks on minor), `architecture`, `test-quality`, `dependency-hygiene`. A `develop_reviewers` pool entry of the same name overrides the canonical one.

Findings are first-class: each has a stable id carried across rounds, a severity, a status (`open` / `fixed` / `accepted` / `disputed` / `needs-decision` / `out-of-scope` …) and the coder's per-finding response. Gate-produced findings (`gate/<check>-NNN`, e.g. from ruff) sit in the same ledger and cannot be waved away by the coder. A passing reviewer handoff must also carry a `## Criteria` map — one `met` / `deferred` verdict per acceptance criterion with evidence and the proving test — so approval means *done*, not merely *sound*.

---

## How a run ends

| `develop_status` | Meaning | What the runner does |
|------------------|---------|----------------------|
| `approved` | Panel LGTM and gate green; PR pushed and opened | `succeeded` → `pr` gate on the story, task left open for human merge |
| `max_rounds`, `stalled`, `disputed`, `needs_decision`, `cost_exceeded` | A verdict on the **work** | `failed` → `human` gate with that reason; completing the gate re-develops from scratch, or `develop deliver <run>` ships the branch as is |
| `infra_failed` | An auth / transport / spawn failure persisted through its retries | `failed`, reason `infra`; the gate names the host action, and completing it **resumes** the run from its last committed round |
| `interrupted` | Provider usage limit, pause budget exhausted | Re-dispatched at `resume_after`, continuing the checkpointed branch |

Every agent turn passes through one failure classifier (`usage_limited`, `auth_failed`, `transient_infra`, `oom_or_spawn`, `timeout` / `agent_error`) with a per-class retry table; a reviewer or coder turn that died *after* writing a valid handoff proceeds on that artifact. A stopped run's branch and rounds are never discarded silently: `develop list` / `attach` / `dump` inspect them, `develop resume` continues one by hand, and `develop prune` removes finished run dirs.

The PR body publishes the story description, acceptance criteria and review verdicts; text Loom did not author (an issue reporter's body, the coder's quote) is fenced, and the PR title is sanitised so a mirrored issue title cannot smuggle `Closes #N` into a squash-merge commit. With `[story_develop].operator_github_login` set, the operator is requested as reviewer (or assigned, when they authored the PR) so GitHub's own notifications fire.

---

## On-demand surfaces

These reuse the same panel, gate and loop primitives, and each has a full reference page:

| Command | What it does |
|---------|--------------|
| [`develop review`](cli/review.md) | **Review-only mode**: panel + gate against an existing PR, `base..head` range or branch; no coder, no push; non-zero exit when blocking |
| [`develop converge`](cli/converge.md) | Converge an existing PR to review-green: intake review, then a coder fix loop on the PR branch, then a leased fast-forward push. `--from-github` ingests external review comments (trust-filtered and triaged) instead of Loom's panel; `--resolve-conflicts` composes a merge with the base |
| [`develop merge-gate`](cli/merge-gate.md) | Zero-token trial merge of the base's current tip plus the project's current check-set; green and behind → the merge commit is pushed; a conflict names the paths |
| [`develop deliver`](cli/deliver.md) | Push a stopped run's branch, open or adopt its PR, raise the `pr` gate and retire the needs-human gate — the operator's third choice beside "re-develop" and "abandon" |
| [`develop converge-push`](cli/converge-push.md) | Report an exhausted converge run's unpushed rounds and, with `--yes`, push them as a human push |
| [`develop resume`](cli/resume.md) | Continue a run whose host died mid-loop from its checkpoint, leaving a local branch |
| [`develop brief-review`](cli/brief-review.md) | One read-only agent turn that drafts a story's brief-review addendum (scope cuts, facts, decisions) against the commit a coder would start from |

The GitHub watcher dispatches `merge-gate`, `converge --from-github` and `converge --resolve-conflicts` itself on delivered PRs — see [PR-gate resolution](github-watcher.md#pr-gate-resolution). All of these need `docker`, the agent CLIs and `gh` on the host; none run in the repo's hermetic `make check`.

**Brief review at dispatch** (`develop_brief_review: true` on a project; off by default) holds a story that carries `metadata.prd` behind a `Brief review: <story>` gate until the operator approves the drafted addendum, which is then appended to the story verbatim before the coder is cut at that exact commit.

---

## Evals

`lithos-loom eval review` is a seeded-defect benchmark for the reviewer panel (catch rate, severity correctness, false positives, each with a Wilson 95% CI over K runs); `eval rescore` re-scores a retained report dir offline; `eval triage` and `eval resolve` benchmark the external-review triage step and the conflict-resolution path. Cases live under `evals/` in the repo; all are host-only and run on demand.
