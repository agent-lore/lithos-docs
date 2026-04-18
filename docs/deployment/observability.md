# Observability

Lithos v0.1.8 introduced comprehensive observability: structured JSON logging, OpenTelemetry tracing, Prometheus metrics, and read audit logging. v0.2.1 extends this with full LCMA pipeline metrics coverage and the `--telemetry-console` developer shortcut.

---

## Structured Logging

All log output is **structured JSON** by default. Set the log level via the `LITHOS_LOG_LEVEL` environment variable:

```bash
LITHOS_LOG_LEVEL=info   # default
LITHOS_LOG_LEVEL=debug  # includes link resolution + slug computation traces
LITHOS_LOG_LEVEL=warn
```

Example log entry:

```json
{
  "timestamp": "2026-04-11T06:00:00.123Z",
  "level": "INFO",
  "logger": "lithos.knowledge",
  "message": "document written",
  "document_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "agent": "research-agent",
  "trace_id": "1234abcd",
  "span_id": "5678ef01"
}
```

`trace_id` and `span_id` are populated automatically when OTEL tracing is enabled (see below), enabling correlation between traces and log lines in tools like Grafana Loki.

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
    environment:
      LITHOS_LOG_LEVEL: info
```

---

## OpenTelemetry Tracing

Lithos uses a **push-only OTEL model**: all telemetry (traces, metrics, logs) is exported via OTLP to an external collector. There is no `/metrics` scrape endpoint — metrics flow through the OTLP pipeline to your collector (e.g. OpenTelemetry Collector → Prometheus remote-write).

To enable export to an OTEL collector:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
OTEL_SERVICE_NAME=lithos
```

Per-signal overrides are supported:

```bash
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://tempo:4318
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://otel-collector:4318
```

Or in Docker:

```yaml
# docker-compose.override.yml
services:
  lithos:
    environment:
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4318
      OTEL_SERVICE_NAME: lithos
      LITHOS_LOG_LEVEL: info
```

Spans are created for:
- Each MCP tool call (e.g., `lithos_write`, `lithos_search`, `lithos_retrieve`)
- LCMA pipeline stages (scouts, rerank, consolidation)
- Embedding operations
- Index writes and queries
- Graph traversal

### Developer shortcut: `--telemetry-console`

For local debugging without a collector, use the `--telemetry-console` flag to stream spans and metrics to stdout:

```bash
lithos serve --transport sse --port 8765 --telemetry-console
```

This enables in-process OTEL console exporters — no `OTEL_EXPORTER_OTLP_ENDPOINT` required.

!!! tip "Grafana stack"
    If you run Grafana + Tempo + Loki + Prometheus, Lithos integrates with the full stack via the OTLP push path:
    - Traces → Tempo via OTLP
    - Logs → Loki (structured JSON, with trace correlation)
    - Metrics → OpenTelemetry Collector → Prometheus remote-write (or direct OTLP receiver)

---

## Metrics

Lithos emits Prometheus-compatible metrics via **OTLP push** — metrics are exported to your OTEL collector, which forwards them to Prometheus (or another metrics backend). There is no direct `/metrics` scrape endpoint.

### Available Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `lithos_knowledge_write_duration_ms` | Histogram | Write operation latency (ms) |
| `lithos_documents_total` | Gauge | Total documents in knowledge base |
| `lithos_chunks_total` | Gauge | Total embedding chunks in ChromaDB |
| `lithos_agents_total` | Gauge | Total registered agents |
| `lithos_open_tasks_total` | Gauge | Current open coordination tasks |
| `lithos_startup_duration_seconds` | Histogram | Server startup duration |
| `lithos_file_watcher_events_total` | Counter | File system events processed |
| `lithos_event_bus_subscriber_drops_total` | Counter | Event bus messages dropped (slow subscriber) |
| `lithos_event_bus_buffer_utilisation` | Gauge | Event bus buffer fill fraction (0–1) |
| `lithos_tool_calls_total` | Counter | MCP tool calls (labelled by tool name) |
| `lithos_tool_errors_total` | Counter | MCP tool errors (labelled by tool name) |
| `lithos_sse_active_clients` | Gauge | Currently connected SSE clients |
| `lithos_sse_events_delivered_total` | Counter | Total SSE events delivered |
| `lithos_lcma_retrieve_duration_ms` | Histogram | LCMA `lithos_retrieve` end-to-end latency |
| `lithos_lcma_scout_hits_total` | Counter | LCMA scout results (labelled by scout type) |
| `lithos_lcma_rerank_duration_ms` | Histogram | LCMA rerank stage latency |

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

### Grafana Dashboard

Example PromQL queries once metrics are flowing via OTLP:

```promql
# Write latency P99
histogram_quantile(0.99, sum(rate(lithos_knowledge_write_duration_ms_bucket[5m])) by (le))

# Tool call rate
sum(rate(lithos_tool_calls_total[1m])) by (tool)

# Error rate per tool
sum(rate(lithos_tool_errors_total[1m])) by (tool)

# SSE clients
lithos_sse_active_clients

# Event bus health (drops indicate slow subscribers)
rate(lithos_event_bus_subscriber_drops_total[5m])

# LCMA retrieve latency P95
histogram_quantile(0.95, sum(rate(lithos_lcma_retrieve_duration_ms_bucket[5m])) by (le))
```

---

## Read Audit Log

Every `lithos_read` call is appended to an audit log at `<data_dir>/.lithos/read_audit.jsonl`.

Example entry:

```json
{"timestamp": "2026-04-11T06:00:00Z", "document_id": "f47ac10b-...", "agent": "research-agent", "path": "python-asyncio-gather-patterns.md"}
```

The audit log is **append-only** and never rotated by Lithos itself. Use standard log rotation (`logrotate`, `cron`) if you need size management.

To tail the audit log in real time:

```bash
tail -f /path/to/data/.lithos/read_audit.jsonl | jq .
```

---

## lithos_stats — Health Indicators

`lithos_stats` now returns a `health` block alongside statistics (added v0.1.8):

```json
{
  "documents": 142,
  "chunks": 1893,
  "agents": 5,
  "active_tasks": 3,
  "open_claims": 2,
  "tags": 48,
  "duplicate_urls": 0,
  "health": {
    "overall": "pass",
    "index": {"status": "pass", "detail": "Tantivy index OK"},
    "embedding": {"status": "pass", "detail": "ChromaDB OK, model loaded"},
    "coordination": {"status": "pass", "detail": "3 active tasks, 2 open claims"}
  }
}
```

Health status values: `"pass"` | `"warn"` | `"fail"`.

Use this from agents to verify the server is fully operational before starting a long batch:

```python
stats = lithos_stats()
if stats.get("health", {}).get("overall") != "pass":
    raise RuntimeError(f"Lithos not healthy: {stats['health']}")
```
