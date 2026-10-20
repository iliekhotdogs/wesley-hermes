---
name: system-health-watchdogs
description: "Use when building scheduled system health watchdogs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [watchdog, monitoring, health-checks, cron, alerting, deduplication, windows]
---

# System Health Watchdogs

Build lightweight scheduled watchdogs that are silent when healthy, emit actionable transition alerts, and can be tested without damaging the system being monitored.

## When to Use

Use this skill for host or service health monitors, recurring configuration-drift audits, cron-driven watchdogs, silent-on-success automation, transition-based alerting, reminder/recovery logic, and safe fault simulation. It applies whether the scheduler is Hermes, a CI system, cron, or another script runner. For Hermes on Windows, also load the linked Hermes-specific reference. For recurring Hermes configuration audits, load `references/hermes-config-audits.md`.

## Core contract

A watchdog run should:

1. Measure current health without mutating monitored resources.
2. Convert measurements into a small set of stable statuses such as `OK`, `WARNING`, and `CRITICAL`.
3. Compare only those stable statuses with the previous run.
4. Emit output only for an allowed transition, a single timed reminder, or recovery.
5. Persist the new stable status and per-incident reminder metadata atomically.
6. Exit silently when healthy and unchanged.

Never use timestamps, free-space values, RAM values, counters, PIDs, or error text as deduplication keys. Include them in alert text, but do not compare them across runs.

## State design

Keep comparison status separate from alert lifecycle metadata:

```json
{
  "statuses": {
    "disk_status": "OK",
    "ram_status": "OK",
    "service_status": "OK"
  },
  "alerts": {
    "disk": {"first_alert_ts": null, "reminder_sent": false},
    "ram": {"first_alert_ts": null, "reminder_sent": false},
    "service": {"first_alert_ts": null, "reminder_sent": false}
  }
}
```

The `statuses` object is the only comparison input. The `alerts` object controls timing and is not part of deduplication.

Use one alert lifecycle per operational incident group. Several low-level statuses may belong to one group when they share a failure domain—for example, a gateway process and its messaging connection.

## Transition policy

For each incident group:

- `OK → WARNING` or `OK → CRITICAL`: initial failure alert; set `first_alert_ts`; clear `reminder_sent`.
- `WARNING → CRITICAL`: escalation alert; preserve the original `first_alert_ts`.
- Same unresolved status: no output unless the reminder becomes due.
- `CRITICAL → WARNING`: update state without a de-escalation alert unless the user explicitly requests one.
- Any non-OK status → `OK`: recovery alert; clear incident metadata.
- Reminder: when `now - first_alert_ts` reaches the configured delay and `reminder_sent` is false, emit once and set it true.

Do not return early merely because no status changed: the reminder check must still run.

## Safe simulation

Every watchdog should support deterministic simulation through command-line arguments and, where scheduled runners cannot pass arguments, an environment variable or disposable runner script.

Safety requirements:

- Simulation must never modify the monitored resource.
- `--dry-run` must never write production state.
- A non-dry simulation should reject the production state path unless the caller explicitly supplies a test-state path.
- Support an injectable clock for testing reminders without waiting in real time.
- Hash or otherwise verify sensitive monitored files before and after destructive-looking simulations.
- Test initial failure, unchanged silence, escalation, one reminder, no repeated reminder, recovery, and healthy silence.

## Health-check selection

Prefer authoritative supported checks over guesses:

1. Supported service health/status command or API.
2. Verified PID identity or service manager state.
3. Structured runtime connection state owned by the current process.
4. File freshness only when the file is documented and verified to advance periodically while idle.

Never assume a process executable name. Never treat a state-file modification time as a heartbeat until both implementation and live behavior confirm periodic updates.

## Scheduled delivery pattern

For script-only scheduled checks:

- Use a scheduler's no-agent/script-only mode when available.
- Let the script print the complete alert; let the scheduler deliver stdout.
- Empty stdout must mean no delivery.
- Capture stderr inside subprocess checks so healthy runs cannot leak status chatter into the delivery channel.
- Verify delivery through a disposable simulated job before enabling the regular schedule.
- Verify both the durable execution record and the delivery log/readback target.

## Scheduler failure domains

A watchdog cannot recover the scheduler process that must execute it. Before choosing a scheduler, identify what happens when the monitored service dies:

- Use an in-process scheduler such as Hermes cron for health observation, alerts, and checks that may stop when Hermes stops.
- Use an independent OS scheduler or service manager for automatic recovery of the Hermes gateway itself. An internal Hermes cron job cannot restart a gateway after the gateway—and therefore its scheduler—has exited.
- Keep startup-at-login and crash recovery separate: a login startup entry handles reboot/login, while an external repeating task handles later crashes.
- Pause or remove redundant LLM-driven self-watchdogs after the external recovery path is verified; otherwise they waste inference and create misleading confidence.

