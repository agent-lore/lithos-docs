# Observability

Lithos ships with structured JSON logging, OpenTelemetry tracing and metrics, and a read-audit log. Telemetry is **push-only OTLP**: everything flows to a collector you run — there is no `/metrics` scrape endpoint on the Lithos process.

---

## Structured Logging

All log output is **structured JSON** by default (single-line, via `python-json-logger`). Control it with environment variables:

```bash
LITHOS_LOG_LEVEL=info   # default; debug | info | warning | error
LITHOS_LOG_FORMAT=text  # revert JSON logging to plain text (local dev)
```

Example log entry:

```json
{
  "timestamp": "2026-09-05T06:00:00.123Z",
  "level": "INFO",
  "logger": "lithos.knowledge",
  "message": "document written",
  "document_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "agent": "research-agent",
  "trace_id": "1234abcd",
  "span_id": "5678ef01"
}
```

`trace_id` and `span_id` are populated automatically when OTEL tracing is enabled, enabling correlation between traces and log lines in tools like Grafana Loki. Health-check requests are filtered out of the logs.

In Docker, redirect logs to your preferred log aggregator:

```yaml
# docker-compose.override.yml
services:
  lithos:
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"
```

---

## OpenTelemetry: Push-Only Model

All telemetry (traces, metrics, logs) is exported via OTLP/HTTP to an external collector:

```
Lithos ──OTLP push──▶ OTEL Collector ──▶ Prometheus (metrics)
                                     ──▶ Tempo (traces)
                                     ──▶ Loki (logs)
```

Enable export:

```bash
LITHOS_TELEMETRY__ENABLED=true            # or LITHOS_OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
OTEL_SERVICE_NAME=lithos
LITHOS_ENVIRONMENT=production             # → deployment.environment label
```

