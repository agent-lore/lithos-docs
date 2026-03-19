# Docker Deployment

Docker is the recommended deployment method for Lithos. It bundles all dependencies (Python, Tantivy, ChromaDB, sentence-transformers) into a single image.

## Quick Start

```bash
git clone https://github.com/agent-lore/lithos.git
cd lithos
docker compose up -d
```

Lithos is now running at `http://localhost:8765/sse`.

## Default docker-compose.yml

```yaml
services:
  lithos:
    image: davesnowdon/lithos:latest
    restart: unless-stopped
    ports:
      - "8765:8765"
    volumes:
      - lithos_data:/app/data
    environment:
      LITHOS_LOG_LEVEL: info

volumes:
  lithos_data:
```

## Using a Local Data Directory

To store your knowledge base in a directory on the host (recommended for easy access and backup):

```yaml
# docker-compose.override.yml
services:
  lithos:
    volumes:
      - /path/to/your/knowledge-base:/app/data
```

Then restart:

```bash
docker compose up -d
```

Your Markdown files will be at `/path/to/your/knowledge-base/knowledge/`.

## Configuration

Pass configuration via environment variables in your override file:

```yaml
# docker-compose.override.yml
services:
  lithos:
    environment:
      LITHOS_LOG_LEVEL: debug
      LITHOS_DATA_DIR: /app/data
    volumes:
      - ./my-kb:/app/data
```

Or mount a config file:

```yaml
services:
  lithos:
    volumes:
      - ./lithos.yaml:/app/lithos.yaml
      - ./my-kb:/app/data
    command: ["lithos", "--config", "/app/lithos.yaml", "serve", "--transport", "sse", "--host", "0.0.0.0", "--port", "8765"]
```

## Using the CLI Inside Docker

```bash
# Knowledge base stats
docker compose exec lithos lithos stats

# Search
docker compose exec lithos lithos search "my query"

# Rebuild indices
docker compose exec lithos lithos reindex --clear

# Validate
docker compose exec lithos lithos validate
```

## First Run: Model Download

On first start, Lithos downloads the `all-MiniLM-L6-v2` sentence-transformers model (~90 MB). This is cached in the data volume — subsequent starts are fast.

To pre-warm the model (useful in CI/CD or offline environments):

```bash
# Pull the image first
docker compose pull

# Start and wait for model download
docker compose up
# Watch for "Lithos ready" in logs, then Ctrl+C
# The model is now cached in the volume

# Start in background
docker compose up -d
```

## Health Check

The Docker image includes a health check that polls the HTTP health endpoint:

```bash
docker compose ps  # shows health status
```

Or query directly:

```bash
curl http://localhost:8765/health
```

## Upgrade

```bash
docker compose pull
docker compose up -d
```

Data in the volume is preserved across upgrades.

## Backup

Back up the critical directories:

```bash
# If using a host-mounted volume
rsync -av /path/to/your/knowledge-base/knowledge/ /backup/lithos/knowledge/
rsync -av /path/to/your/knowledge-base/.lithos/ /backup/lithos/.lithos/
```

For Docker volumes:

```bash
docker run --rm \
  -v lithos_data:/data \
  -v /backup:/backup \
  alpine tar czf /backup/lithos-backup-$(date +%Y%m%d).tar.gz /data/knowledge /data/.lithos
```

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

## Production Considerations

!!! tip "Run on your home network"
    Lithos is designed for single-node, local-network deployment. If you need agents on multiple machines to access the same KB, expose Lithos on your local network (`--host 0.0.0.0`) and connect agents to the server's IP or hostname.

!!! warning "No authentication"
    Lithos assumes a single trusted network. Do not expose port 8765 to the public internet without additional security (VPN, firewall, reverse proxy with auth).

For a reverse proxy setup:

```nginx
# nginx — basic auth example
location /lithos/ {
    auth_basic "Lithos";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:8765/;
}
```
