# Knowledge Read Tools

Five tools read the corpus: `lithos_read` (one document), `lithos_search` (ranked search), `lithos_list` (filtered listing), `lithos_tags` (tag counts), and `lithos_related` (per-document relationship view).

## `lithos_read`

Read a knowledge file by ID or path.

```python
lithos_read(id: str | None = None, path: str | None = None,
            max_length: int | None = None, agent_id: str | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `id` | string* | UUID (or unambiguous ≥6-char prefix) of the note |
| `path` | string* | File path relative to `knowledge/` |
| `max_length` | int | Truncate content to N characters (default: unlimited) |
| `agent_id` | string | Caller identity recorded in the read-access audit log (defaults to `"unknown"`) |

*One of `id` or `path` is required.

**Returns:** `{ id, title, content, metadata, links, truncated, retrieval_count }`

- `metadata` includes the reserved frontmatter fields, `derived_from_ids`, and `extra` — the free-form metadata dict written via `lithos_write(metadata=...)`.
- `truncated: true` when `max_length` shortened the content (cut at the nearest paragraph/sentence boundary).
- Unknown id/path → `{status: "error", code: "doc_not_found", message}`.

---

## `lithos_search`

Unified search across the knowledge base.

```python
lithos_search(query: str, limit: int = 10, mode: str = "hybrid",
              tags: list[str] | None = None, author: str | None = None,
              path_prefix: str | None = None, threshold: float | None = None,
              seed_ids: list[str] | None = None, graph_depth: int = 2,
              entities: list[str] | None = None, agent_id: str | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `query` | string | Search query |
| `limit` | int | Max results (default 10) |
| `mode` | string | `hybrid` (default) \| `fulltext` \| `semantic` \| `graph` |
| `tags` | string[] | Filter by tags (AND) |
| `author` | string | Filter by author |
| `path_prefix` | string | Filter by path prefix |
| `threshold` | float | Minimum similarity 0–1 for semantic/hybrid/graph (default 0.5) |
| `seed_ids` | string[] | Starting document IDs for `graph` mode; omitted → seeds auto-discovered via a fast hybrid pass |
| `graph_depth` | int | BFS hop depth for `graph` mode, 1–3 (default 2) |
| `entities` | string[] | Only documents whose `entities` frontmatter contains every named entity (exact match, AND) |
| `agent_id` | string | Caller identity for the read-access audit log |

**Returns:**

```json
{"results": [{"id": "…", "title": "…", "snippet": "…", "score": 0.87,
              "path": "…", "source_url": "…", "updated_at": "…",
              "is_stale": false, "derived_from_ids": []}]}
```

**Modes:**

- `hybrid` — Reciprocal Rank Fusion over full-text and semantic results
- `fulltext` — Tantivy BM25
- `semantic` — ChromaDB vector similarity (`score` is the similarity value)
- `graph` — wiki-link traversal from `seed_ids` (or auto-discovered seeds), bounded by `graph_depth`

**Notes:**

- Search operates on chunks internally but returns deduplicated documents.
- Entity names are indexed in Tantivy and included in the default query fields — query terms matching a document's entities boost its ranking.
- Invalid `mode` → `{status: "error", code: "invalid_mode", message}`.
- Every returned document is recorded in the read-access audit log.

---

## `lithos_list`

List knowledge documents with filters.

```python
lithos_list(path_prefix: str | None = None, tags: list[str] | None = None,
            author: str | None = None, since: str | None = None,
            limit: int = 50, offset: int = 0,
            title_contains: str | None = None, content_query: str | None = None,
            metadata_match: dict | None = None, entities: list[str] | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `path_prefix` | string | Filter by path prefix |
| `tags` | string[] | Filter by tags |
| `author` | string | Filter by author |
| `since` | string | `updated >= since` (ISO 8601; unparseable → `invalid_input`) |
| `limit` / `offset` | int | Pagination (default 50 / 0) |
| `title_contains` | string | Case-insensitive substring match on title |
| `content_query` | string | Tantivy full-text query applied after the base filters |
| `metadata_match` | object | Filter by free-form metadata (see below) |
| `entities` | string[] | Documents whose `entities` frontmatter contains every listed name (exact, AND) — resolved via an inverted index, never a full scan |

**Returns:** `{ items: [{ id, title, path, updated, tags, source_url, derived_from_ids, metadata }], total }`

**`metadata_match` semantics:**

- AND across keys — a document must match every `key: value` pair.
- Per key, a document matches when its stored value **equals** the query value or **is a list containing** it (e.g. `github_repos: ["org/a", "org/b"]` matches `{"github_repos": "org/a"}`).
- Query values must be JSON scalars (string/number/boolean); `null`/list/dict values → `invalid_input`. Matching is type-sensitive (`"1"` ≠ `1`).
- Resolved through an in-memory inverted index — a metadata-filtered list never scans the whole knowledge base.

`content_query` backend failures → `{status: "error", code: "search_backend_error", message}`.

---

## `lithos_tags`

List all tags with document counts.

```python
lithos_tags(prefix: str | None = None)
```

**Returns:** `{ "tags": { "python": 42, "pattern": 17, … } }` — a name→count map, not a list.

To find documents with a specific tag, use `lithos_list(tags=["tag-name"])`.

---

## `lithos_related`

Composite "what is this document related to?" view. Merges wiki-link navigation, derived-from provenance, and typed LCMA edges into a single response.

!!! note
    This tool replaced the separate `lithos_links` and `lithos_provenance` tools (removed in v0.2.1). For edge-table queries not centred on a single document (e.g. "list all `contradicts` edges"), use [`lithos_edge_list`](graph-edges.md#lithos_edge_list).

```python
lithos_related(id: str, include: list[str] | None = None,
               depth: int = 1, namespace: str | None = None)
```

| Name | Type | Description |
|------|------|-------------|
| `id` | string | UUID (or unambiguous ≥6-char prefix) of the note |
| `include` | string[] | Subset of `["links", "provenance", "edges"]` to populate (default: all three) |
| `depth` | int | BFS depth 1–3 for `links` and `provenance` (default 1); ignored by `edges` |
| `namespace` | string | Namespace filter applied to `edges` only |

**Returns:**

```json
{
  "id": "<queried-uuid>",
  "included": ["links", "provenance", "edges"],
  "links": {
    "outgoing": [{"id": "<uuid>", "title": "…"}],
    "incoming": [{"id": "<uuid>", "title": "…"}]
  },
  "provenance": {
    "sources": [{"id": "<uuid>", "title": "…"}],
    "derived": [{"id": "<uuid>", "title": "…"}],
    "unresolved_sources": ["<uuid>"]
  },
  "edges": {"outgoing": [], "incoming": []},
  "related_ids": ["<uuid>"]
}
```

**Behavior:**

- Sections not listed in `include` are omitted entirely; unknown `include` values are silently ignored (forward-compatible).
- `edges` is empty when LCMA is disabled.
- `related_ids` is the deduped, sorted union of every id referenced across the included sections, excluding the queried document itself.
- Unknown id → `{status: "error", code: "doc_not_found"}`.
