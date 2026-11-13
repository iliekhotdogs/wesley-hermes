# Contributor Quick Reference

For occasional contributors and PR authors. Full developer docs: https://hermes-agent.nousresearch.com/docs/developer-guide/

### Project Layout

```
hermes-agent/
├── run_agent.py          # AIAgent — core conversation loop
├── model_tools.py        # Tool discovery and dispatch
├── toolsets.py           # Toolset definitions
├── cli.py                # Interactive CLI (HermesCLI)
├── hermes_state.py       # SQLite session store
├── agent/                # Prompt builder, context compression, memory, model routing, credential pooling, skill dispatch
├── hermes_cli/           # CLI subcommands, config, setup, commands
│   ├── commands.py       # Slash command registry (CommandDef)
│   ├── config.py         # DEFAULT_CONFIG, env var definitions
│   └── main.py           # CLI entry point and argparse
├── tools/                # One file per tool
│   └── registry.py       # Central tool registry
├── gateway/              # Messaging gateway
│   └── platforms/        # Platform adapters (telegram, discord, etc.)
├── cron/                 # Job scheduler
├── tests/                # Extensive pytest suite (run via scripts/run_tests.sh)
└── website/              # Docusaurus docs site
```

Config: `~/.hermes/config.yaml` (settings), `~/.hermes/.env` (API keys) — both under `$HERMES_HOME` when it is set.

### Adding a Tool

Two files. Auto-discovery imports any `tools/*.py` with a top-level
`registry.register()` call, but a tool is only *exposed* to an agent once
its name appears in a toolset.

**1. Create `tools/your_tool.py`:**
```python
import json, os
from tools.registry import registry

def check_requirements() -> bool:
    return bool(os.getenv("EXAMPLE_API_KEY"))

def example_tool(param: str, task_id: str = None) -> str:
    return json.dumps({"success": True, "data": "..."})

registry.register(
    name="example_tool",
    toolset="example",
    schema={"name": "example_tool", "description": "...", "parameters": {...}},
    handler=lambda args, **kw: example_tool(
        param=args.get("param", ""), task_id=kw.get("task_id")),
    check_fn=check_requirements,
    requires_env=["EXAMPLE_API_KEY"],
)
```

**2. Wire it into a toolset in `toolsets.py`** — add the name to
`_HERMES_CORE_TOOLS` (every platform) or to a specific toolset.

All handlers must return JSON strings. Use `get_hermes_home()` for paths,
never hardcode `~/.hermes`. For custom/local-only tools, write a plugin in
`~/.hermes/plugins/` instead of editing core — see the developer docs.

### Deploying local policy plugins

1. Inspect the installed engine's plugin interfaces and existing task/write safeguards before implementing a replacement. Stage only necessary nonsecret source into isolated workspaces; retain privileged validation and live deployment on main. Reuse existing deterministic remote IDs and operation ledgers before introducing a competing store.
2. Run candidate tests on the deployment OS as well as the isolated worker backend. For SQLite fixtures use `with contextlib.closing(sqlite3.connect(path)) as db, db:` when both connection lifetime and transactions need context management: `with sqlite3.connect(...)` commits or rolls back but does not close the handle, which can break Windows temporary-directory cleanup. Join spawned workers and close their queues before cleanup.
3. Declare exact registered names in manifest `provides_tools` and `provides_hooks` lists, not booleans or a substitute `hooks` list. Run `hermes plugins validate <candidate-path>` and `hermes plugins doctor <candidate-path> --ci`; an offline registration harness alone does not validate native admission. Review private-import warnings against the installed version rather than silently treating them as a stable public API.
4. Bind the evidence manifest to final candidate hashes and rerun its declared checks on main after corrections. Preserve real output and label provider simulations explicitly; a local evidence PASS does not prove live external integration.
5. Install into the intended profile and enable with the supported plugin CLI. Read back `hermes plugins show <name>` and run doctor against the installed name. Capture the gateway's reload result: hooks can become active immediately while tools remain deferred until a new session. Never claim the current conversation has new tools merely because registration passed.
6. Exercise real plugin-produced vetoes through the installed native directive parser: a block requires a nonempty `message`; `reason` alone is ignored. Include exception fallback vetoes. Registration and action-only harness assertions cannot establish enforcement.
7. Start observe-only, then verify a narrowly opted-in real workflow before enforcement. Inspect actual host dispatch, result shape, task/run identity, and controller-versus-container workspace paths; mocked callbacks do not establish real receipt issuance. Identify each participating profile explicitly: installing in main does not cover isolated specialists. Verify both callback failure handling and outer dispatcher failure handling before calling a guard fail-closed.
8. Report four distinct states: files installed, runtime loaded, scopes opted in, actions enforced. An observer configured with no tasks is deployment scaffolding, not duplicate-work prevention. Keep the original acceptance task incomplete until required live integration is verified; preserve an explicit disable command and retain audit state for rollback.

