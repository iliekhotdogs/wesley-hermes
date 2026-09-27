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

## Pitfalls

- Mixing account timezone with machine timezone
- Treating tentative meetings as confirmed
- Creating calendar events while the user only requested a brief
- Hiding all-day commitments below timed meetings
