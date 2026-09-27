---
name: daily-journal-synthesis
description: "Use when summarizing daily activity from multiple sources."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [daily-journal, synthesis, cron, session-history, obsidian, project-audit]
    related_skills: [personal-command-center, obsidian, hermes-agent, weekly-review-planning]
---

# Daily Journal Synthesis

Generate a concise, evidence-based daily journal from all meaningful activity—not merely from cron output or notes that happen to exist. This skill is for scheduled daily summaries, retrospective corrections, and diagnosing omissions in an existing journal pipeline.

## Core principle

A successful cron run is not evidence that the journal is complete. User work can live in session history, project files, test output, external-action receipts, Kanban records, and notes. Treat the journal as a reconciliation task across sources.

## Required source lanes

Inspect every applicable lane for the target period:

1. **Conversation/session activity** — completed work, decisions, research, discussions, file edits, external actions, and unresolved items.
2. **Scheduled-run artifacts** — cron output files and status, separating routine automation from user-facing work.
3. **Active projects** — files modified in the period, implementation notes, test reports, and verified build results. A project’s filesystem evidence can recover work missed by session-history tooling.
4. **Knowledge store** — the actual active Obsidian vault, not an assumed or stale path. Include new or modified notes when present.
5. **Domain journals** — all configured investing, decision, or idea journals; report “none” only after checking each one.
6. **Durable work queues** — Kanban/task records when they explain completed, blocked, resumed, or abandoned work.

See `references/source-reconciliation.md` for the source matrix, Windows path checks, and omission-recovery recipe.

## Period handling

- Define the exact period in the heading, normally from the previous 2:00 AM run through the current 2:00 AM run.
- Use timestamps from source records rather than file names alone.
- If a source cannot be queried, do not convert that limitation into “no activity.” Use available artifact evidence and disclose the limitation if it materially affects completeness.
- Prefer the user’s calendar day in their configured timezone when labeling the entry.

## Evidence standards

For each claimed completion, retain at least one concrete anchor: a verified test result, file/project path, task ID, external receipt, or source message. Distinguish:

- **Completed** — evidence confirms the work finished.
- **In progress** — work started but completion was not verified.
- **Blocked/abandoned** — source explicitly records the blocker or decision to stop.
- **Planned** — do not present as completed.

Never let routine cron volume bury substantive work. A day with many watchdog runs may still have important implementation work.

## Recommended output

Keep the final delivery within the platform’s message limit; for Discord, target under 1,500 characters:

```text
📓 **Daily Journal — [period]**
📋 **Completed**
- [concrete user/project work]
📈 **Domain journals**
- [new entries, or verified no-change result]
🤖 **Automation**
- [important runs, failures, recoveries]
🧠 **Decisions / notes**
- [durable decisions and unresolved items]
```

Include project work before routine automation. Do not claim “quiet day,” “no direct user sessions,” or “no work” unless the complete source checklist was actually executed.

## Scheduled-job design

When improving a journal cron job:

1. Preserve its schedule and delivery target unless explicitly changing them.
2. Replace vague source instructions with concrete, current paths and project directories.
3. Add a fallback artifact scan using modification times and verified files when session search is unavailable to the cron runtime.
4. Explicitly instruct the worker not to infer inactivity from missing session results.
5. Keep the response cap realistic for the delivery platform.
6. Read the job back after updating it and verify its enabled state, next run, and delivery target.

## Retrospective correction

When a summary omitted real work:

1. Identify the missing activity from the strongest available evidence.
2. Explain the omission plainly, without blaming the user.
3. Produce the corrected activity list.
4. Fix the pipeline so the omission class is less likely to recur.
5. Verify the changed job configuration before reporting success.

Do not silently rewrite historical reports unless explicitly asked; a corrected retrospective in the current response is safer and preserves the original audit trail.

## Pitfalls

- Using only cron outputs, which can report successful automation while missing interactive sessions.
- Hardcoding an outdated Obsidian vault path after the active vault moved.
- Treating “no direct user sessions” as a valid result when session search was unavailable or not actually run.
- Reporting a project as planned when tests or implementation evidence show it was completed.
- Counting watchdog repetitions as the main accomplishment of the day.
- Claiming both journals are unchanged without reading both files.
- Using a stale date heading because the run date and covered period differ.
- Updating a recurring job without reading back its resulting configuration.
