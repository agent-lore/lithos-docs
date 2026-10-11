# Operations

This page covers the operator-facing surfaces as the code implements them: the admin HTTP API, readiness, the local run ledger, logging, OpenTelemetry export and webhook notifications. For symptom-driven troubleshooting — failed runs, log shapes, squatter cleanup, the weekly review — use the [Runbook](runbook.md), which is the Influx repo's `docs/operations/runbook.md` imported at build time.

## Admin HTTP API

`influx serve` binds FastAPI to `INFLUX_ADMIN_BIND_HOST:INFLUX_ADMIN_PORT` (default `127.0.0.1:8080`). There is no authentication: a non-loopback bind is refused unless `[security] allow_remote_admin = true`.

| Method and path | Returns |
|-----------------|---------|
| `GET /live` | `200 {"live": true}` while the process is up |
| `GET /ready` | `200 {"ready": true}` when cached probes pass, else `503 {"ready": false}` |
| `GET /status` | Always `200`: `status`, `ready`, `version`, `dependencies.lithos.status`, `dependencies.llm_credentials.status`, per-profile `{scheduled, currently_running, next_run_at, last_run_at, last_run_status}`, and an `inbox` block when the inbox is enabled |
| `GET /runs/recent?limit=20&profile=<name>` | `{"active": [...], "runs": [...]}` from the run ledger |
| `POST /runs` | Body `{"profile": "<name>"}` **or** `{"all_profiles": true}`. `202` with `request_id`, `kind`, `scope`, `submitted_at` |
| `POST /backfills` | Body `{"profile"|"all_profiles", "days"|("from","to"), "confirm"?}`. Same `202` shape |

Health endpoints read **cached** state from the probe loop and the last inbox tick; they never probe Lithos or list tasks per request.

Error responses are compact JSON aligned with the Lithos envelope:

```json
{"status": "invalid_request", "error": "unknown_profile", "message": "Unknown profile: 'x'", "reason": "unknown_profile"}
```

| Status | `error` | When |
|--------|---------|------|
| `422` | `unknown_profile`, `invalid_request` | Profile not in config; body fails validation (`detail` lists the errors) |
| `409` | `profile_busy` | The profile's coordinator lock is held; includes `active_run` from the ledger when known |
| `400` | `confirm_required` | Backfill estimate above 1000 without `confirm`; includes `estimated_items` |

`all_profiles` acquires every profile lock all-or-nothing: if any profile is busy, locks already taken are released and the request is `409`. There is no cancel endpoint; restarting the service marks in-flight ledger entries `abandoned`.

---

## Readiness and probes

A background `ProbeLoop` runs every 30 seconds and caches:

- **Lithos** — opens an SSE connection to `lithos.url` and expects HTTP 200 (no `agent_register` call). After **3 consecutive** degraded cycles the circuit opens and every Run is skipped with ledger `status="skipped", error="lithos_unhealthy"` until the next OK probe.
- **LLM credentials** — presence of each provider's `api_key_env` in the environment (no remote call).
- **LCMA tools** — the Lithos tool list includes the tools Influx needs; otherwise runs skip with `lcma_tools_unavailable`.

`/ready` is `503` when any probe fails, the cached state is stale (older than 3 intervals), a repair-sweep terminal write failure is latched, or the LCMA latch is set. The repair latch clears on the next successful sweep.

---

## Run ledger

Operational history lives under `storage.state_dir` (default `/state`), not in Lithos:

```
<state_dir>/
├── active-runs.json                   # in-flight runs keyed by run_id
├── runs.jsonl                         # append-only terminal history
└── unresolved-slug-collisions.jsonl   # writes that survived the recovery chain
```

