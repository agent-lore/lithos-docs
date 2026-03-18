# Installation

## System Requirements

| Component | Minimum | Notes |
|-----------|---------|-------|
| Python | 3.11+ | 3.12 recommended |
| RAM | 512 MB | 1 GB+ for large knowledge bases |
| Disk | 200 MB | Base install; data grows with your KB |
| OS | Linux, macOS, Windows (WSL2) | Docker image is `linux/amd64` and `linux/arm64` |

!!! note "Sentence Transformers"
    Lithos downloads a sentence-transformers model (`all-MiniLM-L6-v2`, ~90 MB) on first run to power semantic search. Subsequent starts use the cached model. No internet connection is required after the first run.

---

## Install Methods

=== "Docker (recommended)"

    Docker is the easiest way to run Lithos — no Python environment management, no dependency conflicts.

    **Prerequisites:** [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (v2+)

    ```bash
    git clone https://github.com/agent-lore/lithos.git
    cd lithos
    docker compose up -d
    ```

    This starts Lithos on SSE transport at `http://localhost:8765/sse`.

    Data is persisted in a Docker volume (`lithos_data`). To use a local directory instead:

    ```yaml
    # docker-compose.override.yml
    services:
      lithos:
        volumes:
          - ./my-knowledge-base:/app/data
    ```

=== "pip"

    ```bash
    pip install lithos-mcp
    ```

    Then start the server:

    ```bash
    # SSE transport (recommended for network clients)
    lithos serve --transport sse --host 0.0.0.0 --port 8765

    # stdio transport (for Claude Desktop, local MCP clients)
    lithos serve
    ```

=== "uv (fast)"

    [uv](https://github.com/astral-sh/uv) is the fastest way to install Python packages:

    ```bash
    uv pip install lithos-mcp
    lithos serve --transport sse --port 8765
    ```

=== "Development install"

    For hacking on Lithos itself:

    ```bash
    git clone https://github.com/agent-lore/lithos.git
    cd lithos
    uv sync --extra dev
    uv run lithos serve --transport sse --port 8765
    ```

---

## Connect an Agent

Once Lithos is running, add it to your agent's MCP config:

=== "Claude Desktop"

    Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the equivalent on your platform:

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

    Restart Claude Desktop. You'll see the Lithos tools in the tool list.

=== "Claude Code"

    ```bash
    claude mcp add --transport sse lithos http://localhost:8765/sse
    ```

=== "OpenClaw"

    In `~/.openclaw/workspace/config/mcporter.json`:

    ```json
    {
      "mcpServers": {
        "lithos": {
          "baseUrl": "http://localhost:8765/sse"
        }
      },
      "imports": []
    }
    ```

    If Lithos is on a different machine:

    ```json
    {
      "mcpServers": {
        "lithos": {
          "baseUrl": "http://samsara.local:8765/sse"
        }
      }
    }
    ```

=== "Agent Zero"

    In Agent Zero's MCP server config (usually in the web UI or `mcp_servers.json`):

    ```json
    {
      "mcpServers": {
        "lithos": {
          "url": "http://host.docker.internal:8765/sse"
        }
      }
    }
    ```

    Use `host.docker.internal` when Agent Zero runs in Docker on the same machine as Lithos.

=== "Any MCP client"

    Lithos speaks standard MCP. Any client that supports SSE transport can connect:

    ```
    SSE endpoint: http://<host>:8765/sse
    ```

    For stdio transport, use `lithos serve` (no flags) as the command.

---

## Verify the Installation

```bash
# Check the server is running
curl http://localhost:8765/health

# Or use the CLI
lithos stats
```

You should see:

```json
{
  "documents": 0,
  "chunks": 0,
  "agents": 0,
  "active_tasks": 0,
  "open_claims": 0,
  "tags": 0,
  "duplicate_urls": 0
}
```

---

## Upgrading

=== "Docker"

    ```bash
    docker compose pull
    docker compose up -d
    ```

=== "pip / uv"

    ```bash
    pip install --upgrade lithos-mcp
    # or
    uv pip install --upgrade lithos-mcp
    ```

!!! warning "Pre-1.0 compatibility"
    Lithos follows a **migration safety over API stability** policy pre-1.0. MCP tool signatures may change between minor versions, but your on-disk Markdown knowledge is always preserved. Check the [Changelog](../changelog.md) before upgrading.

---

## Next Steps

- [Quickstart →](quickstart.md) — write your first knowledge item and run a search
- [Configuration →](configuration.md) — tune data directory, search thresholds, and more
