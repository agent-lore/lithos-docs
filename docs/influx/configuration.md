# Configuration

Influx is configured by a single TOML file validated through Pydantic models (`src/influx/config.py`, root model `AppConfig`). Every field below is listed with the default the code applies when the key is absent. `influx.example.toml` in the repo is the annotated template.

## Discovery and precedence

The file is found in this order; the first match wins:

1. `$INFLUX_CONFIG`
2. `./influx.toml`
3. `~/.influx/influx.toml`
4. `/etc/influx/influx.toml`

A `.env` file in the working directory is loaded before discovery. A small set of environment variables override specific TOML keys **after** the file is read and before validation:

| Environment variable | Overrides | Type |
|----------------------|-----------|------|
| `LITHOS_URL` | `lithos.url` | string |
| `LITHOS_MCP_TRANSPORT` | `lithos.transport` | string |
| `INFLUX_ARCHIVE_DIR` | `storage.archive_dir` | string |
| `INFLUX_OTEL_ENABLED` | `telemetry.enabled` | bool (`true`/`1`/`yes`) |
| `INFLUX_OTEL_CONSOLE_FALLBACK` | `telemetry.console_fallback` | bool |
| `INFLUX_ENVIRONMENT` | `telemetry.environment` | string |

Other runtime knobs are environment-only and never appear in the TOML: `INFLUX_ADMIN_BIND_HOST`, `INFLUX_ADMIN_PORT`, `INFLUX_LOG_FORMAT`, `INFLUX_LOG_LEVEL`, and the standard `OTEL_EXPORTER_OTLP_*` / `OTEL_SERVICE_NAME` variables (see [Operations](operations.md)).

Validation failures raise `ConfigError` with the offending key. Unknown keys under `[prompts]` and on RSS entries are rejected; elsewhere unknown keys are ignored.

---

## `[influx]`

| Field | Default | Description |
|-------|---------|-------------|
| `note_schema_version` | `1` | Stamped on every note as the `schema:<n>` tag; printed by `influx migrate-notes` |

## `[lithos]`

| Field | Default | Description |
|-------|---------|-------------|
| `url` | `""` | The Lithos `/sse` endpoint, e.g. `http://localhost:8765/sse`. Empty skips the `validate-config` dry-connect; `serve` then reports Lithos as degraded |
| `transport` | `"sse"` | Only `"sse"` is accepted; any other value raises `ConfigError` before connecting |

!!! note
    `influx.example.toml` does not contain a `[lithos]` block. Add one or set `LITHOS_URL`.

## `[schedule]`

| Field | Default | Description |
|-------|---------|-------------|
| `cron` | `"0 6 * * *"` | Cron expression for the single `influx-tick` job that runs every profile |
| `timezone` | `"UTC"` | Timezone for `cron` |
| `misfire_grace_seconds` | `3600` | A missed fire within this window still runs (APScheduler `misfire_grace_time`, `coalesce=True`) |
| `shutdown_grace_seconds` | `30` | Bound on graceful shutdown of in-flight runs |
| `initial_jitter_seconds` | `0` | Uniform random delay `[0, N]` before a tick's fan-out, to avoid hour-boundary arXiv 429 clusters |
| `inter_profile_gap_seconds` | `0` | Gap between profiles within one tick; profiles always run sequentially in config order |

Both jitter fields must be non-negative. All profiles share one cron expression; per-profile cadence is not supported.

## `[storage]`

| Field | Default | Description |
|-------|---------|-------------|
| `archive_dir` | `"/archive"` | Root for archived PDFs/HTML; note `## Archive` paths are relative to it |
| `state_dir` | `"/state"` | Run ledger (`active-runs.json`, `runs.jsonl`) and `unresolved-slug-collisions.jsonl` |
| `retain_days` | `3650` | Declared retention; **no pruning worker exists yet**, so nothing is deleted |
| `max_download_bytes` | `52_428_800` | Streaming cap on any fetched document (50 MB) |
| `download_timeout_seconds` | `30` | Timeout for PDF/HTML downloads (arXiv API discovery uses `resilience.arxiv_api_timeout_seconds`) |

### `[storage.archive_policy]`

Per-domain archive acquisition policy. Each map is `"<host suffix>" = "<operator note>"`; the note is free text for diagnostics.

| Field | Default | Effect on a matching domain |
|-------|---------|-----------------------------|
| `blocked` | `{}` | Attempt the download but expect 403/WAF; failures tag `influx:archive-blocked` + `influx:archive-terminal` so the repair sweep stops retrying |
| `rate_limited` | `{}` | Attempt but expect 429; failures tag `influx:archive-rate-limited` and stay in the repair loop with a cool-down |
| `skip` | `{}` | Never attempt; tag `influx:archive-skipped-by-policy` + `influx:archive-missing`; still counts as a degraded run |
| `unsupported` | `{}` | Never attempt; tag `influx:archive-unsupported` + `influx:archive-terminal`, **not** `archive-missing`, so the run is not degraded |
| `include_defaults` | `true` | Merge the built-in list (`science.org`, `alignmentforum.org`, `therobotreport.com`, `tnmoc.org`, `lesswrong.com`, …) under your overrides |

