---
hide:
  - navigation
  - toc
---

# Lithos

<div class="lithos-hero" markdown>

## The meta system prompt your entire agent team shares

**Persistent. Searchable. Always up to date.**

Lithos is a local, privacy-first knowledge base that lets heterogeneous AI agents — Agent Zero, Claude Code, OpenClaw, LangGraph, CrewAI, and more — read, write, and coordinate through a single MCP interface. Human-readable Markdown on disk. Zero cloud. Zero lock-in.

[Get Started →](getting-started/installation.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/agent-lore/lithos){ .md-button }

</div>

---

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
<div class="icon">📁</div>
**Markdown-first**

Every knowledge item is a plain `.md` file compatible with Obsidian. Your agents' memory is human-readable and version-controllable — inspect it, edit it, `git diff` it.
</div>

<div class="feature-card" markdown>
<div class="icon">🔍</div>
**Hybrid search**

Tantivy full-text BM25 + ChromaDB semantic vectors, fused with Reciprocal Rank Fusion (RRF) — plus LCMA cognitive retrieval that learns which notes actually help.
</div>

<div class="feature-card" markdown>
<div class="icon">🤝</div>
**Multi-agent coordination**

Task claiming with TTL-based locks, plus a full task graph: blocking dependencies, epics, gates on the outside world, and a query for what's ready to work right now.
</div>

<div class="feature-card" markdown>
<div class="icon">🕸️</div>
**Knowledge graph**

Wiki-links (`[[note]]`) build a NetworkX graph automatically. Traverse relationships, query provenance lineage, and assert typed edges between notes.
</div>

<div class="feature-card" markdown>
<div class="icon">🔌</div>
**MCP native**

Exposes 37 tools via the Model Context Protocol over stdio or HTTP (StreamableHTTP + legacy SSE on one port). Add Lithos to any MCP-compatible agent in seconds — no SDK required.
</div>

<div class="feature-card" markdown>
<div class="icon">🏠</div>
**Truly local**

No API keys. No telemetry by default. No cloud sync. Runs on a Raspberry Pi, a Mac Mini, or a VPS. Your data stays where you put it.
</div>

</div>

---

## Quickstart

=== "Docker (recommended)"

    ```bash
    git clone https://github.com/agent-lore/lithos.git
    cd lithos/docker
    docker compose up -d
    ```

    Lithos is now serving MCP at `http://localhost:8765/mcp` (StreamableHTTP) and `http://localhost:8765/sse` (legacy SSE).

=== "pip / uv"

    ```bash
    pip install lithos-mcp
    # or
    uv pip install lithos-mcp

    lithos serve --transport http --host 0.0.0.0 --port 8765
    ```

=== "Claude Desktop"

    Add to your `claude_desktop_config.json`:

    ```json
    {
      "mcpServers": {
        "lithos": {
          "command": "lithos",
          "args": ["serve"]
        }
      }
    }
    ```

=== "Claude Code"

    ```bash
    claude mcp add --transport http lithos http://localhost:8765/mcp
    ```

=== "OpenClaw"

    In `~/.openclaw/workspace/config/mcporter.json`:

    ```json
    {
      "mcpServers": {
        "lithos": {
          "baseUrl": "http://localhost:8765/sse"
        }
      }
    }
    ```

=== "Agent Zero"

    ```json
    {
      "mcpServers": {
        "lithos": {
          "url": "http://host.docker.internal:8765/sse"
        }
      }
    }
    ```

---

## Your agents, talking to each other

```python
# Agent A discovers something useful
lithos_write(
    title="Rate limiting pattern for OpenAI API",
    content="Use exponential backoff with jitter. Base delay 1s, max 60s...",
    tags=["openai", "rate-limiting", "patterns"],
    agent="research-agent"
)

# Agent B finds it instantly — no re-researching, no duplicated work
results = lithos_search(query="openai rate limit backoff", mode="hybrid")
# → [{ title: "Rate limiting pattern for OpenAI API", score: 0.94, ... }]

# Agent C coordinates parallel work
task = lithos_task_create(title="Audit all API integrations", agent="orchestrator")
lithos_task_claim(task_id=task["task_id"], aspect="OpenAI audit",
                  agent="agent-c", ttl_minutes=60)

# Agent D just asks what's unblocked and ready to work
ready = lithos_task_ready()
```

---

## Why Lithos?

In 2026, running one agent is table stakes. Running a team of agents is where it gets interesting — and where it gets messy. Agents duplicate research, contradict each other, lose context, and can't coordinate without a shared channel.

Lithos is that channel. It's the **shared memory layer** your agents can actually trust: every item is timestamped, attributed, versioned, and searchable. Agents can declare confidence, set freshness deadlines, and build provenance chains. The knowledge base is a first-class artefact you can open in Obsidian, commit to git, and inspect at any time.

!!! tip "The AI Runtime"
    Think of Lithos like a software runtime for knowledge — not a static library. Notes are executable instructions. Outdated notes are bugs. Retrieval feedback adjusts each note's salience over time, and the reconcile pipeline flags stale knowledge.

---

## What's next?

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
<div class="icon">🚀</div>
**[Installation](getting-started/installation.md)**

System requirements, install methods, Docker Compose.
</div>

<div class="feature-card" markdown>
<div class="icon">⚡</div>
**[Quickstart](getting-started/quickstart.md)**

Your first knowledge item in under 5 minutes.
</div>

<div class="feature-card" markdown>
<div class="icon">🧠</div>
**[Concepts](concepts/overview.md)**

How Lithos stores, indexes, and retrieves knowledge.
</div>

<div class="feature-card" markdown>
<div class="icon">🔧</div>
**[MCP Tools](mcp-tools/index.md)**

Full reference for all 37 MCP tools.
</div>

</div>
