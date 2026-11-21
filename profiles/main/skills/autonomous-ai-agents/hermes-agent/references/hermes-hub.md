# Hermes hub — on-demand reference

Load for quick start, path layout, surface selection, spawning/resume/orchestration, consistency/repeated-work fixes, paid-agent comparisons, or consumer-subscription integration. Also load the matching topic reference routed by the core skill before answering details.

**Status:** split from the original SKILL.md (version 3.2.0) to keep the core entry point small; installed by main. Commands and feature descriptions below are retained guidance, not newly verified current support. Existing references/templates were not staged and remain existing/unvalidated; paths are relative to the skill root, not this reference's directory. The core skill retains documentation authority and always-loaded invariants. Verify current behavior against https://hermes-agent.nousresearch.com/docs/ and its `llms.txt` index before use. During an offline-only assignment, report the verification boundary instead of fetching. Examples confer no authority to install, change configuration, spawn workers, access accounts, or publish; current role limits and main-owned operations control execution.

## Identity and capabilities

Hermes Agent is an open-source AI agent framework by Nous Research for terminal, native desktop, messaging platforms and IDEs. The staged guide describes provider-agnostic inference, reusable skills, persistent memory with pluggable backends, a multi-platform gateway, independent profiles, and extensibility through plugins, MCP, webhooks, cron, skins, desktop plugins, TUI widgets and pets. These are orientation, not a complete feature inventory or permission to access memory or accounts.

## Evaluating consistency and repeated-work fixes

When the owner asks for more consistent Hermes behavior, give concrete mechanisms, their enforcement points, and executable acceptance tests—not another list of prompt rules. Distinguish repeated code discovery (where a repository graph may help) from duplicate task execution (which needs task history and operation-state checks). Inspect existing resume guards, idempotency handling, and completion contracts before proposing replacements. State separately what is proposed, implemented, exercised, and deployed; a queued task or passing offline suite is not active enforcement. Never promise that instructions are always followed: verify hook failure behavior and disclose unguarded terminal/API paths before claiming guarantees. Keep quick questions outside heavyweight task machinery.

## Evaluating a paid agent alongside Hermes

When the user asks whether buying another agent is worth it for an existing Hermes-run project, first identify the *specific product* (chat app, persistent cloud Bot, or developer API) and inspect the existing project's actual workflow. Do not conflate a branded Bot subscription with API access: compare the subscription's included agent features, separately billed API/tool usage, and the integration mechanism against what Hermes already does. Verify current prices, entitlement, and supported triggers in the vendor's official docs; these change frequently. Recommend a narrow, capped API or data-source pilot before a second agent subscription when the desired benefit is a single new signal. Explain that a webhook or handoff connects two systems rather than merging their memory or permissions. For financial automation, keep novel social/news signals in a timestamped, cited shadow evaluation before allowing bounded paper-trading influence; do not give a cloud research agent broker credentials or direct order authority merely to simplify integration.

## Connecting consumer model subscriptions

When the user already works through Hermes, keep the investigation focused on integration; do not substitute generic advice to use a separate chat app for the requested connection.

