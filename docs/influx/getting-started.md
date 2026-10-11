# Getting Started

This page takes you from a clone to a first ingestion run against a running Lithos.

## Prerequisites

| Component | Requirement | Notes |
|-----------|-------------|-------|
| Python | 3.12 | `requires-python = ">=3.12,<3.13"`; `.python-version` pins it |
| uv | any recent | The project is managed with `uv` exclusively; there is no PyPI package |
| Lithos | running, reachable | Influx connects to the `/sse` endpoint — see [Lithos installation](../getting-started/installation.md) |
| LLM provider | OpenAI-compatible | At least one `[providers.*]` entry whose `/chat/completions` accepts `response_format = {"type": "json_object"}` |

!!! warning "Anthropic's native API is not supported"
    Influx only speaks the OpenAI-compatible chat-completions JSON mode. To use Claude models, route them through OpenRouter or another OpenAI-compatible gateway rather than pointing a provider at Anthropic directly.

---

## Install

=== "uv (development checkout)"

    ```bash
    git clone https://github.com/agent-lore/influx.git
    cd influx
    uv sync                      # runtime + dev dependencies
    uv run influx --help
    ```

    `uv sync` installs the `dev` dependency group (pytest, pyright, ruff, OTEL SDK). `make check` runs lint, type check and tests.

