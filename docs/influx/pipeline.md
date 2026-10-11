# Pipeline

This page describes what Influx does to an item, stage by stage, as implemented in `src/influx/`. The vocabulary (Profile, Source, Filter, Cascade, Run, …) is the one pinned in the repo's `CONTEXT.md`.

## Runs and the scheduler

A **Run** is one end-to-end execution of the pipeline for one profile. Runs have a **kind**: `scheduled`, `manual` (`POST /runs`), `backfill` (`POST /backfills`) or `inbox` (dispatched per item by the [inbox tick](inbox.md)). The kind is mapped to a `RunPlan` with three flags:

| Kind | Repair sweep | Skip cache hits | Notify |
|------|--------------|-----------------|--------|
| `scheduled`, `manual`, `inbox` | yes | no | yes |
| `backfill` | **skipped** | **yes** | **no** |

The scheduler registers a single `influx-tick` cron job. Each tick sleeps a random `[0, schedule.initial_jitter_seconds]`, then runs every profile **sequentially in config order**, waiting `schedule.inter_profile_gap_seconds` between them. A per-tick `FetchCache` means two profiles sharing an arXiv category or RSS feed fetch it once.

A `Coordinator` holds one lock per profile: scheduled ticks, manual runs, backfills and inbox dispatches all take it, so the same profile never runs twice concurrently. Different profiles may overlap when triggered manually.

Before a Run starts, two probe-time gates can skip it entirely (ledger `status="skipped"`): `lithos_unhealthy` (the Lithos probe has been degraded for 3 consecutive 30-second cycles) and `lcma_tools_unavailable` (the Lithos tool list is missing a required LCMA tool).

`Run.execute()` then walks five stages.

---

## Stage 1 — Repair sweep

The sweep lists notes tagged `influx:repair-needed` **and** `profile:<this profile>`, oldest `updated_at` first, up to `repair.max_items_per_run`. For each note it selects which stages to retry from the note's tags and archive state:

| Missing | Retry | Terminal tag when the cap is reached |
|---------|-------|--------------------------------------|
| Archive file | re-download by note identity (arXiv id, feed slug + `source_url`) | `influx:archive-terminal` |
| Extracted text | re-extract from the archived file; `text:abstract-only` upgrade | `influx:text-terminal` |
| Tier 2 full text | run the Cascade's Tier 2 again | `influx:tier2-terminal` |
| Tier 3 deep extraction | run the Cascade's Tier 3 again | `influx:tier3-terminal` |

Attempt counters live in a `## Repair` section in the note body (`tier2_attempts`, `tier3_last_stage`, …). Only **counted** failures (model output that fails to parse or validate; permanent HTTP 403/404/410 and operator-`blocked` domains on the archive stage) advance a counter; transient network errors never do. At 3 attempts the stage is marked terminal and waived, and `influx:repair-needed` is cleared once every remaining condition is satisfied or waived. Tier 1 (the summary) is never re-run by the sweep: its only input, the abstract, is not persisted (ADR 0001).

Every visited note is rewritten so `updated_at` advances, which is what moves it to the back of the queue. A terminal Lithos write failure during the sweep aborts the run and latches `/ready` degraded until a later sweep succeeds.

---

## Stage 2 — Feedback

Influx calls `lithos_list` for recent notes tagged `influx:rejected:<profile>` — a tag an **operator** applies to a note to say "this was a bad pick" — and formats up to `feedback.negative_examples_per_profile` of their titles into the `{negative_examples}` slot of the filter prompt. There is no automatic rejection memory: a below-threshold candidate is simply not written, and will be re-scored if it shows up again.

Every `feedback.recalibrate_after_runs` runs, a per-tag rejection-rate line is logged for the profile (informational; in-memory counters reset on restart).

---

## Stage 3 — Acquire

`Source.fetch_candidates → Filter.score → Source.acquire`.

### Sources

