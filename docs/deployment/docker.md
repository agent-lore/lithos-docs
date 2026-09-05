# Docker Deployment

Docker is the recommended deployment method for Lithos. The image bundles all dependencies — Python 3.12, Tantivy, ChromaDB, sentence-transformers, and spaCy — with both ML models **baked in at build time**, so containers start fully offline.

## Quick Start

The shipped compose file builds the image from source:

```bash
git clone https://github.com/agent-lore/lithos.git
cd lithos/docker
docker compose up -d
```

Lithos is now serving MCP at `http://localhost:8765/mcp` (StreamableHTTP) and `http://localhost:8765/sse` (legacy SSE).

Alternatively, use the published image directly:

```bash
docker pull davesnowdon/lithos:latest
docker run -d --name lithos -p 8765:8765 -v /path/to/kb:/data \
  -e LITHOS_DATA_DIR=/data davesnowdon/lithos:latest
```

(Version-pinned tags are published per release, e.g. `davesnowdon/lithos:0.4.0`.)

## The shipped docker-compose.yml

`docker/docker-compose.yml` is parametrized entirely through environment variables (all optional):

| Variable | Default | Purpose |
|----------|---------|---------|
| `LITHOS_IMAGE` | `lithos:local` | Image to run (`pull_policy: never` — built locally, or pre-pulled) |
| `LITHOS_DATA_PATH` | `./data` | Host directory mounted at `/data` |
| `LITHOS_HOST_PORT` | `8765` | Host port |
| `LITHOS_CONTAINER_NAME` | `lithos` | Container name |
| `LITHOS_UID` / `LITHOS_GID` | `1000` | Container user (matches your files' owner) |
| `LITHOS_ENVIRONMENT` | `dev` | OTEL `deployment.environment` label |
| `LITHOS_OTEL_ENABLED` | `true` | OTLP telemetry export |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://host.docker.internal:4318` | Collector endpoint |
| `LITHOS_LCMA__LLM__*` | unset | Optional [LLM synthesis](../getting-started/configuration.md#lcmallm-background-synthesis) config, passed through to the container |

The container runs `lithos serve --transport http --host 0.0.0.0 --port 8765`, stores data at `/data`, and health-checks `GET /health` every 10s (60s start period).

Your Markdown files land at `${LITHOS_DATA_PATH}/knowledge/` on the host — open them in Obsidian directly.

## Configuration

Environment variables are the cleanest way to configure the container — nested config uses the `LITHOS_<SECTION>__<FIELD>` form:

```yaml
# docker-compose.override.yml
services:
  lithos:
    environment:
      LITHOS_LOG_LEVEL: debug
      LITHOS_SEARCH__SEMANTIC_THRESHOLD: "0.4"
```

Or mount a config file:

```yaml
services:
  lithos:
    volumes:
      - ./lithos.yaml:/app/lithos.yaml
    command: ["python", "-m", "lithos.cli", "--config", "/app/lithos.yaml",
              "serve", "--transport", "http", "--host", "0.0.0.0", "--port", "8765"]
```

## Using the CLI Inside Docker

```bash
docker compose exec lithos lithos stats
docker compose exec lithos lithos search "my query"
docker compose exec lithos lithos reindex --clear
docker compose exec lithos lithos validate
```

## Health Check

The image's `HEALTHCHECK` polls `GET /health`:

```bash
docker compose ps  # shows health status

curl http://localhost:8765/health
# 200 OK when healthy, 503 when degraded
```

## Upgrade

With the shipped (build-from-source) compose:

```bash
cd lithos && git pull
cd docker && docker compose build && docker compose up -d
```

With the published image: `docker pull davesnowdon/lithos:latest`, then recreate the container. Data under `/data` is preserved either way. Check the [Changelog](../changelog.md) for breaking changes first.

## Backup

Back up the authoritative directories:

```bash
rsync -av ${LITHOS_DATA_PATH}/knowledge/ /backup/lithos/knowledge/
rsync -av ${LITHOS_DATA_PATH}/.lithos/   /backup/lithos/.lithos/
```

`.lithos/` holds `coordination.db` (tasks/claims/findings/agents), `edges.db` (asserted edges), `stats.db` (salience/receipts), and the read-audit log. The index directories (`.tantivy/`, `.chroma/`, `.graph/`) are rebuildable with `lithos reindex --clear`.

## Agent Zero + Docker

If running Agent Zero in Docker on the same host, use `host.docker.internal` to reach Lithos:

```json
{
  "mcpServers": {
    "lithos": {
      "url": "http://host.docker.internal:8765/sse"
    }
  }
}
```

The compose file maps `host.docker.internal` to the host gateway, so the reverse direction (Lithos reaching an Ollama or OTEL collector on the host) works too.

## Running Multiple Environments

Lithos ships with `docker/run.sh`, a thin wrapper around `docker compose` that drives each environment from its own `.env.<name>` file and a distinct compose project name (`-p lithos-<name>`). This lets you run `prod`, `staging`, and `fuzz` side-by-side on one host without container name, port, or volume collisions.

### Set up env files

Create one file per environment under `docker/`:

=== "prod"

    ```bash
    # docker/.env.prod
    LITHOS_ENVIRONMENT=production
    LITHOS_DATA_PATH=/path/to/lithos/data
    LITHOS_HOST_PORT=8765
    LITHOS_CONTAINER_NAME=lithos
    ```

=== "staging"

    ```bash
    # docker/.env.staging
    LITHOS_ENVIRONMENT=staging
    LITHOS_DATA_PATH=/path/to/lithos/data-staging
    LITHOS_HOST_PORT=8766
    LITHOS_CONTAINER_NAME=lithos-staging
    ```

=== "fuzz"

    ```bash
    # docker/.env.fuzz
    LITHOS_ENVIRONMENT=fuzz
    LITHOS_DATA_PATH=/path/to/lithos/data-fuzz
    LITHOS_HOST_PORT=8767
    LITHOS_CONTAINER_NAME=lithos-fuzz
    ```

`LITHOS_ENVIRONMENT` becomes the OTEL `deployment.environment` resource attribute, so metrics, traces, and logs are labelled per environment in your observability stack. Add `LITHOS_LCMA__LLM__*` entries to an env file to enable LLM synthesis for that environment only.

### Use the launcher

```bash
cd docker

./run.sh prod                 # build & start production (default action = up)
./run.sh staging up           # same, explicit
./run.sh fuzz logs            # follow container logs
./run.sh staging status       # show running containers for this stack
./run.sh prod down            # stop & remove the stack
./run.sh fuzz restart         # down + up
```

Each environment gets its own container, host port, and data directory — they can all run concurrently. Running `./run.sh` with no arguments prints usage.

!!! note "Env files are gitignored"
    The `.env.<name>` files are gitignored so your data paths and any secrets (e.g. an LLM API key) stay off the repository.

---

## Production Considerations

!!! tip "Run on your home network"
    Lithos is designed for single-node, local-network deployment. If you need agents on multiple machines to access the same KB, expose Lithos on your local network and connect agents to the server's IP or hostname.

!!! warning "No authentication"
    Lithos assumes a single trusted network. The MCP endpoints, `/events`, and `/audit` are unauthenticated. Do not expose port 8765 to the public internet without additional security (VPN, firewall, reverse proxy with auth).

For a reverse proxy setup:

```nginx
# nginx — basic auth example
location /lithos/ {
    auth_basic "Lithos";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:8765/;
}
```
