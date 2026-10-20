# Security & Privacy Toggles

Common "why is Hermes doing X to my output / tool calls / commands?" toggles — and the exact commands to change them. Most of these need a fresh session (`/reset` in chat, or start a new `hermes` invocation) because they're read once at startup.

### Secret redaction in tool output

Secret redaction is **on by default** — tool output (terminal stdout, `read_file`, web content, subagent summaries, etc.) is scanned for strings that look like API keys, tokens, and secrets before it enters the conversation context and logs. Leave it enabled for normal use:

```bash
hermes config set security.redact_secrets true       # keep enabled globally
```

**Restart required.** `security.redact_secrets` is snapshotted at import time — toggling it mid-session (e.g. via `export HERMES_REDACT_SECRETS=false` from a tool call) will NOT take effect for the running process. Tell the user to change it in config from a terminal, then start a new session. This is deliberate — it prevents an LLM from flipping the toggle on itself mid-task.

Disable only when you deliberately need raw credential-like strings for debugging or redactor development:
```bash
hermes config set security.redact_secrets false
```

### PII redaction in gateway messages

Separate from secret redaction. When enabled, the gateway hashes user IDs and strips phone numbers from the session context before it reaches the model:

```bash
hermes config set privacy.redact_pii true    # enable
hermes config set privacy.redact_pii false   # disable (default)
```

### Command approval prompts

By default (`approvals.mode: smart`), Hermes asks an auxiliary LLM to assess shell commands flagged as destructive (`rm -rf`, `git reset --hard`, etc.). The modes are:

- `smart` — auto-approve a low-risk command once, deny high-risk commands, and prompt when uncertain (default)
- `manual` — always prompt
- `off` — skip all approval prompts (equivalent to `--yolo`)

```bash
hermes config set approvals.mode smart       # recommended middle ground
hermes config set approvals.mode off         # bypass everything (not recommended)
```

Per-invocation bypass without changing config:
- `hermes --yolo …`
- `export HERMES_YOLO_MODE=1`

Note: YOLO / `approvals.mode: off` does NOT turn off secret redaction. They are independent.

### "Reset permissions" / "make Hermes ask again"

The user usually means: wipe the accumulated "Always allow" state — NOT yolo
mode, and NOT a per-edit diff prompt (which doesn't exist; file writes never
go through the approval prompt, only shell commands do). Two stores hold it:

1. Shell-command allowlist: `hermes config set command_allowlist '[]'`
2. Shell-hook consent (only if present): `rm -f ~/.hermes/shell-hooks-allowlist.json`

Then sanity-check `hermes config get approvals.mode` (should not be `off`)
and confirm `--yolo` isn't baked into their launch alias or systemd unit.

### Shell hooks allowlist

Some shell-hook integrations require explicit allowlisting before they fire. Managed via `~/.hermes/shell-hooks-allowlist.json` — prompted interactively the first time a hook wants to run.

## Scoped specialist Google Workspace authority

- Inspect the actual `profile-permissions` pre-tool hook when `approvals.mode: off` still yields `MAIN_REQUIRED`; command approval mode does not override role hooks.
- For explicitly authorized full Workspace access on cron/builder, permit their own installed `google_api.py` service operations and trusted `scripts/workspace_api.py --request-file <absolute JSON>` or `--clock` commands. Preserve standalone-command parsing, profile ownership, credential/config-write protections, and restrictions on unrelated roles; do not disable the entire plugin.
- Use the trusted JSON route for exact GET, Calendar timezone/colors, pagination and wrapper feature gaps. Requests contain service/version/resource-segments/method/params/optional-body, not arbitrary code. The deployed service versions are Calendar v3, Tasks v1, Gmail v1, Drive v3, Docs v1, Sheets v4, People v1. Preserve partial batch successes and halt on failure without automatically replaying mutations.
- Align each authorized profile's SOUL override and profile-scoped installed wrapper/credentials. Existing OAuth grants remain the external limit; API permission policy cannot manufacture missing scopes. Never print tokens, revoke working credentials or start repeated consent.
- Exercise the deployed route through actual plugin discovery and `model_tools.handle_function_call` in a fresh process under each target HERMES_HOME. Verify live read-only source output and confirm unrelated admin commands still fail. Drain/restart only the affected live gateway and read back its process status; fresh workers reload policies automatically.
- Pin evidence-gate subprocess argv to the actual Hermes interpreter (`sys.executable`): shell `python` and subprocess PATH `python` may resolve differently on Windows, leaving pytest unavailable despite a successful direct test.
- Verify every injected Kanban skill exists on the ASSIGNEE before using `skills=[...]`; main's installed skills do not imply another profile has them. Repair one concrete missing dependency on the same card rather than recreating the assignment.

### Disabling the web/browser/image-gen tools

To keep the model away from network or media tools entirely, open `hermes tools` and toggle per-platform. Takes effect on next session (`/reset`). See `references/configuration.md` for the toolset list.

