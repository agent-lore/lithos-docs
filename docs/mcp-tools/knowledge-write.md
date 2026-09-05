# Knowledge Write Tools

Three tools mutate the Markdown corpus: `lithos_write` (full body write), `lithos_note_update` (frontmatter patch), and `lithos_delete`.

## Status envelope

Unlike every other tool family, the write path reports contract-level outcomes with the code as the **top-level `status`** — there is no separate `code` field on these envelopes. These are *actionable outcomes*, not failures: they carry payloads your retry logic acts on.

| `status` | Extra payload | Meaning |
|----------|---------------|---------|
| `created` / `updated` | `id`, `title`, `path`, `version`, `warnings` | Success |
| `duplicate` | `duplicate_of: {id, title, source_url}` | A document with the same normalized `source_url` already exists (source-URL dedup only) |
| `invalid_input` | `message` | Bad argument values |
| `content_too_large` | `message` | Content exceeds `storage.max_content_size_bytes` |
| `slug_collision` | `existing_id` | A different document already owns this slug |
| `path_collision` | `existing_id` | Another document already owns the requested `.md` file path |
| `version_conflict` | `current_version` | `expected_version` did not match — re-read, merge, retry |
| `error` | `code`, `message` | Fallback (`code: "note_not_found"` for an unknown `id`; `code: "internal_error"` for unexpected failures) |

---

## `lithos_write`

Create or update a knowledge file.

```python
lithos_write(
    title: str, content: str, agent: str,
    tags: list[str] | None = None, confidence: float | None = None,
    path: str | None = None, id: str | None = None,
    source_task: str | None = None, source_url: str | None = None,
    derived_from_ids: list[str] | None = None,
    ttl_hours: float | None = None, expires_at: str | None = None,
    expected_version: int | None = None,
    schema_version: int | None = None, namespace: str | None = None,
    access_scope: str | None = None, note_type: str | None = None,
    status: str | None = None, summaries: dict | None = None,
    metadata: dict | None = None,
)
```

**Core (required):**

| Name | Type | Description |
|------|------|-------------|
| `title` | string | Title of the knowledge item |
| `content` | string | Markdown content (without frontmatter) |
| `agent` | string | Your agent identifier |

**Identity & metadata:**

| Name | Type | Description |
|------|------|-------------|
| `id` | string | UUID to update existing; omit to create new. Unknown `id` → `{status: "error", code: "note_not_found"}`. |
| `tags` | string[] | List of tags |
| `metadata` | object | Free-form key/value metadata persisted to frontmatter. On update: omit/`null` preserves; **`{}` clears all**; a non-empty dict is an additive per-key merge (`{"key": null}` deletes that key). Keys must not collide with reserved frontmatter fields (`invalid_input`). Returned by `lithos_read` (as `metadata.extra`) and `lithos_list`; filterable via `lithos_list(metadata_match=...)`. |
| `confidence` | float | Confidence 0–1 (default 1.0). Non-finite, boolean, or out-of-range values → `invalid_input`. |
| `path` | string | Either a subdirectory (`"procedures"` — filename derived from slugified title) **or** a full relative path ending in `.md` (used verbatim). Intermediate segments must not end in `.md` (`invalid_input`). An already-owned path → `path_collision`. |

**Provenance:**

| Name | Type | Description |
|------|------|-------------|
| `source_url` | string | Canonical URL provenance (http/https); dedup key after normalization. Pass `""` to clear on update. |
| `derived_from_ids` | string[] | Declared lineage (UUIDs). Create: omit stores `[]`. Update: omit preserves, `[]` clears, non-empty replaces. Self-references rejected. |
| `source_task` | string | Task ID stored as `source` in frontmatter. An unambiguous ≥6-char prefix of an existing task resolves to its full id; other values stored as given. |

**Freshness & concurrency:**

| Name | Type | Description |
|------|------|-------------|
| `ttl_hours` | float | Relative freshness window; converted to `expires_at` |
| `expires_at` | string | Absolute ISO datetime freshness deadline |
| `expected_version` | int | Optimistic-locking guard for updates; ignored on create |

