# Diagnosing and fixing duplicate Hermes cron schedulers

Hermes can run cron from two places at once: the native Windows gateway (host `profiles/<p>/cron/jobs.json`) and the Docker container (its own copy of the data under `/opt/data/profiles/<p>/cron/jobs.json`, in a Docker volume). The two job lists are independent files, so a job enabled in both fires twice whenever both gateways tick.

## Audit order (read-only first)
1. Which scheduler is actually ticking: `executions.db` (host `profiles/cron/cron/`) `executions` table, `order by claimed_at desc`; the `pid` column shows which process claimed each run (compare with the native `gateway run` PID from `gateway_state.json`). Query the Docker copy via `docker exec hermes python3 ...` the same way.
2. Which Docker gateways are allowed to run: `docker exec hermes sh -c 'for s in /run/service/gateway-*; do [ -e $s/down ] && echo "$s down"; done'`. A `down` file means s6 will not start that service; `s6-svstat` is not installed, so use the `down` file and `ps -eo pid,args`.
3. Compare job lists: `docker exec hermes cat /opt/data/profiles/cron/cron/jobs.json > $TMPDIR/x.json` and diff ids/enabled against the host file. Only profiles with a `cron/jobs.json` in both places can double-fire.
4. Check OS scheduler entries (`schtasks /query`, `Get-ScheduledTask`) for a gateway task that also starts a scheduler, and confirm its target script still exists.

## Fix
- Choose ONE authoritative scheduler based on what is observably running and healthy, not on what the docs say; note any conflict with published docs.
- In the non-authoritative copy, back up `jobs.json`, then set every enabled job `enabled=false`, `state=paused`, `next_run_at=None` (pause, do not delete, so it can be re-enabled). Re-read and count enabled jobs to verify zero.
- Verify the authoritative list has unique ids and names.
- Do not edit the live DB or the engine; do not replay missed runs.

## Pitfalls
- A paused Docker copy is safe even if the gateway is down today; the risk is a later container restart re-enabling duplicate ticking.
- Docker `hermes` container can report unhealthy while its s6 supervision exists; check for an actual gateway python process before assuming Docker is scheduling.
- Publishing a setup repo: merge the open PR only after confirming CI checks passed, then read back the default-branch SHA. The repo is a sanitized snapshot, so later live changes are not in it until re-exported.
