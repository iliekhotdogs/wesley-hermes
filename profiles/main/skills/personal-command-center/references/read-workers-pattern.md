# read_workers() Pattern — Always Include All Crew

## Problem

The original `read_workers()` only returned agents with active Kanban tasks. This meant idle crew members were invisible in the office view — contradicting the requirement that all subagents be visible even when idle.

## Solution

Build a `task_map` from Kanban, then iterate `DESKS.keys()` so every crew member gets an entry. Agents without an active task get `status: "idle"` and `zone: "crew-quarters"`.

## Implementation

```python
def read_workers() -> list[dict]:
    """Read current workers from Kanban DB. Always includes all agents from DESKS."""
    task_map = {}
    if KANBAN_DB_PATH.exists():
        try:
            conn = sqlite3.connect(str(KANBAN_DB_PATH), timeout=5)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, title, assignee, status, worker_pid, last_heartbeat_at, started_at, completed_at
                FROM tasks
                WHERE assignee IS NOT NULL
                ORDER BY
                  CASE status
                    WHEN 'running' THEN 0
                    WHEN 'blocked' THEN 1
                    WHEN 'ready' THEN 2
                    WHEN 'todo' THEN 3
                    ELSE 4
                  END,
                  started_at DESC
                """
            ).fetchall()
            conn.close()
            for row in rows:
                task_map[row["assignee"]] = {
                    "id": row["id"],
                    "title": (row["title"] or "untitled")[:40],
                    "assignee": row["assignee"],
                    "status": row["status"],
                    "zone": status_to_zone(row["status"], row["assignee"]),
                }
        except Exception:
            pass

    # Always include every agent from DESKS
    workers = []
    for key in DESKS:
        if key in task_map:
            t = task_map[key]
            workers.append({
                **t,
                "initials": AGENT_INITIALS.get(key, key[:2].upper()),
                "color": AGENT_COLORS.get(key, "#8a8f98"),
                "persona": AGENT_PERSONAS.get(key, key),
                "model": AGENT_MODELS.get(key, ""),
                "role": AGENT_ROLES.get(key, ""),
                "image": AGENT_IMAGES.get(key, ""),
            })
        else:
            workers.append({
                "id": f"idle-{key}",
                "title": "Standing by",
                "assignee": key,
                "status": "idle",
                "zone": "crew-quarters",
                "initials": AGENT_INITIALS.get(key, key[:2].upper()),
                "color": AGENT_COLORS.get(key, "#8a8f98"),
                "persona": AGENT_PERSONAS.get(key, key),
                "model": AGENT_MODELS.get(key, ""),
                "role": AGENT_ROLES.get(key, ""),
                "image": AGENT_IMAGES.get(key, ""),
            })
    return workers
```

## Key Rules

1. **One entry per DESKS key** — not per Kanban row. Never inject a "synthetic-main" entry; the DESKS iteration covers the main agent.
2. **Idle defaults** — agents without a task get `status: "idle"`, `zone: "crew-quarters"`, title "Standing by".
3. **Deterministic** — same DESKS + same Kanban data = same output every call.
4. **No filtering** — do not exclude `done`/`completed` cards inside `read_workers()`. Let the caller decide what to display.
5. **Bounded query** — read-only SQLite with `timeout=5`, closed via `conn.close()`.

## Migration Notes

- Remove any `if not any(w.get("assignee") == "main" ...)` blocks from `render_office()` and `render_team()` — they are no longer needed.
- The office view's JS `poll()` already handles idle avatars correctly via `updateChar()`.
- The team page's `render_team()` automatically classifies idle agents into the Crew Roster grid.

## Testing

After implementing:
1. Kill the server, delete `__pycache__`, restart.
2. Visit `/office` — all 8 crew members should appear at Crew Quarters (idle) even with empty Kanban.
3. Visit `/team` — Crew Roster should show all 8 agents as idle cards.
4. Create a running Kanban task — that agent moves to their station in office, and appears in Active Operations on team page.
