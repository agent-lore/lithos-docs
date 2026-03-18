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
  -c, --config PATH    Path to config YAML
  -d, --data-dir PATH  Data directory path
  --help               Show this message and exit
```

## Commands

### `serve` — Start the MCP server

```bash
# stdio transport (for Claude Desktop and local MCP clients)
lithos serve

# SSE transport (for Agent Zero, remote Claude Code, OpenClaw)
lithos serve --transport sse --host 0.0.0.0 --port 8765

# Disable file watcher (useful in read-only or CI environments)
lithos serve --no-watch
```

| Option | Default | Description |
|--------|---------|-------------|
| `-t, --transport` | `stdio` | Transport: `stdio` or `sse` |
| `--host` | `127.0.0.1` | Bind host (SSE only) |
| `-p, --port` | `8765` | Bind port (SSE only) |
| `--watch / --no-watch` | watch enabled | Watch for filesystem changes |

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
Documents:      42
Chunks:         187
Agents:         3
Active tasks:   2
Open claims:    1
Tags:           18
Duplicate URLs: 0
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

```bash
# Reconcile everything
lithos reconcile

# Dry run to see what would change
lithos reconcile --dry-run --json-output

# Reconcile only the graph cache
lithos reconcile --scope graph
```

---

### `inspect` — Inspect backends and documents

```bash
# Server health
lithos inspect health

# List all registered agents
lithos inspect agents

# List all tasks
lithos inspect tasks --all

# Inspect a specific document
lithos inspect doc <id-or-path>
lithos inspect doc <id-or-path> --content
```

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
lithos search --help
lithos reindex --help
lithos validate --help
lithos stats --help
lithos inspect --help
```
