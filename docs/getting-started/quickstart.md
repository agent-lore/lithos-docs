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
  "title": "Python asyncio.gather patterns",
  "path": "python-asyncio-gather-patterns.md",
  "version": 1,
  "warnings": []
}
```

---

## Step 2 — Search for it

```python
# Full-text search
results = lithos_search(query="asyncio gather concurrent", mode="fulltext")

# Semantic search
results = lithos_search(query="how to run async tasks in parallel", mode="semantic")

# Hybrid (default — best results)
results = lithos_search(query="asyncio gather concurrent")
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
      "source_url": "",
      "updated_at": "2026-09-05T12:00:00+00:00",
      "is_stale": false,
      "derived_from_ids": []
    }
  ]
}
```

When quality matters more than speed, use `lithos_retrieve(query=...)` instead — it runs multi-scout cognitive retrieval with reranking. See [Retrieval Tools](../mcp-tools/retrieval.md).

---

## Step 3 — Read the full document

```python
doc = lithos_read(id="f47ac10b-58cc-4372-a567-0e02b2c3d479")
```

Short ID prefixes work everywhere — `lithos_read(id="f47ac10b")` resolves as long as the prefix is unambiguous.

For large documents, truncate to avoid filling context windows:

```python
doc = lithos_read(id="f47ac10b", max_length=2000)
# doc["truncated"] → True if content was shortened
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
# → { "task_id": "1c9e4a7b-...", "title": "Audit all Python...", "updated_at": "..." }

# Agent B claims the asyncio part
lithos_task_claim(
    task_id=task["task_id"],
    aspect="asyncio patterns review",
    agent="agent-b",
    ttl_minutes=60
)
# → { "success": true, "expires_at": "...", "task_id": "...", "title": "..." }

# Agent C tries to claim the same aspect — normal contention, not a fault
lithos_task_claim(task_id=task["task_id"], aspect="asyncio patterns review", agent="agent-c")
# → { "status": "error", "code": "claim_failed", "message": "..." }

# Agent C claims a different aspect instead
lithos_task_claim(task_id=task["task_id"], aspect="threading patterns review", agent="agent-c")
# → { "success": true, ... }

# Check what's in progress
lithos_task_status(task_id=task["task_id"])
```

Tasks can also depend on each other, roll up under epics, and wait on external gates — ask `lithos_task_ready()` for what's unblocked right now. See [Task Graph](../mcp-tools/task-graph.md).

---

## Step 5 — Browse in Obsidian

Your knowledge is stored as plain Markdown files. Open the data directory in [Obsidian](https://obsidian.md) to browse, visualise the graph, and edit notes as a human:

```bash
# Find your data directory
lithos stats
# → the last line prints "Data directory: ..."

# Open in Obsidian (macOS)
open -a Obsidian /path/to/lithos/data/knowledge
```

Lithos uses Obsidian-compatible `[[wiki-links]]` and YAML frontmatter — the knowledge graph view in Obsidian directly mirrors Lithos's internal graph. External edits are picked up by the file watcher and re-indexed automatically.

---

## Check the stats

```bash
lithos stats
```

```
Lithos Statistics
========================================
Documents:     1
Search chunks: 4
Graph nodes:   1
Graph edges:   0
Tags:          3
Agents:        3
Active tasks:  1
Open claims:   2

Data directory: /path/to/lithos/data
```

---

## What's next?

- [Configuration](configuration.md) — set your data directory, adjust semantic search thresholds
- [Concepts: Memory Model](../concepts/memory-model.md) — understand how write/search/list fit together
- [Envelopes, Errors & IDs](../concepts/envelopes.md) — how tools report outcomes and how to branch on them
- [MCP Tools Reference](../mcp-tools/index.md) — all 37 tools documented