## `[notifications]`

| Field | Default | Description |
|-------|---------|-------------|
| `timeout_seconds` | `5` | Timeout for every outbound webhook call |
| `webhook_url` | `""` | Legacy single sink: when set and `webhooks` is empty, one `generic_digest` is sent here |
| `webhooks` | `[]` | List of typed sinks, see below |

### `[[notifications.webhooks]]`

| Field | Default | Description |
|-------|---------|-------------|
| `name` | required | `^[a-z0-9][a-z0-9-]{0,63}$`, unique across sinks |
| `type` | required | `generic_digest` \| `agent_zero_message_async` \| `agent_zero_notification_create` \| `agent_zero_rfc_message` \| `openclaw_agent` |
| `url` | required | `http` or `https` only |
| `enabled` | `true` | |
| `notify_on` | `["manual", "scheduled"]` | Run kinds that trigger this sink: `scheduled`, `manual`, `backfill`, `inbox`. Must be non-empty |
| `event_mode` | `"digest"` | `digest` = one call per run; `article` = one call per ingested article with `score >= min_score` |
| `min_score` | unset | Article-mode score floor |
| `auth_token_env` | `""` | Env var holding a bearer token; a missing token skips the sink with a warning |
| `context` | `""` | Agent Zero context name; **required** for `agent_zero_message_async` and `agent_zero_rfc_message` |
| `rfc_module`, `rfc_function`, `rfc_password_env` | `""` | **Required** for `agent_zero_rfc_message` (e.g. `usr.influx_rfc`, `enqueue_message`, `AGENT_ZERO_RFC_PASSWORD`) |
| `deliver` | `false` | OpenClaw: deliver to the channel |
| `wake_mode` | `""` | OpenClaw `wakeMode` (e.g. `now`) |
| `channel` | `""` | OpenClaw channel (e.g. `whatsapp`) |
| `sender_name` | `"Influx"` | OpenClaw sender; must be non-empty |

Type constraints enforced at load: `generic_digest` only supports `event_mode = "digest"`; `agent_zero_notification_create` only supports `event_mode = "article"`.

## `[security]`

| Field | Default | Description |
|-------|---------|-------------|
| `allow_private_ips` | `false` | Allow outbound fetches to private/loopback IPs (SSRF guard off) |
| `allow_remote_admin` | `false` | Allow `INFLUX_ADMIN_BIND_HOST` to be a non-loopback address |

---

## `[[profiles]]`

One entry per interest profile. Profiles run sequentially in the order written.

| Field | Default | Description |
|-------|---------|-------------|
| `name` | required | `^[a-z][a-z0-9-]{0,31}$`; becomes the `profile:<name>` tag |
| `description` | `""` | Free text injected into the filter prompt as `{profile_description}` |

### `[profiles.thresholds]`

Scores are 1–10 integers from the filter model.

| Field | Default | Gate |
|-------|---------|------|
| `relevance` | `7` | Minimum score to ingest at all (Tier 1 summary) |
| `full_text` | `8` | Tier 2 full-text extraction |
| `deep_extract` | `9` | Tier 3 deep extraction (needs full text) |
| `notify_immediate` | `8` | Item appears in digest `highlights` |
| `lcma_edge_score` | `0.75` | Minimum `lithos_retrieve` score to upsert a `related_to` edge |

### `[profiles.sources.arxiv]`

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `true` | |
| `categories` | `["cs.AI", "cs.RO", "cs.MA", "cs.NE", "cs.CL", "cs.LO"]` | arXiv categories queried |
| `max_results_per_category` | `200` | Per category per fetch; also drives the backfill estimate |
| `lookback_days` | `3` | Client-side date window (3 tolerates weekend release gaps) |

### `[[profiles.sources.rss]]`

| Field | Default | Description |
|-------|---------|-------------|
| `name` | required | Must slugify to a non-empty `feed-slug:` tag |
| `url` | required | `http`/`https` only |
| `source_tag` | required | `"rss"` or `"blog"`; selects the archive subtree and `source:<tag>` |

Unknown keys on an RSS entry are rejected.

---

## `[providers.<name>]`

| Field | Default | Description |
|-------|---------|-------------|
| `base_url` | required | OpenAI-compatible root, e.g. `https://openrouter.ai/api/v1` |
| `api_key_env` | `""` | Env var holding the key; when non-empty it must be set at load time (except under `serve`, where the probe loop reports it instead) |
| `extra_headers` | `{}` | Sent on every call — e.g. OpenRouter's `HTTP-Referer` / `X-OpenRouter-Title` for spend attribution |

## `[models.<slot>]`

Slots in use: `filter`, `enrich`, `extract`.

| Field | Default | Description |
|-------|---------|-------------|
| `provider` | required | Key into `[providers]` |
| `model` | required | Model identifier as the provider expects it |
| `temperature` | `0.0` | |
| `max_tokens` | unset | |
| `request_timeout` | `30` | Seconds |
| `max_retries` | `2` | |
| `json_mode` | `false` | Send `response_format = {"type": "json_object"}`; `validate-config` dry-calls slots with this on |
| `json_schema_strict` | `false` | Use OpenAI structured outputs pinned to the slot's Pydantic schema; only for providers that support it |

