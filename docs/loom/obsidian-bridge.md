# Obsidian bridge

The `obsidian-sync` child projects Lithos work into an Obsidian vault and pushes a narrow set of edits back. It is spawned on the one host whose TOML has an `[obsidian_sync]` block — the vault host. Lithos stays the source of truth; the vault is a projection plus a write surface for ticks, priorities, due dates and project-context bodies.

## Configuration

```toml
[obsidian_sync]
vault_path           = "/home/you/Obsidian/Vault"     # absolute
tasks_file           = "_lithos/tasks.md"             # relative to vault_path
projects_dir         = "_lithos/projects"             # per-project context docs + done files
awaiting_review_file = "_lithos/awaiting-review.md"   # open tasks with a delivered PR
resolved_ttl_days    = 7      # how long resolved tasks linger in tasks_file
include_blocked      = true   # false hides tasks Lithos reports as blocked
exclude_tags         = []     # e.g. ["influx:run", "influx:backfill"]
```

The block only spawns the child. Each behaviour is a `[[subscriptions]]` stanza naming an action — the example config in the repo has them all, commented out:

| Action | Events | Effect |
|--------|--------|--------|
| `obsidian-projection` | `lithos.task.*` (incl. `claimed` / `released`) | Rewrites `tasks_file` from scratch on every flush (atomic dot-prefixed temp file + rename) |
| `obsidian-awaiting-review` | `lithos.task.*` | Rewrites `awaiting_review_file`: open tasks carrying `develop_pr_url`, as PR links |
| `obsidian-status-transition` | `obsidian.task.status_changed` | `[ ]→[x]` completes, `[ ]→[-]` cancels, `[x]→[ ]` posts `[ReopenRequested]`; `[/]` and `[>]` are no-ops |
| `obsidian-priority-changed` | `obsidian.task.priority_changed` | `lithos_task_update(metadata={priority})` |
| `obsidian-due-date-changed` | `obsidian.task.due_date_changed` | `lithos_task_update(metadata={scheduled_for})` |
| `project-context-projection` | `lithos.note.*` | Writes each `project-context` doc to `<projects_dir>/<slug>/<filename>.md` |
| `note-push` | `obsidian.note.modified` | `lithos_write(id, body, expected_version)`; conflicts go to `_lithos/conflicts/` |
| `task-archive` | `lithos.task.completed` / `cancelled` | Appends the resolved line to `<projects_dir>/<slug>/<slug>-done.md` |

`note-push` needs `project-context-projection` (it seeds the body-hash baselines) and `task-archive` needs `obsidian-projection` (it only archives tasks the operator saw); the daemon warns at startup if either pairing is missing.

---

## Projects

A **project** exists in Lithos when a `project-context`-tagged doc lives at `projects/<slug>/` — canonically `projects/<slug>/<slug>-project-context.md`. The slug is the directory name; Lithos enforces uniqueness. The TOML's `[projects.<slug>]` entry is a separate, host-local fact: which checkout this host may act on. `lithos-loom project list` merges the two views (slug, `active` / `archived` status, repo path).

Create one from the CLI or the `create-project` macro:

```bash
lithos-loom project create --title "My Project" [--slug my-project] [--body-file ./README.md]
lithos-loom project import /path/to/existing.md [--dry-run]   # adopt an existing doc + its - [ ] lines as tasks
```

`project import` extracts `- [ ]` lines as real Lithos tasks: `#tags`, priority emoji, and indentation become an epic with children (parallel by default; a `[sequential]` token on the parent chains them with `blocks` edges). See [`project import`](cli/project-import.md).

---

## The task inbox projection

Every open task the operator should see becomes one Tasks-plugin line in `tasks_file`, fields always in this order:

```markdown
- [ ] <title> 🆔 lithos:<id> [#project/<slug>] [#lithos/<route>] [⛔ lithos:<blocker-id>…] [🔺⏫🔼🔽⏬] [📅 YYYY-MM-DD]
- [x] <title> 🆔 lithos:<id> #project/<slug> ✅ YYYY-MM-DD
- [-] <title> 🆔 lithos:<id> #project/<slug> ❌ YYYY-MM-DD
```

