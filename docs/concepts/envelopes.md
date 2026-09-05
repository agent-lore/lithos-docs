# Envelopes, Errors & IDs

How Lithos tools report outcomes, how agents should branch on them, and how IDs resolve. This page is the narrative companion to the [error-code table](../mcp-tools/index.md#error-envelope) in the tools reference.

## The canonical error envelope

Since **v0.4.0**, every tool *failure* — validation and operational alike — returns exactly one shape:

```json
{
  "status": "error",
  "code": "<stable_snake_case_code>",
  "message": "<human-readable sentence>"
}
```

Three rules follow from it:

1. **Branch on `code`, never on `message`.** Codes are machine-stable; messages are for humans and may change wording between releases.
2. **Validation failures are `code: "invalid_input"`** — including paths that used to raise protocol-level errors, such as unparseable datetime filters on `lithos_list(since=...)`, `lithos_agent_list(active_since=...)`, and `lithos_finding_list(since=...)`.
3. **Error envelopes carry no `warnings` key.** If your client reads `warnings` off error responses, stop — the key exists only on write-path *status* envelopes.

Some codes append documented extra keys after the three canonical ones (`ambiguous_id_prefix` adds `candidates`; `version_conflict` adds `current_version`) — extras may never override the canonical keys.

Protocol-level MCP errors (`ToolError`) still exist, but only for two cases: the MCP schema rejecting a call before the handler runs, and genuine internal bugs. Everything anticipatable comes back as an envelope your code can branch on.

## Outcomes are not errors

Not everything that stops a write is a *failure*. The write path deliberately keeps a family of **actionable outcomes** as their own top-level `status`, because each carries a payload your retry logic acts on:

| `status` | Payload | What to do |
|----------|---------|------------|
| `version_conflict` | `current_version` | Re-read, merge, retry with the new `expected_version` |
| `duplicate` | `duplicate_of: {id, title, source_url}` | Update the existing doc instead of writing a new one |
| `slug_collision` | `existing_id` | Pick a different title, or update the squatting doc |
| `path_collision` | `existing_id` | Pick a different path, or update the owner |
| `content_too_large` | — | Split or trim the content |

On `lithos_write` and `lithos_note_update`, even `invalid_input` arrives as `status="invalid_input"` — the code **is** the status, with no separate `code` field. `status="error"` remains only as the write path's generic fallback (with `code: "note_not_found"` or `code: "internal_error"`). Every other tool family uses `status="error"` + `code` uniformly.

The claim tools keep their historical success shape too: `{"success": true, ...}` from claim/renew/release/complete/cancel/reopen, with error envelopes on failure. A `claim_failed` is **normal contention**, not a fault — another agent holds the aspect; pick another task or wait.

## Optimistic concurrency

Every note carries a `version` in frontmatter. Pass `expected_version` on `lithos_write`/`lithos_note_update` whenever concurrent edits are possible:

```python
doc = lithos_read(id=note_id)
current = doc["metadata"]["version"]

result = lithos_write(id=note_id, title=..., content=merged,
                      agent="me", expected_version=current)

if result["status"] == "version_conflict":
    # someone wrote between our read and write
    fresh = lithos_read(id=note_id)          # re-read
    merged = merge(fresh["content"], my_changes)
    # retry with fresh["metadata"]["version"]
```

The loop terminates because each retry starts from the newest version; the conflict envelope's `current_version` tells you how far behind you were.

## Short ID prefixes

!!! tip "Since v0.4.0 (unreleased)"

Every task and note id parameter accepts an **unambiguous short prefix**, minimum 6 characters — the git idiom. `lithos_task_get(task_id="83257ced")` just works.

- **Per-domain namespaces.** Task prefixes resolve against tasks only, note prefixes against notes only. There is no unified id space.
- **Exact match always wins** on the note side, at any length — hand-authored notes may carry arbitrary ids shorter than 6 characters.
- **Ambiguity fails loudly.** A prefix matching more than one record returns `code: "ambiguous_id_prefix"` with up to 5 `{id, title}` candidates. Lithos never picks silently; retry with a longer prefix or a full id from the list.
- **Misses are typed.** Under 6 chars with no exact match → `invalid_input`. An unknown 6–35-char task prefix → `task_not_found` on *every* task tool — including claim/renew/release (which historically said `claim_failed`/`claim_not_found`) and list-shaped tools (which historically returned silently empty).
- **Reference fields resolve leniently.** Fields whose contract allows not-yet-existing values — `derived_from_ids` forward references, finding `knowledge_id`, asserted-edge endpoints, `source_task`, `lithos_retrieve.task_id` — resolve a unique hit, error on ambiguity, and otherwise pass the value through unchanged. Forward references and free-form correlation keys keep working.
- **Mutating responses echo the resolved full id and title**, so you can verify you touched the right record and transcripts retain full ids.

!!! danger "Never reconstruct a UUID"
    Short ids in prose are display-only — pass them as prefixes. A UUID guessed from surrounding context that happens to exist writes to the **wrong** record and reports success; the prefix path can only resolve correctly or fail loudly.

## Change detection: `updated_at`

!!! tip "Since v0.4.0 (unreleased)"

Task records carry an `updated_at` last-modified stamp:

- **Bumped by every task-row write** — create (`= created_at`), any `lithos_task_update` (even a `metadata={}` merge that changes no keys), complete/cancel (`= resolved_at`), reopen.
- **Never bumped by claim/renew/release** — lease heartbeats touch only the claims table, so they can't masquerade as edits.
- Returned by `lithos_task_get`/`lithos_task_list`/`lithos_task_status` (and the ready/blocked/children views), carried in row-mutating event payloads, and **echoed by every mutating response** — record your own write's stamp without a racy re-read.
- Detect "edited since I last looked" by comparing stamps for **equality** with the one you recorded. A different stamp means someone wrote the row; don't rely on ordering.

## Migrating older clients

### From 0.3.x

The 0.4.0 envelope change partially **reverses** 0.3.0's error handling, so 0.3.x clients need one mechanical rewrite:

```python
# 0.3.x                                   # 0.4.0+
if result["status"] == "invalid_input":   if result["status"] == "error" and \
    ...                                        result["code"] == "invalid_input":
                                              ...
```

…for every tool **except** `lithos_write`/`lithos_note_update`, where `status="invalid_input"` remains correct. Also stop reading `warnings` from error responses.

### From 0.2.x

Everything above, plus the 0.3.x changes you skipped:

- **`completed_at` → `resolved_at`** on task records (0.3.0), now set on *both* terminal transitions.
- **Task `metadata` updates became an additive per-key merge** (0.3.0) — `{"key": null}` deletes a key; there is no wholesale clear.
- **Transport `sse` was renamed `http`** (0.3.2) with no alias — `lithos serve --transport http`, and one port now serves both `POST /mcp` (StreamableHTTP) and `GET /sse`. See [Installation](../getting-started/installation.md).
- **`lithos_write(path=...)` treats a `.md`-terminated path as the complete filename** (0.3.0) — it no longer silently creates a directory named `foo.md`.
- **`metadata.depends_on`/`blocked_on` are rejected** (0.4.0) — dependencies are first-class [task edges](../mcp-tools/task-graph.md).

The pre-1.0 policy is **migration safety over API stability**: tool contracts may change between minors, but your on-disk Markdown is always preserved. Check the [Changelog](../changelog.md) before upgrading.