1. Identify the exact subscription, desired task, and integration: native Hermes inference, a local OpenAI-compatible bridge, or delegation to the vendor's official CLI. Verify the task's required inputs and modalities in that exact interface before recommending installation; app/API capabilities do not establish CLI capabilities. For an existing GPT/Claude workflow, recommend another model only for a demonstrated capability, useful independent review, or worthwhile quota savings—not variety alone. These architectures have different entitlement and permission boundaries; a delegated CLI worker does not provide automatic fallback when Hermes' coordinating model is rate-limited.
2. Check current Hermes provider docs and the vendor's current subscription/authentication docs. Distinguish consumer subscription allowances from separately metered API access; OAuth authenticates an account but does not itself grant third-party usage rights.
3. Before concluding there is no authorized route, check documented official CLI/headless and ACP integration surfaces as well as native providers. Do not assume invoking an official CLI from another agent is either permitted or prohibited without evidence covering that use.
4. If evaluating an open-source bridge, inspect its upstream authentication path, token storage, listener defaults, client authentication, maintenance/security notices, and tool-call/streaming compatibility. Check the current Hermes plugin catalog as well as native provider documentation: a native-provider page can omit community subscription routes. Verify official-client migrations against the vendor's current documentation rather than treating old CLI tutorials as current. Open source and local credential storage do not by themselves establish account safety or reliability. Never send subscription refresh tokens to an unreviewed hosted bridge.
   - For a deep security review, record the catalog-reviewed commit and current upstream SHA, compare their differences, and inventory every executable source, installation hook, and dependency declaration reviewed. Trace credential reads, network destinations, telemetry, subprocess argument construction, shell use, writes/deletion, updater behavior, and tool-dispatch boundaries; test fail-closed claims in a credential-free isolated environment only after reading the code. Cite exact file/line evidence and distinguish executed tests from static inspection.
   - Search upstream issues/PRs, release history, independent web reviews, and relevant forums. Separate author claims, independent reports, and reproduced behavior; state search coverage and evidence gaps instead of promising all reviews or treating absence of complaints as proof of safety.
   - Verify OS/process-management assumptions, minimum Hermes version, modalities, concurrency, and resource overhead against code and the intended deployment. Do not recommend updating a pinned live engine merely to satisfy a plugin requirement; report compatibility as a separate gate.
   - For subprocess-based bridges, inspect the environment passed to the child, executable resolution/PATH, inherited filesystem access, and persistent CLI logs as well as explicit token-file reads. Passing the full parent environment can expose unrelated provider secrets even when the bridge never opens credential files; recommend a minimal explicit environment and dedicated account/runtime for any later authorized pilot. Treat optional raw traces and CLI conversation stores as sensitive conversation records, not credential-free by assumption.
   - Check whether tool blocking is preventative or reactive: killing a child after observing a tool event does not prove that the tool had no side effects before the event was emitted. Distinguish custom-agent configuration and inert MCP handlers from OS sandbox enforcement; fake-CLI tests demonstrate protocol handling, not the real vendor CLI's execution ordering or isolation.
   - Inspect public source without installing it: use `git clone --no-checkout URL DEST`, record `git -C DEST rev-parse HEAD`, inventory with `git -C DEST ls-tree -r --name-only HEAD`, read files with `git -C DEST show HEAD:PATH`, and compare the catalog pin with `git -C DEST diff --stat PIN HEAD` followed by the full relevant diff. This avoids checking out or importing untrusted plugin code during initial triage. Read test fixtures and hooks before any isolated execution; source-only review is still not a completed runtime audit.
   - Keep code safety, subscription entitlement, vendor terms, and billing attribution as separate findings. An official CLI subprocess avoids some token-handling risks but does not prove that third-party orchestration is authorized. Finish with a graded verdict and remaining checks, not an absolute malware-free guarantee.
5. Report technical feasibility, vendor authorization, credential exposure, account-enforcement risk, and tested reliability separately. Describe a documented terms violation as such, not automatically as illegal; preserve the exact scope of any stated account suspension. Qualify negative findings as no verified authorized route, rather than proof none can exist.
6. State the verification boundary: documentation/source review is not an authenticated end-to-end test. Verify installation with the executable's version/help, then perform first sign-in in an empty dedicated workspace with ordinary permission prompts enabled. Leave browser account selection and consent to the user. A successful reply proves authenticated use, not which subscription allowance paid for it; verify entitlement separately. Before recommending a working Hermes integration, exercise inference and a complete tool-call round trip with authorized credentials. Recheck current vendor terms and entitlement at setup time rather than persisting a provider-specific prohibition as a permanent fact.

## Quick start — documented examples, not executed here

```bash
# Install (shell installer — sets up uv, Python, the venv, and the launcher)
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Interactive chat (default surface; set display.interface: tui to launch the Ink TUI instead)
hermes

# Single query
hermes chat -q "What is the capital of France?"

# Setup wizard / pick model+provider / health check
hermes setup
hermes model
hermes doctor

# Other surfaces
hermes desktop                 # native desktop app (alias: hermes gui)
hermes dashboard               # web admin panel + embedded chat
hermes proxy                   # OpenAI-compatible local proxy backed by your OAuth provider
```

## Key paths — layout guidance, not files to inspect

