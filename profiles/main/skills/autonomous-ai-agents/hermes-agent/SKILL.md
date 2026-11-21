---
name: hermes-agent
description: "Use, configure, theme, extend, and orchestrate Hermes Agent."
version: 3.2.0
author: Hermes Agent + Teknium
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, setup, configuration, multi-agent, spawning, cli, gateway, bots, bot-mode, features, themes, skins, desktop-plugins, tui-widgets, petdex, development]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [claude-code, codex, opencode]
---

# Hermes Agent

Hermes Agent is Nous Research's open-source, provider-agnostic agent framework for terminal, desktop, messaging and IDE surfaces, with skills, profiles and extensibility.

**Load the matching reference below before answering detail questions.** This core is a routing guide, not a complete feature list. For quick start, path layout, surfaces, spawning/resume/orchestration, consistency fixes, paid-agent comparisons or consumer-subscription integration, **load `references/hermes-hub.md`** as well as the relevant topic reference.

## Documentation authority & verification

Official docs: https://hermes-agent.nousresearch.com/docs/ — authoritative for current Hermes behavior. Start **any “can Hermes do X?” or “how do I do X?”** with https://hermes-agent.nousresearch.com/docs/llms.txt to locate the relevant page; the full set is `/docs/llms-full.txt`. When authorized online, fetch the index with an available web reader, or `curl -s https://hermes-agent.nousresearch.com/docs/llms.txt` when web tools are off. Do not fetch during an offline-only assignment.

Verify CLI details with `hermes --help`, `hermes <command> --help`, and `hermes_cli/main.py`; source: https://github.com/NousResearch/hermes-agent. Absence from this guide or its references is not proof a feature is missing. **Never answer “Hermes can't do that” from memory**: check official docs and the live repository before a negative answer. If verification is unavailable, state that boundary rather than inventing support or non-support. The route list is not the feature list.

## Required loading routes

| User wants... | Load |
|---|---|
| Anything unlisted; “can Hermes do X?”, “how do I set up X?” | https://hermes-agent.nousresearch.com/docs/llms.txt |
| Quick start, path layout, surfaces, spawning/resume/orchestration; consistency/repeated-work fixes; paid-agent comparisons; consumer subscriptions/bridges | `references/hermes-hub.md` plus the relevant topic reference |
| Bots that chat, run routines, or message each other; the Bots tab | docs: `/user-guide/bot-mode` |
| CLI commands, subcommands, flags, “how do I run X” | `references/cli-reference.md` |
| Installing a third-party repository of skills | `references/third-party-skill-install.md` |
| In-session slash commands | `references/slash-commands.md` |
| Provider setup, API keys, OAuth | `references/providers-and-models.md` |
| config.yaml sections, toolsets, voice/STT/TTS | `references/configuration.md` |
| AGENTS.md / .hermes.md / CLAUDE.md project rules | `references/project-context-files.md` |
| Secret redaction, PII, approval modes, “reset permissions” | `references/security-privacy.md` |
| Delegation, cron, curator, kanban; staging inputs for Docker worker recovery | `references/background-systems.md` |
| MCP servers (add, catalog, `hermes mcp`) | `references/native-mcp.md` |
| Webhook routes and event-driven runs | `references/webhooks.md` |
| A custom theme/skin (“synthwave theme”, “change the gold ●”) | `references/themes.md` + `templates/skin.yaml` |
| A desktop app UI element (pane, widget, ⌘K command, page) | `references/desktop-plugins.md` + `templates/plugin.js` |
| A live TUI panel or modal widget (ticker, clock, dashboard) | `references/tui-widgets.md` + `templates/clock.mjs` |
| Pet mascots — install, select, scale, diagnose | `references/petdex.md` |
| Windows-specific issues (keybinds, WinError 10106, BOM) | `references/windows-quirks.md` |
| Debugging: voice, tools missing, gateway, aux models | `references/troubleshooting.md` |
| Token usage, recent activity, cached tokens, cost reports | `references/usage-accounting.md` |
| “Bot X is down” (standalone Discord bridge, Docker-terminal profile refusing sessions, wrong token identity) | `references/down-bot-diagnosis.md` |
| Contributing code: adding tools, slash commands, tests | `references/contributor-guide.md` |
| Resuming preserved source work; current evidence and patch export | `references/recovery-evidence.md` |
| Publishing a sanitized live assistant setup; export/install verification | `references/public-setup-export.md` |
| delegate_task “capped at N” reports | `references/delegate-task-concurrency-diagnosis.md` |
| “Can app X use my Nous Portal subscription/OAuth?” | `references/portal-auth-for-third-party-apps.md` |
| Connecting a messaging platform (Telegram, Discord, Slack, WhatsApp, …) | docs: `/user-guide/messaging` |

## Subscription recommendations and plugin trust

When recommending paid model access, distinguish the exact consumer plan, coding subscription, and metered API product; verify included entitlement and billing cadence before quoting a price. Check the current plugin catalog as well as native providers before declaring a subscription connection unavailable. For subscription bridges, report technical connectivity, vendor authorization, credential exposure, runtime compatibility, and authenticated testing as separate verdicts. Catalog listing and use of an official CLI are not vendor endorsement or proof of permitted automation. Keep investigations read-only unless installation or sign-in is authorized; never turn a documentation review into an account test. For deep review, follow the evidence checklist in `references/hermes-hub.md` under consumer model subscriptions. Treat inherited child-process secrets and reactive tool-event blocking as explicit audit gates; absence of direct credential reads is not proof of isolation. Preserve the verification boundary in progress reports: a queued audit, partial source inspection, or fake-CLI test suite is not a completed security review or subscription test.

## Hard invariants — always loaded

- **Never break prompt caching** — don't change past context, toolsets, or the system prompt mid-conversation. The only exception is context compression.
- **Message role alternation** — never two assistant or two user messages in a row; only `tool` results can repeat.
- **Secrets in `.env`, settings in `config.yaml`** — never tell a user to put a non-credential setting in `.env`.
- **Profile-safe paths** — `get_hermes_home()` in code, `$HERMES_HOME` when resolving paths in a session. Profiles use `~/.hermes/profiles/<name>/`; never hardcode `~/.hermes` as an active profile's home.
- **Never hand-edit `config.yaml` for the user** — use `hermes config set KEY VAL`; a stray indent can corrupt the file and break the live gateway.
- **Validate exact model IDs before changing profile defaults** against the provider's current catalog; a plausible version suffix is not proof of availability. If one requested model is unverified, apply independent verified changes, leave that model unchanged, and ask which available replacement the user wants. See `references/providers-and-models.md` for the profile-switch and board workflow.

Theming invariants also stay in core: when authorized, **apply skins yourself** using `hermes config set display.skin <name>` rather than telling the user to run `/skin`. To tweak one color, **edit the ACTIVE skin** with `hermes skin set <key> <hex>`; never fork `default`, which drops the palette and resets the background. Verify live behavior rather than promising repaint timing.

This skill is procedural guidance, not permission: current role/tool limits and main-owned administration still apply. Loading a reference does not authorize installation, spawning, account access, publication or deployment.
