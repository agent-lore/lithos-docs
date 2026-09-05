# Installation

## System Requirements

| Component | Minimum | Notes |
|-----------|---------|-------|
| Python | 3.12+ | Required since v0.4.0 |
| RAM | 512 MB | 1 GB+ for large knowledge bases |
| Disk | 200 MB | Base install; data grows with your KB |
| OS | Linux, macOS, Windows (WSL2) | Docker image is `linux/amd64` and `linux/arm64` |

!!! note "Models downloaded on first use"
    Lithos uses a sentence-transformers model (`all-MiniLM-L6-v2`, ~90 MB) for semantic search and the spaCy `en_core_web_sm` model for entity extraction. PyPI installs download both on first use and cache them; the Docker image bakes them in and starts fully offline. To pre-install the spaCy model: `python -m spacy download en_core_web_sm`.

---

## Install Methods

=== "Docker (recommended)"

    Docker is the easiest way to run Lithos — no Python environment management, and both models are baked into the image.

    **Prerequisites:** [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (v2+)

    ```bash
    git clone https://github.com/agent-lore/lithos.git
    cd lithos/docker
    docker compose up -d
    ```

    This starts Lithos with the HTTP transport on port 8765 — `POST /mcp` (StreamableHTTP) and `GET /sse` (legacy SSE) on the same port.

    Data is stored in `./data` next to the compose file by default; set `LITHOS_DATA_PATH` to use another directory:

    ```bash
    LITHOS_DATA_PATH=/mnt/nas/lithos-kb docker compose up -d
    ```

    See [Docker deployment](../deployment/docker.md) for multi-environment setups (`run.sh`, `.env.<name>` files).

=== "pip"

    ```bash
    pip install lithos-mcp
    ```

    Then start the server:

    ```bash
    # HTTP transport (recommended for network clients)
    lithos serve --transport http --host 0.0.0.0 --port 8765

    # stdio transport (for Claude Desktop, local MCP clients)
    lithos serve
    ```

=== "uv (fast)"

    [uv](https://github.com/astral-sh/uv) is the fastest way to install Python packages:

    ```bash
    uv pip install lithos-mcp
    lithos serve --transport http --port 8765
    ```

    !!! tip "Local dev with telemetry"
        Use the global `--telemetry-console` option to stream OTEL spans and metrics to stdout without a collector:
        ```bash
        lithos --telemetry-console serve --transport http --port 8765
        ```

=== "Development install"

    For hacking on Lithos itself, the project uses `uv` exclusively:

    ```bash
    git clone https://github.com/agent-lore/lithos.git
    cd lithos
    uv sync --extra dev
    make check        # lint + type check + unit tests
    uv run lithos serve --transport http --port 8765
    ```

---

## Connect an Agent

Once Lithos is running, add it to your agent's MCP config. Network clients should prefer the StreamableHTTP endpoint (`/mcp`); the legacy SSE endpoint (`/sse`) remains for clients that only speak SSE.

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

    Lithos speaks standard MCP. Both HTTP transports are served on one port:

    ```
    StreamableHTTP endpoint: http://<host>:8765/mcp   (MCP 2025-03-26+, stateless)
    Legacy SSE endpoint:     http://<host>:8765/sse
    ```

    For stdio transport, use `lithos serve` (no flags) as the command.

---

## Verify the Installation

```bash
curl http://localhost:8765/health
```

You should see `200 OK` with:

```json
{
  "status": "ok",
  "timestamp": "2026-09-05T12:00:00+00:00",
  "components": {
    "kb_directory": {"status": "ok"},
    "search": {"status": "ok"},
    "knowledge_base": {"status": "ok"}
  }
}
```

Or from the CLI: `lithos stats` prints document, index, graph, agent, task, and claim counts plus the data directory in use.

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

!!! note "Upgrading from 0.3.x or earlier?"
    v0.4.0 changed the error envelope, and v0.3.2 renamed the `sse` transport to `http` (no alias — update any `lithos serve --transport sse` invocations). See [Envelopes, Errors & IDs → Migrating older clients](../concepts/envelopes.md#migrating-older-clients) for the full list.

---

## Next Steps

- [Quickstart →](quickstart.md) — write your first knowledge item and run a search
- [Configuration →](configuration.md) — tune data directory, search thresholds, and more
