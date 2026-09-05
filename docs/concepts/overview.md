# Overview

## What is Lithos?

Lithos is a **shared memory layer** for teams of AI agents. It solves a fundamental problem in multi-agent systems: agents are powerful individually, but without a shared knowledge channel, they duplicate work, contradict each other, and lose context between sessions.

Lithos provides:

1. **A knowledge base** — structured Markdown notes that agents can read and write
2. **Fast search** — full-text, semantic, and cognitive retrieval over the entire KB
3. **A knowledge graph** — wiki-link relationships, provenance lineage, and typed edges
4. **Coordination primitives** — tasks with claims, findings, dependencies, epics, and gates
5. **An MCP interface** — 37 tools accessible from any MCP-compatible agent

---

## Core Concepts

### Knowledge Items

Everything in Lithos is a **knowledge item** — a Markdown file with YAML frontmatter. Each item has:

- A unique UUID (`id`)
- A title and human-readable content
- Metadata: author, tags, confidence, timestamps, freshness deadline, plus free-form key/value metadata
- Optional relationships: `derived_from_ids`, `source_url`, wiki-links
- LCMA fields: `note_type` (affects retrieval ranking), `namespace`, `access_scope`, `entities`

```markdown
---
id: f47ac10b-58cc-4372-a567-0e02b2c3d479
title: Python asyncio.gather patterns
author: research-agent
tags: [python, asyncio, patterns]
confidence: 0.95
note_type: agent_finding
created_at: 2026-03-18T12:00:00Z
updated_at: 2026-03-18T12:00:00Z
version: 1
---

# Python asyncio.gather patterns

Use `asyncio.gather()` to run coroutines concurrently...

## Related

- [[python-event-loop-internals]]
- [[concurrency-patterns]]
```

### The Knowledge Graph

Lithos actually maintains **three graphs** over your notes:

| Graph | Built from | Query with |
|-------|------------|------------|
| Wiki-links | `[[note-title]]` in bodies (NetworkX) | [`lithos_related`](../mcp-tools/knowledge-read.md#lithos_related) (`links`), `lithos_search(mode="graph")` |
| Provenance | `derived_from_ids` frontmatter | `lithos_related` (`provenance`) |
| Typed edges | Agent assertions + LLM inference in `edges.db` | `lithos_related` (`edges`), [`lithos_edge_list`](../mcp-tools/graph-edges.md) |

One call — `lithos_related(id=...)` — merges all three into a single "what is this note connected to?" view.

### Search and Retrieval

Lithos maintains two parallel indices:

| Index | Technology | Best for |
|-------|-----------|---------|
| Full-text | Tantivy (Rust BM25) | Exact terms, code snippets, error messages |
| Semantic | ChromaDB + sentence-transformers | Natural language questions, concepts, intent |

The default `lithos_search` mode is **hybrid** — it fuses both using Reciprocal Rank Fusion (RRF), giving the precision of BM25 with the recall of semantic search.

On top of both sits **LCMA cognitive retrieval** (`lithos_retrieve`): parallel scouts, reranking by learned salience and usage, and an audit receipt per call. When agents complete tasks and report which notes were useful, salience updates — retrieval literally learns which notes help. See [Retrieval Tools](../mcp-tools/retrieval.md).

### Agents

Any agent that talks to Lithos is **auto-registered** on first use. Agents are identified by free-form string IDs (e.g., `"research-agent"`, `"claude-code"`). Optional registration with `lithos_agent_register` attaches a display name, type, and metadata.

### Coordination

Lithos provides coordination without requiring a central orchestrator:

- **Tasks**: named units of work, with status (`open`/`completed`/`cancelled`) and free-form metadata
- **Claims**: TTL-based locks on a specific *aspect* of a task (prevents duplicate effort)
- **Findings**: structured results agents post back to a task
- **The task graph**: `blocks` dependencies, `parent_child` hierarchy under epics, and **gates** that model waits on the outside world — with `lithos_task_ready` answering "what can I work on right now?"

One agent claims "API research", another claims "implementation"; dependencies keep a deploy task blocked until its build task completes; a gate holds it behind a human sign-off. See [Task Graph](../mcp-tools/task-graph.md).

---

## The Obsidian Connection

Lithos deliberately stores everything as Obsidian-compatible Markdown. This means:

- **Obsidian is the human UI** — open your data directory in Obsidian to browse, visualise the graph, and edit notes
- **Wiki-links are first-class** — `[[note-title]]` links are parsed by Lithos and reflected in the graph API
- **External edits are safe** — the file watcher picks up Obsidian saves and renames and re-indexes incrementally
- **No opaque formats** — your knowledge is not locked into a proprietary database

!!! tip
    The Obsidian Graph View is a great way to spot clusters of related knowledge, orphaned notes, and gaps in your agent team's shared understanding.

---

## Local-first Philosophy

Lithos is designed to run entirely on your own infrastructure:

- **No API keys** — the embedding and NER models run locally; the optional LLM synthesis feature only activates if you point it at an endpoint you choose
- **No cloud sync** — your knowledge stays on your machine (use git externally if you want sync)
- **No telemetry** — OTEL export is opt-in and points at your own collector
- **Human-readable** — if Lithos ever disappears, your notes are still plain Markdown

This makes Lithos suitable for private research, sensitive enterprise knowledge, air-gapped environments, and anyone who wants to own their data.
