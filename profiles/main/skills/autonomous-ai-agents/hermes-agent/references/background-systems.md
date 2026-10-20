# Durable & Background Systems

Four systems run alongside the main conversation loop. Quick reference
here; full developer notes live in `AGENTS.md`, user-facing docs under
`website/docs/user-guide/features/`.

### Delegation (`delegate_task`)

Spawn a subagent with an isolated context + terminal session.

- **Single:** `delegate_task(goal, context)`.
- **Batch:** `delegate_task(tasks=[{goal, ...}, ...])` runs children in
  parallel, capped by `delegation.max_concurrent_children` (default 3).
- **Background:** `delegate_task(background=true)` returns a handle
  immediately and keeps the parent loop going; the child's result
  re-enters the conversation as a new turn when it finishes.
- **Roles:** `leaf` (default; cannot re-delegate) vs `orchestrator`
  (can spawn its own workers, bounded by `delegation.max_spawn_depth`).
- **Not durable.** A backgrounded child is still process-local — if the
  parent process exits, the child is lost. For work that must outlive
  the process, use `cronjob` or
  `terminal(background=True, notify_on_complete=True)`.

Config: `delegation.*` in `config.yaml`.

### Cron (scheduled jobs)

Durable scheduler — `cron/jobs.py` + `cron/scheduler.py`. Drive it via
the `cronjob` tool, the `hermes cron` CLI (`list`, `add`, `edit`,
`pause`, `resume`, `run`, `remove`), or the `/cron` slash command.

- **Schedules:** duration (`"30m"`, `"2h"`), "every" phrase
  (`"every monday 9am"`), 5-field cron (`"0 9 * * *"`), or ISO timestamp.