Each entry carries `run_id`, `profile`, `kind` (`scheduled` | `manual` | `backfill` | `inbox`), `status` (`running` | `completed` | `failed` | `skipped` | `abandoned`), `run_range`, `started_at`, `completed_at`, `duration_seconds`, `sources_checked`, `ingested`, `cache_hits`, `error`, `degraded` and `degraded_reasons`. Manual runs reuse the HTTP `request_id` as `run_id`; scheduled runs get a UUID. On start-up, leftovers in `active-runs.json` are marked `abandoned`.

`degraded_reasons` values you will see:

| Reason | Meaning |
|--------|---------|
| `source_acquisition` | At least one source fetch failed and was swallowed |
| `archive_acquisition` | At least one archive download failed (note written with `influx:archive-missing`) |
| `source_cooldown_skip` | arXiv or a feed was skipped because it is in cooldown |
| `dedup_cache_lookup` | A `lithos_cache_lookup` failed for a candidate (skipped this run) |
| `ingestion_stall` | This and the previous scheduled run ingested 0 despite candidates |
| `fetch_stall` | This and the previous scheduled run fetched 0 from every source |
| `filter_stall` | Sources fetched normally but the filter rejected everything, twice in a row |
| `filter_error` | The filter scorer raised at least once this run |

The three stall reasons are mutually exclusive on a run; backfills and inbox runs are excluded from stall detection. `scripts/influx-diagnose.py recent|failures|run` read these files directly.

---

## Logging

Logs go to stderr as single-line JSON with the same core fields Lithos uses — `timestamp`, `level`, `logger`, `message` — plus any structured extras (`run_id`, `profile`, `source_url`, `status`, `detail`, `note_id`, `sweep_stage`, …). `httpx`/`httpcore` are quietened to WARNING.

```bash
INFLUX_LOG_LEVEL=DEBUG     # Python level name; default INFO
INFLUX_LOG_FORMAT=text     # plain text for local work; default json
```

With `INFLUX_OTEL_ENABLED=true` the same records are also forwarded to an OTEL `LoggingHandler`, so every `extra` field becomes a log attribute in your collector; the stderr stream is unchanged.

---

## Telemetry

Influx exports traces, metrics and logs by **OTLP push** to a collector you run; nothing is scraped from the process. The feature is opt-in and controlled by environment variables (the `[telemetry]` TOML block is validated but not read by the exporter wiring at the current `main`):

| Variable | Effect |
|----------|--------|
| `INFLUX_OTEL_ENABLED=true` | Turn on all three signals (requires the `otel` extra, which the Docker image installs) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP/HTTP collector base URL; per-signal `OTEL_EXPORTER_OTLP_{TRACES,METRICS,LOGS}_ENDPOINT` also honoured |
| `INFLUX_OTEL_CONSOLE_FALLBACK=true` | With no endpoint set, print spans and metrics to stdout |
| `OTEL_SERVICE_NAME` | `service.name` resource attribute (default `influx`) |
| `INFLUX_ENVIRONMENT` | `deployment.environment` resource attribute (`dev`, `staging`, `prod`) |

When OTEL is disabled every telemetry call is a boolean check and returns; no SDK objects are built. Spans cover the run, source fetches, archive downloads, enrichment calls, Lithos writes and retrieves.

Metric instruments (label values are bounded; per-item ids are never labels):

