# CLI Reference

The `influx` command (entry point `influx.main:main`, argparse) has five subcommands. Three of them (`validate-config`, `serve`, `migrate-notes`) work on the config file directly; `run` and `backfill` are HTTP clients for a running `influx serve` and do nothing without it.

```
usage: influx [-h] {validate-config,migrate-notes,serve,run,backfill} ...
```

Run it as `uv run influx …` from a checkout, or `influx …` inside the Docker container (`docker compose exec influx influx --help`). An unknown subcommand, or no subcommand, exits `64`.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success / request accepted |
| `1` | Partial or conflict — the profile is already running (`409`) |
| `2` | Runtime failure — config error, failed dry-call, network error, unexpected response |
| `64` | Usage error — unknown command, bad `--days`/`--from`/`--to` combination, or `confirm_required` without `--confirm` |

## Environment

| Variable | Default | Used by |
|----------|---------|---------|
| `INFLUX_CONFIG` | discovery order | All commands; see [Configuration](configuration.md#discovery-and-precedence) |
| `INFLUX_ADMIN_BIND_HOST` | `127.0.0.1` | `serve` bind host |
| `INFLUX_ADMIN_PORT` | `8080` | `serve` bind port **and** the port `run`/`backfill` connect to on `127.0.0.1` |
| `INFLUX_LOG_LEVEL` | `INFO` | `serve` |
| `INFLUX_LOG_FORMAT` | `json` | `serve`; `text` for plain logs |

---

## `validate-config`

```bash
influx validate-config
```

Loads and validates `influx.toml`, prints the effective configuration as JSON to stdout, then performs two live checks:

1. **JSON-mode dry calls.** For every `[models.*]` slot with `json_mode = true`, sends a one-token `/chat/completions` request with `response_format = {"type": "json_object"}` to the slot's provider. A missing provider, a network error, or an HTTP 4xx/5xx reply prints the provider's error message and exits `2`.
2. **Lithos dry-connect.** If `lithos.url` is set, opens the SSE connection and calls `lithos_agent_register`. Skipped when the URL is empty.

Provider API keys named by `api_key_env` must be set, or loading fails before either check.

---

## `serve`

```bash
influx serve
```

Takes no flags. Starts uvicorn with the FastAPI admin API, the probe loop and the scheduler (plus the inbox tick when `[inbox] enabled`). Config is loaded with `check_api_keys=False` — missing keys are reported by the probe loop in `/status` rather than preventing start-up.

Refuses to start if the bind host is not a loopback address and `security.allow_remote_admin` is false. Handles SIGINT and SIGTERM itself, drains in-flight runs within `schedule.shutdown_grace_seconds`, and exits `0` on either signal.

Endpoints are described under [Operations](operations.md#admin-http-api).

---

## `run`

```bash
influx run --profile <name>
```

| Option | Required | Description |
|--------|----------|-------------|
| `--profile` | yes | Profile name from `[[profiles]]` |

Sends `POST /runs {"profile": "<name>"}` to `http://127.0.0.1:$INFLUX_ADMIN_PORT`. On `202` prints the `request_id` and exits `0`; on `409` (profile busy) prints `influx: profile '<name>' is busy` and exits `1`; connection errors and other responses exit `2`. The run itself proceeds in the background of the service — watch its logs or `GET /runs/recent`.

There is no `--all-profiles` flag; use `POST /runs {"all_profiles": true}` directly.

---

## `backfill`

```bash
influx backfill --profile <name> --days <n> [--confirm]
influx backfill --profile <name> --from <YYYY-MM-DD> --to <YYYY-MM-DD> [--confirm]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--profile` | yes | Profile name |
| `--days` | one of | Number of days back from now |
| `--from`, `--to` | one of | ISO date range (both required together) |
| `--confirm` | no | Accept a large backfill |

`--days` and `--from/--to` are mutually exclusive and validated locally (exit `64`). The command sends `POST /backfills` **without** `confirm`, even when `--confirm` was given. If the server estimates more than 1000 items (`days × categories × max_results_per_category`) it replies `400 confirm_required`:

- without `--confirm`: prints `Estimated <n> items. Re-run with --confirm to proceed.` and exits `64`;
- with `--confirm`: re-POSTs with `"confirm": true` and prints the `request_id`.

Busy profile → exit `1`; network/unexpected → exit `2`. Backfills skip the repair sweep, skip every item already in Lithos, and send no notifications.

---

## `migrate-notes`

```bash
influx migrate-notes
```

Prints `note_schema_version: <n>` from `[influx]` and exits `0`. There is no migration logic behind it yet; the command exists so the schema version is queryable.

---

## Operator scripts

Three scripts under `scripts/` complement the CLI. Each takes `--env <name>` (default `staging`) and reads `docker/.env.<name>` for the container name, admin port, state path and Lithos URL, so the same invocation works against any environment.

### `influx-diagnose.py`

The runbook's toolbox. Read-only by default: no HTTP POSTs, no `docker exec`, no ledger writes.

| Subcommand | Purpose |
|------------|---------|
| `recent` | Recent terminal run-ledger entries |
| `failures` | Recent failed or degraded runs |
| `run RUN_ID` | One run's ledger entry plus matching log lines |
| `warnings` | WARNING/ERROR container log lines, filterable by run id |
| `terminal-flips` | Per-stage terminal-flip events with note ids |
| `squatters` | Lithos docs squatting slugs that block writes; deletes only with `--apply --yes <doc-id>` |
| `slug-collision-backlog` | Entries in `unresolved-slug-collisions.jsonl` |
| `invalid-source` | Audit notes tagged `influx:source-invalid`; `--apply` reconstructs or tombstones |
| `promotion-gate` | PASS/FAIL on recent scheduled-run health (exit 0/1 for CI) |
| `feed-yield` | Notes ingested per RSS feed; finds dead and silent feeds |
| `cancel` | Prints the restart command for aborting a run (never sends it) |

### `influx-report.py`

```bash
scripts/influx-report.py --env staging --limit 10 [--base-url http://127.0.0.1:18080]
```

Calls `/status` and `/runs/recent` and prints readiness, version, per-profile scheduler state, active and recent runs, archive file counts, inferred Lithos article-note counts, and the `runs.jsonl` path.

### `influx-inbox-submit.py`

Creates an `influx:inbox` task for a URL or local PDF. Documented on the [Inbox](inbox.md#helper-script-for-humans) page.
