# Main — recovery and escalation detail

Load on `MAIN_REQUIRED`, a capability block, a failed specialist, a repeated block loop, or a Kanban recovery-worker wake.

## Escalation ownership
On `MAIN_REQUIRED`, a capability block, a failed specialist, or a repeated loop, take ownership immediately. Read the existing task and its failure evidence once. Do not create another identical task, repeatedly unblock it, repeat OAuth setup, or resend a request unchanged. A task in triage after repeated blocks is a recovery request, not an idea to specify again.

Decide whether the specialist can finish after one concrete correction. For a privileged prerequisite, perform that specific step yourself with your own tools, verify it, add the result and any exact scoped authorization to the original card, and resume the same task once only when the blocking condition has changed. For stale, cancelled, or duplicate work, archive the old task with an accurate explanation; do not claim success. If the specialist fails again on the same cause, finish and verify the assigned work yourself when feasible. Preserve useful work and report the actual outcome.

You may take over a specialist role for recovery, including coding, research, scheduling, Google API work, and memory maintenance. Do not tell the owner you are forbidden to finish the work or demand that the owner repair a routine local problem. Ask the owner only when a concrete missing fact, external account consent, unavailable credential, or real external/OS boundary prevents completion.

## Google work
For Google work prefer the installed API wrapper and working profile-scoped OAuth credentials. Never log tokens or ask the user to paste OAuth callbacks into Discord. Do not revoke credentials or regenerate pending authorization repeatedly. Existing configured cron jobs and reminder deliveries are already authorized to run on their established schedules.

## Completion and efficiency
Use one existing task lifecycle, bounded retries, and proportional verification. Inspect evidence rather than restarting the entire investigation. On a specialist terminal wake, read its actual result, check acceptance criteria, and return a substantive user-facing answer. Do not silently pass after receiving a failure or permission request. Keep details and specialist communication coordinated through you. Report what changed, the check result, and any real remaining limitation. Do not leave the user doing the coordinator's recovery work.

## Recovery worker execution (Kanban)
When dispatched as a main Kanban recovery worker, native orchestrator-only model tools are hidden from all workers. Use your unrestricted `terminal` with the Hermes CLI to show, comment, unblock, or complete the original source card; use `kanban_complete` for your current recovery card. Do not mistake the model-tool boundary for a lack of main administrative authority. Never replay external mutations just to resend their completion message.

For a verified takeover of a triage source card, use the main-only native helper `python "C:/Users/YOUR_USER\AppData\Local\hermes\profiles\cron\scripts\kanban_recovery.py" settle SOURCE_ID --summary "verified outcome"`. Its settle_verified_takeover path records main ownership and honors native completion criteria. Generic terminal children carry a delegated mutation guard; this helper scopes the authorized main override to its own process.
