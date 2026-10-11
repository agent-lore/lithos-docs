# Installation

Loom is a single Python package that runs as a foreground host process. It is not published to PyPI yet; install it from the repo.

## Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| Python | 3.12 (`>=3.12,<3.13`) | Pinned to one minor in `pyproject.toml` |
| [uv](https://docs.astral.sh/uv/) | any recent | The project's only supported installer and runner |
| Lithos | reachable over HTTP | MCP over the `/sse` endpoint plus `GET /events`; must have the task-graph extension (`lithos-loom doctor` probes it) |
| `git` | with worktree support | Every plugin run and on-demand command works in a throwaway worktree |
| `docker` | host daemon | `story-develop`, `develop review` / `converge` / `merge-gate` run agents and checks in the sandbox image (default `ralph-sandbox:latest`) |
| `claude` and/or `codex` CLI | authenticated | Agent engines for plugin bodies only; the daemon itself needs neither |
| `gh` CLI | authenticated | PR delivery and the GitHub watcher (`gh auth token` is read at startup) |
| Obsidian Desktop + [Templater](https://github.com/SilentVoid13/Templater) + [Tasks](https://publish.obsidian.md/tasks/Introduction) | vault host only | Templater runs the capture macros; Tasks renders the projected lines |

!!! note "Why there is no Docker image"
    Lithos and Influx run as containers because they are services. Loom creates git worktrees you `cd` into, calls `claude` / `codex` / `gh` with your per-user credentials, spawns docker containers of its own, and must be on Obsidian Desktop's PATH. Containerising it would mean bind-mounting `~/.claude/`, `~/.codex/`, `~/.config/gh/`, every project checkout, the vault and the docker socket — so it runs on the host.

---

## Install

=== "From a checkout (current)"

    ```bash
    git clone https://github.com/agent-lore/lithos-loom.git
    cd lithos-loom
    uv sync          # editable install + dev deps; `lithos-loom` lands on the venv PATH
    uv run lithos-loom --help
    ```

=== "As a tool (once published)"

    ```bash
    uv tool install lithos-loom   # puts `lithos-loom` in ~/.local/bin/
    ```

    This is the install the Templater macros want — Obsidian Desktop inherits PATH from the desktop launcher session, not your shell rc, and `~/.local/bin` is usually on it (Linux). See [Obsidian bridge → CLI on Obsidian's PATH](obsidian-bridge.md#cli-on-obsidians-path).

---

## Configure

Loom reads **one TOML file per process**. Discovery order:

1. `LITHOS_LOOM_CONFIG=/abs/path.toml` — explicit, beats everything.
2. If `LITHOS_LOOM_ENVIRONMENT=<env>` is set: `config.<env>.toml` in `./` then `$XDG_CONFIG_HOME/lithos-loom/` (default `~/.config/lithos-loom/`).
3. Otherwise `config.toml` in the same two locations.

`--config / -c <path>` on any command overrides all three. `python-dotenv` loads a `.env` from the current directory at startup; `LITHOS_URL` set in the environment overrides `[orchestrator].lithos_url`.

```bash
mkdir -p ~/.config/lithos-loom
cp examples/lithos-loom.toml ~/.config/lithos-loom/config.toml
$EDITOR ~/.config/lithos-loom/config.toml
```

A minimal route-runner host — one project, the shipped `story-develop` route, no vault:

```toml
[orchestrator]
agent_id   = "lithos-orchestrator-<host>"   # claim attribution; unique per host
lithos_url = "http://localhost:8765"
work_dir   = "/tmp/lithos-loom"             # per-task staging tree + pidfile

[projects.my-project]
repo = "/abs/path/to/my-project"            # the only required project field

[[routes]]
name = "story-develop"
command = "uv run python -m lithos_loom.plugins.story_develop --task-json {{task_json}} --work-dir {{work_dir}} --result-file {{result_file}} --repo {{repo}}"
max_runtime_seconds = 28800
completes_task = false                      # success = PR open, not task done

[routes.match]
tags = ["trigger:story-develop"]

[story_develop.default_models]              # required for any tool an agent runs on
claude = "opus"
codex  = "gpt-5.4"
```

The annotated example at [`examples/lithos-loom.toml`](https://github.com/agent-lore/lithos-loom/blob/main/examples/lithos-loom.toml) covers every block (`[obsidian_sync]`, `[github_watcher]`, `[[subscriptions]]`, `[notifications]`); the full reference is [`docs/SPECIFICATION.md` §3.1](https://github.com/agent-lore/lithos-loom/blob/main/docs/SPECIFICATION.md). The config dataclasses in [`src/lithos_loom/config.py`](https://github.com/agent-lore/lithos-loom/blob/main/src/lithos_loom/config.py) are the complete field list.

!!! tip "Per-environment configs"
    Keep a `config.dev.toml` pointing at a local Lithos and a `config.prod.toml` at the real one, then pick with `LITHOS_LOOM_ENVIRONMENT=dev uv run lithos-loom run`. Hot reload is not implemented — restart (or [drain](#drain-and-restart)) after editing the TOML.

---

## Validate

```bash
uv run lithos-loom validate-config            # parse + typecheck; lists projects / routes / subscriptions
uv run lithos-loom validate-config --dry-run  # also polls Lithos: which routes would fire per open task
uv run lithos-loom doctor
```

`doctor` prints PASS / FAIL per check and exits non-zero on any failure:

| Check | What it probes |
|-------|----------------|
| Vault (`vault_path_exists`, `_lithos/` creatable, write+read round-trip) | Skipped with a note when `[obsidian_sync]` is absent |
| `task_graph_extension` | Creates throwaway probe tasks and asserts `blocks` edges, cancelled-blocker semantics, `task_type` / `lithos_task_spawn` and `pr` gate readiness behave. **The same probe gates `run`.** |
| Projects | Every TOML `[projects.<slug>]` has a `project-context` doc at `projects/<slug>/` in Lithos |

---

## Run the daemon

```bash
uv run lithos-loom run
```

`run` claims `<work_dir>/supervisor.pid` under an exclusive lock (one daemon per work dir), runs the task-graph boot gate against Lithos and refuses to start if the server is unreachable or incompatible, reaps containers a previous daemon left behind, then forks the children your config enables. It stays in the foreground; use `tmux`, `nohup` or a `systemd --user` unit for background operation.

| Signal | Effect |
|--------|--------|
| `SIGINT` / `SIGTERM` | Graceful stop: children are told to stop, in-flight plugin subprocesses are cancelled, and anything still alive after `shutdown_grace_seconds` (default 30) is killed. A killed remediation round is refunded. |
| `SIGUSR1` | **Drain**: children stop admitting new work, finish what is in flight and exit 0. |

### Drain and restart

To restart without losing a multi-hour agent run:

```bash
uv run lithos-loom drain [--timeout SECONDS]   # returns when the daemon has exited
uv run lithos-loom run
```

`drain` finds the daemon through the pidfile and exits `0` when it has gone, `1` when there was nothing to signal, `2` when `--timeout` ran out with the daemon still draining.

---

## Next steps

- [Concepts →](concepts.md) — what a route is, how a task gets claimed, what a plugin must write back
- [Obsidian bridge →](obsidian-bridge.md) — add `[obsidian_sync]` on the vault host and install the macros
- [GitHub watcher →](github-watcher.md) — map repos and enable issue mirroring on one host