**arXiv** queries `https://export.arxiv.org/api/query` per configured category with `max_results_per_category`, parses the Atom reply, and keeps entries inside the `lookback_days` window (or the backfill date range). Requests are spaced at least `arxiv_request_min_interval_seconds` apart process-wide; HTTP 429 honours `Retry-After` (capped) or backs off exponentially with its own retry budget, and repeated exhausted 429s put the source into a cooldown during which fetches are skipped with the degraded reason `source_cooldown_skip`.

**RSS / Atom** fetches each `[[profiles.sources.rss]]` URL through the guarded HTTP client and parses it with `feedparser`. Each item carries the feed's configured `source_tag` (`rss` or `blog`) verbatim. A feed that times out repeatedly is cooled down per URL.

Both go through the **guarded HTTP client**: `http`/`https` only, DNS resolution with private-IP blocking (unless `security.allow_private_ips`), streaming size cap, timeouts, content-type checks. URLs whose shape is known not to be an article (another feed, a Hacker News discussion page) are classified `non_html_source` without a request.

### Filter

Candidates are scored in batches of `filter.batch_size` by one call to the `filter` model slot with the profile description and negative examples. The model returns `{"results": [{"id", "score" (1–10), "tags" (≤5), "reason"}]}`, omitting anything below `min_score_in_results`. Items absent from the reply or below `thresholds.relevance` are dropped. A batch whose call fails (transport, parse, schema) is skipped and the run is flagged `filter_error`; other batches are kept.

### Dedup before download

For every scored candidate Influx calls `lithos_cache_lookup(query, source_url)`. Only a reply with `match: "source_url"` counts as a hit (Lithos found the URL in its own index); semantic matches are ignored with a warning. Then:

- backfills drop every hit;
- other runs drop a hit whose note already carries `profile:<profile>` or `influx:rejected:<profile>` (`action=skip-present`);
- any other hit continues, so the profile can merge into the existing note.

### Acquire

Passing candidates are downloaded and archived:

| Source | Archive path (relative to `storage.archive_dir`) |
|--------|--------------------------------------------------|
| arXiv | `arxiv/YYYY/MM/<arxiv-id>.pdf` |
| RSS / blog | `<source_tag>/YYYY/MM/<feed-slug>-YYYY-MM-DD-<url-hash>.html` |
| Inbox URL | `inbox/YYYY/MM/<url-hash>.<ext>` |
| Inbox PDF | `inbox-pdf/YYYY/MM/<sha256>.pdf` |

