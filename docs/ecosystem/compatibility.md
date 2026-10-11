# Compatibility

The four projects version independently. This page records what each one needs from Lithos, and which versions these pages were written against, so that a mismatch is something you can look up rather than discover.

## Versions these pages describe

| Project | Documented from | Version on that branch | Release state |
|---------|-----------------|------------------------|---------------|
| Lithos | `main`, with "since vX.Y.Z, unreleased" admonitions where `main` is ahead of the latest tag | 0.6.0 | Tagged releases on GitHub, PyPI (`lithos-mcp`) and Docker Hub |
| Influx | `main` | 0.1.0 | No tagged release yet; stable in daily use |
| Loom | `main` | 0.1.0 | No tagged release yet (only `eval/*` tags); under active development |
| Lens | `main` | 0.5.0 | No tagged release yet; under active development |

The sibling sections are refreshed whenever their repos move: the Lens manual and the Loom per-command CLI pages are pulled straight from those repos at build time, and a weekly drift check fails when any imported file disappears upstream.

## What each project needs from Lithos

| Project | Needs from Lithos | Minimum Lithos |
|---------|-------------------|----------------|
| **Influx** | `lithos_write` with the canonical envelope (`status="version_conflict"` on CAS failure), `lithos_search`, `lithos_task_list`/`lithos_task_claim`/`lithos_task_complete` with task `metadata` for the inbox | **0.4.0** — the canonical envelope Influx's write handling is built on |
| **Loom** | `GET /events` with `task.*` and `note.*` events; `lithos_task_create(metadata=...)` in one call; task `metadata`; `lithos_task_blocked`/`lithos_task_ready` and blocking edges; gates (`pr`, `human`); `lithos_write(id=..., expected_version=...)`; MCP over the legacy `/sse` endpoint | **0.5.0** — the first release whose `/events` stream carries the `note.*` events the Obsidian bridge subscribes to |
| **Lens** | The task graph tools (`lithos_task_ready`, `lithos_task_blocked`, `lithos_task_children`, `lithos_task_status`), `lithos_edge_list` for the knowledge graph, `lithos_finding_list`, `lithos_agent_list`, `lithos_task_reopen`, `/events`, MCP over `/sse`. Lens pins the exact tool surface it was built against in `tests/contracts/_tools_snapshot.json` and verifies it against a live server with `make contracts-verify` | **0.5.0** — `/events` as above; the contract snapshot is the precise statement and is refreshed against the Lithos Lens was built with |

!!! tip "Upgrading Lithos"
    Upgrade Lithos first and keep the others on their current versions: every sibling tolerates a newer Lithos, none tolerates an older one than the row above. After a Lithos release, the [changelog](../changelog.md) lists breaking changes at the top of each section; check it against this table before upgrading a host that runs Loom.

## What they need from each other

- **Loom ↔ Lens**: nothing at the API level. Lens reads Loom's work through Lithos (findings prefixed `[DevelopResult]`, `[GateResolved]` and so on, task metadata such as `develop_pr_url`, `pr` gates), so a Loom that changes those prefixes or keys changes what Lens shows.
- **Influx ↔ Lens**: Lens's knowledge pages read whatever Influx writes; the `ingested-by:influx` tag and the `influx` namespace are what you filter by.
- **Influx ↔ Loom**: none. Submitting to the Influx inbox is an ordinary Lithos task with `influx:inbox` metadata, which any agent or Loom route can create.
