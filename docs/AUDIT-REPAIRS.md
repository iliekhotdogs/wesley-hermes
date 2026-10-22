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
