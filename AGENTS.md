# lithos-docs Agent Guide

User/developer docs for the **Lithos ecosystem** — [Lithos](https://github.com/agent-lore/lithos) (the hub), [Influx](https://github.com/agent-lore/influx), [Loom](https://github.com/agent-lore/lithos-loom) and [Lens](https://github.com/agent-lore/lithos-lens) — built with MkDocs Material and published to https://getlithos.dev via GitHub Pages (`.github/workflows/deploy.yml`: every push to `main`, a `repository_dispatch` from a source repo, and a weekly schedule). One site, one tab per project; Lithos keeps the root URLs (`/getting-started/…`, `/mcp-tools/…`) and the siblings live under `/influx/`, `/loom/`, `/lens/`, with `/ecosystem/` for the cross-project pages.

The site documents **each project's current `main`**. Lithos changes shipped after the latest tag get a "since vX.Y.Z, unreleased" admonition; the siblings have no releases yet and each tab's index carries a status admonition (stable / pre-release) in a fixed shape — keep the four consistent.

## Done criteria

A docs change is not done unless all three pass:

```bash
# 0. Pull the build-time imports (gitignored; see sources.toml)
python3 scripts/sync_sources.py
# 1. Strict build (fails on broken links/anchors/nav)
mkdocs build --strict
# 2. Drift check: lithos tool catalog, imports, gitignore, stale markers
python3 scripts/check_drift.py
```

Local setup (uv venvs ship without pip — install via `uv pip`; both scripts need Python ≥ 3.11 for `tomllib`, so use the venv's interpreter):

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements-docs.txt
LITHOS_DOCS_SOURCES_ROOT=~/projects/lithos/code .venv/bin/python scripts/sync_sources.py   # sibling checkouts instead of GitHub
.venv/bin/mkdocs build --strict     # or `mkdocs serve` to preview
```

## Build-time imports (`sources.toml`)

Material the source repos already maintain in end-user form is **imported at build time, never copied**: the Lens user manual and its screenshots (→ `docs/lens/manual.md`, `docs/lens/screenshots/`), Loom's per-command CLI pages (→ `docs/loom/cli/*.md`) and the Influx runbook (→ `docs/influx/runbook.md`). `scripts/sync_sources.py` reads `sources.toml`, fetches from each repo's `main` (or from sibling checkouts with `LITHOS_DOCS_SOURCES_ROOT`), rewrites relative links (to a co-imported file → relative; anything else → a GitHub blob URL), prepends a "pulled from upstream" admonition, and writes the gitignored destinations. To add an import: add an entry to `sources.toml`, add the destination to `.gitignore`, reference it from `mkdocs.yml`. The drift check asserts every destination is gitignored and still exists upstream. **Never hand-edit an imported file; fix it in its repo.**

## Sources of truth

Never transcribe from memory or from this site's own older pages — go to the code repos.

### Lithos (`lithos` repo)

| Topic | Source |
|-------|--------|
| Tool list + signatures | `docs/generated/tool_catalog.md` — **generated and drift-checked in lithos CI**; the authoritative tool catalog (the drift check reads its count) |
| Tool contracts / response shapes | `docs/SPECIFICATION.md` §5; §7 task-graph schema; §8 events/SSE; §9 CLI+config; §10 errors + short-ID rules |
| Config reference | `src/lithos/config.py` (`LithosConfig`) — the only complete field list, incl. `lcma.*` and `lcma.llm.*` |
| CLI commands/options | `src/lithos/cli.py` (the repo's own `docs/cli.md` has lagged before) |
| Metric names | `src/lithos/telemetry.py` — **dotted** OTEL names (`lithos.tool.calls`); Prometheus renders underscores |
| Error codes | `src/lithos/errors.py`, `src/lithos/envelopes.py`, spec §10.2 |
| Docker | `docker/docker-compose.yml` + `docker/Dockerfile` + `docker/run.sh` |
| Release history | git tags + GitHub releases (the repo's `CHANGELOG.md` is incomplete — it has no 0.3.x sections) |
| Agent-facing phrasing | `agent-skills/plugins/lithos/skills/lithos/references/*.md` — accurate, good prose to borrow |

### Influx (`influx` repo)

| Topic | Source |
|-------|--------|
| Config fields and defaults | `src/influx/config.py` (`AppConfig` and section models); `influx.example.toml` is the annotated template but **omits `[lithos]`** |
| CLI commands, options, exit codes | `src/influx/main.py` (argparse; `EXIT_*` constants) — the README's list lags (no `migrate-notes`) |
| Admin HTTP API | `src/influx/http_api.py`; `docs/SPECIFICATION.md` §5 |
| Pipeline stages, note format, Lithos write handling, repair sweep | `docs/SPECIFICATION.md` §6–§11; `src/influx/run.py`, `cascade.py`, `lithos_client.py`, `note_merge.py`, `repair.py` |
| Inbox contract | `docs/plans/inbox.md`; `docs/adr/0002-inbox-submitter-overrides.md`; `src/influx/inbox.py`, `inbox_overrides.py`; the `influx-inbox` skill in lithos `agent-skills/plugins/influx-inbox/` |
| Metrics, telemetry env vars | `docs/SPECIFICATION.md` §13; `src/influx/metrics.py`, `telemetry.py` — the `[telemetry]` TOML section is validated but **not** what wires exporters; `INFLUX_OTEL_*` env vars are |
| Notifications | `docs/SPECIFICATION.md` §12; `src/influx/notifications.py`; `docs/AGENT_ZERO_RFC.md` |
| Docker | `docker/docker-compose.yml`, `docker/.env.example`, `docker/run.sh` — compose does not pass `LITHOS_URL`; the URL must be in `/data/influx.toml` |
| Runbook | `docs/operations/runbook.md` — imported |

### Loom (`lithos-loom` repo)

| Topic | Source |
|-------|--------|
| Architecture, projection rules, finding prefixes, Lithos prerequisites | `docs/SPECIFICATION.md` §2, §6–§8, §10 (414 KB, very long lines — grep it) |
| Config fields + defaults | `src/lithos_loom/config.py` dataclasses; `examples/lithos-loom.toml`; spec §3.1 lags (`pr_merge_poll_enabled`, `default_review_profile` missing there) |
| CLI | **Typer**, not Click: `src/lithos_loom/main.py` + `src/lithos_loom/cli/{task,project,obsidian_sync,develop}.py` + `src/lithos_loom/evals/*/cli*.py`; the README's subcommand table is incomplete |
| Per-command reference | `docs/cli/*.md` — imported |
| Plugin contract / `result.json` | spec §5; `docs/result-schema.json`; `src/lithos_loom/gates.py` (`ESCALATION_REASONS`) — spec §9.2 is older than §5.3 where they disagree |
| story-develop settings | spec §5.5; `src/lithos_loom/plugins/story_develop/{settings_resolver,profiles,personas,model_policy}.py` |
| Obsidian macros | `docs/macros/README.md` |
| Decisions as behaviour | `docs/adr/0001`–`0012` |
| Known stale spec text | §12 still lists the GitHub watcher as unimplemented and §1.2 denies plugin bodies exist — both shipped; `prd-decompose` **is** still a stub |

### Lens (`lithos-lens` repo)

| Topic | Source |
|-------|--------|
| User-facing behaviour | `docs/user-manual/manual.md` — imported; regenerated in that repo with `/regen-manual` (must be re-run after UI milestones; check `git log -- docs/user-manual` against recent commits) |
| Routes / views | `src/lithos_lens/*_routes.py`, `web.py`; templates under `src/lithos_lens/templates/` |
| Config | `lithos-lens.example.toml` (complete, annotated); `src/lithos_lens/config_schema.py`; env overrides in `config_env.py` |
| Write actions and the operator identity | `src/lithos_lens/operator.py`, `write_guards.py`, `write_routes.py`; `docs/prd/t3-curated-write-actions.md` — the README still says Lens is read-only; it is not |
| Lithos tool surface Lens was built against | `tests/contracts/_tools_snapshot.json` |
| Docker | `docker/docker-compose.yml`, `docker/.env.example`, `docker/run.sh` |

## Site map

| Area | Files |
|------|-------|
| Ecosystem | `docs/index.md` (home: Lithos hero + the four project cards), `docs/ecosystem/index.md` (how they fit), `docs/ecosystem/compatibility.md` (versions documented, minimum Lithos per sibling) |
| Influx | `docs/influx/` — index, getting-started, configuration, pipeline, inbox, cli, operations, changelog (+ imported `runbook.md`) |
| Loom | `docs/loom/` — index, installation, concepts, story-develop, obsidian-bridge, github-watcher, cli overview, changelog (+ imported `cli/*.md`) |
| Lens | `docs/lens/` — index, changelog (+ imported `manual.md`, `screenshots/`) |
| Tool reference | `docs/mcp-tools/` — 8 category pages: `knowledge-write` (write/note_update/delete), `knowledge-read` (read/search/list/tags/related), `retrieval` (retrieve/cache_lookup/node_stats), `graph-edges` (edge_upsert/edge_list/conflict_resolve), `tasks` (11 lifecycle tools), `task-graph` (7 graph tools + gates), `agents-findings`, `system` (stats + HTTP endpoints). A new tool goes in its category page **and** the tables in `mcp-tools/index.md`. |
| Concepts | `docs/concepts/` — overview, architecture, memory-model, **envelopes** (error contract, short IDs, migration notes) |
| Getting started | `docs/getting-started/` + `docs/index.md` (home) + `docs/cli.md` |
| Deployment | `docs/deployment/` — docker, self-hosted, observability |
| Changelog | `docs/changelog.md` — newest first, breaking changes lead each section, install snippets per release |

## Facts that are easy to get wrong

- **Transport is `http`, not `sse`** (renamed v0.3.2, no alias). One port serves `POST /mcp` (StreamableHTTP, primary) and `GET /sse` (legacy). Claude Code connects via `/mcp`; OpenClaw/Agent Zero examples use `/sse`.
- **There is no `GET /metrics`** — telemetry is OTLP push-only.
- **The shipped compose builds from source** (`image: lithos:local`, `pull_policy: never`, data at `/data`, default `LITHOS_DATA_PATH=./data`); the published `davesnowdon/lithos` image is the alternative path with different upgrade instructions.
- **Write-path envelope asymmetry**: `lithos_write`/`lithos_note_update` use `status="<code>"` (e.g. `status="version_conflict"`); every other tool uses `status="error"` + `code`. Error envelopes carry no `warnings`.
- **`metadata={}` asymmetry**: clears on `lithos_write`, no-op merge on `lithos_task_update`, rejected on `lithos_note_update`.
- **Models**: PyPI installs download sentence-transformers + spaCy models on first use; the Docker image bakes both in and starts offline.
- There is no `lithos --version`; `--telemetry-console` is a **global** CLI option, not a `serve` flag.
- Python floor is **3.12**.

## The drift check

`scripts/check_drift.py` (run by `.github/workflows/drift-check.yml` on PRs, pushes, and a Monday cron) fetches lithos main's `tool_catalog.md` and asserts: every catalog tool has a `` ## `tool` `` section under `docs/mcp-tools/`; no documented tool is absent from the catalog; every "N tools" claim equals the catalog count; and no stale markers (`lithos_links`, `--transport sse`, `GET /metrics`, …) appear outside the changelogs. It also checks the imports: every `sources.toml` destination is gitignored, and every upstream file it names still exists (so a renamed Loom CLI page or a dropped Lens screenshot fails the Monday run). **The weekly cron failing is the "a repo moved, docs didn't" signal** — treat a red scheduled run as a docs-update task, not a flake. The sibling sections are hand-written against `main`, so when Influx, Loom or Lens ships a user-visible change, the matching page here is a docs task even though no check fires.

A line that mentions a banned marker deliberately (migration notes, "there is no X") must carry an HTML comment containing `drift-allow`:

```markdown
... update any `lithos serve --transport sse` invocations. <!-- drift-allow -->
```

## Syncing after a lithos release

When a new lithos version is tagged:

1. Move the changelog's **Unreleased** section under a `## vX.Y.Z` heading (release date, GitHub/PyPI/Docker Hub links, install snippet); start a fresh Unreleased section if `main` is already ahead.
2. Remove the "since vX.Y.Z, unreleased" admonitions for features now released (grep for `unreleased`).
3. Run the drift check — it catches tool-surface changes; sweep the spec/config/CLI sources above for anything it can't see (response-shape changes, new config fields, CLI flags).
4. Update version-pinned examples (install snippets, `requires-python`) if they changed.

## PR conventions

- Feature branch off `main`, PR base `main`. **Do not stack PRs on other doc branches** — a stacked PR merged before its base lands in the wrong branch (it happened; repo now auto-deletes head branches, which limits but doesn't remove the hazard).
- Style: Material admonitions (`!!! note/tip/warning/danger`), content tabs (`=== "Docker"`), tables for enumerable facts. Version-scoped facts get a version admonition, not inline prose.
- Keep the changelogs historical — old sections state old facts and are excluded from the drift check; never "fix" them to current behaviour.
- A sibling page states what the code does on `main`; where a README or spec lags the code, document the code and say nothing about the lag unless an operator would hit it.
