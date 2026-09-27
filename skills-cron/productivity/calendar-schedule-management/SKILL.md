---
name: calendar-schedule-management
description: "Use when managing a class timetable in Google Calendar."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [calendar, google-calendar, schedules, timetables, timezone, colorId]
    related_skills: [google-workspace]
---

# Calendar Schedule Management

Use this skill for importing, auditing, replacing, recoloring, or verifying a structured class timetable in Google Calendar.

## Core safety model

- Treat the user-provided schedule as the source of truth.
- Never delete or alter unmarked personal events merely because they fall in the same date range.
- Mark managed class events with a stable description marker such as `Auto-imported from schedule`.
- Before destructive changes, report the proposed scope and obtain confirmation unless the user has already explicitly authorized that exact change.
- Prefer a reversible replacement: delete only marked managed events, then create the new rows.
- After every external write, read the target range back and verify it; successful API responses alone are insufficient.

## Audit workflow

1. Authenticate and check the calendar connection before the first read.
2. Parse the source rows into `(date, summary, start, end)` records. Preserve course identifiers and times literally.
3. List the complete target range. Request a high limit such as `--max 1000`; default list limits can silently return only an initial page.
4. Partition events into managed class events and unmarked personal events using the description marker.
5. Compare normalized local date/time keys, not just summaries. Report old-only courses, new-only courses, count differences, and timezone anomalies.
6. When the user confirms, remove only the old managed events and recreate the source rows with explicit timezone-aware timestamps.
7. Verify exact equality of the source and calendar managed-event key sets, plus preservation of unmarked events.

## Timezone handling

Use a real IANA timezone such as `zoneinfo.ZoneInfo('America/Vancouver')` when constructing timestamps. Do not attach a fixed `-07:00` or `-08:00` offset to every semester event: Vancouver changes between PDT and PST during a fall term. When reading back, convert API timestamps into the same IANA timezone before comparing local date/time fields.

## Event colors

Google Calendar event colors are assigned with the event `colorId` field. The bundled compatibility CLI may support list/create/delete but not update or `colorId`; in that case use the authenticated Calendar API with `googleapiclient.discovery.build('calendar', 'v3', credentials=...)`.

- Filter to managed events before updating colors.
- Choose one explicit color per course and apply it to all meeting types for that course.
- Update with `sendUpdates='none'` when no attendee notifications are intended.
- Read the event range back and assert every managed event has the expected color ID.
- Keep the color mapping in a reference file or task output so the choice is reproducible.

See `references/google-calendar-timetable-patterns.md` for the validated replacement, DST, and color-assignment pattern.

## Common pitfalls

- **Truncated audit:** a calendar list that stops early is not evidence that later classes are absent. Increase the max/page through results.
- **DST drift:** fixed offsets can make post-transition events display one hour late. Rebuild or correct them using `America/Vancouver` and verify local times.
- **Course-name drift:** compare full summaries, including section type (`LEC`, `TUT`, `SEM`), while grouping colors by course prefix.
- **Over-broad deletion:** never delete all events in a semester range; delete only events bearing the managed marker.
- **False success:** count created/deleted events and perform an exact read-back comparison before reporting completion.
