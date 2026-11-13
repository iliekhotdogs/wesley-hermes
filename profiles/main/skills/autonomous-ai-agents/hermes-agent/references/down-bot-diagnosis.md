# Diagnosing a "bot is down" report (Discord / specialist profiles)

## 1. Identify WHICH bot first
"Terminal bot" can mean a Docker-terminal profile (builder/cowsearcher) OR a standalone Discord bot outside the gateway. Before deep digging, enumerate candidates cheaply:
- `discord_admin list_channels` / `list_roles` for the guild: a channel like `#pc-terminal` plus a managed role like `city pc terminal bot` identifies a separate bot application.
- `grep -rIl <channel_id>` over `C:/Users/<user>` (exclude AppData/OneDrive/node_modules, set a generous timeout) finds the standalone script (e.g. `~/pc-terminal-bridge/bridge.py` + `config.env` + `run-hidden.vbs`, started from the Startup folder).
- If the first guess yields a plausible-but-unconfirmed cause, say so and ask/verify rather than declaring victory.

## 2. Standalone Discord bot (outside the gateway)
- Check the process list for its script name; a dead loop (`run.cmd`) means nothing is running.
- Verify the token's identity WITHOUT printing it: the first dot-segment of a Discord bot token is base64 of the bot's user ID. Decode it and compare with the bot's ID from `fetch_messages` author ids / `list_roles`. A token that decodes to another bot (e.g. lib) explains "offline" even though the code is fine.
- Never test-run the script while the token is unverified: it logs in and posts as whichever bot owns the token (and can collide with that bot's gateway connection). Decode first, then run.
- Search `.env` files, quarantine folders and backups by decoding candidate tokens' ID segment; if the right token is absent, it must be reset in the Developer Portal. Give the user a `Read-Host` PowerShell snippet that rewrites only `BRIDGE_BOT_TOKEN=` and relaunches via `wscript run-hidden.vbs`; never accept the token in chat.
- Confirm recovery by reading the channel: the bot's own "online" message from the correct author id, plus exactly one bridge python process.

## 3. Docker-terminal profiles (builder, cowsearcher)
- Symptom: `TERMINAL_CWD does not exist: /workspace` and `session.create refused ... must be an absolute path to an existing directory`; `hermes -p <profile> chat -q ...` ends in `agent_init_failed`.
- Cause: `terminal.cwd: /workspace` is a container path, but Hermes validates the cwd on the HOST before starting the agent. Fix: create the host directory (`mkdir C:/workspace`); the Docker volume mapping stays unchanged.
- Verify via a throwaway kanban card for the profile (CLI `chat -q` from main may be routed back with "send through @main"); check the card completes and the file appears in the host workspace.

## 4. Triage hygiene
- Report unrelated findings (unhealthy container, plugin load warnings, other-profile reconnects) separately and mark them unfixed/untested rather than implying they are resolved.
