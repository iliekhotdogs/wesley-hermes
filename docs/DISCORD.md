# Discord layout

A suggested server layout. Apply it by hand in Discord; nothing in this repository creates, renames or deletes channels. Update job destinations after you move a channel.

Rules: one purpose per channel, one thread per task, and only actionable output in alert channels. Diagnostics go to an ops thread, never to report channels.

| Category | Channel | Purpose |
| --- | --- | --- |
| Start | #announcements | Read-only. Define its purpose (reminder pings) or archive it. |
| Start | #ask-main | Talk to `main`. One thread per task. |
| Reports | #daily-briefing | One digest per day. |
| Reports | #reminders | Timed reminders only. |
| Reports | #weekly-review | Accomplishments plus weekly metrics (`completion_log.py --metrics`). |
| Reports | #journal | Retire in favor of #completed, or keep for manual notes. |
| Automation | #completed | Completion log: one line per finished Kanban task. |
| Automation | #system-alerts | Actionable failures only. Receives the standalone `gateway_watchdog.py` webhook (`WATCHDOG_WEBHOOK_URL`). |
| Automation | #cron-health | One daily health line. |
| Workspace | #ideas | Ideas and backlog. |
| Workspace | #council | Define a purpose or archive it. |
| Trading | #trading | All trading reports and bot announcements. |
| Trading | #markets | Optional raw market feed. |
| Sandbox (muted) | #channel-test | Bot and webhook tests. |
| Off-topic | #gambling | Unchanged. |

## Old to new

| Old | New |
| --- | --- |
| #markets, #trading-reports | #trading (keep #markets only as an optional feed) |
| #trading-bot-anncoucements (typo) | #trading |
| Daily journal posts | #completed |
| Briefing diagnostics in report channels | #system-alerts or an ops thread |
| Tests in working channels | #channel-test |
