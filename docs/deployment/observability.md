# Observability

Lithos v0.1.8 introduces comprehensive observability: structured JSON logging, OpenTelemetry tracing, Prometheus metrics, and read audit logging.

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

Lithos emits OTEL spans for all MCP tool calls. To enable export to an OTEL collector:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
OTEL_SERVICE_NAME=lithos
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
- Each MCP tool call (e.g., `lithos_write`, `lithos_search`)
- Embedding operations
- Index writes and queries
- Graph traversal

!!! tip "Grafana stack"
    If you run Grafana + Tempo + Loki + Prometheus, Lithos integrates with the full stack out of the box:
    - Traces → Tempo via OTLP
    - Logs → Loki (structured JSON, with trace correlation)
    - Metrics → Prometheus scrape endpoint

---

## Prometheus Metrics

Lithos exposes a Prometheus scrape endpoint at `GET /metrics` (added in v0.1.8).

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

### Prometheus Scrape Config

```yaml
# prometheus.yml
scrape_configs:
  - job_name: lithos
    static_configs:
      - targets: ["localhost:8765"]
    metrics_path: /metrics
```

### Grafana Dashboard

Example PromQL queries for a Grafana dashboard:

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
