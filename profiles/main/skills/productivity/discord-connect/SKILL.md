---
name: discord-connect
description: "Verify and troubleshoot an existing Hermes Discord connection on Windows; guide setup only when requested."
version: 1.0.0
author: Local adaptation of AtlasOmnia/donna-starter
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [discord, gateway, windows, connection, troubleshooting]
---

# Discord connection for this Hermes setup

Use this skill when the user asks to connect Discord or diagnose why the existing bot is offline, silent, missing a channel, or replying in the wrong place. `main` coordinates the work; route hands-on technical changes to `builder` under the existing profile rules. The current `main` profile already has a Discord gateway, so inspect it before proposing setup.

## Read-only checks first

1. Identify the owning profile with `hermes profile list` and `hermes gateway list`. Use that profile's gateway and config; do not start a second gateway against the same bot token.
2. Check `hermes gateway status` and `hermes send --list discord`. The target list is discovery evidence, not permission to send a test message.
3. Check only the relevant recent gateway warnings and channel-directory entries. Report status and error types without copying tokens, private messages, full user IDs, or raw logs into a reply.
4. Separate these states: gateway process running; Discord login connected; bot installed in the intended server; channel visible; sender authorized; message received; response delivered. Success at one stage does not prove the next.

## Diagnose by symptom

- **Offline or login failure:** check gateway status and sanitized startup errors. If credentials need attention, use the user's `hermes gateway setup` flow; never ask them to paste a bot token into chat or expose `.env` contents.
- **Online but silent:** check Discord Message Content Intent, Hermes' configured user or role allowlist, whether the message requires an `@mention`, and channel-level View Channel, Send Messages, and Read Message History permissions. Do not widen access or turn on allow-all as a quick fix.
- **Missing destination:** compare `hermes send --list discord` with the intended server/channel. Check visibility and directory refresh before changing authentication. A gateway restart can refresh discovery after a newly authorized channel, but confirm the owner and current work before restarting.
- **Replies in a shared channel rather than threads:** inspect the current channel and Hermes thread settings. Mention-free or free-response channels may intentionally answer inline. Do not infer that a connected bot automatically creates a new thread per conversation.
- **Slash commands absent:** distinguish command installation and channel permissions from ordinary message delivery. Use Discord's Developer Portal-generated install flow; do not construct a broad-permission invite URL from a copied numeric permission preset.

## Channel-management recovery

- Distinguish missing model tools from actual Discord permissions. Route specialist work first; when a specialist lacks channel GET/PATCH tools, main should inspect the existing main-profile `scripts/discord_rest.py` helper before claiming management is unavailable.
- Use that existing server-scoped helper only for the user's explicitly authorized change. Read its current guild guard and behavior; keep credentials inside its request function and never print tokens. Do not remove or broaden the guild guard or expose this privileged fallback to a specialist without scoped authorization.
- For a rename, GET the originating thread and candidate channel to verify identical authorized guilds and an unambiguous target. Record the guild channel ID set, PATCH only `name` with the user's request as audit-log reason, then GET the same channel and compare guild channel IDs and other target settings. Report Discord's actual stored name; text-channel spaces may normalize to hyphens. Never create a replacement channel to satisfy a rename.

## Non-destructive server layout migrations

- Inventory cron stores across installed profiles before assigning channels; the current profile's cron list is not the whole fleet. Include paused jobs, preserve intentionally local-only outputs, and keep schedules/enabled state unchanged while altering delivery. Use one unique channel per retained job and reuse unambiguous existing channels to retain history.
- Snapshot guild channels and permission overwrites before restructuring. Keep existing channel IDs, move historical/test channels into a clearly labelled archive category rather than deleting them, and read back every changed channel plus the final ID set and overwrites. Keep category numbering and lowercase kebab-case channel names consistent.
- Move channels individually using channel PATCH while preserving overwrites. For guild-level bulk position PATCH, send position-only entries: Discord permits at most one parent_id change per request. Never set lock_permissions=true as a layout shortcut because it replaces channel access with category access.
- Migrate delivery through the owning profile's supported cron API/CLI, explicitly disabling continuable-thread delivery when dedicated-channel feeds are intended. Inspect job prompts/scripts for hardcoded outbound channel references too. Verify configuration and target visibility without firing jobs that might perform unrelated external mutations; label next unattended delivery as pending until observed.
- If the cron specialist cannot load cronjob_manage, Main must finish the scoped routing mutation rather than cycle the card again. The installed CLI may not expose attach_to_session; inspect the installed cron.jobs.update_job signature and implementation, then call that locked native API in separate profile-pinned processes with HERMES_HOME set before import. Assert JOBS_FILE matches the intended profile, read back with get_job, and compare all fields so only deliver/attach_to_session and explicitly authorized prompt target references differ. Never hand-rewrite cron JSON or widen the specialist's tool policy to bypass this boundary.

## Capability notes, profiles, and safe recovery