## `[prompts.<key>]`

All three keys are required; unknown keys are rejected. Each entry has exactly one of `text` (inline) or `path` (file; relative paths resolve against the config file).

| Key | Model slot | Required template variables |
|-----|-----------|-----------------------------|
| `filter` | `filter` | `{profile_description}`, `{negative_examples}`, `{min_score_in_results}` |
| `tier1_enrich` | `enrich` | `{title}`, `{abstract}`, `{profile_summary}` |
| `tier3_extract` | `extract` | `{title}`, `{full_text}` |

---

## `[filter]`

| Field | Default | Description |
|-------|---------|-------------|
| `batch_size` | `25` | Candidates per filter LLM call |
| `min_score_in_results` | `6` | Passed to the prompt; the model omits lower-scoring items from its reply |
| `negative_example_max_title_chars` | `200` | Truncation for negative-example titles |

## `[extraction]`

| Field | Default | Description |
|-------|---------|-------------|
| `min_html_chars` | `1000` | arXiv HTML extraction shorter than this falls back to PDF |
| `min_web_chars` | `500` | Web article extraction shorter than this falls back to the feed summary |
| `min_summary_chars` | `80` | Thin-summary suppression: an item whose archive failed **and** whose summary is shorter than this is dropped entirely; `0` disables the length rule only |
| `strip_tags` | `["script", "iframe", "object", "embed"]` | Removed before text extraction |

## `[resilience]`

| Field | Default | Description |
|-------|---------|-------------|
| `max_retries` | `5` | Transient network / 5xx retries |
| `backoff_base_seconds` | `1` | Exponential backoff base |
| `arxiv_request_min_interval_seconds` | `3` | Per-process minimum spacing between arXiv requests |
| `arxiv_429_backoff_seconds` | `30` | Base delay on HTTP 429, doubling per retry |
| `arxiv_429_backoff_max_seconds` | `120` | Cap on the doubled delay and on honoured `Retry-After` |
| `arxiv_429_max_retries` | `5` | Separate retry budget for 429 |
| `arxiv_429_cooldown_threshold` | `3` | Consecutive exhausted-429 fetches before entering cooldown; `0` disables |
| `arxiv_429_cooldown_seconds` | `900` | Cooldown length; arXiv fetches are skipped with reason `source_cooldown_skip` |
| `rss_timeout_cooldown_threshold` | `3` | Consecutive timeouts on one feed URL before cooling it down; `0` disables |
| `rss_timeout_cooldown_seconds` | `1800` | Per-feed cooldown length |
| `lithos_write_conflict_max_retries` | `1` | Re-read-and-merge attempts on `version_conflict` |
| `arxiv_api_timeout_seconds` | `60` | Timeout for `export.arxiv.org/api/query`; must be positive |

Cooldown state is process-local; a restart clears it.

## `[feedback]`

| Field | Default | Description |
|-------|---------|-------------|
| `negative_examples_per_profile` | `20` | Recent `influx:rejected:<profile>` titles pulled into the filter prompt |
| `recalibrate_after_runs` | `7` | Emit the per-tag rejection-rate log line every N runs per profile |

## `[repair]`

| Field | Default | Description |
|-------|---------|-------------|
| `max_items_per_run` | `100` | Repair-needed notes visited per run, oldest `updated_at` first |

## `[telemetry]`

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `false` | |
| `console_fallback` | `false` | |
| `service_name` | `"influx"` | |
| `environment` | unset | |
| `export_interval_ms` | `30000` | |

!!! warning "Environment variables are what the exporter reads"
    At the current `main` the telemetry module checks `INFLUX_OTEL_ENABLED`, `INFLUX_OTEL_CONSOLE_FALLBACK`, `OTEL_SERVICE_NAME`, `INFLUX_ENVIRONMENT` and `OTEL_EXPORTER_OTLP_*` directly. The `[telemetry]` TOML fields are parsed and validated but are not consulted when wiring the exporters, so set the environment variables. See [Operations](operations.md#telemetry).

## `[inbox]`

Opt-in agent submission channel; see [Inbox](inbox.md).

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `false` | Register the `influx-inbox-tick` scheduler job |
| `poll_cron` | `"*/5 * * * *"` | Tick cadence; validated as a cron expression at load |
| `timezone` | `"UTC"` | |
| `max_items_per_tick` | `20` | Tasks claimed and processed per tick; `>= 1` |
| `agent_id` | `"influx-inbox"` | Lithos agent used for task claim/update/complete |
| `pdf_root` | unset | Directory under which `kind="pdf"` `local_path` values must resolve; must exist. Unset disables local-PDF intake |
| `filter_unavailable_max_retries` | `48` | Deferrals before an unscorable item completes with `error: filter_unavailable`; `0` = no deferral |
| `filter_unavailable_backoff_minutes` | `15` | First deferral; doubles per attempt; `>= 1` |
| `filter_unavailable_backoff_max_minutes` | `240` | Backoff ceiling; must be `>=` the base |

The task tag `influx:inbox` is a protocol constant and cannot be changed.
