# Cron inventory

Review every scheduled job before keeping it. The inventory script is read-only and never prints prompt text.

## Run it

```sh
python3 tools/cron_inventory.py                     # uses $HERMES_HOME, else ~/.hermes (%LOCALAPPDATA%\hermes on Windows)
python3 tools/cron_inventory.py --hermes-home /path/to/hermes > cron-inventory.md
```

It reads `cron/jobs.json` at the root and `profiles/*/cron/jobs.json`, then prints one Markdown row per job. Fill the empty **Decision** column with `keep`, `combine`, `on-demand` or `pause`.

## Decision rules

- **Keep** a job only if a human reads its output at least weekly. Otherwise make it `on-demand` or `pause` it.
- **Combine** overlapping briefings into one job:
  - `daily-briefing` + `Morning Briefing`
  - `AI/Tech Digest` + `research-monitor`
- **Replace** the Daily Journal job with the completion log (`extensions/host-automation/completion_log.py`). It writes one record per finished task and posts to #completed.
- **Output contract**: every job declares exactly one of these:
  - `report`: post the useful result to its report channel.
  - `dependency`: post only when a named dependency needs the owner's action (for example an expired OAuth grant).
  - `silent-unless-changed`: post only when something changed; print nothing (or `[SILENT]`) otherwise.
- **Diagnostics never go to report channels.** Health checks, watchdog output and stack traces go to an ops or diagnostics channel, or stay in local logs.

## After deciding

Apply each change in Hermes yourself, one job at a time. Run the inventory again to confirm the result. This repository never activates or edits scheduled jobs.