**LCMA fields:**

| Name | Type | Description |
|------|------|-------------|
| `schema_version` | int | LCMA schema version (default 1 on create) |
| `namespace` | string | LCMA namespace; derived from path at read time unless explicitly set |
| `access_scope` | enum | `shared` \| `task` \| `agent_private` (default `shared`). `task` requires `source_task`. |
| `note_type` | enum | `observation` \| `agent_finding` \| `summary` \| `concept` \| `task_record` \| `hypothesis` (default `observation`) |
| `status` | enum | `active` \| `archived` \| `quarantined` (default `active`) |
| `summaries` | object | `{short, long}` — both optional strings |

**Returns:** the [status envelope](#status-envelope). Success:

```json
{"status": "created", "id": "…", "title": "…", "path": "shared/my-note.md", "version": 1, "warnings": []}
```

**Update semantics:** omitted optional fields preserve existing values; the updating agent is appended to `contributors`; `author` is immutable. Clearable string fields use `""` as the clear signal (FastMCP cannot distinguish omitted from `null` at the MCP boundary).

### Optimistic locking

```python
doc = lithos_read(id=note_id)
version = doc["metadata"]["version"]
result = lithos_write(id=note_id, title=..., content=merged, agent="me",
                      expected_version=version)
if result["status"] == "version_conflict":
    # someone else wrote first — re-read, merge, retry
    ...
```

---

## `lithos_note_update`

Patch a note's frontmatter (tags / metadata / title / status) **without resending its body** — the note counterpart to `lithos_task_update`. Use this instead of `lithos_write` whenever only frontmatter changes: the body is never read into the request, so there is no lost-update risk from reproducing it.

```python
lithos_note_update(
    id: str, agent: str,
    title: str | None = None, tags: list[str] | None = None,
    status: str | None = None, metadata: dict | None = None,
    expected_version: int | None = None,
)
```

| Name | Type | Description |
|------|------|-------------|
| `id` | string | UUID (or unambiguous ≥6-char prefix) of the note to patch |
| `agent` | string | Your agent identifier |
| `title` | string | New title. Renaming may change the slug; a collision → `slug_collision`. |
| `tags` | string[] | Omit/`null` preserves; `[]` clears all tags; non-empty replaces |
| `status` | enum | `active` \| `archived` \| `quarantined`. Out-of-enum → `invalid_input`. |
| `metadata` | object | Additive per-key merge (`{"key": null}` deletes a key; unmentioned keys preserved). **No wholesale clear** — `metadata={}` makes no change. |
| `expected_version` | int | Optimistic-locking guard → `version_conflict` on mismatch |

At least one mutable field must be provided; otherwise (including `metadata={}` alone) the call returns `status="invalid_input"` and writes no revision.

**Returns:** the same [status envelope](#status-envelope) as `lithos_write` (`updated` on success). Emits `note.updated`.

!!! warning "The `{}` asymmetry"
    `lithos_write(metadata={})` **clears** all free-form metadata; `lithos_note_update(metadata={})` (and `lithos_task_update(metadata={})`) is a **no-op merge**. When you mean "clear everything", use `lithos_write`; when you mean "delete one key", pass `{"key": null}` to either.

---

## `lithos_delete`

Delete a knowledge file.

```python
lithos_delete(id: str, agent: str)
```

| Name | Type | Description |
|------|------|-------------|
| `id` | string | UUID (or unambiguous ≥6-char prefix) of the note to delete |
| `agent` | string | Agent performing the deletion (audit trail + auto-registration) |

**Returns:**

```json
{"success": true, "id": "<resolved-full-id>", "title": "…", "path": "shared/my-note.md"}
```

or `{"status": "error", "code": "doc_not_found", "message": "…"}` if the document does not exist.

Deletion removes the file, its index entries, and its graph node. Incoming wiki-links from other documents become unresolved links (visible in [`lithos_stats`](system.md#lithos_stats) as `unresolved_links`).
