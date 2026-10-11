# Inbox

The inbox lets any agent hand Influx a single URL or PDF for ingestion without knowing about profiles or the admin API. The interface is a **Lithos task**: you create a task tagged `influx:inbox` with a small metadata payload, Influx polls for such tasks, runs the item through the normal pipeline, and completes the task with the result.

!!! tip "Agent skill"
    The `influx-inbox` agent skill in the Lithos repo (`agent-skills/plugins/influx-inbox/`) packages the submission templates and pitfalls below for agents that load skills.

## Enable it

The inbox is off by default. In `influx.toml`:

```toml
[inbox]
enabled = true
poll_cron = "*/5 * * * *"     # how often to poll for open tasks
max_items_per_tick = 20
agent_id = "influx-inbox"
# pdf_root = "/tmp/staging-pdf-inbox"   # only for local-PDF submissions
```

When enabled, `serve` registers a second scheduler job, `influx-inbox-tick`. See [Configuration → `[inbox]`](configuration.md#inbox) for every field.

---

## Submitting a URL

Create the task with [`lithos_task_create`](../mcp-tools/tasks.md#lithos_task_create):

```python
lithos_task_create(
    title="Influx inbox: <descriptive title or URL>",
    agent="<your-agent-id>",
    tags=["influx:inbox"],
    metadata={
        "kind": "url",
        "url": "https://example.com/interesting-article",
        "submitted_by": "<your-agent-id>",
        "title": "Optional title hint",
        "summary": "Optional pre-fetched summary",
        "source_tag": "inbox"
    }
)
```

Keep the returned `task_id`. A public PDF URL works too: the extraction branch is chosen from the response `Content-Type`, not the URL shape.

### Metadata fields

| Field | Required | Validation |
|-------|----------|------------|
| `tags` includes `"influx:inbox"` | yes | Without the tag Influx never sees the task |
| `kind` | yes | Exactly `"url"` or `"pdf"`; anything else completes the task with a terminal error |
| `url` | if `kind="url"` | `http://` or `https://` scheme |
| `local_path` | if `kind="pdf"` | Must resolve inside `[inbox] pdf_root` |
| `submitted_by` | yes | Sanitised to `[A-Za-z0-9:._-]`, truncated to 64 chars; becomes the `submitter:<id>` note tag |
| `source_tag` | no (default `"inbox"`) | `^[a-z0-9][a-z0-9-]{0,31}$`; sets the note's `source:<tag>` only, never the archive path |
| `title` | no | Hint for the candidate title if extraction cannot recover one |
| `summary` | no | Used as the abstract for filter scoring when extraction yields nothing better |
| `force` | no | JSON boolean; anything else is a terminal `invalid_override` |
| `tier` | no | Only `"full"`; anything else is a terminal `invalid_override` |

There is deliberately **no** `profile` field: every enabled profile scores the item, and every profile that clears its own `relevance` threshold contributes an entry to one shared note.

---

## Submitting a local PDF

For PDFs that are only on the Influx host (conference papers, email attachments), set `[inbox] pdf_root` to a directory that exists, mount it at the **same absolute path** in Docker (`INFLUX_INBOX_PDF_ROOT`), and submit:

```python
lithos_task_create(
    title="Influx inbox: research-paper.pdf",
    agent="<your-agent-id>",
    tags=["influx:inbox"],
    metadata={
        "kind": "pdf",
        "local_path": "/tmp/staging-pdf-inbox/research-paper.pdf",
        "submitted_by": "<your-agent-id>",
        "source_tag": "papers"
    }
)
```

A relative `local_path` is resolved against `pdf_root`, never the server's working directory. The file is identified by the SHA-256 of its bytes (synthetic `source_url = inbox-pdf:sha256:<hex>`, so the same file submitted twice dedups to one note), copied to `<archive_dir>/inbox-pdf/YYYY/MM/<sha256>.pdf`, and extracted with pypdf. Influx never deletes the submitted file.

Terminal errors specific to PDFs: `pdf_root_not_configured`, `path_not_in_pdf_root` (after `Path.resolve()`, so `..` and symlinks cannot escape), `file_missing`.

---

## Curated references: `force` and `tier`

By default an inbox item is screened like a feed item — scored by every profile, dropped if none reaches its threshold (usually 7), given full text only at a high score (usually 8+). When you have already decided an item belongs in Lithos in full, add both overrides (ADR 0002):

```python
metadata={
    "kind": "url",
    "url": "https://arxiv.org/abs/1705.05363",
    "submitted_by": "<your-agent-id>",
    "source_tag": "literature",
    "force": true,
    "tier": "full"
}
```

- **`force: true`** — if no profile clears its threshold the note is written anyway, filed under the **top-scoring profile** (ties go to config order; if nothing scored, the first profile whose filter call worked, at score 0). The note is tagged `influx:forced` and its Profile Relevance reason starts `Forced by submitter <id>`, so it never reads as a pass on merit. Every profile is still scored and reported.
- **`tier: "full"`** — the dispatch runs with its `relevance` / `full_text` / `deep_extract` gates lowered to the item's score, so it gets the Tier 1 summary, Tier 2 full text and Tier 3 deep extraction whenever full text can be obtained. An arXiv `abs`/`pdf`/`html` URL is acquired the way the scheduled arXiv source does it: title and abstract from the export API, the PDF archived, text from the HTML → PDF cascade, `arxiv-id:` and `text:*` tags. `notify_immediate` is never lowered.
- `tier` alone does **not** stop an item being filtered out; combine it with `force` for a reference that must land.

!!! warning "Overrides never upgrade an existing note"
    If the URL is already in Lithos (even as a summary-only note), resubmitting with `force`/`tier` does not add full text to it. Overrides also do not bypass the filter-unavailable deferral described below.

Reserve these for deliberately chosen references; bulk or feed-style submitters should leave them off so the profiles keep screening volume.

---

## What the tick does

Every `poll_cron` the `influx-inbox-tick` job:

1. Lists open tasks tagged `influx:inbox` (`lithos_task_list`), skips any whose retry backoff has not elapsed, takes the first `max_items_per_tick`, and claims each (aspect `ingest`, agent `agent_id`).
2. Runs `lithos_cache_lookup` on the URL. On a hit it reads the existing note and re-scores only the **complement**: enabled profiles not already in `## Profile Relevance` and not operator-suppressed with `influx:rejected:<profile>`.
3. Acquires the item **once** (download + extract, or read the PDF) and scores it against every candidate profile with the normal filter prompt.
4. For each profile that clears its threshold (or the forced host), dispatches a real single-profile Run with `kind="inbox"` under that profile's coordinator lock. The first write creates the note; later ones merge into it. A busy profile is skipped this tick and picked up on a later one; if every clearing profile is busy the task stays open.
5. Writes `metadata.inbox_result`, then completes the task with an outcome string and `cited_nodes` = the note id.

Per-profile failures are isolated: one profile's filter timeout does not sink the item. Tasks completed with an `error:` outcome are **never** re-claimed; resubmit after fixing the submission.

**Filter unavailable.** When *every* profile's filter call fails (an LLM-provider outage, HTTP 402/5xx) the item has no verdict. Instead of completing it as filtered-out, the tick writes `metadata.inbox_retry = {reason, attempts, last_attempt_at, not_before}`, releases its claim and defers with exponential backoff (15 min doubling to 4 h by default). After `filter_unavailable_max_retries` deferrals (about a week) it completes with `error: filter_unavailable after N attempt(s)`. An operator can force an immediate retry by clearing the block (`lithos_task_update … metadata={"inbox_retry": null}`) or give up with `lithos_task_cancel`.

---

## Checking results

Poll with [`lithos_task_get`](../mcp-tools/tasks.md#lithos_task_get) until `status` is `completed` (or `cancelled`), then read:

**`outcome`** — human-readable, for example:

```
ingested into 2 profile(s): ai-robotics, web-tech
ingested into 1/2 profiles (web-tech); ai-robotics filter failed: timeout
filtered out: top score 4 (ai-robotics) below threshold 7
cache_hit: existing note <id>; no new profiles matched
ingested into 1 profile(s): ai-foundations; forced: ai-foundations (score 6 below threshold 7); tier full achieved: full
error: invalid submission (…)
```

`tier full achieved` is `full` (full text + deep extraction), `full_text`, or `summary` (no full text could be extracted).

**`metadata.inbox_result`** — structured:

```json
{
  "per_profile": {
    "ai-robotics": {"score": 8, "ingested": true, "note_id": "…", "run_id": "…"},
    "web-tech":    {"score": 4, "ingested": false, "reason": "below_threshold"}
  },
  "source_url": "https://example.com/article",
  "archive_path": "inbox/2026/05/abc….html",
  "processing_time_ms": 1234,
  "override": {
    "force_requested": true, "forced": true, "forced_profile": "ai-foundations",
    "tier_requested": "full", "tier_achieved": "full"
  }
}
```

`override` is present only when you sent `force` or `tier`; a forced host's `per_profile` entry carries `"forced": true`. If you sent an override, the outcome is not an `error:`, and `override` is missing, the running Influx predates overrides and ignored them. When `note_id` is absent, find the note by URL with `lithos_search`.

Each per-profile dispatch is also an ordinary ledger entry with `kind="inbox"` in `GET /runs/recent`, and `GET /status` carries an `inbox` block (`enabled`, `pending`, `in_flight`, `awaiting_retry`, `last_tick_at`, `last_tick_outcome`) from the last tick — see [Operations](operations.md#admin-http-api).

---

## Helper script for humans

`scripts/influx-inbox-submit.py` creates the task for you. The positional argument is auto-detected: an `http(s)://` URL submits `kind="url"`, anything else is treated as a local PDF and staged into `pdf_root` under `<sha256-prefix>-<basename>` if it is not already there.

```bash
./scripts/influx-inbox-submit.py https://arxiv.org/abs/1705.05363 --force --tier full
./scripts/influx-inbox-submit.py ./papers/attention.pdf --title "Attention Is All You Need" --env prod
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--title`, `--summary` / `--summary-file` | unset | Title and summary hints |
| `--source-tag` | `inbox` | The note's `source:*` tag |
| `--force`, `--tier full` | off | The overrides above |
| `--submitted-by` | `manual:<username>` | Submitter id |
| `--env` | `staging` | Reads `docker/.env.<env>` to resolve the Lithos URL and config |
| `--lithos-url` | from `LITHOS_URL` / config | Override the Lithos `/sse` URL |
| `--pdf-root` | from config | Override `[inbox] pdf_root` |
| `--dry-run` | off | Print the task body without creating it |

The script is write-only against Lithos (one `lithos_task_create`) and never calls the Influx service.

---

## Security note

Influx fetches arbitrary URLs and feeds their content to an LLM for scoring — an indirect prompt-injection surface by design. Fetched content is stored as knowledge, never executed, and profile scoring issues no tool calls; but the submitting agent is responsible for source trust. Do not submit URLs from untrusted sources, and treat Lithos content derived from external URLs as untrusted data when querying. This matters more with `force: true`, which skips the profile screen.
