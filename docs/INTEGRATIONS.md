# Optional integrations and custom extensions

Nothing under `extensions/` is enabled by `tools/bundle.py install`. No setup command here transfers the owner's grants. Review the code, its dependencies and the current Hermes plugin interface before deploying any extension. Do not expose an assistant with local tools to untrusted Discord users.

## Models and tool backends

Use `hermes -p <profile> model` and `hermes -p <profile> setup` to select an available model and authenticate **your own** account. The observed source uses OpenAI Codex for four of the five shipped profiles and Nous for cowsearcher; separate fallback choices are recorded in the inventory. A `:free` model label does not guarantee present availability, a free subscription or a particular provider's data policy.

Web/browser/image/research tools have separate capabilities, dependencies and authentication requirements. Configure them with the current Hermes setup/tools UI. A skill is guidance and code, not an already-authorized service connection.

## Google Workspace

The installed skill snapshots contain the `productivity/google-workspace` procedure and wrapper. Follow that procedure and the [official Workspace guide](https://hermes-agent.nousresearch.com/docs/user-guide/skills/google-workspace) for your account and requested scopes.

`extensions/scripts/workspace_api.py` is the observed data-only request helper for Calendar, Tasks, Gmail, Drive, Docs, Sheets and People Discovery APIs. It loads the profile's own installed Google skill wrapper, validates a request's service/resource/method fields, preserves earlier successes on batch failure and stops rather than blindly replaying mutations. It does **not** supply credentials or a new OAuth setup flow. Its `--clock` behavior is deployment/timezone-specific, not a universal clock policy.

Port/install the helper only after reviewing the profile's own skill path and account grants. Test a harmless read first. A source copy and syntax check do not certify account access or mutation permissions. Never paste OAuth callbacks or tokens into a public chat or commit them.

## Canvas

The included Canvas skill is optional. Supply your own institution's endpoint/token through its documented setup. No student identity, courses, submissions, grades or assignments are exported. Do not reuse old absolute local paths in reference docs.

## Memory and second brain

One source of truth: the Obsidian vault plus its second-brain index. `MEMORY.md` stays compact (essential cross-session rules only) and never holds completion logs. Main handles routine lookups and writes itself through the `memory` and `second_brain_search` tools; `lib` only curates (deduplicate, reconcile, flag stale entries; deletions are proposed to main) on a schedule or on main's request. The templates enable built-in memory for main and lib and carry **no existing memory records**. `second_brain_search` still needs the optional retrieval plugin.

`extensions/host-automation/completion_log.py` writes one deterministic entry per completed Kanban task (no LLM call) to `<HERMES_HOME>/profiles/lib/completion_log/completions.jsonl`, posts a one-liner to #completed (the first run seeds the log silently; at most 10 lines per run, then "+N more"), and `--metrics` prints weekly per-profile completion, block and takeover counts. A takeover counts against the specialist that needed help.

- `extensions/plugins/second-brain-retrieval/` contains the Hermes plugin entry point.
- `extensions/second-brain/` contains the associated observed Python package source and metadata, so the plugin is not presented as a self-contained two-line implementation.
- The plugin depends on that package, a configured local vault/index and the required dependencies. No private vault, index or embedding dataset is included.

Read the package README and current Hermes plugin instructions, choose your own vault roots, build/test an index of explicitly authorized notes and verify a scoped read-only query. Do not point it at someone else's documents or assume automatic data migration/capture is enabled.

## Runtime permission hook

`extensions/plugins/profile-permissions/` records the custom role-policy hook. The observed deployment loads it for every named profile. Role rules live in `policy.json`; each block is appended to `<home>/state/permission_blocks.jsonl`. Only cron may run the Google helpers; every other role, including builder (also through `cd ... && ...`), is blocked. Specialists are also blocked from delete-like memory actions (delete, clear, reset, remove, forget, purge, prune). The hook can return `MAIN_REQUIRED` for privileged operations even when shell approval prompts are off; approval mode and role policy are separate layers.

**`workspace_api.py` (cron).** Cron may run `scripts/workspace_api.py --request-file/--clock` with a bare `python`, `python3`, `py` or `pythonw` interpreter. The hook rejects request paths containing shell expansion characters. Each request must match the `cron_workspace_routine` allowlist in `policy.json` (service plus `resource.method`; a method name that itself contains a dot is rejected):

- Calendar: `events.list/get/insert/patch/update`, `calendarList.list`, `colors.get`, `settings.get`
- Tasks: `tasklists.list`, `tasks.list/get/insert/patch/update`
- Gmail (read-only): `users.messages.list/get`, `users.threads.list/get`, `users.labels.list`
- Drive: `files.list/get/create/update`
- Docs: `documents.get/create/batchUpdate`; `batchUpdate` is limited to an allowlist of insert/style request types, with no delete or replace requests
- Sheets: `spreadsheets.get/create`, `values.get/batchGet/update/append`
- People (read-only): `people.connections.list`, `people.get`

A request carrying any of these keys anywhere in its params or body is rejected: `trashed`, `deleted`, `addParents`, `removeParents`, `parents`, `conferenceData`, `attendees`, `media_body`/`media_mime_type`/`media` (no local-file uploads), Drive sharing-setting fields, or a `sendUpdates`/`sendNotifications` value other than `none`. `workspace_api.py` enforces the same policy itself before any API call, so a request file changed between the hook check and the run is still checked. It fails closed if `policy.json` cannot be found; `HERMES_PERMISSION_POLICY` overrides the path.

**`google_api.py` (older route).** Argparse abbreviations are disabled. The hook blocks `--att*` flags, `--output` into the Hermes install or to code/config suffixes, and uploads of secret-named or install-dir files. `drive download` must name an absolute `--output` path. Arguments may not contain shell-expansion characters (`$`, `%`, backtick; unquoted also `* ? [ ] { } ~`), so text like "50%" cannot go in a quoted `google_api.py` argument; use `workspace_api.py` for that.

Sending, deleting, trashing, moving, clearing, invites, webhooks, and sharing actions and sharing settings are therefore unavailable to cron and return to main. Files cron creates land in My Drive root. Accepted residual risks: cron has full Gmail and Drive read access; it can blank Sheets values or rewrite Docs text (recoverable from revision history); and it can create events on any calendar it can write to.

**Builder.** Builder's block on Google helpers and the Hermes home is lexical and best-effort. Builder can run arbitrary Python it writes, so this is not a sandbox. Real isolation needs a separate OS user or container.

This is source reference, **not an OS sandbox**, and it is not enabled in the installable templates. Its trusted script paths/hashes and role assumptions must be reconciled with a new installation before use. Do not disable the whole hook to bypass a denial or assume copying it recreates an administrative authority grant.

## Briefing curation

`extensions/plugins/briefing-curation/` includes the source for the current single-gateway briefing/feedback bridge and its modules. The owner's per-channel preference stores, listener state, story records and delivery/interaction ledgers were excluded. Configure your own destinations and sources, review the Discord hook interface, and test in a private channel before enabling it.

## Host automation

`extensions/host-automation/` is sanitized source reference for the observed gateway watchdog (one `gateway_watchdog.py` replaces the old doctor, supervisor and Discord bot watchdogs), backup, board alert/recovery, completion log, health-check, thread cleanup and second-brain maintenance helpers. `thread_cleanup.py` archives old threads; it deletes only when `THREAD_DELETE_AFTER_DAYS` is set, counted from archive time. Board recovery keeps one open recovery card per source and creates a new one only after the previous card is done. Review scheduled jobs with the [cron inventory](CRON-INVENTORY.md); see [Discord layout](DISCORD.md) for where each output belongs. These scripts are **not installed, scheduled, launched or integration-tested by the bundle**. They may depend on local helper modules, filesystem layout, native tasks, exact runtime revisions or other assets outside this export. `YOUR_USER` paths are explicit porting placeholders, not ready-to-run settings.

### Gateway watchdog must run outside Hermes

A watchdog scheduled as a Hermes cron job stops when the gateway stops, so it cannot report a dead gateway. Run `gateway_watchdog.py --standalone` from the OS scheduler instead. In this mode it posts health changes to the Discord webhook in `WATCHDOG_WEBHOOK_URL` (point it at #system-alerts). It never restarts anything; restarts belong to the OS service manager. A failed post exits non-zero and the next run retries.

Windows Task Scheduler, every 5 minutes:

```powershell
schtasks /Create /SC MINUTE /MO 5 /TN "Hermes gateway watchdog" /TR "python C:\Users\YOUR_USER\AppData\Local\hermes\scripts\gateway_watchdog.py --standalone"
```

Set `WATCHDOG_WEBHOOK_URL` (and `HERMES_HOME`/`HERMES_EXE` if not default) as user environment variables first, for example with `setx`.

macOS (launchd) or Linux (cron), every 5 minutes. On Linux add this line with `crontab -e`; on macOS use a launchd agent with `StartInterval` 300 running the same command:

```sh
*/5 * * * * HERMES_HOME=$HOME/.hermes WATCHDOG_WEBHOOK_URL=https://discord.com/api/webhooks/... python3 /path/to/gateway_watchdog.py --standalone
```

The old `discord_bot_watchdog.py` also restarted a separate Next.js app ("poopyclaw"). The merged watchdog drops that. If you still need it, run that app under its own OS service (Task Scheduler, launchd or systemd) with its own restart policy.

### Environment variables

| Name | Used by | Default | Purpose |
| --- | --- | --- | --- |
| `HERMES_HOME` | all host-automation scripts | `~/AppData/Local/hermes` in most scripts (some use the script's parent folder); set it explicitly on macOS/Linux | Hermes data root. |
| `HERMES_EXE` | `gateway_watchdog.py` | `hermes` on `PATH` | Path to the Hermes executable. |
| `WATCHDOG_WEBHOOK_URL` | `gateway_watchdog.py --standalone` | none | Discord webhook that receives health changes. |
| `RAM_ALERT_PERCENT` | `gateway_watchdog.py` | `90` | RAM usage percent that counts as high. |
| `RAM_ALERT_HOLD_MINUTES` | `gateway_watchdog.py` | `10` | Minutes RAM must stay high before an alert. |
| `CRON_HEALTH_IGNORE_IDS` | `cron_health_check.py` | empty | Comma-separated job ids to skip. The live machine hard-coded job `85d20664dc76`; set this to keep ignoring it. |
| `COMPLETION_LOG_PATH` | `completion_log.py` | `<HERMES_HOME>/profiles/lib/completion_log/completions.jsonl` | Where completion entries are written. |
| `DISCORD_GUILD_ID` | `thread_cleanup.py` | none (required) | Discord server whose threads are cleaned up. |
| `THREAD_DELETE_AFTER_DAYS` | `thread_cleanup.py` | unset (never delete) | Delete threads this many days after they were archived. |
| `DISCORD_BOT_TOKEN` | `thread_cleanup.py`, `plugins/briefing-curation/discord_curation_service.py` | none (required) | Discord bot token. Never print or commit it. |
| `GATEWAY_PROFILE` | `gateway_watchdog.py` | `main` | Profile passed to `hermes -p <profile> gateway status`. |
| `KANBAN_BLOCK_ALERT_STATE` | `kanban_block_alert.py` | `<HERMES_HOME>/kanban_block_alert_state.json` | State file for blocked-card alerts. |
| `OBSIDIAN_VAULT_PATH` | `obsidian_briefing_archiver.py`, `obsidian_second_brain_health.py`, `second_brain_index_refresh.py`, `second-brain` package | `/opt/data/vault` (Windows: `C:\Users\YOUR_USER\OneDrive\Desktop\thesleyfiles`); required by the `second-brain` package (or pass `--vault`) | Obsidian vault root. |
| `SECOND_BRAIN_PROJECT` | `obsidian_second_brain_health.py`, `second_brain_index_refresh.py` | `/projects/second-brain` (Windows: `C:\Users\YOUR_USER\hermes-projects\second-brain`) | Second-brain project folder. |
| `HERMES_PERMISSION_POLICY` | `scripts/workspace_api.py` | unset (uses the profile-permissions `policy.json`; fails closed if not found) | Path to the permission `policy.json`. |

Use the official [native Windows service guide](https://hermes-agent.nousresearch.com/docs/user-guide/windows-native) or your platform's documented service mechanism for a fresh system. Import no old supervisor XML, private backup archive or live process ledger. Personal contact, finance and journal reminder scripts are intentionally not exported.

## Automation examples

`examples/automation.json` is an inert checklist, not `cron/jobs.json`. Use the current Hermes scheduler UI/CLI or your assistant to create a **new explicitly requested** job with your own timezone, scope and destination. Each template names an `output_contract` (`report`, `dependency` or `silent-unless-changed`); send diagnostics to an ops thread, not report channels. Confirm the stored schedule and a test delivery before depending on it. No existing job is started by installing this repository.
