# Hermes Windows Watchdog Reference

Condensed implementation notes for a Windows watchdog driven by Hermes cron in no-agent mode.

## Script location constraint

Hermes cron resolves relative `--script` values below `<HERMES_HOME>/scripts` and rejects absolute paths or symlinks that resolve outside that directory. Verify the live source/help before planning an external path.

If the user requires the real files in another directory and `<HERMES_HOME>/scripts` does not already exist, a reversible NTFS directory junction can make the Hermes scripts root resolve to the external directory:

```powershell
$HermesScripts = "$env:LOCALAPPDATA\hermes\scripts"
$ExternalScripts = "$env:USERPROFILE\Scripts"
if (Test-Path -LiteralPath $HermesScripts) {
    throw "Refusing to replace existing path: $HermesScripts"
}
New-Item -ItemType Junction -Path $HermesScripts -Target $ExternalScripts
```

Preflight the directory first. Never replace or merge an existing scripts directory blindly. The custom script and state remain physically in the external directory; the private Hermes tree contains only the junction.

## Recurring schedule syntax

Hermes distinguishes a relative one-shot from a recurring interval:

```powershell
# One shot, thirty minutes from now:
hermes cron create "30m" ...

# Recurring forever every thirty minutes:
hermes cron create "every 30m" ...
```

Do not create with `30m` and then merely edit the schedule: the job can retain a finite repeat count inherited from the one-shot. If this happens, remove and recreate it with `every 30m`, then verify the job record has `repeat.times = null` or the CLI displays `Repeat: ∞`.

Canonical creation shape:

```powershell
hermes cron create "every 30m" `
  --name "System Watchdog" `
  --script "watchdog.py" `
  --no-agent `
  --deliver "discord:<channel-id>"
```

## Output and delivery

In no-agent mode, Hermes delivers script stdout verbatim and suppresses delivery when stdout is empty. Therefore:

- Print no startup banners, debug status, or healthy summaries.
- Capture child stdout/stderr when invoking health commands.
- Emit the complete human-readable alert to stdout only when due.
- Do not add a Discord webhook; Hermes is the delivery mechanism.

For a delivery simulation when `--script` cannot receive arguments, use a disposable Python runner in the scripts directory. It may set `HERMES_WATCHDOG_SIMULATE` and a test-state path, then invoke the real script with `runpy.run_path`. Create a temporary no-agent cron job, trigger it, verify execution and delivery, then remove the job, runner, and test state before creating the regular job.

## Gateway recovery must run outside Hermes

Hermes cron is hosted by the gateway process. It is suitable for observing gateway/Discord health while Hermes is alive, but it cannot recover the gateway after the hosting process exits. Do not present an internal `every 5m` Hermes cron job as crash recovery for that same gateway.

For actual self-recovery on Windows:

1. Keep the normal Hermes login/startup entry for reboot and sign-in startup.
2. Create a small external script that calls the supported `hermes gateway status` and runs `hermes gateway start` only when down.
3. Schedule that script with Windows Task Scheduler at a short interval.
4. Use absolute paths to the Hermes executable and a windowless Python host where appropriate; scheduled tasks may have a smaller `PATH` than interactive shells.
5. Keep healthy runs silent. Log only restart attempts, recoveries, and failures.
6. Configure the task to allow battery execution when gateway availability matters on a laptop, and use an `IgnoreNew`/non-overlap policy.
7. Run the task manually, wait for completion, and verify Task Scheduler reports `Last Result: 0` before trusting it.
8. Leave any previous internal recovery cron paused rather than deleting it until the external task has completed successfully, making rollback easy.

The external recovery script should be deterministic and narrowly scoped: status, conditional start, bounded timeout, and no unrelated repairs. Hermes cron can remain responsible for richer alerts, disk/RAM checks, Discord state, and cron-execution health.

## Discord bot auto-restart (Hermes cron no-agent)

This pattern complements the gateway recovery above by providing automatic Discord bot recovery when the bot process crashes but Hermes remains running.

### When to use

- Your Discord bot runs as a Node.js/Next.js process (e.g., poopyclaw)
- The bot may crash due to unhandled errors, memory leaks, or external dependencies
- You want silent-on-success monitoring with transition alerts only
- You prefer Hermes cron recovery over external Task Scheduler when Hermes is already running

### Implementation

1. **Create a watchdog script** in `<HERMES_HOME>/scripts/` that:
   - Checks for the Discord bot process (via `tasklist` or hermes gateway state)
   - Attempts restart via `npm run start` in the bot's directory
   - Logs all checks and restart attempts to a dedicated log file
   - Emits NO output when healthy/unchanged (no-agent mode requirement)

2. **Create a Hermes cron job** with:
   ```
   hermes cron create "every 5m" \
     --name "Discord Bot Auto-Restart" \
     --script "discord_bot_watchdog.py" \
     --no-agent \
     --deliver "discord:<channel-id>"
   ```
   - `every 5m` = recurring interval (not one-shot `30m`)
   - `--no-agent` = script stdout delivered verbatim, silent when healthy
   - `--deliver discord:<channel-id>` = deliver alerts to Discord

3. **Script requirements** (from the implemented `discord_bot_watchdog.py`):
   - No startup banners or healthy summaries
   - Capture child stdout/stderr when invoking health commands
   - Emit complete human-readable alert to stdout only when status changes
   - Do not add a Discord webhook; Hermes is the delivery mechanism
   - Log file at `C:\Users\wesle\AppData\Local\hermes\logs\discord_bot_watchdog.log`

### Transition policy (integrated with system-health-watchdogs)