Per-signal overrides are supported (`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, `_METRICS_`, `_LOGS_`). The shipped Docker compose enables OTLP export by default, pointed at `http://host.docker.internal:4318`.

Spans are created for every MCP tool call (`lithos.tool.<name>`), LCMA pipeline stages (scouts, rerank, enrichment), embedding operations, index writes/queries, and SSE connect/replay.

### Developer shortcut: `--telemetry-console`

For local debugging without a collector, the global `--telemetry-console` option streams spans and metrics to stdout:

```bash
lithos --telemetry-console serve --transport http --port 8765
lithos --telemetry-console reconcile   # works for any command
```

---

## Metrics

Metric names are **dotted OTEL names** at the source; the collector's Prometheus exporter renders them with underscores (e.g. `lithos.tool.calls` → `lithos_tool_calls_total`), which is what your PromQL sees.

### Counters and histograms

| Metric | Type | Description |
|--------|------|-------------|
| `lithos.tool.calls` / `lithos.tool.errors` | Counter | MCP tool calls / errors, labelled by tool |
| `lithos.knowledge.operations` | Counter | Knowledge operations by kind |
| `lithos.knowledge.write_duration_ms` | Histogram | Write latency |
| `lithos.search.operations` / `lithos.search.duration_ms` | Counter / Histogram | Search calls and latency |
| `lithos.cache.lookups` / `lithos.cache.lookup_duration_ms` | Counter / Histogram | `lithos_cache_lookup` traffic |
| `lithos.coordination.operations` | Counter | Task/claim/finding operations |
| `lithos.event_bus.operations` / `lithos.event_bus.subscriber_drops` | Counter | Bus traffic and slow-subscriber drops |
| `lithos.sse.events_delivered` | Counter | SSE events delivered |
| `lithos.file_watcher.events_total` | Counter | Filesystem events processed |
| `lithos.reconcile.operations` | Counter | Reconcile runs |
| `lithos.startup_duration` | Histogram | Server startup time |
| `lithos.fts_index.dropped_total` | Counter | Documents the full-text indexer failed to index |
| `lithos.lcma.retrieve.duration_ms` | Histogram | `lithos_retrieve` end-to-end latency |
| `lithos.lcma.retrieve.candidates_considered` / `.final_nodes` | Histogram | Retrieval funnel sizes |
| `lithos.lcma.scout.duration_ms` / `.candidates` | Histogram | Per-scout latency and yield |
| `lithos.lcma.scout.failures` | Counter | **Alertable** — a scout's backend raised (labelled by scout); pairs with the `degraded` flag on `lithos_retrieve` responses |
| `lithos.lcma.salience.updates` | Counter | Reinforcement feedback applied |
| `lithos.lcma.enrich_queue.processing_lag_ms` / `.attempts` / `lithos.lcma.enrich.exhausted` | Histogram / Counter | Background enrichment health |
| `lithos.lcma.llm.calls` / `.tokens` / `.call_duration_ms` | Counter / Histogram | LLM synthesis spend and latency |
| `lithos.lcma.edge_inference.skips` / `.edges_written` | Counter | Typed-edge inference outcomes |

### Gauges (observable)

| Metric | Description |
|--------|-------------|
| `lithos.knowledge.document_count` / `.stale_document_count` | Corpus size and staleness |
| `lithos.search.tantivy_document_count` / `.chroma_chunk_count` | Index sizes (drift shows here) |
| `lithos.graph.node_count` / `.edge_count` | Wiki-link graph size |
| `lithos.coordination.active_claims` | Open claims |
| `lithos.agents.active_count` | Registered agents |
| `lithos.sse.active_clients` | Connected SSE clients |
| `lithos.event_bus.buffer_utilisation` | Ring-buffer fill fraction (0–1) |
| `lithos.lcma.salience.mean` / `.fraction_below_floor` / `.node_count` | Salience distribution health |
| `lithos.lcma.enrich_queue.depth` | Pending enrichment items |
| `lithos.lcma.working_memory.active_tasks` / `lithos.lcma.coactivation.pairs` | LCMA activity |

### Collector → Prometheus setup

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

exporters:
  prometheusremotewrite:
    endpoint: http://prometheus:9090/api/v1/write

service:
  pipelines:
    metrics:
      receivers: [otlp]
      exporters: [prometheusremotewrite]
```

### Example PromQL

```promql
# Write latency P99
histogram_quantile(0.99, sum(rate(lithos_knowledge_write_duration_ms_bucket[5m])) by (le))

# Tool call / error rate per tool
sum(rate(lithos_tool_calls_total[1m])) by (tool)
sum(rate(lithos_tool_errors_total[1m])) by (tool)

# Retrieval degradation (alert on this)
sum(rate(lithos_lcma_scout_failures_total[5m])) by (scout)

# Index drift: corpus vs full-text index
lithos_knowledge_document_count - lithos_search_tantivy_document_count

# Event bus health (drops indicate slow subscribers)
rate(lithos_event_bus_subscriber_drops_total[5m])

# LLM synthesis spend
sum(increase(lithos_lcma_llm_tokens_total[1d]))
```

---

## Read Audit Log

Document reads (search results returned, documents fetched) are recorded in an audit log queryable three ways:

- HTTP: [`GET /audit`](../mcp-tools/system.md#get-audit) with `agent_id` / `after` / `limit` / `doc_id` filters
- CLI: `lithos audit --agent <id> --since <iso> -n 100`
- On disk under `<data_dir>/.lithos/`

!!! warning
    `agent_id` values are self-reported by callers and the endpoint is unauthenticated — the audit log is advisory, for usage analysis and debugging retrieval behaviour, never for access control.

---

## Health Signals for Agents

`GET /health` (200/503) is the infrastructure probe; [`lithos_stats`](../mcp-tools/system.md#lithos_stats) is the agent-readable version, returning core counts plus health indicators — `index_drift_detected`, `unresolved_links`, `expired_docs`, `expired_claims`, and per-index last-updated timestamps:

```python
stats = lithos_stats()
if stats["index_drift_detected"]:
    # corpus and full-text index disagree — run `lithos reindex`
    ...
```

`lithos_retrieve` responses additionally carry `degraded` / `failed_scouts`, so an agent can tell partial results from an empty corpus mid-flight.
