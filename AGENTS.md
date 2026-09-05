# lithos-docs Agent Guide

User/developer docs for [Lithos](https://github.com/agent-lore/lithos), built with MkDocs Material and published to https://getlithos.dev via GitHub Pages on every push to `main` (`.github/workflows/deploy.yml`). The site documents **current lithos `main`** — changes shipped after the latest tag get a small "since vX.Y.Z, unreleased" admonition.

## Done criteria

A docs change is not done unless both pass:

```bash
# 1. Strict build (fails on broken links/anchors/nav)
mkdocs build --strict

# 2. Drift check against lithos main's generated tool catalog
python3 scripts/check_drift.py
```

Local setup (uv venvs ship without pip — install via `uv pip`):

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements-docs.txt
.venv/bin/mkdocs build --strict     # or `mkdocs serve` to preview
```

## Sources of truth (in the sibling `lithos` repo)

Never transcribe from memory or from this site's own older pages — go to the code repo:

| Topic | Source |
|-------|--------|
| Tool list + signatures | `docs/generated/tool_catalog.md` — **generated and drift-checked in lithos CI**; the authoritative 37-tool catalog |
| Tool contracts / response shapes | `docs/SPECIFICATION.md` §5; §7 task-graph schema; §8 events/SSE; §9 CLI+config; §10 errors + short-ID rules |
| Config reference | `src/lithos/config.py` (`LithosConfig`) — the only complete field list, incl. `lcma.*` and `lcma.llm.*` |
| CLI commands/options | `src/lithos/cli.py` (the repo's own `docs/cli.md` has lagged before) |
| Metric names | `src/lithos/telemetry.py` — **dotted** OTEL names (`lithos.tool.calls`); Prometheus renders underscores |
| Error codes | `src/lithos/errors.py`, `src/lithos/envelopes.py`, spec §10.2 |
| Docker | `docker/docker-compose.yml` + `docker/Dockerfile` + `docker/run.sh` |
| Release history | git tags + GitHub releases (the repo's `CHANGELOG.md` is incomplete — it has no 0.3.x sections) |
| Agent-facing phrasing | `agent-skills/plugins/lithos/skills/lithos/references/*.md` — accurate, good prose to borrow |

## Site map

| Area | Files |
|------|-------|
| Tool reference | `docs/mcp-tools/` — 8 category pages: `knowledge-write` (write/note_update/delete), `knowledge-read` (read/search/list/tags/related), `retrieval` (retrieve/cache_lookup/node_stats), `graph-edges` (edge_upsert/edge_list/conflict_resolve), `tasks` (11 lifecycle tools), `task-graph` (6 graph tools + gates), `agents-findings`, `system` (stats + HTTP endpoints). A new tool goes in its category page **and** the tables in `mcp-tools/index.md`. |
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

`scripts/check_drift.py` (run by `.github/workflows/drift-check.yml` on PRs, pushes, and a Monday cron) fetches lithos main's `tool_catalog.md` and asserts: every catalog tool has a `` ## `tool` `` section under `docs/mcp-tools/`; no documented tool is absent from the catalog; every "N tools" claim equals the catalog count; and no stale markers (`lithos_links`, `--transport sse`, `GET /metrics`, …) appear outside the changelog. **The weekly cron failing is the "lithos moved, docs didn't" signal** — treat a red scheduled run as a docs-update task, not a flake.

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
- Keep the changelog historical — old sections state old facts and are excluded from the drift check; never "fix" them to current behaviour.
