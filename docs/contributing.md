# Contributing

Lithos is open source ([MIT License](https://github.com/agent-lore/lithos/blob/main/LICENSE.md)). Contributions are welcome.

## Development Setup

```bash
git clone https://github.com/agent-lore/lithos.git
cd lithos

# Install with dev dependencies
uv sync --extra dev

# Run the test suite
uv run --extra dev pytest -m "not integration" tests/ -q
```

## Running Tests

```bash
# Unit tests only (fast)
uv run --extra dev pytest -m "not integration" tests/ -q

# Integration tests (requires a running Lithos instance)
uv run --extra dev pytest -m integration tests/ -q

# All tests with coverage
uv run --extra dev pytest tests/ --cov=lithos --cov-report=xml
```

## Code Style

```bash
# Format
uv run --extra dev ruff format src/ tests/

# Lint
uv run --extra dev ruff check src/ tests/

# Type check
uv run --extra dev mypy src/
```

## Project Structure

```
src/lithos/
├── cli.py          ← Click CLI entry point
├── config.py       ← Configuration loading and validation
├── coordination.py ← Task/claim/finding/agent SQLite management
├── errors.py       ← Error types and envelopes
├── events.py       ← In-memory event bus
├── graph.py        ← NetworkX wiki-link graph
├── knowledge.py    ← Knowledge Manager (read/write/delete Markdown)
├── reconcile.py    ← Index reconciliation and repair
├── search.py       ← Search engine (Tantivy + ChromaDB + hybrid)
├── server.py       ← FastMCP server and tool definitions
└── telemetry.py    ← OpenTelemetry integration
```

## Submitting a PR

1. Fork the repo and create a branch: `git checkout -b feat/your-feature`
2. Make your changes and add tests
3. Run the linters and test suite
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
