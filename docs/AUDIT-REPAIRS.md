# Audit repairs

## 1. One authoritative scheduler

Docker is the authoritative runtime. The native Windows cron gateway was
drained and stopped, its two watchdog tasks disabled, and its legacy startup
launcher retired. The startup task could not be disabled by the current Windows
account; its writable VBS now exits without launching a gateway. Its original
launcher and both registries are preserved in private rollback snapshots.

The Docker registry was reconciled against newer native definitions. Completed
run history is retained, paused source jobs stay paused, target-only definitions
are retained, and overdue cutover fires are moved to the next future occurrence
rather than replayed. Nine jobs are enabled. Newer maintenance, completion-log,
weekly evidence, and Canvas context helpers were ported; private routing and
job prompts are intentionally not published here. The current isolated Builder
deployment and image digest pin were preserved.

`tools/reconcile_jobs.py` performs an offline merge only. Its output is private
runtime data, not a shareable bundle. Stop the owning scheduler before replacing
its registry, validate all enabled script/workdir paths, and calculate future
fires with the installed scheduler's timezone and cron implementation.

Rollback requires stopping Docker scheduling before restoring native scheduling;
never start both registries concurrently. Preserve new execution history and
reconcile external effects before any replay.

## 2. Verified private recovery

`extensions/operations/recovery_backup.py` replaces the failed backup producer.
It snapshots SQLite using its backup API (including committed WAL content),
extracts the resulting archive, checks every SHA-256, and integrity-checks each
restored SQLite database. Failures replace stale success status; success expires
after 36 hours. The backup directory now belongs to the runtime account. Only
seven newest recovery archives are retained after a successful new restore test.

`tools/export_recovery.py` creates a separate private host export covering main
data, projects/vault, isolated Builder home/workspaces, isolation code, and a
separate copy of deployment configuration. A limited owner Windows task runs it
daily at 03:15 with StartWhenAvailable. It requires a logged-in owner and Docker
Desktop; this is not an off-machine disaster-recovery service. An independent
off-machine copy remains advisable for host/disk loss. The first export was
extracted and hash-checked: 4,321 files and 37 SQLite databases.

These archives **include credentials and private state** and must remain in
owner-restricted local storage. No backup producer uploads to GitHub. Historical
backups, caches, logs, package caches, and node_modules are excluded; symlinks and
original file modes are recorded in the manifest. Restore symlinks only after
reviewing targets and remapping roots, then restore ownership/modes explicitly.
The verification is an extraction/hash/SQLite restore check, not an automated
gateway startup or a cross-database atomic checkpoint.

## 3. Scheduled inference and portable wrapper paths

Five enabled agent-driven jobs now clear obsolete per-job model/provider pins
through Hermes' native job API and refresh their inference snapshots to the
configured cron profile. The diagnostic successfully used that provider/model
and returned the requested marker without tools or Discord delivery. Existing
failure history is retained; it is not relabeled successful. Full task semantics
and scheduled delivery must still be assessed from their next real executions.

Docker Cron's instructions now point to its actual installed Linux wrapper,
recognize its Tasks support, and allow bounded recovery for missing-file or
unsupported-command errors. The portable template uses a profile-relative path.

## 4. Enforced Discord consent

The optional `extensions/discord-channel-management` plugin now calls Hermes'
trusted human-approval gate inside its handler before channel deletion or a
category change. The approval describes the exact guild, channel, action, and
changed fields, and uses a fresh rule key for every invocation. Repeating a
model-supplied channel ID grants no authority. Errors, denial, missing approval
surfaces, and non-manual approval mode fail closed before Discord HTTP calls.

Main now uses manual approval, denies dangerous unattended/cron/one-shot actions,
and restores destructive slash confirmation. Its guild ID stays in private
environment configuration. Tests mock approval and HTTP for denial, exact-action
approval, unique rule keys, timeout, and policy-off cases. No actual channel was
deleted and no end-to-end human approval interaction was performed.