For the Windows implementation and verification pattern, see `references/hermes-windows-watchdog.md`.

## Windows practices

- Use `shutil.disk_usage()` rather than `os.statvfs()`.
- Prefer `psutil.virtual_memory().available`; use `GlobalMemoryStatusEx` via `ctypes` as a dependency-free fallback.
- Use `ctypes.c_uint`, not malformed type spellings.
- Provide PowerShell-compatible creation, test, and rollback commands.
- Store custom scripts and custom state in the user-selected directory, not inside an application's private state tree unless the application requires it and the user approves.
- Use atomic adjacent temporary-file replacement for state writes.

## Verification checklist

- [ ] Script passes syntax validation.
- [ ] Dependencies and dependency-free fallbacks are both understood.
- [ ] State contains only stable statuses plus separate incident metadata.
- [ ] Measurements do not affect deduplication.
- [ ] Unchanged healthy and unchanged failed runs are silent.
- [ ] Reminder fires once after the requested delay.
- [ ] Recovery clears reminder metadata.
- [ ] Simulation cannot alter production state or monitored resources.
- [ ] Scheduler is truly recurring, not a relative one-shot.
- [ ] Delivery is verified at the exact destination.
- [ ] Temporary test jobs and artifacts are removed.
- [ ] Rollback commands use the actual discovered job identifier.

## Hermes-specific references

- For Hermes no-agent cron, Windows script-path constraints, gateway/Discord state, and `executions.db` handling, read `references/hermes-windows-watchdog.md` before implementation.
- For read-only recurring Hermes configuration health and drift reviews, read `references/hermes-config-audits.md`.
- For restart persistence, Discord reconnection, missed-message recovery, and automatic continuation of interrupted gateway turns, read `references/hermes-gateway-restart-continuity.md`.

## Hermes Gateway Watchdog and Recovery

### Overview

Gateway resilience uses two separate mechanisms. Keep them separate.

1. **Restarts belong to the OS service manager.** Use `hermes gateway install --start-on-login`, a Windows startup item, Task Scheduler, launchd or systemd with a restart policy. `gateway_watchdog.py` never restarts the gateway.

2. **Health alerts come from `gateway_watchdog.py --standalone`, run by the OS scheduler every 5 minutes.** It checks `hermes gateway status`, gateway/Discord state, disk and RAM, and posts health changes (not every run) to the Discord webhook in env `WATCHDOG_WEBHOOK_URL` (for example #system-alerts). Because it runs outside Hermes, it can still report a dead gateway.

3. **Optional in-Hermes copy.** A Hermes cron job may also run `gateway_watchdog.py` (without `--standalone`) for alerts through Hermes delivery. It stops when the gateway stops, so it never replaces the OS-scheduled run. Each mode keeps its own state file (`state/gateway_watchdog_state.json` vs `state/gateway_watchdog_standalone_state.json`), so they do not suppress each other's alerts.

### Setup

Copy `extensions/host-automation/gateway_watchdog.py` to `<HERMES_HOME>/scripts/` and set `WATCHDOG_WEBHOOK_URL`. Then schedule it every 5 minutes:

```powershell
schtasks /Create /SC MINUTE /MO 5 /TN "Hermes gateway watchdog" /TR "python C:\Users\YOUR_USER\AppData\Local\hermes\scripts\gateway_watchdog.py --standalone"
```

```bash
# Linux crontab; on macOS use a launchd agent with StartInterval 300
*/5 * * * * WATCHDOG_WEBHOOK_URL=https://discord.com/api/webhooks/... python3 /path/to/gateway_watchdog.py --standalone
```

Full details, including env vars and verification, are in `references/hermes-windows-watchdog.md`.

### Verification

```bash
# Run once by hand; a healthy unchanged run posts nothing
python <path>/gateway_watchdog.py --standalone

# Confirm the OS task exists (Windows)
schtasks /Query /TN "Hermes gateway watchdog"
```

Look up any Hermes cron job ids with `hermes cron list`; never hard-code them.

### Related patterns

- **Discord Bot Watchdog**, gateway doctor and supervisor watchdogs: retired; their checks are merged into `gateway_watchdog.py`. Run one watchdog, not several.
- Any older Hermes cron job that tried to restart the gateway with `hermes gateway run`: pause or remove it once the OS service manager and the standalone watchdog are verified.
