# OpenClaw → Hermes Migration Reference

Session-specific detail from migrating Wesley's OpenClaw setup to Hermes Agent (2026-08-27).

## What we found

**Archive:** `C:\Users\wesle\shared with old pc\old-pc-setup\openclaw-migration-z_user.zip` (833 entries, ~64 MB uncompressed)
- Path-rewritten for username `z_user` (old PC)
- Contains: `.openclaw/` (agents, state, workspace, memory-vault, credentials, plugin-skills, config), `poopyclaw/` (Next.js dashboard source)
- SQLite DBs: `state/openclaw.sqlite` (gateway state, cron jobs, sessions), per-agent `openclaw-agent.sqlite`, MindBase vault, Codex-home state
- 12 cron jobs in `cron_jobs` table

**Live install also exists:** `C:\Users\wesle\.openclaw` — separate from the archive, may contain newer state. Check before assuming archive is authoritative.

## Config mapping

| OpenClaw | Hermes |
|----------|--------|
| `openclaw.json` (agents, models, channels, gateway, plugins, mcp) | `config.yaml` (model, agent, display, memory, platforms, messaging, mcp_servers, toolsets) |
| `agents.list[]` with per-agent workspaces | Single active profile + `delegate_task` for ad-hoc specialists |
| `channels.discord`, `channels.telegram` | `platforms.discord`, `messaging.telegram` |
| `mcp.servers.mindbase` | `mcp_servers` (not ported — empty vault) |
| `plugins.entries` | `toolsets` + plugins |
| `cron_jobs` table (SQLite) | `cronjob` tool (durable scheduler) |
| `workspace/AGENTS.md`, `SOUL.md`, `USER.md`, `MEMORY.md` | `SOUL.md` (identity), memory tool (persistent), `AGENTS.md` (project context) |

## What we kept

1. **Behavioral conventions** (ported to SOUL.md):
   - "Be genuinely helpful, not performatively helpful"
   - "Tell the truth simply"
   - "Have opinions"
   - "Be resourceful before asking"
   - "Earn trust through competence"
   - "Remember you're a guest"

2. **Memory conventions** (added to Hermes memory):
   - Existing Solutions Preflight (check for existing tools before building custom)
   - Group Chat Protocol (when to speak vs stay silent)
   - Memory File Discipline (daily logs + curated long-term)

3. **Structured automation** (3 cron jobs to create):
   - Morning Briefing (daily 8:00 AM — Gmail + calendar + failed jobs + focus)
   - Market Scan (weekdays 7:30 AM — watchlist movers + cited news + earnings/macro)
   - Weekly Market Review (Sunday 6:00 PM — week review + catalysts + flags)

4. **Durable data**:
   - Investment watchlist: AAPL, NVDA, MSFT, GOOGL, TSLA, AMZN, TD, RY
   - Decision journal pattern (append-only)
   - Report archiving pattern (dated + latest.md)

5. **Google auth**: `gog` v0.34.1 installed and authenticated for `milesrlangston@gmail.com` (gmail+calendar). No reconnection needed.

## What we discarded

- **Miles R. Langston persona** (name, "dancing cow", 🐄 emoji, "Miles R. Langston & Associates") — user explicitly rejected
- **Multi-agent crew** (Teach Err, Invest Err, En Gineer, Mem Oree) — only Invest Err was meaningfully built; use `delegate_task` instead
- **MindBase memory vault** — 50-tool MCP server, empty shell, adds complexity
- **Poopyclaw/Mission Control dashboard** — coupled to OpenClaw gateway/RPC; Hermes has its own dashboard
- **All 12 old cron jobs** — most were framework-specific (Discord dashboard feeds, OpenClaw maintenance, security scripts, memory folding)
- **Empty structures** (teach-err deadlines/inbox, uninitialized skills)
- **Raw session transcripts** — too voluminous, wrong format

## Cron job execution limits

**Critical:** Hermes cron has a ~3-minute hard limit per run. OpenClaw allowed 5-30 minute jobs. Old prompts must be shortened, split, or supported with deterministic scripts.

Old jobs and their fates:
- `morning-briefing` (900s timeout) → recreate, tighten prompt
- `evening-memory-fold` (900s) → skip (Hermes has native memory)
- `weekly-maintenance` (1800s) → skip (OpenClaw-specific)
- `discord-feed-hourly/daily/weekly/morning` → skip (dashboard-specific)
- `security-check-twice-daily` → skip (OpenClaw-specific)
- `vault-lint` (900s) → skip (empty vault)
- `invest-scan` (900s) → recreate, tighten prompt
- `invest-weekly` (900s) → recreate, tighten prompt
- `teach-brief` (600s) → pause (empty inbox, enable later)

## Security findings

The archive contains sensitive material:
- Discord bot token, Telegram bot token
- Gateway auth tokens
- `.env.txt` (API keys)
- Google OAuth client secret (`client-secret.json`)
- OpenAI/Codex auth state (Codex-home directory)
- Pairing/allowlist data
- Personal Discord/GitHub identifiers