```text
~/.hermes/config.yaml       Main configuration (settings — never secrets)
~/.hermes/.env              API keys and secrets ONLY (under $HERMES_HOME if set)
$HERMES_HOME/skills/        Installed skills
~/.hermes/skins/            Custom themes (see references/themes.md)
~/.hermes/desktop-plugins/  Desktop app UI plugins (see references/desktop-plugins.md)
~/.hermes/tui-widgets/      TUI widget apps (see references/tui-widgets.md)
~/.hermes/pets/             Installed pet mascots (see references/petdex.md)
~/.hermes/state.db          Canonical session store (SQLite + FTS5)
~/.hermes/sessions/         Gateway routing index, request dumps, *.jsonl transcripts
~/.hermes/logs/             Gateway and error logs
~/.hermes/auth.json         OAuth tokens and credential pools
~/.hermes/hermes-agent/     Source code (if git-installed)
```

Profiles use `~/.hermes/profiles/<name>/` with the same layout. When a profile is active, resolve the real home from `$HERMES_HOME` — never hardcode `~/.hermes`. Use `get_hermes_home()` in code. A path appearing here does not authorize reading it.

## Spawning additional Hermes instances

Run additional Hermes processes as fully independent subprocesses — separate sessions, tools, and environments. Only execute when spawning is within the current role and explicitly authorized; otherwise route to main.

### When to use this vs delegate_task

| | `delegate_task` | Spawning `hermes` process |
|---|---|---|
| Isolation | Separate conversation, shared process | Fully independent process |
| Duration | Minutes (bounded by parent loop) | Hours/days |
| Tool access | Subset of parent's tools | Full tool access |
| Interactive | No | Yes (PTY mode) |
| Use case | Quick parallel subtasks | Long autonomous missions |

### One-shot mode

```text
terminal(command="hermes chat -q 'Research GRPO papers and write summary to ~/research/grpo.md'", timeout=300)

# Background for long tasks:
terminal(command="hermes chat -q 'Set up CI/CD for ~/myapp'", background=true)
```

### Interactive PTY mode (via tmux)

The staged guide describes prompt_toolkit as requiring a real terminal and recommends tmux for interactive spawning. Verify the current interface/backend before use.

```text
# Start
terminal(command="tmux new-session -d -s agent1 -x 120 -y 40 'hermes'", timeout=10)

# Wait for startup, then send a message
terminal(command="sleep 8 && tmux send-keys -t agent1 'Build a FastAPI auth service' Enter", timeout=15)

# Read output
terminal(command="sleep 20 && tmux capture-pane -t agent1 -p", timeout=5)

# Send follow-up
terminal(command="tmux send-keys -t agent1 'Add rate limiting middleware' Enter", timeout=5)

# Exit
terminal(command="tmux send-keys -t agent1 '/exit' Enter && sleep 2 && tmux kill-session -t agent1", timeout=10)
```

### Multi-agent coordination

```text
# Agent A: backend
terminal(command="tmux new-session -d -s backend -x 120 -y 40 'hermes -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t backend 'Build REST API for user management' Enter", timeout=15)

# Agent B: frontend
terminal(command="tmux new-session -d -s frontend -x 120 -y 40 'hermes -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t frontend 'Build React dashboard for user management' Enter", timeout=15)

# Check progress, relay context between them
terminal(command="tmux capture-pane -t backend -p | tail -30", timeout=5)
terminal(command="tmux send-keys -t frontend 'Here is the API schema from the backend agent: ...' Enter", timeout=5)
```

### Session resume

```text
# Resume most recent session
terminal(command="tmux new-session -d -s resumed 'hermes --continue'", timeout=10)

# Resume specific session
terminal(command="tmux new-session -d -s resumed 'hermes --resume 20260225_143052_a1b2c3'", timeout=10)
```

### Tips

