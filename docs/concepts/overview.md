# Overview

## What is Lithos?

Lithos is a **shared memory layer** for teams of AI agents. It solves a fundamental problem in multi-agent systems: agents are powerful individually, but without a shared knowledge channel, they duplicate work, contradict each other, and lose context between sessions.

Lithos provides:

1. **A knowledge base** — structured Markdown notes that agents can read and write
2. **Fast search** — full-text and semantic search over the entire KB
3. **A knowledge graph** — relationships between notes via wiki-links
4. **Coordination primitives** — task claiming, findings, status tracking
5. **An MCP interface** — 22 tools accessible from any MCP-compatible agent

---

## Core Concepts

### Knowledge Items

Everything in Lithos is a **knowledge item** — a Markdown file with YAML frontmatter. Each item has:

- A unique UUID (`id`)
- A title and human-readable content
- Metadata: author, tags, confidence, timestamps, freshness deadline
- Optional relationships: `derived_from_ids`, `source_url`, wiki-links

```markdown
---
id: f47ac10b-58cc-4372-a567-0e02b2c3d479
title: Python asyncio.gather patterns
author: research-agent
tags: [python, asyncio, patterns]
confidence: 0.95
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

When an agent writes `[[note-title]]` in a knowledge item, Lithos automatically builds a directed graph (via NetworkX) of those relationships. This lets agents ask:

- "What documents link *to* this note?" (`lithos_links` with `direction="incoming"`)
- "What does this note link *out to*?" (`direction="outgoing"`)
- "What's the provenance chain for this synthesis?" (`lithos_provenance`)

### Search

Lithos maintains two parallel indices:

| Index | Technology | Best for |
|-------|-----------|---------|
| Full-text | Tantivy (Rust BM25) | Exact terms, code snippets, error messages |
| Semantic | ChromaDB + sentence-transformers | Natural language questions, concepts, intent |

The default `lithos_search` mode is **hybrid** — it fuses both indices using Reciprocal Rank Fusion (RRF), giving you the precision of BM25 with the recall of semantic search.

### Agents

Any agent that talks to Lithos is **auto-registered** on first use. Agents are identified by free-form string IDs (e.g., `"research-agent"`, `"claude-code"`, `"openclaw"`). Optional registration with `lithos_agent_register` lets you attach a display name, type, and metadata.

### Coordination

Lithos provides lightweight coordination without requiring a central orchestrator:

- **Tasks**: named units of work that agents can create and track
- **Claims**: TTL-based locks on a specific *aspect* of a task (prevents duplicate effort)
- **Findings**: structured results that agents post back to a task

This lets agents divide work dynamically — one agent claims "API research", another claims "implementation", and they can check each other's status without stepping on each other's work.

---

## The Obsidian Connection

Lithos deliberately stores everything as Obsidian-compatible Markdown. This means:

- **Obsidian is the human UI** — open your data directory in Obsidian to browse, visualise the graph, and edit notes
- **Wiki-links are first-class** — `[[note-title]]` links are parsed by Lithos and reflected in the graph API
- **No opaque formats** — your knowledge is not locked into a proprietary database

!!! tip
    The Obsidian Graph View is a great way to spot clusters of related knowledge, orphaned notes, and gaps in your agent team's shared understanding.

---

## Local-first Philosophy

Lithos is designed to run entirely on your own infrastructure:

- **No API keys** — the embedding model runs locally via sentence-transformers
- **No cloud sync** — your knowledge stays on your machine (use git externally if you want sync)
- **No telemetry** — disabled by default
- **Human-readable** — if Lithos ever disappears, your notes are still plain Markdown

This makes Lithos suitable for:
- Private research and internal tooling
- Sensitive enterprise knowledge
- Air-gapped environments
- Anyone who wants to own their data