| Token | Source | Direction |
|-------|--------|-----------|
| `[ ]` / `[x]` / `[-]` | `task.status` | **Bidirectional** |
| `🆔 lithos:<id>` | `task.id` | identity, never edited |
| `#project/<slug>` | `metadata.project` | one-way |
| `#lithos/<route>` | the `human_blocking` route holding the claim | one-way |
| `⛔ lithos:<id>` | `lithos_task_blocked` (one per blocker) | one-way |
| priority emoji | `metadata.priority` (`highest` … `lowest`) | **Bidirectional** |
| `📅 date` | `metadata.scheduled_for`, else today for human-blocking tasks | **Bidirectional** |
| `✅` / `❌ date` | `resolved_at` | one-way, within `resolved_ttl_days` |

A task is projected when it is open, is not a non-`human` gate (a `pr` gate must never be tickable from the vault), and either no route matches its tags or the matching route is `human_blocking = true` and currently holds the claim. Autonomous work therefore stays out of the inbox; a loom-raised `human` gate lands in it as a tickable line — ticking it is the retry gesture.

Edits flow back within ~250 ms: the file watcher parses line by line, suppresses the daemon's own writes by mtime + content hash, and emits one event per divergent field. Task tags from Lithos are not rendered on the line today.

---

## Bidirectional project-context sync

Each `project-context` doc projects to `<projects_dir>/<slug>/<filename>.md` with a daemon-managed frontmatter envelope (`lithos_id`, `lithos_version`, `lithos_updated_at`, `slug`, `status`, `tags`) above `# <title>` and the body.

- **Body edits** in Obsidian are pushed with `lithos_write(id, content, expected_version)`. On `version_conflict` the operator's body is moved to `_lithos/conflicts/<slug>.<file>.<ts>.md`, the canonical body is pulled back, and a `[Friction]` is logged — diff the two to recover the edit. Edits made while the daemon was down route through the same resolver on the next bootstrap.
- **Frontmatter-only edits are silently absorbed**: the watcher hashes the body only, and the next projection rewrite reconstructs frontmatter from scratch.
- **Done files** (`<slug>-done.md`, written by `task-archive`) are vault-only and append-only; the watcher ignores them. Rebuild one from Lithos with [`project regenerate-done`](cli/project-regenerate-done.md).

---

## Templater macros

Two Templater templates in the repo's [`docs/macros/`](https://github.com/agent-lore/lithos-loom/tree/main/docs/macros) complete the capture flow from inside the editor. Each is a single `<%* %>` execution block — copy the file verbatim into your Templater template folder, register it under *Settings → Templater → Template Hotkeys*, and bind a hotkey to the **`Templater: Insert <name>`** command (not `Create`, which opens a new note instead of inserting at the cursor).

| Macro | What it does |
|-------|--------------|
| `capture-task.md` | One modal (project, title defaulted to your selection, brief, scheduled date, priority, tags) → `lithos-loom task create --no-insert` → inserts `[[<tasks_file>\|<title>]] 🆔 lithos:<id>` at the cursor. The canonical task line lands in `tasks_file` via the projection ~250 ms later. |
| `create-project.md` | One modal (title, auto-derived slug, tags, description) → `lithos-loom project create --format json --body-file <tmp>` → inserts a wikilink to `_lithos/projects/<slug>/<slug>-project-context`. |

The macros insert a **wikilink, not the task line**, so the task exists in exactly one place the daemon owns; the link preserves the capture context and is greppable by id. Both read `lithos-loom obsidian-sync show --format json` at fire time, so a customised `tasks_file` or `projects_dir` resolves without editing the macro. Errors from the CLI surface as a 10-second Notice.

### CLI on Obsidian's PATH

The macros shell out through Node's `child_process`, and Obsidian Desktop inherits PATH from the desktop launcher session, not your shell rc. Check from Obsidian's developer console (++ctrl+shift+i++ → Console):

```javascript
require("child_process").execSync("which lithos-loom").toString()
```

If that errors, install with `uv tool install lithos-loom` (puts the binary in `~/.local/bin/`, usually on the launcher PATH on Linux; on macOS use `launchctl setenv PATH …` or symlink into `/usr/local/bin/`), or hard-code the absolute path in the macro's `execFileSync` call. The daemon must be running too — otherwise the task is created in Lithos but the wikilink dangles. Full install notes and behaviour details: [`docs/macros/README.md`](https://github.com/agent-lore/lithos-loom/blob/main/docs/macros/README.md).