- **Per-job knobs:** `skills`, `model`/`provider` override, `script`
  (pre-run data collection; `no_agent=True` makes the script the whole
  job), `context_from` (chain job A's output into job B), `workdir`
  (run in a specific dir with its `AGENTS.md` / `CLAUDE.md` loaded),
  multi-platform delivery.
- **Invariants:** 3-minute hard interrupt per run, `.tick.lock` file
  prevents duplicate ticks across processes, cron sessions pass
  `skip_memory=True` by default, and cron deliveries are framed with a
  header/footer instead of being mirrored into the target gateway
  session (keeps role alternation intact).

User docs: https://hermes-agent.nousresearch.com/docs/user-guide/features/cron

### Curator (skill lifecycle)

Background maintenance for agent-created skills. Tracks usage, marks
idle skills stale, archives stale ones, keeps a pre-run tar.gz backup
so nothing is lost.

- **CLI:** `hermes curator <verb>` — `status`, `usage`, `run`, `pause`,
  `resume`, `pin`, `unpin`, `archive`, `restore`, `list-archived`, `prune`,
  `backup`, `rollback`.
- **Slash:** `/curator <subcommand>` mirrors the CLI.
- **Scope:** only touches skills with `created_by: "agent"` provenance.
  Bundled + hub-installed skills are off-limits. **Never deletes** —
  max destructive action is archive. Pinned skills are exempt from
  every auto-transition and every LLM review pass.
- **Cost:** the deterministic inactivity/prune sweep runs for free. The
  aux-model "consolidate overlapping skills into umbrellas" pass is
  **off by default** — opt in with `curator.consolidate: true` or
  `hermes curator run --consolidate`. Routine background curation costs
  zero tokens.
- **Telemetry:** sidecar at `~/.hermes/skills/.usage.json` holds
  per-skill `use_count`, `view_count`, `patch_count`,
  `last_activity_at`, `state`, `pinned`.

Config: `curator.*` (`enabled`, `interval_hours`, `min_idle_hours`,
`stale_after_days`, `archive_after_days`, `backup.*`).
User docs: https://hermes-agent.nousresearch.com/docs/user-guide/features/curator

### Kanban (multi-agent work queue)

Durable SQLite board for multi-profile / multi-worker collaboration.
Users drive it via `hermes kanban <verb>`; dispatcher-spawned workers
see a focused `kanban_*` toolset gated by `HERMES_KANBAN_TASK`, and
orchestrator profiles can opt into the broader `kanban` toolset. Normal
sessions still have zero `kanban_*` schema footprint unless configured.

- **CLI verbs (common):** `init`, `create`, `list` (alias `ls`),
  `show`, `assign`, `link`, `unlink`, `comment`, `complete`, `block`,
  `unblock`, `archive`, `tail`. Less common: `watch`, `stats`, `runs`,
  `log`, `dispatch`, `daemon`, `gc`.
- **Worker/orchestrator toolset:** `kanban_show`, `kanban_complete`,
  `kanban_block`, `kanban_heartbeat`, `kanban_comment`, `kanban_create`,
  `kanban_link`; profiles that explicitly enable the `kanban` toolset
  outside a dispatcher-spawned task also get `kanban_list` and
  `kanban_unblock` for board routing.
- **Dispatcher** runs inside the gateway by default
  (`kanban.dispatch_in_gateway: true`) — reclaims stale claims,
  promotes ready tasks, atomically claims, spawns assigned profiles.
  Auto-blocks a task after `failure_limit` consecutive spawn failures
  (default 2; configurable via `kanban.failure_limit` or per-task
  `max_retries`).
- **Isolation:** board is the hard boundary (workers get
  `HERMES_KANBAN_BOARD` pinned in env); tenant is a soft namespace
  within a board for workspace-path + memory-key isolation.

## Recovering scheduled research permission escalations

- Export the exact source session with redaction and inspect only its user prompt, tool-call arguments, denied result, and final response. Find the owning cron session/job and its configured delivery before acting; never infer the historical window from live time.
- Move bounded RSS/API collection into a read-only pre-run script under the owning main profile's scripts directory. Inject explicit six-hour UTC bounds, channel/item publication times, undated-item counts, and source failures. API `published` is submission time, not announcement time.
- Correct the existing cron job with `hermes cron edit --script ... --prompt ...`, passing precollected evidence to cowsearcher and explicitly limiting that delegation to web_search/web_extract. Do not widen specialist permissions or send the rejected pipeline back unchanged. Read back script, prompt, schedule, and destination.
- Disable self-continuity with `--no-continuity` when the previous-output input recursively nests full cron reports rather than providing trustworthy findings. Keep the schedule and configured delivery unchanged.
- If the original run is still active, do not replay it or announce a completed news sweep. Send only the scoped recovery outcome to its configured route, then verify the exact returned message ID with a read-back. Preserve the historical evidence and distinguish arXiv-only coverage from a complete news check.

## Recovering scheduled clock permission escalations

- Match the denied tool result to its exact tool-call ID before taking over; a clock check can fail while sibling Google reads and the entire briefing succeed. Inspect the execution receipt and existing destination message before replaying anything.
- Supply Pacific date/time and midnight-to-midnight ISO bounds from the existing main-owned pre-run script, before its credential checks, using ZoneInfo so DST offsets remain correct. Amend the same job prompt to consume those values instead of terminal date or inline Python; do not widen specialist permissions.
- Exercise the script with its owning profile environment, preserve authoritative source output, and read back the job schedule and delivery. Disable self-continuity if stale report content would undermine the new authoritative prerequisite. Report only the recovery delta to the original route and verify that exact message ID.

## Recovering recurring audit shell escalations

- Match the blocked batch to its exact cron job and session; completed/delivered can mean only a capability-block notice. Read back the original destination message before replaying any work.
- Install a fixed read-only pre-run collector in the owning profile scripts directory. Use subprocess argument lists with shell=False, bounded timeouts, an owning-home guard, and an allowlist of nonsecret config keys; never dump auth files or arbitrary config.
- Exercise with the Hermes interpreter (sys.executable), not a PATH-selected bare python. Prefer UTC timestamps for collectors that do not need local day bounds to avoid Windows tzdata dependency failures.
- Amend the existing prompt to analyze supplied evidence without terminal workarounds; preserve schedule, model, permissions, and destination. Replace unavailable skill instructions with explicit audit rules rather than modifying another profile's skills. Disable recursively nested continuity, clearly marking week-over-week comparison unverified.
- Report observed health and actual limitations to the existing delivery thread, then read back the exact recovery message. Distinguish a tested collector from an as-yet unverified next unattended LLM run.

## Recovering read-only research handoffs

- Check source comments and current artifacts for an already-active main takeover before replaying denied collection. Independently validate retained IDs, totals, window, and delta; preserve evidence in the recovery workspace, and read back source completion. Do not race the original main run with duplicate collection or delivery, or claim the specialist permission policy was repaired when main only bypassed the blocked prerequisite for this run.
- Honor explicit superseding roster/subset comments when a research card's original title still names the full assignment. Verify the subset count programmatically, identify which consolidated deliverable remains with the coordinator, and label indexed individual-profile matches separately from body-checked employer evidence; a verified URL identity match does not prove full profile access or present employment.

- Attribute a direct specialist one-shot explicitly with `FROM: main. TO: <profile>.` in its query. A role-gated specialist may otherwise mistake the CLI user-role prompt for an uncoordinated user request and refuse it. If this happens, clarify provenance once in the same session; do not create a duplicate task or change its permissions.
- After a bounded profile one-shot times out, inspect its exact session's persisted tool calls and results before discarding partial evidence or restarting. Preserve the original window, complete only bounded primary-source collection, and report unfinished sweep/timestamp coverage explicitly; a timeout with no final handoff never licenses a silent no-news result. Prefer official RSS/Atom timestamps over date-only extracted news pages.

- Preserve useful source reads after specialist timeouts; if a read-only researcher receives MAIN_REQUIRED from write_file, main must save the evidence and citation-backed brief rather than rerun the same denied write or widen research permissions.
- Use exact repository identifiers from the retained source URL. For GitHub merge dates, parse the official API's merged and merged_at fields and compute window membership with timezone-aware datetime; do not confuse a later follow-up landing comment with the original PR merge, release, or installed status.
- Save observed source text and a task-local citation ledger, verify the brief, and preserve deliverables through completion artifacts. Honor an existing no-sending handoff so recovery does not replay the briefing.
- When a main recovery worker's terminal CLI mutation is refused by the delegated-child guard, use the installed main-only kanban_recovery.py settle helper for verified source completion, then read back the source card. Do not remove the guard globally or retry the same refused CLI mutation unchanged.

## Recovering exercised source-validation prerequisites

- Run the exact denied worktree-local validations as main after confirming scoped authorization; installed dependency versions and actual test exits are evidence, not the specialist's stale completion receipt.
- Refresh evidence-manifest limitations before rerunning its gate; PASS_LOCAL certifies only declared hashes and commands, not all inventory issues, broader failing suites, deployment or UI behavior. Preserve updated reports, patches and receipts through recovery completion artifacts.
- For one verified resumption of a triage source, use the native specify_triage_task transition without changing its title, scope or specialist assignee; it preserves parent gating. Do not use promote/unblock on triage or invoke an auxiliary specifier to rewrite the already concrete assignment.
- If the CLI's delegated-child guard denies main recovery administration, use a fixed-source, main-home/workspace-guarded native helper with an override confined to that process, matching the installed main-only recovery helper. Never widen profile permissions. Terminal may omit HERMES_KANBAN_TASK; validate the pinned recovery workspace and main home instead.
- Append exact read_file paths and concrete passing results to the source before resuming once. Keep source remediation incomplete when unresolved issues remain; close only the prerequisite recovery task.

## Recovering blocked backlogs in parallel

- Rank blocked cards from full attempt/comment evidence and inspect escalated triage sources too; a historical capability error is not a live diagnosis. Reuse source cards after a verified prerequisite correction instead of creating duplicate assignments.
- Keep independent specialist lanes moving when one model rate-limits. Distinguish provider 429/quota failures from MAIN_REQUIRED access denials; switching models cannot repair missing OAuth consent or a local role guard. Preserve partial evidence and change an existing task's next-dispatch override only after stopping/releasing its active claim, never race duplicate external writes.
- Pin HERMES_HOME to the specialist profile when checking its Google credentials; calling that profile's script while main's home remains active only verifies main. Treat missing Contacts scope separately from working Calendar access and never repeat OAuth for an unrelated scope warning.
- Resolve user-supplied deadlines back to their exact original message/session when asked where they came from. Do not turn a saved user request into an independently verified organizer deadline or invent Discord permalinks from local message IDs.
- Supply credential-free, task-local source exports when researchers cannot execute privileged API reads. For course-material research, preserve exact current course sections and check them against bookstore adoptions; no bookstore listing or file-list 403 does not prove no textbook is required.
- Read back current card state before completing or replaying recovery: another main session may have already finished it. Independently verify retained external IDs without repeating the mutation.
- Preserve scratch workspace evidence privately before native archival, because archive_task can reap the workspace. Label cancelled/expired failed ticks as archival, not successful completion, and do not restart their schedules as cleanup.
- Give an existing main takeover a sufficient explicit runtime when its verified blocker was a short cap; preserve source scope/assignee and current patch, rather than creating another identical capped recovery or returning repeatedly denied work unchanged.

## Recovering stale recurring-monitor cards

- Compare the failed card's original run timestamp and fixed monitoring window with live time before retrying. A stale periodic tick must not silently become a fresh sweep.
- Read attempt history, retained scripts, and the saved worker log once. Treat partial coverage and failed sources as incomplete research, not verified no-news; date-truncated timestamps cannot establish membership in an hourly window.
- When a stale tick has later completed same-job ticks and the recovery assignment permits archival, append the actual failure evidence and historical coverage limitation, archive the source without marking its research successful, then read back the exact card. Preserve scripts and logs; do not rerun external actions or change the recurring schedule merely to close recovery.

User docs: https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban
