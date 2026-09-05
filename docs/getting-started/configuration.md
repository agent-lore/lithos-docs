# Configuration

Lithos is configured through `pydantic-settings` (`LithosConfig`). Values are resolved in order — later wins:

1. Defaults (hardcoded)
2. YAML config file (`--config` / `LITHOS_CONFIG`)
3. Environment variables with the `LITHOS_` prefix

```bash
lithos --config /etc/lithos/config.yaml serve --transport http
# or
LITHOS_CONFIG=/etc/lithos/config.yaml lithos serve
```

**Environment variable form:** nested fields use a double underscore — `LITHOS_<SECTION>__<FIELD>`, e.g. `LITHOS_TELEMETRY__ENABLED=true`, `LITHOS_LCMA__LLM__BASE_URL=http://localhost:11434/v1`. Blank env vars are treated as unset.

---

## Full Configuration Reference

All settings have sensible defaults — override only what you need.

```yaml
# server — transport and binding
server:
  transport: stdio          # stdio | http (http serves both /mcp and /sse)
  host: 127.0.0.1
  port: 8765
  watch_files: true         # watch the knowledge dir for external edits

# storage — where to keep your knowledge
storage:
  data_dir: ./data              # Base data directory
  knowledge_subdir: knowledge   # Subdirectory for Markdown files
  max_content_size_bytes: 1000000  # lithos_write size limit (→ content_too_large)

# search — tune retrieval behaviour
search:
  embedding_model: all-MiniLM-L6-v2  # sentence-transformers model name
  semantic_threshold: 0.3            # Minimum similarity score (0–1)
  max_results: 50                    # Hard cap on search results
  chunk_size: 500                    # Target chunk size in characters
  chunk_max: 1000                    # Maximum chunk size
  device: auto                       # auto | cpu | cuda | cuda:0 …

# coordination — task claiming and TTLs
coordination:
  claim_default_ttl_minutes: 60
  claim_max_ttl_minutes: 480

# indexing — startup and file-watching behaviour
index:
  rebuild_on_start: false
  watch_debounce_ms: 500

# telemetry — OpenTelemetry OTLP push (disabled by default)
telemetry:
  enabled: false
  endpoint: null               # OTLP/HTTP collector endpoint
  console_fallback: false
  service_name: lithos
  environment: null            # → OTEL deployment.environment (dev/staging/prod)
  export_interval_ms: 30000

# events — internal event bus and SSE delivery
events:
  enabled: true
  event_buffer_size: 500       # Ring buffer (last N events kept for replay)
  subscriber_queue_size: 100
  sse_enabled: true            # Enable GET /events SSE endpoint
  max_sse_clients: 50

# lcma — cognitive memory layer (retrieval, salience, enrichment)
lcma:
  enabled: true
  temperature_default: 0.5
  temperature_edge_threshold: 50
  enrich_drain_interval_minutes: 5
  max_enrich_attempts: 3
  wm_eviction_days: 7              # working-memory eviction
  decay_inactive_days: 7
  sweep_interval_hours: 24
  sweep_startup_delay_minutes: 10
  entity_max_per_doc: 50           # 0 disables entity extraction

  # Scout rerank weights — must sum to ~1.0; unknown keys rejected,
  # missing keys filled from defaults and renormalized
  rerank_weights:
    vector: 0.21
    lexical: 0.22
    exact_alias: 0.10
    tags_recency: 0.07
    freshness: 0.04
    provenance: 0.04
    task_context: 0.04
    graph: 0.13
    coactivation: 0.10
    source_url: 0.05

  # Ranking priors by note_type
  note_type_priors:
    agent_finding: 0.6
    summary: 0.55
    hypothesis: 0.5
    observation: 0.5
    concept: 0.45
    task_record: 0.35

  # Salience dynamics
  salience_floor: 0.3              # decay never drops below this
  salience_decay_per_day: 0.005
  salience_decay_daily_cap: 0.1
  salience_cited_boost: 0.02
  salience_consolidation_boost: 0.01
  salience_misleading_penalty: 0.05
  salience_ignored_penalty: 0.02

  # Rerank composite weights
  rerank_salience_weight: 0.1
  rerank_note_type_weight: 0.1
  rerank_usage_weight: 0.1

  # Usage signal (non-decaying popularity)
  usage_freq_weight: 0.6
  usage_recency_weight: 0.4
  usage_recency_halflife_days: 14.0
  usage_freq_norm_k: 20.0

  # llm — background LLM synthesis (edge inference). Enabled iff base_url
  # is set; leaving it unset (or blank) is the operational kill switch.
  llm:
    base_url: null               # OpenAI-compatible /v1/chat/completions endpoint
    model: ""                    # required when base_url is set
    api_key: null                # never echoed in errors or logs
    timeout_seconds: 120.0
    max_output_tokens: 4096
    daily_token_budget: 250000
    max_calls_per_drain: 10
    confidence_floor: 0.6
    neighbour_k: 5
    min_similarity: 0.35
    max_similarity: 0.92
    snippet_chars: 700
```