| Instrument | Type | Labels |
|------------|------|--------|
| `influx_run_starts_total` | counter | `profile`, `run_type` |
| `influx_run_completions_total` | counter | `profile`, `run_type`, `outcome` (`success` \| `failure` \| `degraded`) |
| `influx_run_duration_seconds` | histogram | `profile`, `run_type` |
| `influx_active_runs` | up-down counter | `profile` |
| `influx_runs_skipped_total` | counter | `profile`, `reason` |
| `influx_source_candidates_fetched_total` | counter | `profile`, `source` |
| `influx_articles_filtered_total` | counter | `profile`, `decision` (`pass` \| `drop`) |
| `influx_articles_inspected_total` | counter | `profile`, `source` |
| `influx_cache_hits_total` | counter | `profile`, `source` |
| `influx_lithos_writes_total` | counter | `profile`, `source`, `status` |
| `influx_repair_candidates_total` | counter | `profile`, `kind` (`archive` \| `text_extraction` \| `tier2` \| `tier3`) |
| `influx_llm_validation_failures_total` | counter | `profile`, `tier` (`1` \| `3`) |
| `influx_archive_missing_total` | counter | `profile`, `source` |
| `influx_source_acquisition_errors_total` | counter | `profile`, `source`, `kind` |
| `influx_ingestion_stall_runs_total` | counter | `profile`, `reason` |
| `influx_slug_collision_dedup_recovery_total`, `…_reclaimed_total` | counter | none |
| `influx_slug_collision_unresolved_total` | counter | `profile`, `source` |
| `influx_inbox_tick_started_total`, `…_tasks_listed_total`, `…_tasks_claimed_total` | counter | none |
| `influx_inbox_items_processed_total` | counter | `outcome` (`ingested`, `filtered_out`, `cache_hit`, `profile_busy_skipped`, `error`, `invalid_submission`, `invalid_source_tag`, `pdf_rejected`, `filter_unavailable_deferred`, `filter_unavailable`) |
| `influx_inbox_task_call_failures_total` | counter | `phase` (`list` \| `claim` \| `update` \| `release` \| `complete`) |

The runbook's [§7](runbook.md#7-reading-metrics-from-the-otel-backend) gives PromQL for the common questions. The same collector layout used for Lithos ([Observability](../deployment/observability.md)) works for Influx; filter by `service.name`.

---

## Notifications

After a completed run (never after a backfill; inbox runs only for sinks that list `inbox` in `notify_on`) Influx POSTs to each enabled `[[notifications.webhooks]]` sink whose `notify_on` includes the run kind. Delivery goes through the guarded HTTP client with `notifications.timeout_seconds`, follows no redirects, and counts only `2xx` as success — a `302 /login` is logged as a failure. Failures never fail the run.

| Type | Event modes | Payload |
|------|-------------|---------|
| `generic_digest` | `digest` | Zero-ingest run: quiet digest with message and stats. Otherwise `highlights` (items with `score >= notify_immediate`), `all_ingested`, `stats.high_relevance` |
| `agent_zero_message_async` | `digest`, `article` | `{"text", "context"}` to Agent Zero's `/api/message_async` (session-authenticated when Agent Zero login is on) |
| `agent_zero_notification_create` | `article` | One toast payload per matching article |
| `agent_zero_rfc_message` | `digest`, `article` | `{"rfc_input", "hash"}` to `/api/rfc`, naming `rfc_module`.`rfc_function` with `text` and `context`; the shared secret comes from `rfc_password_env`. The helper to deploy inside Agent Zero is `integrations/agent_zero/usr/influx_rfc.py` (see the repo's `docs/AGENT_ZERO_RFC.md`) |
| `openclaw_agent` | `digest`, `article` | `{"message", "name", "deliver"}` plus `wakeMode` and `channel` when set, to OpenClaw's `/hooks/agent` |

Bearer tokens come from `auth_token_env`; a sink whose token variable is unset is skipped with a warning. The legacy `notifications.webhook_url` sends a single `generic_digest` when no typed sinks are configured.

---

## Security boundaries

- **Outbound HTTP** — every fetch and webhook POST passes the guarded client: `http`/`https` only, DNS resolution with private-IP blocking unless `security.allow_private_ips`, streaming size cap (`storage.max_download_bytes`), timeouts, content-type checks, redirect re-validation.
- **Admin bind** — loopback unless `security.allow_remote_admin`.
- **Archive paths** — item ids with traversal or absolute components are rejected; resolved paths must stay under `archive_dir`; inbox `local_path` must resolve under `pdf_root`.
- **Secrets** — only ever named by environment variable (`api_key_env`, `auth_token_env`, `rfc_password_env`), never written in `influx.toml`.
