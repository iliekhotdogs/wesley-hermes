# Cron job audit and Discord server cleanup

Use when the user asks to review, cut down, or tidy scheduled jobs and the Discord server that receives their output.

## Audit procedure
1. Jobs live per profile: `hermes -p <profile> cron list` (cron and main both hold jobs). Get ids and enabled state from `profiles/<p>/cron/jobs.json`. `profiles/cron/cron/executions.db` and `reliability_metrics.json` give 7-day failure counts.
2. Pull `last_status` / `last_error` for each job. Cluster by cause (shared failing script, dead provider pin, catch-up after gateway downtime, never-run).
3. Propose cut / keep / merge, with a reason per group, and wait for go-ahead. Default to CUT over repurposing: a repurposed job drags along its old script, channel, and model pin. Merge only jobs doing the same thing at different cadences (e.g. a daily digest plus a 6-hourly monitor -> one daily job).
4. Apply: `hermes -p <profile> cron remove <id>`, `cron edit <id> --schedule "..." / --deliver discord:<channel_id>`. Re-run `cron list` for both profiles to verify.

## Folding a job into another, and model changes
- To fold a script-only sweep into an agent job, extend that job's pre-run `script` (e.g. the audit evidence collector) to subprocess the sweep and add its output under a new JSON key, then append one sentence to the job prompt telling the agent to report it; then remove the standalone job. Run the collector by hand to confirm the new key is populated.
- Choosing "newest" models: read `profiles/<p>/models_dev_cache.json` (providers `openai`, `anthropic`; sort by `release_date`) rather than guessing names. Apply per job with `hermes -p <p> cron edit <id> --model M --provider P`, and set the profile default with `hermes -p <p> config set model.default M`. Script-only (`no_agent`) jobs have no model; skip them.
- Cost preference: jobs that previously ran on a "luna" tier go back to the newest luna tier (cheaper), not the top tier; keep the top tier only where the user asks.

## Pitfalls
- A consolidated maintenance job (`consolidated_maintenance.py`) wraps child scripts (thread cleanup, health, summaries). A child exiting 1 marks the whole job `error`, so fix the child, not the wrapper. Removing a standalone job does not remove its child inside the wrapper.
- Jobs with `Deliver: origin` post to the thread where they were created; thread auto-archive/cleanup will eventually bury them. Point recurring jobs at a fixed channel id.
- Before deleting a Discord channel, grep each profile's `config.yaml`, `.env`, and `cron/jobs.json` for its id (not the whole hermes tree; that times out). `channel_directory.json` is auto-generated and can be ignored. Delete channels idle for weeks that serve a removed job or project; keep voice, ideas, and user-content channels unless told otherwise.
- Deleting a job leaves its dedicated Discord channel behind (channel topics embed the job id); delete or retitle the channels too.

## Discord cleanup
- Check the bot's real permissions first: `GET /guilds/{g}/members/{bot}` plus role permissions (bit 4=Manage Channels `1<<4`, Manage Threads `1<<34`). The `discord`/`discord_admin` tools cannot delete channels or archive threads; use the REST API with a bot token that has the permission.
- The `cron` bot is a limited role; the `main` bot has administrator. A 403 on every PATCH/DELETE means missing permission, not a script bug: grant the minimal bit (Manage Threads) to the role, or perform the one-off action with the main bot's token from `profiles/main/.env`.
- Per-channel overrides can still deny a bot after a role grant; a few channels may need `default_auto_archive_duration` set by the main bot.
- Thread cleanup via API: `GET /guilds/{g}/threads/active`, PATCH `{archived:true}` for threads idle >24h (use `last_message_id` snowflake time, skip the current thread); `GET /channels/{c}/threads/archived/public` paginated by `before=archive_timestamp`, DELETE old ones.
- Verify by running `thread_cleanup.py` by hand with `HERMES_HOME` set to the cron profile: it should print `[SILENT]` and exit 0.
