---
name: agent-migration
description: "Use when migrating between AI agent frameworks."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [migration, agent-frameworks, openclaw, hermes, portability, state-inspection]
---

# Agent Migration

Migrate configuration, state, and automation between AI agent frameworks. Common triggers: moving from OpenClaw to Hermes, consolidating multiple agents, or auditing a legacy setup before decommissioning.

## When to Use

- User asks to migrate from one AI agent framework to another (e.g., OpenClaw → Hermes)
- User wants to consolidate multiple agents or decommission an old setup
- User asks to audit an old agent's state/config/automation before switching
- User wants to extract reusable parts (cron jobs, watchlists, preferences) from a legacy agent

## Workflow

### 1. Inspect the old state

Most agent frameworks store state in a mix of flat files, SQLite databases, and binary blobs. Start by inventorying everything without modifying it.

**Archives (zip/tar):** Use Python's `zipfile` module to list and read members without extracting to disk:

```python
import zipfile
with zipfile.ZipFile(path) as z:
    for info in z.infolist():
        print(info.file_size, info.filename)
    data = z.read('config.json')
```

**SQLite databases:** Use Python's `sqlite3` module to inspect schema and row counts. For read-only access to a zip member, write to a temp file first (Windows locks the file, so use a context manager that yields):

```python
import zipfile, sqlite3, tempfile, os
with zipfile.ZipFile(path) as z, tempfile.TemporaryDirectory() as d:
    f = os.path.join(d, 'db.sqlite')
    open(f, 'wb').write(z.read('state.sqlite'))
    con = sqlite3.connect(f)
    con.row_factory = sqlite3.Row
    tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
```

**Key locations to check:**
- Main config (e.g., `openclaw.json`, `config.yaml`)
- Agent definitions and identities
- Cron/scheduled jobs (usually a `cron_jobs` table in SQLite)
- Workspace documents (AGENTS.md, SOUL.md, MEMORY.md, USER.md, TOOLS.md)
- Skills and plugin registries
- Channel/messaging credentials (redact these in output)
- Session transcripts (usually not worth porting — too voluminous, wrong format)

### 2. Categorize: keep vs discard

For each item, decide:

**Keep and port:**
- User preferences and communication style
- Structured automation (cron jobs, alerts, scans)
- Durable data (watchlists, journals, project notes)
- Useful conventions (group chat behavior, memory discipline, existing-solutions-preflight)

**Discard unless user explicitly asks to keep:**
- Personas, names, mascots, emoji — strip by default, offer to restore specific elements
- Framework-specific scripts (e.g., PowerShell that calls old-framework-only APIs)
- Empty structures (empty inboxes, uninitialized skills)
- Coupled dashboards/backends tied to the old framework's gateway
- Raw session transcripts and trajectory logs
- Any credentials/tokens (never migrate secrets; re-authorize independently)

**Conditional:**
- Multi-agent setups → consider `delegate_task` instead of separate identities
- Memory vaults/wikis → only port if they contain substantial curated knowledge
- Complex cron jobs → verify they fit within the new framework's execution limits (Hermes cron has a ~3-minute hard limit per run)

### 3. Produce a portable migration plan

Write the plan as a self-contained markdown block the user can paste into a new session. Include:

1. Files to update (SOUL.md, memory entries, config values)
2. Cron jobs to create (with schedules, prompts, delivery targets)
3. Projects/workspaces to set up
4. Jobs to explicitly skip (and why)
5. Security cleanup steps
6. Execution order

### 4. Security cleanup

Old migration archives are sensitive. After confirming the migration is complete:

- Delete unencrypted archives from shared folders
- Rotate any tokens/credentials that were in the archive
- Never copy old credentials into the new framework; re-authorize each integration independently
- If the archive was in a Syncthing/shared folder, ensure it's removed from all nodes

### 5. Decommissioning

When the user wants the old framework *completely removed* (not just migrated away from), wipe every trace. OpenClaw installs itself in multiple locations on Windows — a partial leave-behind can leave dead scheduled tasks, startup entries, and dangling PATH references.

See `references/decommission-openclaw-windows.md` for the full checklist.

**Core principle:** Back up first (timestamped archive, verify gzip integrity + SHA256), then remove in dependency order: kill processes → remove locked files → uninstall npm package → delete startup entries → remove scheduled tasks → clean PATH → verify with a final artifact sweep.

**Minimum removal targets on Windows:**
- `~/.openclaw/` — main data (agents, workspaces, config, state, SQLite DBs)
- `~/AppData/Local/OpenClaw/` — deps (portable-git, etc.)
- `~/AppData/Roaming/npm/openclaw*` — global npm CLI package
- Startup: `~/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/OpenClaw Gateway.vbs`
- Scheduled task: "OpenClaw Gateway"
- PATH entries referencing `OpenClaw`

## Pitfalls

- **Persona carryover:** Users often don't want the old agent's name/mascot. Strip by default and offer to restore specific behavioral traits. Ask before porting identity.
- **Framework-specific automation:** Cron jobs that call the old framework's CLI/APIs won't work. Rewrite them against the new framework's tools.
- **Execution limits:** Old frameworks may have allowed 10-30 minute cron jobs; Hermes has a ~3-minute hard limit. Shorten prompts or split into chained jobs.
- **Archive sensitivity:** Migration zips contain tokens, OAuth secrets, and personal data. Treat them as credentials, not data. Redact tokens in any output.
- **Stale state:** The archive might not be the newest copy. Check for a live installation directory (e.g., `~/.openclaw`) before assuming the archive is authoritative.
- **Windows file locking:** SQLite files extracted from zips on Windows may lock the temp file. Use `tempfile.TemporaryDirectory()` and keep the connection within the context, or copy to a fresh path before opening.

## References

- `references/openclaw-to-hermes.md` — session-specific detail on migrating from OpenClaw to Hermes, including config mapping and common gotchas.
