# Daily Brief Composition

Build an action-oriented start-of-day brief from Gmail, Google Calendar, and Google Tasks.

## Procedure

### 1. Set the day window

Use an explicit half-open window `[day_start, next_day_start)` in the user's timezone. Done when the exact UTC and local window are stated.

### 2. Fetch Gmail

Search a bounded recent window (last 7 days, excluding promotions/social). Read full relevant threads. Done when each included email changes preparation, priority, or follow-up.

### 3. Fetch Calendar

Retrieve all calendars in scope, including accepted and tentative meetings, all-day events, travel/holds, location/video links. Detect overlaps. Done when declined/cancelled events are excluded intentionally.

### 4. Fetch Tasks

Retrieve all open tasks across all tasklists. Mark overdue vs upcoming. Done when task counts are accurate.

### 5. Normalize and Deduplicate

Convert all sources into the normalization contract. Deduplicate by `source:sourceId`. Keep newest copy.

### 6. Rank by consequence

Rank by urgency, impact, and schedule — not message count. Top 3-5 items. Done when each included item has a clear preparation, deadline, conflict, or follow-up reason.

### 7. Offer bounded actions

Present the ranked briefing. Propose replies, calendar holds, or task updates only after presenting. A brief request is not authorization to mutate.

## Output Shape

1. Schedule at a glance
2. Conflicts and tight transitions
3. Urgent items and deadlines
4. Follow-ups owed by the user
5. Waiting on others
6. Source health / connector failures

## Delta brief continuity and recovery

- Extract only the final `## Response` section from retained cron output; recursively nested prompts and failed wrappers are not findings or a source snapshot.
- Recover prior completed collection-card evidence even when the prior coordinator returned before workers finished. Compare Canvas assignment ID, due time, and submission state programmatically; call newly included rolling-window work "newly in the horizon," not newly created.
- On a specialist `MAIN_REQUIRED`, main must execute the exact blocked read immediately using its own installed wrappers and valid profile-scoped OAuth. Never finalize with "checks pending" when main can perform the reads. Preserve partial evidence and close the same card with verified takeover results.
- For upcoming Calendar changes, use the wrapper's `build_service('calendar','v3')` to paginate calendarList and events, retain `updated` timestamps and cancelled events for comparison, and exclude declined/cancelled entries from the active agenda. A calendar cancellation does not cancel a Canvas deadline.
- Keep a profile-local dated source snapshot for the next delta comparison; distinguish collection evidence from proof that delivery occurred. Do not alter an existing scheduled job during its execution.
- Preserve source-specific last-successful cutoffs when OAuth or collection fails; a failed run timestamp must not advance the Gmail cutoff or replace the latest good Calendar baseline. Record stale-source status explicitly and report changes as unverified. Reuse working profile-scoped credentials only when available; invalid_grant requires account consent, not repeated OAuth regeneration in an unattended run.
- If the new-mail query is empty, retry without promotions/social exclusions before asserting no new email; compute its epoch cutoff from the explicit prior-run ISO timestamp and paginate the broad query. Exclude spam/trash explicitly.
- Compare calendar changes on consequential fields (title, status, times, location, description); do not elevate color-only edits into scheduling changes. Label old events entering the seven-day window as newly in the horizon, and check the changed appointments against active, non-declined events for overlaps.
- When an assignment disappears from the rolling due list, read its exact ID in the course assignments before labelling it completed or cancelled; a moved due date can explain disappearance. Preserve the new date in the snapshot even when outside the horizon.
- Carry the moved-out-of-horizon assignment ledger into each subsequent snapshot until it re-enters the window or an exact read establishes a terminal state. Otherwise a later run loses the prior date and cannot distinguish a fresh change from an already reported move; course-list responses without submission data do not establish completion.
- Deliver the actual delta briefing after verification, never a test-result-only final response. Keep internal tests and source snapshots separate from user-facing content; yesterday's incomplete output is not evidence that yesterday had no changes.
- Before labelling schoolwork overdue or incomplete from Canvas `unsubmitted`, read its exact assignment with `include[]=submission` and inspect `submission_types` and description. `none` can mean a practice worksheet or in-class quiz with no online submission; a null grade does not prove absence. Course CLI listings can omit submission data even when an exact assignment GET confirms an external-tool grade. Carry the verified distinction into the next snapshot rather than repeating a false missing-work alert.

## Pitfalls

- Mixing account timezone with machine timezone
- Treating tentative meetings as confirmed
- Creating calendar events while the user only requested a brief
- Hiding all-day commitments below timed meetings
