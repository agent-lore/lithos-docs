# Influx

Influx is the ingestion side of the Lithos ecosystem. It collects research and technical content from arXiv and RSS/Atom feeds, scores each candidate against your **interest profiles** with an LLM, enriches the ones that clear a threshold, archives the source material locally, and writes a canonical Markdown note into [Lithos](../index.md) over MCP. Agents can also hand it individual URLs or PDFs through the [inbox](inbox.md).

!!! info "Status: stable, documents `main`"
    Influx is in day-to-day use and its surfaces change slowly. There is no tagged release yet (package version 0.1.0). These pages describe the current `main` branch of [agent-lore/influx](https://github.com/agent-lore/influx).

---

## How it fits the ecosystem

```
arXiv / RSS feeds ─┐
                   ├─▶ Influx ──lithos_write──▶ Lithos ◀── agents (Claude Code, Agent Zero, …)
agent inbox tasks ─┘      │                       ▲
                          └──lithos_retrieve──────┘  related_to / builds_on edges
```

Influx is a **write-mostly Lithos client**. It keeps no knowledge store of its own: every note lands in Lithos as an ordinary document (`namespace: influx`, tagged `ingested-by:influx`), readable by any agent through the normal [MCP tools](../mcp-tools/index.md). After each write it calls `lithos_retrieve` and upserts `related_to` and `builds_on` graph edges, so ingested papers join the knowledge graph immediately.

Influx talks to Lithos over the legacy `/sse` endpoint (the only transport its client supports) and registers as agent `influx` (`influx-inbox` for inbox work).

What Influx is **not**: a feed reader UI, a standalone knowledge base, or a multi-process service. It is a single Python process with an in-process scheduler and a loopback-only admin API.

---

## What a run does

Every scheduled tick runs one **Run** per profile, in config order:

1. **Repair** — re-visit notes tagged `influx:repair-needed` and retry the stage that failed last time.
2. **Feedback** — pull recent operator-rejected items from Lithos into the filter prompt as negative examples.
3. **Acquire** — fetch candidates from each source, score them in batches with the `filter` model slot, download and archive the ones that pass.
4. **Ingest** — per item: dedup against Lithos, run the tiered enrichment cascade (summary → full text → deep extraction), render the note, write it, wire graph edges.
5. **Finalise** — record the outcome in the local run ledger and fire configured webhooks.

The [Pipeline](pipeline.md) page walks through each stage as the code implements it.

---

## Pages

| Page | What it covers |
|------|----------------|
| [Getting Started](getting-started.md) | `uv sync`, a first `influx.toml`, pointing at Lithos, first run, Docker |
| [Configuration](configuration.md) | Every `influx.toml` section and field with defaults, plus environment overrides |
| [Pipeline](pipeline.md) | Sources, profiles, filtering, enrichment tiers, archiving, notes, Lithos writes, repair |
| [Inbox](inbox.md) | Submitting URLs and PDFs as `influx:inbox` Lithos tasks; `force` / `tier` overrides |
| [CLI](cli.md) | `influx validate-config / serve / run / backfill / migrate-notes` and the operator scripts |
| [Operations](operations.md) | Admin HTTP API, readiness, run ledger, logging, OTEL metrics, notifications |
| [Runbook](runbook.md) | The operator runbook, imported from the Influx repo at build time |
| [Changelog](changelog.md) | Current state of the unreleased `main` branch |

---

## Requirements at a glance

| Component | Requirement |
|-----------|-------------|
| Python | 3.12 (`>=3.12,<3.13`) |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Lithos | A running Lithos server exposing the `/sse` endpoint (see [Lithos installation](../getting-started/installation.md)) |
| LLM provider | Any OpenAI-compatible `/chat/completions` endpoint with JSON mode (OpenAI, OpenRouter, Ollama, …) |
| Disk | An archive directory for fetched PDFs/HTML and a state directory for the run ledger |

---

## Typical deployment

One Influx process per environment, next to the Lithos it writes into:

- `influx serve` runs under Docker (`docker/run.sh <env> up`) or directly from a `uv` checkout, with `influx.toml` on a mounted data volume, an archive volume for fetched documents, and a state volume for the run ledger.
- The admin API stays on loopback; operators drive it with `influx run` / `influx backfill`, `curl`, and the `scripts/influx-*.py` helpers.
- Scheduled runs fire once a day by default (`schedule.cron`), and the optional inbox tick polls Lithos every five minutes for agent submissions.
- Telemetry, when enabled, is pushed to the same OTEL collector as Lithos.

---

## Source repository

Code, issues and the full specification live at [github.com/agent-lore/influx](https://github.com/agent-lore/influx). The documents these pages are written from:

- `docs/SPECIFICATION.md` — the system contract, kept aligned with the implementation
- `influx.example.toml` — the annotated configuration template
- `docs/plans/inbox.md` and `docs/adr/` — inbox design and the decisions behind it
- `docs/operations/runbook.md` — the operator runbook (rendered here as [Runbook](runbook.md))
- `CONTEXT.md` — the domain vocabulary (Profile, Source, Filter, Cascade, Run, InboxTick, …)