### Adding a Slash Command

1. Add `CommandDef` to `COMMAND_REGISTRY` in `hermes_cli/commands.py`
2. Add handler in `cli.py` → `process_command()`
3. (Optional) Add gateway handler in `gateway/run.py`

All consumers (help text, autocomplete, Telegram menu, Slack mapping) derive from the central registry automatically.

### Agent Loop (High Level)

```
run_conversation():
  1. Build system prompt
  2. Loop while iterations < max:
     a. Call LLM (OpenAI-format messages + tool schemas)
     b. If tool_calls → dispatch each via handle_function_call() → append results → continue
     c. If text response → return
  3. Context compression triggers automatically near token limit
```

### Testing

Use the canonical runner — it enforces CI-parity (hermetic `env -i`, unset
credentials, TZ=UTC, per-file subprocess isolation via
`scripts/run_tests_parallel.py` — no xdist, worker count auto-scaled):

```bash
scripts/run_tests.sh                          # full suite
scripts/run_tests.sh tests/tools/             # one directory
scripts/run_tests.sh tests/tools/test_x.py    # one file
scripts/run_tests.sh -v --tb=long             # pass-through pytest flags
```

- Tests auto-redirect `HERMES_HOME` to temp dirs — never touch real `~/.hermes/`.
- The script probes `.venv`, then `venv`, then the shared worktree venv.
- **Windows:** inspect the checkout's runner before choosing a workaround. Recent
  `scripts/run_tests.sh` supports Git Bash/MSYS, native `Scripts/python.exe` venvs
  and an explicit `HERMES_PYTHON`; prefer that canonical clean-env, per-file runner
  when available. Native subprocess executable paths must be absolute, even when
  `cwd` is supplied. For older checkouts without this support, consult
  `references/windows-quirks.md` rather than guessing.

**Cross-platform test guards:** tests using POSIX-only syscalls need a skip marker. Common ones already in the codebase:
- Symlink creation → `@pytest.mark.skipif(sys.platform == "win32", reason="Symlinks require elevated privileges on Windows")` (see `tests/cron/test_cron_script.py`)
- POSIX file modes (0o600, etc.) → `@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX mode bits not enforced on Windows")` (see `tests/hermes_cli/test_auth_toctou_file_modes.py`)
- `signal.SIGALRM` → Unix-only (per-test timeouts no longer use it directly; see the win32 timeout-method shim in `tests/conftest.py::pytest_configure`)
- Live Winsock / Windows-specific regression tests → `@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific regression")`

**Monkeypatching `sys.platform` is not enough** when the code under test also calls `platform.system()` / `platform.release()` / `platform.mac_ver()`. Those functions re-read the real OS independently, so a test that sets `sys.platform = "linux"` on a Windows runner will still see `platform.system() == "Windows"` and route through the Windows branch. Patch all three together:

```python
monkeypatch.setattr(sys, "platform", "linux")
monkeypatch.setattr(platform, "system", lambda: "Linux")
monkeypatch.setattr(platform, "release", lambda: "6.8.0-generic")
```

See `tests/agent/test_prompt_builder.py::TestEnvironmentHints` for a worked example.

### System prompt's execution-environment block

Factual host/backend guidance (OS, `$HOME`, cwd, terminal backend, shell)
is emitted by `agent/prompt_builder.py::build_environment_hints()`. The key
invariant for prompt authors: with a **remote** terminal backend
(`docker, singularity, modal, daytona, ssh, managed_modal`), host info is
suppressed and *every* file tool runs inside the backend container — the
prompt must never describe the host the agent can't touch.

### Commit Conventions

```
type: concise subject line

Optional body.
```

Types: `fix:`, `feat:`, `refactor:`, `docs:`, `chore:`

### Key Rules

- **Never break prompt caching** — don't change context, tools, or system prompt mid-conversation
- **Message role alternation** — never two assistant or two user messages in a row
- Use `get_hermes_home()` from `hermes_constants` for all paths (profile-safe)
- Config values go in `config.yaml`, secrets go in `.env`
- New tools need a `check_fn` so they only appear when requirements are met
