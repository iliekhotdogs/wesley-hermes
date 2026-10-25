# Team Page Pattern — Card-Grid Info Dashboard

## Overview

The `/team` route renders a comprehensive info dashboard with all crew, tasks, and missions in one scrollable view. This is the "everything page" — the office view is pure visual, the team page is pure data.

## Layout

```
┌─────────────────────────────────────────────┐
│  Stats Bar (Active/Waiting/Blocked/Idle)    │
├─────────────────────────────────────────────┤
│  ⚔️ Active Operations                       │
│  ┌──────┐ ┌──────┐ ┌──────┐                 │
│  │ Card │ │ Card │ │ Card │  (running/blocked)│
│  └──────┘ └──────┘ └──────┘                 │
├─────────────────────────────────────────────┤
│  ⚓ Crew Roster                              │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐        │
│  │ Idle│ │ Idle│ │ Idle│ │ Idle│ │ Idle│        │
│  └────┘ └────┘ └────┘ └────┘ └────┘        │
├─────────────────────────────────────────────┤
│  🗓️ Scheduled Missions                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │ Mission  │ │ Mission  │ │ Mission  │     │
│  └──────────┘ └──────────┘ └──────────┘     │
└─────────────────────────────────────────────┘
```

## Section Rules

1. **Stats bar** — Always at top. Shows live counts from Kanban data.
2. **Active Operations** — Only renders when there are running/blocked agents. Uses horizontal card layout with avatar, role, task title, model, status pill.
3. **Crew Roster** — Grid of idle/background agents. Each card shows avatar, name, role, model, status pill. Uses `auto-fill` + `minmax(140px, 1fr)` for responsive wrapping.
4. **Scheduled Missions** — Cards for each cron job from `~/.hermes/cron/jobs.json`. Shows name, description, schedule badge, model, next/last run times.

## Data Sources

- **Crew status**: `read_workers()` (always returns all DESKS agents)
- **Cron jobs**: `read_cron_jobs()` (reads `cron/jobs.json`)

## CSS Grid Pattern

```css
.ops-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
}
.crew-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
}
.missions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 10px;
}
```

## Status Classification

```python
active_workers = [w for w in workers if w["status"] in ("running", "blocked", "ready", "todo")]
idle_workers = [w for w in workers if w["status"] not in ("running", "blocked", "ready", "todo")]
```

## Conditional Rendering

Sections only appear when they have content:

```python
{"<div class='section-title'>...</div><div class='ops-grid'>" + ops_html + "</div>" if ops_html else ""}
```

## Pitfalls

- **f-string dict doubling**: In `office_view.py`, never nest `{dict}` inside an f-string expression. Build dicts first, pass to `json.dumps()`.
- **Stale cache**: Delete `__pycache__/office_view.cpython-311.pyc` after editing — the server doesn't auto-reload on Windows.
- **Port conflicts**: Check `netstat -ano | grep :8765` and `taskkill` stale processes before restarting.
- **Cron jobs.json missing**: If the file doesn't exist, return empty list — never crash the page.
- **HTML escaping**: Always use `html.escape()` for user-controlled content (job names, prompts, task titles).