- `OK → WARNING/CRITICAL`: initial failure alert; set `first_alert_ts`; clear `reminder_sent`
- `WARNING → CRITICAL`: escalation alert; preserve original `first_alert_ts`
- Same unresolved status: no output unless reminder becomes due
- `CRITICAL → WARNING`: update state without de-escalation alert (unless user requests)
- Any non-OK status → `OK`: recovery alert; clear incident metadata
- Reminder: when `now - first_alert_ts` reaches configured delay and `reminder_sent` is false, emit once and set true
- **Do not return early merely because no status changed**: the reminder check must still run

### Verification checklist (Discord-specific)

- [ ] Script passes syntax validation
- [ ] Initial warning/critical output delivered to Discord
- [ ] Identical next run is silent (no output when healthy)
- [ ] Warning-to-critical escalation works
- [ ] Reminder fires just after two hours
- [ ] Later unresolved run remains silent (reminder already sent)
- [ ] Recovery output delivered when bot comes back
- [ ] Healthy next run is silent
- [ ] Dry-run leaves production state absent or byte-identical
- [ ] Monitored runtime-state file remains hash-identical through simulation
- [ ] State contains no numeric measurements
- [ ] Temporary cron delivery test completes and delivery target confirms exact receipt
- [ ] Regular job shows recurring schedule and infinite repeat
- [ ] After enabling production job, trigger it once through Hermes and verify durable execution row
- [ ] If initial alert detected real failure, let it be delivered before running second silence check

### Integration with Hermes cron health

This Discord watchdog integrates with the existing `system-health-watchdogs` framework:
- Shares the same `first_alert_ts`/`reminder_sent` lifecycle model
- Can share an incident group with gateway status (worse of the two statuses determines group severity)
- Script runs in no-agent mode, so Hermes cron handles delivery
- State persisted in Hermes's durable execution DB (`executions.db`)

For the full state design and transition policy, see the base `system-health-watchdogs` skill and its `references/hermes-windows-watchdog.md` reference.

## Gateway health

Use the supported command:

```powershell
hermes gateway status
```

Do not guess an executable name such as `hermes.exe`.

`gateway_state.json` is structured runtime state, but its top-level `updated_at` is not necessarily a periodic idle heartbeat. Hermes explicitly permits a healthy idle gateway to leave it unchanged. Treat its age as diagnostic only unless a future version documents a periodic heartbeat and live testing confirms it.

A useful gateway/Discord check combines:

1. `hermes gateway status` success and a running result.
2. `gateway_state == "running"` as supporting state.
3. `platforms.discord.state` for connection health.
4. `platforms.discord.writer_pid` and `writer_start_time` matching the top-level process identity, so stale data from another gateway process is not trusted.

Suggested Discord classification:

- `connected` with matching writer identity and healthy gateway: `OK`
- `fatal`: `CRITICAL`
- missing, unreadable, disconnected, retrying, unavailable, unrecognized, or wrong writer: `WARNING`

Gateway and Discord can use separate stable status fields while sharing one incident/reminder lifecycle because the delivery path is a single failure domain.

## Cron health from SQLite

Use `<HERMES_HOME>/cron/executions.db` read-only. The verified table contract is:

```sql
CREATE TABLE executions (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  source TEXT NOT NULL,
  process_id TEXT NOT NULL,
  pid INTEGER NOT NULL,
  process_started_at INTEGER,
  status TEXT NOT NULL CHECK(status IN
    ('claimed','running','completed','failed','unknown')),
  claimed_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  error TEXT
);
```

Open with a SQLite URI ending in `?mode=ro`. Do not scrape an assumed log file.

To avoid alerting forever on an old failure:

1. Select terminal rows (`completed`, `failed`) newest first.
2. Keep only the newest terminal row per `job_id`.
3. Count it only when the newest status is `failed` and `finished_at` is parsable and inside the recent window.
4. A newer completed run resolves that job immediately.
5. Ignore unparseable timestamps; never count them as current failures.

Use a recent window longer than the reminder delay, or model unresolved state as above. A two-hour failure window paired with a two-hour reminder can age out just as the reminder becomes due.

## State and reminder logic

Persist stable comparison fields separately from incident metadata. For gateway and Discord, derive the shared group severity as the worse of their two statuses.

Always evaluate reminders even when no status changed. A top-level `if no transitions: return` makes reminders impossible.

Keep `first_alert_ts` anchored to the first failure through escalation. An escalation alert should not reset the two-hour clock. After the reminder, persist `reminder_sent = true`; only recovery clears it.

## Windows resource checks

Disk:

```python
free_bytes = shutil.disk_usage("C:\\").free
```

RAM:

1. Try `psutil.virtual_memory().available`.
2. If importing or calling psutil fails, use Win32 `GlobalMemoryStatusEx` via `ctypes`.
3. Define the structure with `ctypes.c_uint` and `ctypes.c_ulonglong`.
4. Check the API's boolean return value.

## Acceptance checks

Verify all of these with a disposable state file:

- initial warning/critical output
- identical next run is silent
- warning-to-critical escalation
- reminder just after two hours
- later unresolved run remains silent
- recovery output
- healthy next run is silent
- dry-run leaves production state absent or byte-identical
- monitored runtime-state file remains hash-identical through simulation
- state contains no numeric measurements
- temporary cron delivery test completes and the gateway log/readback confirms the exact target
- regular job shows a recurring schedule and infinite repeat

After enabling the production job, trigger it once through Hermes and verify its durable execution row. If it detects a real failure, let that initial alert be delivered before running a second silence check; otherwise a manual pre-schedule run could consume the transition and suppress the user-facing notification.