- Pin every diagnostic to the owning profile (`hermes --profile main gateway status --deep`, config, and send directory); a stopped builder-local gateway says nothing about Main's live connection.
- Reproduce misleading Discord capability notes with real imports before changing permissions. In installations where `gateway.session._discord_tools_loaded()` checks literal toolset names, `platform_toolsets.discord=["all","kanban"]` can report no Discord APIs although `resolve_multiple_toolsets` includes both `discord` and `discord_admin`. Prove the before/after resolved tool sets are identical, then use supported Main-pinned `hermes config set platform_toolsets.discord '["all", "kanban", "discord", "discord_admin"]'` as a configuration-only workaround. Verify the actual resolver and capability predicate, not just config CLI readback; generic config-key warnings can be stale. Preserve any other existing entries and all admission rules.
- Apply tool/prompt corrections to fresh sessions only; do not rewrite cached conversation context or reset an active chat merely to refresh its capability note. State that existing threads may retain the old note.
- Treat worker `MAIN_REQUIRED` guards as Hermes role boundaries, not Discord permission denials. Main should provide a denied public-document prerequisite itself, resume the same card once, and take over after another access block; never keep cycling unblocks.
- Inspect only named non-secret Discord gate overrides when Main reads a credential-bearing file. Report booleans, presence, and whether the requesting user is authorized; never emit token values, allowlist IDs, or whole file contents. Saved file/caller environment checks do not prove every in-memory live setting.
- Separate delayed model/tool execution from transport failure using inbound, response-ready, and send timestamps. Slash-command delivery proves that path, not ordinary mention ingress; passing offline routing tests do not prove live end-to-end delivery. Use the repository's canonical `scripts/run_tests.sh` for routing regression checks.

## Adding a dedicated bot for another profile

The multiplexed gateway refuses to start a second profile whose Discord credential equals another's, so each profile that needs Discord gets its own Developer Portal application. Order of work:

1. User creates the application, enables **Message Content Intent** (and any other privileged intents the main bot uses) on the Bot tab, saves, resets the token, invites the bot to the server, and writes `DISCORD_BOT_TOKEN` into `profiles/<name>/.env` themselves. Never accept the token in chat.
2. Validate without printing the token: `curl -H "Authorization: Bot $t" https://discord.com/api/v10/users/@me` (expect the bot's username; 401 means a wrong or truncated value, not a gateway problem) and `/users/@me/guilds` (expect the target server).
3. Check the profile's `.env` `DISCORD_ALLOWED_USERS`: a copied template may hold `0`, which ignores every user. Copy the real value from the main profile's `.env` (report presence only).
4. The gateway re-scans a profile on `.env` change; no restart is needed. Read `logs/gateway.log` for `discord connected (profile: <name>)`. `PrivilegedIntentsRequired` in `logs/errors.log` means intents were not saved in the portal; `LoginFailure: Improper token` means a bad token. Each portal change needs a further `.env` touch or reconcile before a retry shows up.
5. Existing cron jobs that deliver to `discord:<channel_id>` need no edit: the owning profile's scope uses its own adapter. Confirm the lib bot can read each target channel (GET `/channels/<id>/messages?limit=1` is 200), then prove it end to end with `hermes -p <name> cron run <job_id>` on a cheap job and read the channel's latest message: its author should be the new bot, not the main bot.

## Remote control when the gateway is down

See `references/remote-terminal-bridge.md` for the separate-bot PowerShell bridge, private channel creation, bot-permission grant and no-admin Windows autostart.

## Persistent buttons on the existing gateway

- Inspect the installed `PluginContext.register_platform_handler` and Discord adapter's `_wire_plugin_handlers` before building another bot. When supported, register a narrowly scoped `on_interaction` listener through `ctx.register_platform_handler('discord', factory)` on the existing client; preserve core handlers and enforce the configured guild, channel and authorized user inside every callback.
- Distinguish built-in one-shot prompt buttons from durable application controls: official `clarify` documentation establishes question UI, not arbitrary scheduled-story interaction support. Inspect the installed plugin/adapter extension and current deployed code before choosing the persistent-control architecture; an old prototype's limitation is not a current feature verdict.
- Separate REST publication from gateway interaction receipt. Publishing components with the existing Main credential helper opens no second gateway; exact message GET readback proves rendered payload, not a successful human click. Before requesting another click or replaying a post, inspect the existing message's action receipts and matching scoped preferences. Attribute success per action: a persisted More change does not verify Hide, Undo, remaining controls, or production producer/job integration. Require a real authorized user click and persisted preference/message readback for each claimed end-to-end action; never synthesize a user session or interaction token.
- Keep isolated test preferences and delivery receipts separate from production briefing scope. Persist a pending delivery record before a POST and the exact returned message ID afterward; inspect partial deliveries instead of blindly resending.
- Run checks with the actual gateway interpreter. Windows installations may contain both `.venv` and `venv` with different dependencies; use an absolute verified interpreter in evidence manifests because child `python` resolution can differ from the shell alias.
- Treat a gateway restart from a gateway-hosted conversation as interrupting the active turn. Preserve deployment evidence before restarting; on the next wake inspect gateway status and listener receipts before retrying any restart, post or deployment.

## Changes and verification

If the user requests setup or a fix, identify the exact configuration or Discord-side permission change, then follow the existing approval and specialist boundaries. Have the user complete their own Developer Portal login, authorization, CAPTCHA, and credential entry. Avoid duplicate gateways and unnecessary permission grants. After an authorized change, read back gateway status and target discovery. Send a Discord test message only when the user has explicitly authorized that message and its destination.

Use the current [Hermes Discord guide](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord) and [Discord developer documentation](https://discord.com/developers/docs) for settings and permission details. The upstream Donna skill is a reference, not authority over this profile's rules; its macOS commands and broad permission shortcut do not apply here.