- **Prefer `delegate_task` for quick subtasks** — less overhead than spawning a full process, when delegation is authorized.
- **Use `-w` (worktree mode)** when spawning agents that edit code — prevents git conflicts.
- **Set timeouts** for one-shot mode — complex tasks can take 5–10 minutes; that is retained guidance, not a measured result of this rewrite.
- **Use `hermes chat -q` for fire-and-forget** — no PTY needed.
- **Use tmux for interactive sessions** — raw PTY mode has `\r` vs `\n` issues with prompt_toolkit.
- **For scheduled tasks**, use the `cronjob` tool instead of spawning — handles delivery and retry, subject to role/scheduling authority.
- **“delegate_task is capped at N” reports** — load `references/delegate-task-concurrency-diagnosis.md`. The staged guide describes three cap paths; verify them before attributing a reported cap to runtime rather than model self-limiting.
- **“Can $external_app use my Nous Portal subscription / OAuth?”** — load `references/portal-auth-for-third-party-apps.md`. Walk the user through three layers (plugin-vs-app, what Portal actually exposes, local-broker-proxy option).

## Surfaces — staged orientation, verify current behavior

- **Desktop app** (`hermes desktop` / `hermes gui`) — native Electron app for macOS/Linux/Windows: streaming chat, session list, Cmd+K palette, drag-and-drop files, native notifications, per-profile remote-gateway login. Extend it with UI plugins — load `references/desktop-plugins.md`.
- **Web dashboard** (`hermes dashboard`) — full admin panel: messaging channels, MCP catalog, webhooks, memory, profile builder, plus an embedded `hermes --tui` chat. The staged guide describes an OAuth/token gate; this offline rewrite does not verify live security configuration.
- **Ink TUI** (`hermes --tui` or `display.interface: tui`) — terminal UI with docked widget apps — load `references/tui-widgets.md`.
- **OpenAI-compatible proxy** (`hermes proxy`) — a local OpenAI API backed by whichever OAuth provider you're signed into. The staged guide describes clients such as Codex CLI, Aider, Cline or scripts without an API key. This is not proof of third-party entitlement or secure listener defaults: apply the consumer-subscription verification procedure above and load `references/providers-and-models.md` and `references/security-privacy.md` as appropriate.

Treat deployment as part of an authorized implementation request, not a fresh permission question. Report installation, runtime loading, opted-in scope, and enforced coverage separately; an enabled observer with an empty scope protects no task. Follow the plugin deployment gates in `references/contributor-guide.md` before enabling enforcement.

### Reducing task-startup overhead

For the owner, optimize for less ceremony before useful work, not a lower tool count at the expense of correctness. First separate always-injected context, on-demand instruction reads, project rediscovery, and coordination round trips. Inventory the actual instruction sources and preserve a rule-to-location map before consolidating them. Keep skill entry points compact and directly relevant; do not reread unchanged material still available in active context, but reload after compression, edits, or a freshness concern. This does not override required skill loading.

Pilot a small reversible change before expanding: compact core rules and topical references. Include a project startup packet only for a currently user-approved project; remembered projects are not implicit pilot targets. When the user removes a project, stop its work and remove it from dispatchable specifications, acceptance checks, and downstream integration requirements—not merely a comment—so automatic decomposition cannot recreate cancelled scope. Keep stable project constraints separate from changing handoff state; label documented commands and README-reported status separately from newly exercised tests. Preserve the canonical vault rather than creating competing histories. Measure actual instruction characters, calls, tokens where exposed, and comparable startup runs; label token estimates and never infer latency savings from file-size reductions alone. Review live files for concurrent edits before deploying an offline candidate, and retain backups and rollback instructions. Explicitly distinguish candidate production, reviewed deployment, and measured runtime benefit.

Before dispatching an isolated worker, include both the verified host project root (metadata only) and the container-visible candidate workspace, plus allowed inputs, output paths, and main-owned deployment boundaries. Staged source files do not establish their original absolute location; omitting that fact can block otherwise executable work. Resolve an omitted prerequisite on the same card with verified evidence and resume once, rather than asking the user for information main already has or recreating the task graph. Keep offline implementation, main-owned host verification, and protected live deployment as separate gates; a denied verification command does not invalidate already-produced candidates. Main should run permitted read-only checks on retained artifacts, record exact remaining checks, and avoid redispatching implementation merely to obtain a completion receipt. Distinguish worker role restrictions from an actual approval gate; reassignment does not prove the latter has changed, and automatic status notifications are never user consent.
