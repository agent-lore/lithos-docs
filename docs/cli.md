# CLI Reference

The `lithos` command-line tool lets you interact with the knowledge base directly — without going through an MCP client. Useful for administration, scripts, and debugging.

## Installation

The CLI is included with the `lithos-mcp` package:

```bash
pip install lithos-mcp
# or
uv pip install lithos-mcp
```

Inside Docker:

```bash
docker compose exec lithos lithos --help
```

## Global Options

```
lithos [OPTIONS] COMMAND [ARGS]...

Options:
  -c, --config PATH     Path to config YAML
  -d, --data-dir PATH   Data directory path
  --telemetry-console   Route OTEL metrics + spans to stdout (local debugging
                        without a collector)
  --help                Show this message and exit
```

Logging and telemetry are set up at the group entrypoint, so **every** command exports spans and metrics — `--telemetry-console` is global and works with any command:

```bash
lithos --telemetry-console reconcile
```

## Commands

### `serve` — Start the MCP server

```bash
# stdio transport (for Claude Desktop and local MCP clients)
lithos serve

# HTTP transport — serves both /mcp (StreamableHTTP) and /sse (legacy SSE)
# on the same port, for network clients
lithos serve --transport http --host 0.0.0.0 --port 8765

# Disable file watcher (useful in read-only or CI environments)
lithos serve --no-watch
```

| Option | Default | Description |
|--------|---------|-------------|
| `-t, --transport` | `stdio` | `stdio` or `http` (`http` serves both `/mcp` and `/sse`) |
| `--host` | `127.0.0.1` | Bind host (http only) |
| `-p, --port` | `8765` | Bind port (http only) |
| `--watch / --no-watch` | watch enabled | Watch for filesystem changes |

!!! note "v0.3.2: `sse` → `http`"
    The transport value `sse` was renamed to `http` with no back-compat alias. The old SSE endpoint still exists — the `http` transport serves it alongside StreamableHTTP.

---

### `search` — Search from the command line

```bash
# Full-text search (default)
lithos search "agent coordination"

# Semantic search
lithos search --semantic "how do agents share results"

# Limit results
lithos search -n 10 "knowledge graph"
```

| Option | Default | Description |
|--------|---------|-------------|
| `--semantic / --fulltext` | fulltext | Search mode |
| `-n, --limit` | `5` | Number of results |

---

### `stats` — Knowledge base statistics

```bash
lithos stats
lithos --data-dir ./docker/data stats
```

Example output:

```
Lithos Statistics
========================================
Documents:     42
Search chunks: 187
Graph nodes:   45
Graph edges:   112
Tags:          18
Agents:        3
Active tasks:  2
Open claims:   1

Data directory: /path/to/data
```

---

### `reindex` — Rebuild search indices

```bash
# Incremental (only re-index changed files)
lithos reindex

# Full rebuild from scratch
lithos reindex --clear
```

Use `--clear` after:

- Changing the `embedding_model` in config
- Manual bulk edits to Markdown files
- Recovering from a corrupt index

---

### `validate` — Check knowledge base integrity

```bash
# Report issues
lithos validate

# Report and auto-repair where possible
lithos validate --fix
```

Checks for:

- Missing `id` or `title` in frontmatter
- Missing `author` field
- Broken `[[wiki-links]]` (links to non-existent documents)
- Ambiguous link targets (multiple documents match a wiki-link)

---

### `reconcile` — Repair derived state

Reconciles derived views (search indices, graph cache, provenance projection) against the Markdown corpus without touching the Markdown itself. Exits non-zero when reconciliation reports problems, so it can gate cron jobs and CI.

```bash
# Reconcile everything
lithos reconcile

# Dry run to see what would change
lithos reconcile --dry-run --json-output

# Reconcile a single scope
lithos reconcile --scope graph
```

| Option | Default | Description |
|--------|---------|-------------|
| `-s, --scope` | `all` | `all` \| `indices` \| `graph` \| `provenance_projection` |
| `--dry-run / --no-dry-run` | no-dry-run | Report without applying |
| `--json-output / --no-json-output` | text | Machine-readable report |

---

### `extract-entities` — Re-extract entity frontmatter

```bash
# Preview what would change
lithos extract-entities --dry-run

# Default: only documents with no entities or a stale extractor marker
lithos extract-entities

# Bootstrap a corpus from before extractor provenance existed
lithos extract-entities --force
```

Unlike `reconcile`, this command **mutates Markdown source files**: it replaces each document's `entities` list with the current extractor's output and stamps `entities_extractor` provenance. Entities without a marker are treated as agent-curated and skipped unless `--force` is given. Run `lithos reconcile` afterwards to refresh derived views.

Entity extraction uses spaCy's `en_core_web_sm`, downloaded on first use (pre-install with `python -m spacy download en_core_web_sm`; the Docker image bakes it in). If the model is unavailable, extraction falls back to heuristics.

---

### `recalibrate-salience` — One-time salience backfill

```bash
# Preview the distribution and how many rows would be lifted
lithos recalibrate-salience --dry-run

# Lift decay-collapsed rows up to the floor (config lcma.salience_floor)
lithos recalibrate-salience

# Override the floor explicitly
lithos recalibrate-salience --floor 0.3
```

Lifts every node whose salience decayed below the floor back up to it — except nodes carrying explicit negative feedback (misleading / chronically ignored), which stay below deliberately. Idempotent and safe to re-run; only touches `stats.db`. Going forward the daily sweep holds the floor, so this is a one-time repair for databases from before `lcma.salience_floor` existed.

---

### `inspect` — Inspect backends and documents

```bash
# Server health (exit code 0/1)
lithos inspect health

# List all registered agents
lithos inspect agents

# List tasks (open by default; --all includes closed)
lithos inspect tasks --all

# Inspect a specific document
lithos inspect doc <id-or-path>
lithos inspect doc <id-or-path> --content
```

---

### `audit` — Read-access audit log

The CLI equivalent of [`GET /audit`](mcp-tools/system.md#get-audit):

```bash
lithos audit
lithos audit --agent claude-code-researcher --since 2026-09-01T00:00:00 -n 100
lithos audit --doc <doc-id>
```

| Option | Default | Description |
|--------|---------|-------------|
| `-a, --agent` | — | Filter by reporting agent |
| `-s, --since` | — | ISO timestamp lower bound |
| `-n, --limit` | `50` | Max entries |
| `--doc` | — | Filter by document ID |

---

## Specifying a Data Directory

All commands accept `--data-dir` (`-d`):

```bash
lithos --data-dir /mnt/nas/lithos-kb stats
lithos -d ./docker/data search "my query"
```

Or via config file:

```bash
lithos --config lithos.yaml serve
```

---

## Getting Help

Every command has `--help`:

```bash
lithos --help
lithos serve --help
lithos reconcile --help
lithos inspect --help
```
