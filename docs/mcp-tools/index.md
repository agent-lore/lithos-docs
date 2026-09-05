# MCP Tools Reference

Lithos exposes **37 MCP tools**. All tools are available on every transport: stdio, StreamableHTTP (`POST /mcp`), and legacy SSE (`GET /sse`).

!!! info "v0.4.0"
    This reference reflects **v0.4.0** plus the changes shipped on `main` since the tag (marked "unreleased" where relevant). The 0.4.0 release made one breaking change: every tool **failure** now uses the canonical error envelope described [below](#error-envelope). Nine task-graph and note-patch tools were added in 0.4.0; none were removed.

## Tool Categories

=== "Knowledge — write (3)"

    | Tool | Description |
    |------|-------------|
    | [`lithos_write`](knowledge-write.md#lithos_write) | Create or update a knowledge note (full body write) |
    | [`lithos_note_update`](knowledge-write.md#lithos_note_update) | Patch a note's frontmatter without resending its body |
    | [`lithos_delete`](knowledge-write.md#lithos_delete) | Delete a knowledge note |

    → [Knowledge Write Tools](knowledge-write.md)

=== "Knowledge — read (5)"

    | Tool | Description |
    |------|-------------|
    | [`lithos_read`](knowledge-read.md#lithos_read) | Read a note by ID or path |
    | [`lithos_search`](knowledge-read.md#lithos_search) | Full-text, semantic, hybrid, or graph traversal search |
    | [`lithos_list`](knowledge-read.md#lithos_list) | List notes with filters (metadata, entities, tags, …) |
    | [`lithos_tags`](knowledge-read.md#lithos_tags) | All tags with document counts |
    | [`lithos_related`](knowledge-read.md#lithos_related) | Composite view: wiki-links, provenance, and typed edges in one call |

    → [Knowledge Read Tools](knowledge-read.md)

=== "Retrieval / LCMA (3)"

    | Tool | Description |
    |------|-------------|
    | [`lithos_retrieve`](retrieval.md#lithos_retrieve) | Cognitive retrieval — multi-scout, reranked, with audit receipts |
    | [`lithos_cache_lookup`](retrieval.md#lithos_cache_lookup) | Check for a cached answer before expensive research |
    | [`lithos_node_stats`](retrieval.md#lithos_node_stats) | A note's salience score, retrieval stats, and penalty counts |

    → [Retrieval Tools](retrieval.md)

=== "Graph edges (3)"

    | Tool | Description |
    |------|-------------|
    | [`lithos_edge_upsert`](graph-edges.md#lithos_edge_upsert) | Create or update a typed weighted edge in `edges.db` |
    | [`lithos_edge_list`](graph-edges.md#lithos_edge_list) | Query edges by node, type, or namespace |
    | [`lithos_conflict_resolve`](graph-edges.md#lithos_conflict_resolve) | Resolve a contradiction between two notes |

    → [Graph Edge Tools](graph-edges.md)

=== "Tasks (11)"

    | Tool | Description |
    |------|-------------|
    | [`lithos_task_create`](tasks.md#lithos_task_create) | Create a task (with `task_type`, `depends_on`, `parent_task_id`) |
    | [`lithos_task_update`](tasks.md#lithos_task_update) | Update mutable fields (metadata is a per-key merge) |
    | [`lithos_task_get`](tasks.md#lithos_task_get) | Fetch one task, explicit not-found envelope, no claims |
    | [`lithos_task_list`](tasks.md#lithos_task_list) | List tasks with filters (`with_claims`, `metadata_match`, …) |
    | [`lithos_task_status`](tasks.md#lithos_task_status) | Full record of one task with its active claims |
    | [`lithos_task_claim`](tasks.md#lithos_task_claim) | Claim an aspect of a task (TTL lock) |
    | [`lithos_task_renew`](tasks.md#lithos_task_renew) | Extend an existing claim |
    | [`lithos_task_release`](tasks.md#lithos_task_release) | Release a claim |
    | [`lithos_task_complete`](tasks.md#lithos_task_complete) | Complete a task; reports `unblocked` dependents |
    | [`lithos_task_cancel`](tasks.md#lithos_task_cancel) | Cancel a task, releasing all claims |
    | [`lithos_task_reopen`](tasks.md#lithos_task_reopen) | Reopen a terminal task back to `open` |

    → [Task Tools](tasks.md)

=== "Task graph (6)"

    | Tool | Description |
    |------|-------------|
    | [`lithos_task_edge_upsert`](task-graph.md#lithos_task_edge_upsert) | Create a typed relation between two tasks |
    | [`lithos_task_edge_list`](task-graph.md#lithos_task_edge_list) | List edges touching a task |
    | [`lithos_task_ready`](task-graph.md#lithos_task_ready) | Open tasks that are ready to work (the feasible frontier) |
    | [`lithos_task_blocked`](task-graph.md#lithos_task_blocked) | Open tasks that are not ready, with structured blocker reasons |
    | [`lithos_task_children`](task-graph.md#lithos_task_children) | Child tasks of a parent/epic |
    | [`lithos_task_spawn`](task-graph.md#lithos_task_spawn) | Create a follow-on task linked to a source task |

    → [Task Graph Tools](task-graph.md)

=== "Agents & findings (5)"

    | Tool | Description |
    |------|-------------|
    | [`lithos_agent_register`](agents-findings.md#lithos_agent_register) | Explicitly register an agent |
    | [`lithos_agent_info`](agents-findings.md#lithos_agent_info) | Get info about a specific agent |
    | [`lithos_agent_list`](agents-findings.md#lithos_agent_list) | List all known agents |
    | [`lithos_finding_post`](agents-findings.md#lithos_finding_post) | Post a finding to a task |
    | [`lithos_finding_list`](agents-findings.md#lithos_finding_list) | List findings for a task |

    → [Agent & Finding Tools](agents-findings.md)

=== "System (1)"

    | Tool | Description |
    |------|-------------|
    | [`lithos_stats`](system.md#lithos_stats) | Knowledge base statistics and health indicators |

    → [System Tools & HTTP Endpoints](system.md)

---

## HTTP Endpoints

In addition to MCP tools, Lithos mounts three plain HTTP routes on the same port as the `http` transport:

| Endpoint | Description |
|----------|-------------|
| [`GET /health`](system.md#get-health) | Health check — `200 OK` or `503`. Use with Docker `HEALTHCHECK` and load balancers. |
| [`GET /events`](system.md#get-events) | Server-Sent Events stream for real-time event delivery. |
| [`GET /audit`](system.md#get-audit) | Read-access audit log — filterable by agent, document, and start time. |

There is **no `/metrics` scrape endpoint** — metrics are pushed via OpenTelemetry OTLP to a collector. See [Observability](../deployment/observability.md).

---

## Error Envelope

Since v0.4.0, every tool **failure** returns exactly this canonical envelope:

```json
{
  "status": "error",
  "code": "<stable_snake_case_code>",
  "message": "Human-readable description"
}
```

- Branch on `code`, never parse `message`. Validation failures use the reserved code `invalid_input`.
- Error envelopes carry **no `warnings` key** (0.4.0 change — stop reading it).
- Some codes add documented extra keys after the three canonical ones (e.g. `ambiguous_id_prefix` adds `candidates`).

!!! warning "Write-path exception"
    `lithos_write` and `lithos_note_update` report contract-level outcomes with the code as the **top-level `status`** (e.g. `status="slug_collision"`, `status="version_conflict"`, `status="invalid_input"`) and no separate `code` field, because these are *actionable outcomes* carrying payloads (`current_version`, `existing_id`, `duplicate_of`). See [Knowledge Write Tools](knowledge-write.md#status-envelope).

### Error codes

| Code | Tools | Meaning |
|------|-------|---------|
| `invalid_input` | most tools | Bad argument values (unparseable datetime, bad `metadata_match` value, id shorter than 6 chars matching nothing, …) |
| `doc_not_found` | `lithos_read`, `lithos_delete`, `lithos_related`, `lithos_node_stats` | Document with given ID/path does not exist |
| `note_not_found` | `lithos_write` | Unknown `id` passed for an update |
| `ambiguous_id_prefix` | any id-taking tool | A short id prefix matched more than one task/note; carries `candidates: [{id, title}]` (up to 5) |
| `invalid_mode` | `lithos_search` | Unknown search mode |
| `search_backend_error` | `lithos_list`, `lithos_cache_lookup` | A search backend failed executing the query |
| `task_not_found` | all task tools | Task does not exist (including unknown 6–35-char prefixes on every task tool) |
| `task_not_resolved` | `lithos_task_reopen` | Task is already `open`; nothing to reopen |
| `claim_failed` | `lithos_task_claim` | Task closed or aspect already claimed |
| `claim_not_found` | `lithos_task_renew`, `lithos_task_release` | No active claim for this agent/aspect |
| `receipt_not_found` | `lithos_task_complete` | LCMA feedback references a missing or unrelated receipt |
| `invalid_metadata_key` | task create/update/spawn | Metadata contains `depends_on`/`blocked_on` — dependencies are edges |
| `invalid_task_type` | `lithos_task_create` | `task_type` not one of `task`/`epic`/`gate` |
| `invalid_edge_type` | `lithos_task_edge_upsert` | Edge type not accepted |
| `invalid_relation_type` | `lithos_task_spawn` | `relation_type` not `discovered_from`/`blocks` |
| `self_edge` | `lithos_task_edge_upsert` | Edge from a task to itself |
| `cycle` | task edge writes | Edge would create a dependency or ancestry cycle |
| `parent_exists` | `lithos_task_edge_upsert` | Child already has a different parent (hierarchy is a forest) |
| `not_a_gate` | `lithos_task_edge_upsert` | `waits_on_gate` edge whose blocker is not a `gate` task |
| `lcma_disabled` | `lithos_retrieve` | LCMA is disabled in config |
| `not_found` | `lithos_conflict_resolve` | Edge ID does not exist |
| `update_failed` | `lithos_conflict_resolve` | Edge found but the persistence write failed |
| `internal_error` | write path | Unexpected internal failure |

Write-path top-level statuses (`lithos_write`/`lithos_note_update` only): `created`, `updated`, `duplicate`, `invalid_input`, `content_too_large`, `slug_collision`, `path_collision`, `version_conflict`, `error`.

---

## Short ID Prefixes

!!! tip "Since v0.4.0 (unreleased)"

Every tool parameter that takes a task or note id also accepts an **unambiguous short prefix** — minimum 6 characters, the git idiom:

- **Per-domain namespaces.** A task prefix resolves against tasks only; a note prefix against notes only.
- **Exact match always wins** on the note side, at any length (hand-authored notes may carry arbitrary ids).
- **Ambiguity fails loudly**: `{ "status": "error", "code": "ambiguous_id_prefix", "candidates": [{ "id": ..., "title": ... }] }` — never silently picked. Retry with a longer prefix or a full id from `candidates`.
- A prefix shorter than 6 characters with no exact match is `invalid_input`; an unknown prefix returns the domain not-found code (`task_not_found` / `doc_not_found`).
- Reference fields (`derived_from_ids`, finding `knowledge_id`, edge endpoints, `source_task`, `retrieve.task_id`) resolve **leniently**: a unique hit resolves, ambiguity errors, anything else passes through unchanged — forward references keep working.
- **Mutating responses echo the resolved full id and title** so you can verify you hit the right record.

!!! danger "Never reconstruct a UUID"
    Pass a short id from prose as a prefix — never reconstruct a full UUID from surrounding context. A guessed UUID that happens to exist writes to the wrong record and reports success.

---

## Common Patterns

### Always check before researching

```python
cache = lithos_cache_lookup(query="...", max_age_hours=168)
if not cache["hit"]:
    # do research
    lithos_write(title="...", content="...", agent="...")
```

### Truncate reads to protect context windows

```python
doc = lithos_read(id="...", max_length=2000)
```

### Patch frontmatter without rewriting the body

```python
lithos_note_update(id="...", agent="...", tags=["python", "verified"])
```

### Work the ready frontier

```python
ready = lithos_task_ready(project="my-project")
for task in ready["tasks"]:
    claim = lithos_task_claim(task_id=task["id"], aspect="implementation", agent="me")
    if claim.get("success"):
        break
```

### Tag aggressively

Tags are your primary filtering mechanism. Be consistent. Examples:

- Technology: `python`, `rust`, `docker`
- Type: `pattern`, `antipattern`, `reference`, `decision`
- Status: `draft`, `verified`, `stale`
- Source: `research`, `production`, `test`
