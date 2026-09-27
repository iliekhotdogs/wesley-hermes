# Live Main-Agent Activity Detection

## Problem

The default Hermes profile (Ditto) has no Kanban card to track, so the office view needs an independent signal for when the main agent is actively processing a conversation.

## Solution

Query `state.db` and join `session_turn_leases` to `sessions`. An unexpired lease for a non-cron default session means the main agent is running.

```python
import sqlite3
import time
from pathlib import Path

STATE_DB_PATH = Path.home() / "AppData" / "Local" / "hermes" / "state.db"

def read_main_activity() -> dict | None:
    """Return the active default-profile turn, if one currently holds a lease."""
    if not STATE_DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(str(STATE_DB_PATH), timeout=5)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT s.id, s.title, s.source, s.last_activity_description
            FROM session_turn_leases AS lease
            JOIN sessions AS s ON s.id = lease.conversation_id
            WHERE lease.expires_at > ?
              AND COALESCE(NULLIF(s.profile_name, ''), 'default') = 'default'
              AND s.source != 'cron'
            ORDER BY lease.acquired_at DESC
            LIMIT 1
            """,
            (time.time(),),
        ).fetchone()
        conn.close()
        if row is None:
            return None
        return {
            "task_id": f"session:{row['id']}",
            "title": row["title"] or row["last_activity_description"] or "Active conversation",
            "assignee": "main",
            "status": "running",
            "source": row["source"],
        }
    except (sqlite3.Error, OSError):
        return None
```

## Key Details

- The lease expires ~5 minutes after the last message (configurable in Hermes).
- `COALESCE(NULLIF(s.profile_name, ''), 'default')` treats NULL as default profile.
- Exclude `source='cron'` so scheduled jobs don't count as main activity.
- This query is read-only and bounded — safe to run every 3 seconds.
- Falls back to `None` (→ idle) on any error, which is the safe default.

## Verification

```bash
# Check current leases
python -c "import sqlite3,time,pathlib; p=pathlib.Path.home()/'AppData/Local/hermes/state.db'; c=sqlite3.connect(p); print([dict(r) for r in c.execute('SELECT * FROM session_turn_leases WHERE expires_at > ?', (time.time(),))]); c.close()"

# Check recent sessions
python -c "import sqlite3,pathlib; p=pathlib.Path.home()/'AppData/Local/hermes/state.db'; c=sqlite3.connect(p); print([dict(r) for r in c.execute(\"SELECT id,title,source,profile_name FROM sessions ORDER BY started_at DESC LIMIT 5\")]); c.close()"
```
