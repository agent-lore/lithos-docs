# Configuration

Lithos is configured via a YAML file. All settings have sensible defaults — you only need to override what you need.

## Config File Location

Pass the config file with `--config`:

```bash
lithos --config /etc/lithos/config.yaml serve --transport sse
```

Or set the environment variable:

```bash
LITHOS_CONFIG=/etc/lithos/config.yaml lithos serve
```

---

## Full Configuration Reference

```yaml
# storage — where to keep your knowledge
storage:
  data_dir: ./data          # Base data directory (absolute or relative to CWD)
  knowledge_subdir: knowledge  # Subdirectory for Markdown files

# search — tune retrieval behaviour
search:
  embedding_model: all-MiniLM-L6-v2  # sentence-transformers model name
  semantic_threshold: 0.3            # Minimum similarity score (0–1)
  max_results: 50                    # Hard cap on search results
  chunk_size: 500                    # Target chunk size in characters
  chunk_max: 1000                    # Maximum chunk size

# coordination — task claiming and TTLs
coordination:
  claim_default_ttl_minutes: 60   # Default claim duration
  claim_max_ttl_minutes: 480      # Maximum allowed claim duration (8 hours)

# indexing — startup and file-watching behaviour
index:
  rebuild_on_start: false      # Force a full index rebuild on every startup
  watch_debounce_ms: 500       # Debounce delay for file-change detection (ms)

# telemetry — OpenTelemetry (disabled by default)
telemetry:
  enabled: false
  endpoint: null
  console_fallback: false
  service_name: lithos
  export_interval_ms: 30000

# events — internal event bus and SSE delivery
events:
  enabled: true
  event_buffer_size: 500       # Ring buffer (last N events kept)
  subscriber_queue_size: 100
  sse_enabled: true            # Enable GET /events SSE endpoint
  max_sse_clients: 50
```

---

## Key Settings Explained

### `storage.data_dir`

The root of your knowledge base. Structure inside:

```
data/
├── knowledge/          ← your Markdown files (back this up!)
├── .lithos/            ← coordination DB (back this up!)
├── .tantivy/           ← full-text index (rebuildable)
├── .chroma/            ← vector embeddings (rebuildable)
└── .graph/             ← graph cache (rebuildable)
```

!!! warning "Back up `knowledge/` and `.lithos/`"
    Only these two directories contain data that cannot be regenerated. The index directories are derived from the Markdown files and can always be rebuilt with `lithos reindex --clear`.

### `search.embedding_model`

The sentence-transformers model used for semantic search. `all-MiniLM-L6-v2` is a good balance of quality and speed (~90 MB, runs on CPU). For higher quality at the cost of more RAM:

- `all-mpnet-base-v2` — better quality, ~420 MB
- `paraphrase-multilingual-MiniLM-L12-v2` — multilingual

!!! note
    Changing the embedding model requires a full reindex: `lithos reindex --clear`

### `search.semantic_threshold`

Minimum cosine similarity score to include a result in semantic search. Lower values = more results but potentially less relevant. Default `0.3` is a reasonable starting point.

### `coordination.claim_default_ttl_minutes`

How long a task claim lasts before expiring. Agents should renew claims with `lithos_task_renew` for long-running work. Expired claims are automatically excluded from `lithos_task_status` results.

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `LITHOS_CONFIG` | Path to config YAML |
| `LITHOS_DATA_DIR` | Override `storage.data_dir` |
| `LITHOS_PORT` | Override server port (SSE transport) |
| `LITHOS_HOST` | Override server host (SSE transport) |
| `LITHOS_LOG_LEVEL` | Logging level (`debug`, `info`, `warning`, `error`) |

---

## Docker Configuration

When using Docker Compose, environment variables are the cleanest way to configure Lithos:

```yaml
# docker-compose.override.yml
services:
  lithos:
    environment:
      LITHOS_DATA_DIR: /data
      LITHOS_LOG_LEVEL: info
    volumes:
      - /mnt/nas/lithos-kb:/data
    ports:
      - "8765:8765"
```

---

## Multiple Instances

You can run multiple Lithos instances with different data directories — for example, one for each project team:

```bash
# Team A
lithos --data-dir /data/team-a serve --port 8765

# Team B
lithos --data-dir /data/team-b serve --port 8766
```

Each instance is fully independent.