=== "Docker"

    The image is built from source; nothing is published to a registry yet.

    ```bash
    git clone https://github.com/agent-lore/influx.git
    cd influx
    make docker-build                    # builds influx:dev
    cp docker/.env.example docker/.env.dev
    mkdir -p docker/data docker/archive docker/state
    cp influx.example.toml docker/data/influx.toml
    ./docker/run.sh dev up
    ./docker/run.sh dev logs
    ```

    `run.sh <env> [up|down|restart|logs|status]` wraps `docker compose` with project name `influx-<env>` and env file `docker/.env.<env>`, so several environments (dev, staging, prod) can coexist on one host. See [Docker](#docker) below for the volume and variable layout.

---

## Write `influx.toml`

Copy the annotated template and edit it:

```bash
cp influx.example.toml influx.toml
```

Influx looks for its config in this order: `$INFLUX_CONFIG`, `./influx.toml`, `~/.influx/influx.toml`, `/etc/influx/influx.toml`. A `.env` file in the working directory is loaded first (python-dotenv), so API keys can live there.

The minimum you must change:

1. **Point at Lithos.** The template does not include a `[lithos]` block — add one, or set `LITHOS_URL`:

    ```toml
    [lithos]
    url = "http://localhost:8765/sse"   # the Lithos /sse endpoint
    transport = "sse"                    # the only supported value
    ```

    Without a URL, `validate-config` skips the Lithos check and `serve` will report `lithos` as degraded in `/status`.

2. **Provide API keys.** Each `[providers.<name>]` names an environment variable in `api_key_env`; that variable must be set (and non-empty) or config loading fails. Keyless providers such as Ollama use `api_key_env = ""`.

    ```bash
    export OPENAI_API_KEY=sk-...
    export OPENROUTER_API_KEY=sk-or-...
    ```

3. **Describe at least one profile.** `[[profiles]]` entries carry the interest description the filter model scores against, the score thresholds, arXiv categories and RSS feeds. The template ships two examples (`ai-robotics`, `web-tech`).

4. **Check the prompts.** `[prompts.filter]`, `[prompts.tier1_enrich]` and `[prompts.tier3_extract]` are all required, each as inline `text` or a `path` (relative paths resolve against the config file). Their template variables are validated at load time.

The full field reference is on the [Configuration](configuration.md) page.

---

## Validate

```bash
uv run influx validate-config
```

This prints the effective config as JSON, then:

- sends a one-token JSON-mode dry call to every `[models.*]` slot with `json_mode = true`, so a provider that rejects `response_format` fails here rather than mid-run;
- opens an SSE connection to `lithos.url` and calls `lithos_agent_register`.

Any failure exits `2` with a message on stderr.

---

## Run the service

```bash
uv run influx serve
```

`serve` starts the FastAPI admin API on `127.0.0.1:8080` (override with `INFLUX_ADMIN_BIND_HOST` / `INFLUX_ADMIN_PORT`), the background probe loop, and the APScheduler job that fires every profile on `schedule.cron` (default `0 6 * * *` UTC). It runs until SIGINT/SIGTERM and shuts down within `schedule.shutdown_grace_seconds`.

!!! note "Loopback only by default"
    Binding to anything other than a loopback address is refused unless `[security] allow_remote_admin = true`. The admin API has no authentication; the bind policy is the safety boundary.

Confirm it is up:

```bash
curl -s http://127.0.0.1:8080/live     # {"live": true}
curl -s http://127.0.0.1:8080/ready    # 200 once Lithos and credentials probe ok, else 503
curl -s http://127.0.0.1:8080/status | jq
```

---

## Trigger a first run

The `run` and `backfill` commands are thin HTTP clients for the running service — they do nothing without `serve`.

```bash
# One ingestion cycle for a profile, now
uv run influx run --profile ai-robotics

# Historical window (estimates over 1000 items need --confirm)
uv run influx backfill --profile ai-robotics --days 7
uv run influx backfill --profile ai-robotics --from 2026-04-01 --to 2026-04-07 --confirm
```

`run` prints the accepted `request_id` and exits `0`; if the profile is already running it exits `1`. Watch progress in the service logs, then check the ledger entry and the Lithos side:

```bash
curl -s "http://127.0.0.1:8080/runs/recent?profile=ai-robotics&limit=1" | jq
lithos stats          # document count should have grown
```

Notes land under the `influx` namespace with tags such as `profile:<name>`, `source:arxiv`, `ingested-by:influx` and `schema:1`, so any agent can find them with `lithos_search(…, tags=["profile:ai-robotics"])`.

---

## Docker

`docker/docker-compose.yml` is parametrised entirely through the `.env.<env>` file:

| Variable | Default | Purpose |
|----------|---------|---------|
| `INFLUX_IMAGE` | `influx:dev` | Image to run (`pull_policy: never`; `run.sh up` builds it) |
| `INFLUX_CONTAINER_NAME` | `influx` | Must be unique per environment |
| `INFLUX_DATA_PATH` | `./data` | Mounted at `/data`; must contain `influx.toml` |
| `INFLUX_ARCHIVE_PATH` | `./archive` | Mounted at `/archive` (fetched PDFs/HTML) |
| `INFLUX_STATE_PATH` | `./state` | Mounted at `/state` (run ledger) |
| `INFLUX_INBOX_PDF_ROOT` | `/tmp/staging-pdf-inbox` | Identity-mounted (same path inside and out) for [local-PDF inbox intake](inbox.md#submitting-a-local-pdf) |
| `INFLUX_ADMIN_HOST_PORT` | `8080` | Host port mapped to the admin API |
| `INFLUX_ADMIN_BIND_HOST` | `127.0.0.1` | Bind host inside the container |
| `INFLUX_ENVIRONMENT` | `dev` | OTEL `deployment.environment` label |
| `INFLUX_UID` / `INFLUX_GID` | `1000` | Container user, so archive files are owned by you |
| `INFLUX_OTEL_ENABLED` | `false` | OTLP export toggle; see [Operations](operations.md#telemetry) |
| `OPENAI_API_KEY`, `OPENROUTER_API_KEY` | unset | Passed through to the container |
| `OPENCLAW_TOKEN`, `AGENT_ZERO_RFC_PASSWORD` | unset | Webhook secrets referenced from `influx.toml` |

The container sets `INFLUX_CONFIG=/data/influx.toml` and runs `influx serve` as UID 1000 on port 8080. `LITHOS_URL` is **not** passed through by the compose file, so inside Docker the Lithos endpoint must come from the `[lithos]` block in `/data/influx.toml`. Use `host.docker.internal:8765` to reach a Lithos running on the same host.

---

## Next steps

- [Configuration →](configuration.md) — tune thresholds, sources, resilience and archive policy
- [Pipeline →](pipeline.md) — understand what each stage does to an item
- [Inbox →](inbox.md) — let agents submit individual URLs and PDFs
