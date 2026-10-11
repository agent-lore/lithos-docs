# Changelog

Influx has no tagged releases yet. The package version in `pyproject.toml` is `0.1.0` and `influx.__version__` is read from installed package metadata. Development happens on `main` of [agent-lore/influx](https://github.com/agent-lore/influx) through pull requests; this page summarises the state of that branch rather than a release history.

---

## Unreleased (`main`)

**State as of 2026-10-11** (HEAD `3d64e17`).

Install from source only:

```bash
git clone https://github.com/agent-lore/influx.git && cd influx
uv sync
```

### What is in place

- **Sources:** arXiv (export API, per-category queries, lookback window, 429 backoff and cooldown) and RSS/Atom feeds (feedparser, per-feed timeout cooldown).
- **Filtering:** batched LLM relevance scoring per profile with operator-driven negative examples from `influx:rejected:<profile>` notes.
- **Enrichment:** three score-gated tiers (summary, full text, deep extraction) through OpenAI-compatible JSON-mode model slots, with optional strict structured outputs.
- **Archive:** local PDF/HTML archive with per-domain acquisition policy (`blocked`, `rate_limited`, `skip`, `unsupported`) and thin-summary suppression.
- **Lithos integration:** `lithos_write` over the `/sse` endpoint with `duplicate` merge (multi-profile notes, richer body wins — ADR 0003), slug-collision recovery, `content_too_large` trimming, and post-write `related_to` / `builds_on` graph edges.
- **Repair sweep:** durable retry driven by note tags and `## Repair` counters, with terminal caps per stage (ADR 0001 excludes Tier 1 from recovery).
- **Inbox:** opt-in agent submission of URLs and local PDFs as `influx:inbox` Lithos tasks, multi-profile fan-out, cache-hit replay, filter-unavailable deferral with backoff, and the `force` / `tier` submitter overrides (ADR 0002).
- **Operations:** loopback admin API (`/live`, `/ready`, `/status`, `/runs/recent`, `POST /runs`, `POST /backfills`), local run ledger with stall detection, probe-driven circuit breaker on Lithos health, JSON logging, opt-in OTLP traces/metrics/logs, typed webhook sinks (generic, Agent Zero async/toast/RFC, OpenClaw).
- **Tooling:** `influx` CLI (`validate-config`, `serve`, `run`, `backfill`, `migrate-notes`), `scripts/influx-diagnose.py`, `scripts/influx-report.py`, `scripts/influx-inbox-submit.py`, Docker multi-environment stack, generated architecture docs drift-checked in CI.

### Known constraints

- Only the Lithos SSE transport is supported.
- Single process: scheduler, coordinator and cooldown state are in-process and reset on restart.
- One global cron expression for all profiles; no per-profile cadence.
- `storage.retain_days` is accepted but no archive-pruning worker exists.
- The `[telemetry]` TOML block is parsed but the exporter reads only environment variables.
- No admin API authentication; bind policy is the boundary.
- Resubmitting an already-ingested URL to the inbox with `force`/`tier` does not upgrade the existing note.

### Compatibility

Package metadata is the version authority; the canonical note structure and `## User Notes` preservation are treated as the stable contract, and `influx.toml` evolves through the typed Pydantic schema. Expect config keys and CLI surfaces to change without deprecation shims until a first tag is cut.

For the detailed history, read the merged pull requests on GitHub and the ADRs under `docs/adr/`.