**Recommended cleanup:**
1. Delete unencrypted ZIP + `client-secret.json` from shared folder
2. Rotate old OpenClaw Discord, Telegram, gateway tokens
3. Do NOT copy OpenClaw credentials into Hermes; authorize each integration independently
4. Archive was in a Syncthing folder — ensure removal from all nodes

## Execution results (2026-08-27)

Migration executed successfully. Actual outcomes:

### Files created/updated
- `C:\Users\wesle\AppData\Local\hermes\SOUL.md` — replaced with identity-free version (behavioral traits only, no persona)
- Hermes memory — added 3 conventions (Existing Solutions Preflight, Group Chat Protocol, Memory File Discipline). Memory at 74% (1,629/2,200 chars)
- `C:\Users\wesle\hermes-projects\investing\watchlist.md` — 8 tickers (AAPL, NVDA, MSFT, GOOGL, TSLA, AMZN, TD, RY)
- `C:\Users\wesle\hermes-projects\investing\journal.md` — preserved 7 live entries from `.openclaw` (newer than archive)
- `C:\Users\wesle\hermes-projects\investing\reports\` — created empty

### Cron jobs created
| Job | ID | Schedule | Next run | Deliver |
|-----|----|----------|----------|---------|
| Morning Briefing | `317656cb145d` | Daily 8:00 AM PT | 2026-08-28 08:00 | `discord:1542698856075231285` |
| Market Scan | `33d1edf52c71` | Weekdays 7:30 AM PT | 2026-08-28 07:30 | `discord:1542698856075231285` |
| Weekly Market Review | `208beac9db1f` | Sunday 6:00 PM PT | 2026-08-30 18:00 | `discord:1542698856075231285` |

### Security cleanup performed
- Deleted `C:\Users\wesle\shared with old pc\old-pc-setup\client-secret.json` (Google OAuth secret)
- Deleted `C:\Users\wesle\shared with old pc\old-pc-setup\openclaw-migration-z_user.zip` (full state archive)
- Deleted `C:\Users\wesle\.openclaw\.env.txt` (Discord bot token in plaintext)
- Verified `credentials/` directory contains only pairing/allowlist files, no tokens

### Tokens flagged for manual rotation
1. Discord bot token — in `openclaw.json` and `.bak` copies
2. Telegram bot token — in `openclaw.json`
3. Gateway token — in `openclaw.json`
4. OpenAI API key — in `openclaw.json`

### Key discoveries
- **Live dir newer than archive**: `C:\Users\wesle\.openclaw\workspace\crew\invest-err\journal.md` had entries from Aug 23 and Aug 27 that were NOT in the archive (Aug 6). Always check the live installation before assuming the archive is authoritative.
- **gog binary**: Confirmed at `/c/Users/wesle/bin/gog` (gog.exe), on PATH
- **Discord channel**: Home channel `discord:1542698856075231285` (no thread_id — lands in main chat)
- **Pre-existing cron**: `Morning Command Center Briefing` (7:00 AM daily, `google-workspace` skill, deliver=local) was already running — left untouched

### Techniques used
- `unzip -p` to extract single files to stdout without disk extraction — useful for inspecting archive contents safely
- `project_create` with explicit `path` for named workspace
- `cronjob` tool with `deliver` targeting a specific Discord channel
- `memory` tool with `operations` batch for atomic multi-entry updates
- `skill_view` + `skill_manage(action='patch')` for read-before-write skill updates

## Gotchas discovered

1. **Windows file locking**: SQLite files extracted from zips on Windows lock the temp file. Use `tempfile.TemporaryDirectory()` and keep the connection within the context.
2. **Path rewriting**: The archive was path-rewritten from `wesle` → `z_user`. Any absolute paths in configs need updating for the new machine.
3. **Stale state**: `C:\Users\wesle\.openclaw` exists separately from the shared folder. The archive may not be the newest copy. **Always check the live installation first.**
4. **PowerShell JSON mangling**: PowerShell `Set-Content -Encoding UTF8` writes BOM → parsers fail. Use `[System.IO.File]::WriteAllText` with `UTF8Encoding($false)`.
5. **gog PATH**: Gateway-spawned processes may have stale PATH. Use full binary path (`/c/Users/wesle/bin/gog`) in cron prompts.
6. **npm native scripts**: `npm approve-scripts <pkg>` required for native modules (better-sqlite3, sharp, protobufjs) when VS build tools aren't installed.
7. **npx on Windows**: OpenClaw MCP can't spawn `npx`/`npx.cmd` (EINVAL/ENOENT). Use `node.exe <abs path to cli.js>` instead.
8. **Live vs archive divergence**: The live `.openclaw` directory can contain newer state than a migration archive. Compare timestamps before deciding which is authoritative.