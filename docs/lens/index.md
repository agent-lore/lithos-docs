# Lithos Lens

**Lens** is the web UI for the Lithos ecosystem: a local FastAPI application that shows you the tasks agents are working on, the dependency graph between them, the findings they post, and the knowledge notes and typed edges Lithos holds — all updating live from Lithos's event stream. Reading never changes anything; a small set of curated write actions (create a task, cancel, reopen, add a dependency, proceed past a gate) is offered once you choose an operator identity.

!!! warning "Status: pre-release, under active development, documents `main`"
    Lens has no tagged release yet (package version 0.5.0) and new views land week to week. These pages describe the current `main` branch of [agent-lore/lithos-lens](https://github.com/agent-lore/lithos-lens). The [user manual](manual.md) is regenerated from the live UI in that repo and pulled into this site at build time, so it cannot lag it.

## What it shows

| View | Route | What you get |
|------|-------|--------------|
| Tasks dashboard | `/tasks` | Every task grouped into needs-attention, gates, in progress, ready, blocked, completed and cancelled; epic and project strips; filters held in the URL; live updates |
| Dependency graph | `/tasks/graph` | One project's or epic's blocking structure as a canvas and as text, with cycles, ghosts and the longest blocking chain |
| Task detail | `/tasks/{id}` | Description, nearby graph, dependencies, provenance, metadata, claims and the finding timeline |
| Knowledge | `/knowledge` | Search with namespace facets, the tag index, note pages |
| Knowledge graph | `/knowledge/graph` | Typed edges between notes by namespace or edge type, with node and edge panels and a full-page canvas |
| Operator | `/operator` | Choose the identity your write actions are recorded under |

The [user manual](manual.md) walks through each of these with screenshots.

## Requirements

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- A reachable Lithos server: Lens talks MCP over the legacy `/sse` endpoint and subscribes to `GET /events`
- A browser; Lens is a server-rendered site with small HTMX fragments and a Cytoscape canvas for the graphs

## Install and run

=== "From a checkout"

    ```bash
    git clone https://github.com/agent-lore/lithos-lens.git
    cd lithos-lens
    uv sync
    cp lithos-lens.example.toml lithos-lens.toml   # set [lithos-lens.lithos] url
    uv run lithos-lens                              # http://0.0.0.0:8000
    ```

    `LENS_PORT` and `LENS_HOST` override the bind address; `LITHOS_LENS_CONFIG` points at a config file somewhere other than the working directory, `~/.lithos-lens/`, or `/etc/lithos-lens/`.

=== "Docker"

    ```bash
    cp docker/.env.example docker/.env.dev        # LITHOS_LENS_HOST_PORT, data path, container name
    ./docker/run.sh dev up                        # build and start, detached
    ./docker/run.sh dev logs
    ```

    The compose stack maps `host.docker.internal` to the host, so a Lithos published on the host is `url = "http://host.docker.internal:8765"` in the container's `lithos-lens.toml`. `dev` and `prod` stacks coexist with their own project names, container names and data paths.

## Configuration

Lens reads one TOML file. The annotated template [`lithos-lens.example.toml`](https://github.com/agent-lore/lithos-lens/blob/main/lithos-lens.example.toml) is the complete field list; the sections are:

| Section | Purpose |
|---------|---------|
| `[lithos-lens]` | `environment` (the badge in the header) and `greeting` |
| `[lithos-lens.lithos]` | `url`, `mcp_sse_path`, `sse_events_path`, and the `agent_id` Lens registers itself under |
| `[lithos-lens.tasks]` | board caps and windows, the description preview budget, and the needs-attention thresholds (gate waiting hours, claim expiring minutes, stale-open days, unclaimed-ready minutes) |
| `[lithos-lens.knowledge]` / `[lithos-lens.graph]` | search and list limits, graph node caps, edge-table TTL, default depth and minimum weight |
| `[lithos-lens.writes]` | `default_operator` for a single-operator install and `confirm_cancel` |
| `[lithos-lens.events]`, `[lithos-lens.llm]`, `[lithos-lens.telemetry]`, `[lithos-lens.logging]`, `[lithos-lens.storage]` | live updates, the optional summarisation helper (disabled by default), OTLP export, log level, data directory |

Most fields also have a `LITHOS_LENS_*` environment override, which is how the Docker stack is configured.

!!! danger "No authentication"
    Lens has no login. Anyone who can reach its port can read everything and, with an operator identity set, perform the write actions. It is built for one operator on a trusted local network; do not expose it further.

## Source and tracking

- Source: [agent-lore/lithos-lens](https://github.com/agent-lore/lithos-lens) — `docs/SPECIFICATION.md` is the contract, `docs/prd/` the milestone PRDs, `docs/generated/` the drift-checked architecture views.
- Work is tracked as Lithos tasks under `project:lithos-lens` and as GitHub issues on that repo.