---

## Key Settings Explained

### `storage.data_dir`

The root of your knowledge base. Structure inside:

```
data/
├── knowledge/          ← your Markdown files (back this up!)
├── .lithos/            ← SQLite stores (back this up!)
│   ├── coordination.db   — tasks, claims, findings, agents
│   ├── edges.db          — agent-asserted typed edges (source of truth)
│   ├── stats.db          — salience, receipts, working memory
│   └── read_audit.jsonl  — read-access audit log
├── .tantivy/           ← full-text index (rebuildable)
├── .chroma/            ← vector embeddings (rebuildable)
└── .graph/             ← wiki-link graph cache (rebuildable)
```

!!! warning "Back up `knowledge/` and `.lithos/`"
    Only these two contain data that cannot be regenerated. The index directories are derived from the Markdown files and can always be rebuilt with `lithos reindex --clear`.

### `search.embedding_model`

The sentence-transformers model used for semantic search. `all-MiniLM-L6-v2` is a good balance of quality and speed (~90 MB, runs on CPU). For higher quality at the cost of more RAM:

- `all-mpnet-base-v2` — better quality, ~420 MB
- `paraphrase-multilingual-MiniLM-L12-v2` — multilingual

!!! note
    Changing the embedding model requires a full reindex: `lithos reindex --clear`

### `search.device`

Where embeddings are computed: `auto` (default — uses CUDA when available), `cpu`, or an explicit CUDA device like `cuda:0`.

### `coordination.claim_default_ttl_minutes`

How long a task claim lasts before expiring. Agents should renew claims with `lithos_task_renew` for long-running work. Expired claims are automatically excluded from query results.

### `lcma.llm` — background synthesis

When `base_url` points at any OpenAI-compatible chat-completions endpoint (Ollama, llama.cpp, vLLM, or a hosted provider), the background enrichment worker uses it to infer typed edges between semantically-close notes, writing qualifying judgements into `edges.db` with `provenance_type: "inferred"`. Spend is bounded by `daily_token_budget` and `max_calls_per_drain`. **Unset `base_url` disables all LLM calls** — Lithos never contacts an LLM unless you configure one.

---

## Environment Variables

Nested form (canonical): `LITHOS_<SECTION>__<FIELD>` — e.g. `LITHOS_SERVER__PORT`, `LITHOS_SEARCH__DEVICE`, `LITHOS_LCMA__LLM__API_KEY`.

Flat shortcuts and other variables read directly:

| Variable | Description |
|----------|-------------|
| `LITHOS_CONFIG` | Path to config YAML |
| `LITHOS_DATA_DIR` | Override `storage.data_dir` |
| `LITHOS_PORT` / `LITHOS_HOST` | Override server port/host |
| `LITHOS_LOG_LEVEL` | Logging level (`debug`, `info`, `warning`, `error`) |
| `LITHOS_LOG_FORMAT` | `text` reverts the default single-line JSON logging to plain text |
| `LITHOS_ENVIRONMENT` | Shortcut for `telemetry.environment` (OTEL `deployment.environment`) |
| `LITHOS_OTEL_ENABLED` | Shortcut for `telemetry.enabled` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector endpoint (also `_TRACES_`/`_METRICS_`/`_LOGS_` variants) |

---

## Docker Configuration

When using Docker Compose, environment variables are the cleanest way to configure Lithos:

```yaml
# docker-compose.override.yml
services:
  lithos:
    environment:
      LITHOS_LOG_LEVEL: info
      LITHOS_LCMA__LLM__BASE_URL: http://host.docker.internal:11434/v1
      LITHOS_LCMA__LLM__MODEL: qwen2.5:14b
```

The compose file mounts `${LITHOS_DATA_PATH:-./data}` at `/data` and passes the `LITHOS_LCMA__LLM__*` family through to the container. See [Docker deployment](../deployment/docker.md).

---

## Multiple Instances

You can run multiple Lithos instances with different data directories — for example, one per team or environment:

```bash
lithos --data-dir /data/team-a serve --transport http --port 8765
lithos --data-dir /data/team-b serve --transport http --port 8766
```

Each instance is fully independent. For Docker, `docker/run.sh <env>` runs named prod/staging/fuzz stacks side by side — see [Docker deployment](../deployment/docker.md).