Before downloading, the host is checked against `[storage.archive_policy]` (see [Configuration](configuration.md#storagearchive_policy)). A failed download does not abort the note: it is tagged `influx:archive-missing` and `influx:repair-needed` (plus the policy-specific tag), and the run is marked degraded with reason `archive_acquisition`. One exception: if the archive failed **and** the available summary is thin (shorter than `extraction.min_summary_chars`, equal to the title, or matching boilerplate like "Discussion (47 points)"), the item is dropped entirely rather than written as a stub.

RSS articles are text-extracted with trafilatura right after archiving; if the body is shorter than `extraction.min_web_chars` the feed summary is used instead.

---

## Stage 4 — Ingest

Per item: `Cascade.enrich → Renderer.render → LithosClient.write_note → LcmaWiring.wire`.

### Enrichment cascade

Three score-gated tiers, each adding sections to the note:

| Tier | Gate | Model slot | Produces |
|------|------|-----------|----------|
| 1 | `score >= relevance` | `enrich` | `## Summary` — `contributions` (1–6), `method`, `result`, `relevance` |
| 2 | `score >= full_text` | — | `## Full Text` and the `full-text` tag. arXiv: HTML → PDF cascade (`text:html` / `text:pdf`); RSS: the article extraction from acquire |
| 3 | `score >= deep_extract` and full text present | `extract` | `## Claims`, `## Datasets & Benchmarks`, `## Builds On`, `## Open Questions`; `potential_connections` is kept for LCMA only. Tag `influx:deep-extracted` |

Tier 3 lists are capped (30 for claims/datasets/builds_on, 10 for the rest) by truncation, not rejection; items are trimmed to 500 characters. A Tier 1 failure degrades to an abstract-only note with `influx:repair-needed`; Tier 2/3 failures set the repair flag and, if counted, advance the `## Repair` counters.

### Canonical note

The renderer writes a fixed shape:

```yaml
---
note_type: summary
namespace: influx
source_url: <normalised URL>
tags: [profile:<p>, source:<s>, ingested-by:influx, schema:1, …]
confidence: <float>
---
```

followed by `# Title`, `## Archive` (`path: <relative path>`), `## Summary`, `## Full Text`, the Tier 3 sections, `## Profile Relevance` (always present; one `### <profile>` entry with `Score: n/10` and the reason) and `## User Notes`, which is preserved byte-exactly across every rewrite. Sections without content are omitted. Identity tags: `arxiv-id:<id>` or `feed-slug:<slug>`; text provenance: `text:abstract-only` / `text:html` / `text:pdf`.

### Writing to Lithos

`lithos_write` outcomes are handled as follows:

| Status | Handling |
|--------|----------|
| `created` / `updated` | Success; the note id feeds LCMA wiring |
| `duplicate` | Lithos already has this `source_url`. Influx reads that note and **merges** (ADR 0003): unions `profile:*` tags and `## Profile Relevance` entries, keeps the richer body (full text / Tier 3 beats summary-only; ties keep the existing body), keeps `influx:repair-needed` if either side had it, takes the higher confidence, and updates by id with `expected_version`. Nothing is written if the merge adds nothing |
| `slug_collision` | Inspect the squatting note: same paper → treat as `duplicate`; empty residue → delete and retry; distinct paper → retry with a `[arXiv <id>]` / `[<host>]` / `[inbox]` title suffix. Still colliding → appended to `<state_dir>/unresolved-slug-collisions.jsonl` |
| `version_conflict` | Re-read and merge once more (`resilience.lithos_write_conflict_max_retries`), then skip |
| `content_too_large` | Drop `## Full Text` and retry; on a second failure skip (repair path: retry with Tier 1 only) |
| `invalid_input`, other | Logged with Lithos's message and skipped |

Only notes carrying `ingested-by:influx` are ever merged into; another agent's note is left alone.

### LCMA wiring

After a successful write Influx calls `lithos_retrieve` with the title plus up to three contribution bullets and upserts a `related_to` edge from the new note to every result scoring at least `thresholds.lcma_edge_score`, carrying the retrieve `receipt_id` as evidence. Tier 3 `builds_on` entries containing `arXiv:<id>` are resolved through `lithos_cache_lookup`; a `builds_on` edge is upserted only on an exact `source_url` match.

---

## Stage 5 — Finalise

The run outcome (`sources_checked`, `ingested`, `error`, `degraded`, `degraded_reasons`) is written to the local run ledger (`<state_dir>/runs.jsonl`) and, when the plan allows, the [notification sinks](operations.md#notifications) fire. The ledger also derives stall signals by comparing with the previous scheduled run for the profile: `ingestion_stall`, `fetch_stall`, `filter_stall` (consecutive empty runs at different funnel stages) and `filter_error`.

Each Run is also bracketed by a Lithos task (`lithos_task_create` on entry, `lithos_task_complete` on exit) created as agent `influx`, so run activity is visible from the Lithos side.

---

## Backfills

A backfill is an ordinary Run with `kind="backfill"` over an explicit window (`--days N` or `--from/--to`). The admin API estimates `days × categories × max_results_per_category` and refuses estimates above 1000 unless `confirm` is set. Backfills skip repair, skip every cache hit, and never notify; arXiv pacing still applies.
