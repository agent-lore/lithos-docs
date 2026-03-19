# Quickstart

This guide gets you from zero to a working multi-agent memory system in under 10 minutes.

## Prerequisites

- Lithos running locally ([Installation](installation.md))
- At least one MCP-compatible agent connected

---

## Step 1 — Write your first knowledge item

Via MCP (any connected agent):

```python
lithos_write(
    title="Python asyncio.gather patterns",
    content="""# Python asyncio.gather patterns

Use `asyncio.gather()` to run coroutines concurrently. It returns results
in the same order as the input, regardless of completion order.

## Basic usage

```python
import asyncio

async def fetch(url):
    ...  # some async work

results = await asyncio.gather(fetch(url1), fetch(url2), fetch(url3))
```

## Error handling

Pass `return_exceptions=True` to prevent one failure from cancelling others:

```python
results = await asyncio.gather(*coros, return_exceptions=True)
errors = [r for r in results if isinstance(r, Exception)]
```
""",
    tags=["python", "asyncio", "patterns"],
    agent="my-agent"
)
```

**Response:**

```json
{
  "status": "created",
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "path": "python-asyncio-gather-patterns.md",
  "version": 1,
  "warnings": []
}
```

Or from the CLI:

```bash
cat > /tmp/note.md << 'EOF'
Use asyncio.gather() to run coroutines concurrently...
EOF

lithos write --title "Python asyncio.gather patterns" \
             --tags python asyncio patterns \
             --agent my-agent \
             /tmp/note.md
```

---

## Step 2 — Search for it

```python
# Full-text search
results = lithos_search(query="asyncio gather concurrent")

# Semantic search
results = lithos_search(query="how to run async tasks in parallel", mode="semantic")

# Hybrid (default — best results)
results = lithos_search(query="asyncio gather concurrent", mode="hybrid")
```

**Response:**

```json
{
  "results": [
    {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "title": "Python asyncio.gather patterns",
      "snippet": "Use asyncio.gather() to run coroutines concurrently...",
      "score": 0.94,
      "path": "python-asyncio-gather-patterns.md",
      "updated_at": "2026-03-18T12:00:00Z",
      "is_stale": false
    }
  ]
}
```

---

## Step 3 — Read the full document

```python
doc = lithos_read(id="f47ac10b-58cc-4372-a567-0e02b2c3d479")
```

For large documents, truncate to avoid filling context windows:

```python
doc = lithos_read(id="f47ac10b-...", max_length=2000)
# doc.truncated → True if content was shortened
```

---

## Step 4 — Coordinate between agents

This is where Lithos really shines — let multiple agents divide up work without stepping on each other.

```python
# Agent A creates a task
task = lithos_task_create(
    title="Audit all Python libraries for asyncio usage",
    agent="agent-a"
)
# → { "task_id": "task-abc123" }

# Agent B claims the asyncio part
lithos_task_claim(
    task_id="task-abc123",
    aspect="asyncio patterns review",
    agent="agent-b",
    ttl_minutes=60
)
# → { "success": true, "expires_at": "2026-03-18T13:00:00Z" }

# Agent C tries to claim the same aspect — gets blocked
lithos_task_claim(
    task_id="task-abc123",
    aspect="asyncio patterns review",
    agent="agent-c"
)
# → { "status": "error", "code": "claim_failed", ... }

# Agent C claims a different aspect instead
lithos_task_claim(
    task_id="task-abc123",
    aspect="threading patterns review",
    agent="agent-c",
    ttl_minutes=60
)
# → { "success": true, ... }

# Check what's in progress
lithos_task_status(task_id="task-abc123")
```

---

## Step 5 — Browse in Obsidian

Your knowledge is stored as plain Markdown files. Open the data directory in [Obsidian](https://obsidian.md) to browse, visualise the graph, and edit notes as a human:

```bash
# Find your data directory
lithos stats
# Look for the data_dir in output

# Open in Obsidian (macOS)
open -a Obsidian /path/to/lithos/data/knowledge
```

Lithos uses Obsidian-compatible `[[wiki-links]]` and YAML frontmatter — the knowledge graph view in Obsidian directly mirrors Lithos's internal graph.

---

## Check the stats

```bash
lithos stats
```

```
Documents:      1
Chunks:         4
Agents:         1
Active tasks:   1
Open claims:    2
Tags:           3 (asyncio, patterns, python)
Duplicate URLs: 0
```

---

## What's next?

- [Configuration](configuration.md) — set your data directory, adjust semantic search thresholds
- [Concepts: Memory Model](../concepts/memory-model.md) — understand how write/search/list fit together
- [MCP Tools Reference](../mcp-tools/index.md) — all 22 tools documented
