# Contributing

Lithos is open source ([MIT License](https://github.com/agent-lore/lithos/blob/main/LICENSE.md)). Contributions are welcome.

## Development Setup

Requires Python 3.12+ and [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/agent-lore/lithos.git
cd lithos

# Install with dev dependencies
uv sync --extra dev

# Run the unit test suite
make test
```

## The Definition of Done

A change is not done unless all of these are green — `make check` runs the first three:

```bash
make lint              # ruff lint + format check
make typecheck         # pyright (standard mode)
make test              # unit tests
make test-integration  # integration tests
make check             # lint + typecheck + test
```

## Generated Architecture Docs

`docs/generated/` in the lithos repo (component diagram, domain model, metrics, MCP tool catalog) is **generated from the code** by the guardrail tests and drift-checked in CI:

```bash
make diagrams   # regenerate (runs pytest tests/guardrail/)
```

Note that `make test` runs the same tests, so a test run rewrites `docs/generated/` as a side effect — commit the result if it changed, or the "Diagram drift" CI job will fail. `docs/architecture.toml` is the source of truth for components and tiers; adding a new module without mapping it there fails the orphan checks.

## Project Structure

```
src/lithos/
├── tools/             ← MCP tool registration modules (per category)
├── lcma/              ← cognitive memory internals (scouts, retrieve,
│                        salience, entities, enrichment, LLM synthesis)
├── server.py          ← FastMCP server, transports, HTTP routes
├── cli.py             ← Click CLI entry point
├── config.py          ← LithosConfig (pydantic-settings)
├── knowledge.py       ← Knowledge Manager (Markdown corpus)
├── intake.py          ← CorpusIntake — all corpus mutations flow through here
├── watch_intake.py    ← filesystem-driven mutations (watchdog)
├── search.py          ← SearchEngine (Tantivy + ChromaDB + hybrid)
├── graph.py           ← NetworkX wiki-link graph
├── edge_store.py      ← edges.db (asserted typed edges)
├── coordination.py    ← tasks, claims, findings, task edges, agents
├── cognitive_memory.py← agent-facing LCMA facade
├── envelopes.py       ← canonical response envelopes
├── errors.py          ← error hierarchy
├── events.py          ← in-memory event bus
├── id_resolution.py   ← short-ID prefix resolution
└── telemetry.py       ← OpenTelemetry integration
```

Architectural rules are enforced in CI: three tiers (Entrypoints → Core → Foundation) with import-linter contracts, and ADRs under `docs/adr/` record the load-bearing decisions.

## Submitting a PR

1. Fork the repo and create a branch: `git checkout -b feat/your-feature`
2. Make your changes and add tests
3. Run `make check` (and `make test-integration` for behaviour changes)
4. Open a PR against `main` on `agent-lore/lithos`
5. Include a clear description of what changed and why

## Specification

The [Specification](https://github.com/agent-lore/lithos/blob/main/docs/SPECIFICATION.md) is the authoritative source of truth for Lithos behaviour. If you're changing a tool signature, response format, or storage schema, update the spec first.

## Compatibility Policy

Pre-1.0, Lithos follows:

- **On-disk compatibility is required**: Existing Markdown/frontmatter knowledge must remain readable.
- **MCP/API evolution is allowed**: Tool signatures may change between minor versions.
- **Migration safety over API stability**: When in doubt, preserve the knowledge corpus.

See [Changelog](changelog.md) for breaking changes between versions.

## Questions and Discussions

- [GitHub Issues](https://github.com/agent-lore/lithos/issues) — bug reports and feature requests
- [GitHub Discussions](https://github.com/agent-lore/lithos/discussions) — questions, ideas, and show-and-tell
