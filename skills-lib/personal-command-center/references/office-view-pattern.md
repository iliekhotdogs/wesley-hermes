# Office Floor / Bridge View — Reference Pattern

## Architecture Overview

The `/office` route serves an animated ship-bridge dashboard that visualizes subagents as crew members stationed across a vessel. It polls the Kanban DB every 3 seconds and re-renders agent positions based on their status. A separate `/team` route provides a detailed roster view.

## File Layout

```
desktop-plugins/command-center/
├── command_center_server.py   # Main HTTP server with /, /office, /team, /api/* routes
├── office_view.py             # render_office(), render_team() — full HTML templates
├── static/                    # Profile images for each agent
│   ├── main_ditto.png
│   ├── multimodal.jpg
│   ├── critic.webp
│   ├── coder_a.jpeg
│   ├── doctor.jpeg
│   ├── utility.webp
│   ├── researcher.webp
│   └── coder_b.webp
└── __pycache__/               # MUST be deleted after editing office_view.py
```

## Key Constants (office_view.py)

```python
ROOMS = {
    "helm":       {"label": "Bridge",      "emoji": "☠️", "x": 50, "y": 8},
    "war-room":   {"label": "War Room",    "emoji": "⚔️", "x": 15, "y": 30},
    "mess-hall":  {"label": "Galley",      "emoji": "🍖", "x": 78, "y": 30},
    "docking-bay":{"label": "Docking Bay",  "emoji": "🚀", "x": 50, "y": 92},
    "crew-quarters":{"label": "Crew Quarters", "emoji": "🏠", "x": 50, "y": 82},
}

DESKS = {
    "main":       {"label": "Captain's Chair", "emoji": "👑", "x": 50, "y": 30},
    "multimodal": {"label": "Lookout Tower", "emoji": "👁️", "x": 15, "y": 52},
    "critic":     {"label": "Furnace Room",  "emoji": "🔥", "x": 15, "y": 72},
    "coder-a":    {"label": "Rigging Deck",  "emoji": "⚓", "x": 38, "y": 52},
    "doctor":     {"label": "Medical Bay",   "emoji": "🏥", "x": 38, "y": 72},
    "utility":    {"label": "Armory",        "emoji": "🗡️", "x": 62, "y": 52},
    "researcher": {"label": "Chart Room",    "emoji": "🗺️", "x": 62, "y": 72},
    "coder-b":    {"label": "Workshop",      "emoji": "🔨", "x": 78, "y": 52},
}

AGENT_PERSONAS = {
    "main": "Ditto",
    "multimodal": "Laboon",
    "critic": "Calcifer",
    "coder-a": "Heen",
    "doctor": "Tony Tony Chopper",
    "utility": "Pakkun",
    "researcher": "Gamatasu",
    "coder-b": "Totoro",
}

AGENT_COLORS = {
    "main": "#c084fc",
    "multimodal": "#d97706",
    "critic": "#ef4444",
    "coder-a": "#a3a3a3",
    "doctor": "#22c55e",
    "utility": "#fbbf24",
    "researcher": "#7c3aed",
    "coder-b": "#0ea5e9",
}

# Exact models from `hermes profile show <name>` — refresh when profiles change.
AGENT_MODELS = {
    "main": "gpt-5.6-luna",
    "multimodal": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "critic": "z-ai/glm-5.2:free",
    "coder-a": "qwen3-coder-plus",
    "doctor": "z-ai/glm-5.3",
    "utility": "nvidia/nemotron-3-super-120b-a12b:free",
    "researcher": "gpt-5.6-sol",
    "coder-b": "qwen3-coder-plus",
}

AGENT_FALLBACKS = {
    "main": "",
    "multimodal": "gpt-5.6-luna",
    "critic": "gpt-5.6-luna",
    "coder-a": "gpt-5.6-terra",
    "doctor": "gpt-5.6-luna",
    "utility": "gpt-5.6-luna",
    "researcher": "gpt-5.6-luna",
    "coder-b": "gpt-5.6-terra",
}
```

## Main Agent (Default Profile) Activity Detection

The default profile's activity comes from `state.db` by joining `session_turn_leases` to `sessions`. An unexpired lease for a non-cron default session means Main is running:

def read_main_activity() -> dict | None:
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

## Status → Zone Logic

def status_to_zone(status, assignee):
    if status == "running":
        return assignee if assignee in DESKS else "helm"
    if status == "blocked":
        return "war-room"
    if status in ("ready", "todo"):
        return "helm"
    if status == "idle":
        return "crew-quarters"
    return "mess-hall"
```

## Server-Side Static File Serving

```python
elif parsed.path.startswith("/static/"):
    filename = parsed.path.replace("/static/", "", 1)
    static_dir = Path(__file__).resolve().parent / "static"
    file_path = static_dir / filename
    if file_path.exists() and file_path.is_file():
        suffix = file_path.suffix.lower()
        content_type = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp",
        }.get(suffix, "application/octet-stream")
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
```

## JavaScript Polling Pattern

```javascript
async function poll() {
  const r = await fetch('/api/subagents');
  const data = await r.json();
  const workers = [...data.active, ...data.recent];

  document.querySelectorAll('.room-avatars').forEach(el => el.innerHTML = '');
  document.querySelectorAll('.room-desk').forEach(el => el.classList.remove('active'));

  const counts = { running: 0, waiting: 0, blocked: 0, idle: 0 };

  workers.forEach(w => {
    let zone = 'mess-hall';
    if (w.status === 'running') zone = w.assignee || 'helm';
    else if (w.status === 'blocked') zone = 'war-room';
    else if (w.status === 'ready' || w.status === 'todo') zone = 'helm';
    else if (w.status === 'idle') zone = 'crew-quarters';

    const container = document.getElementById('room-' + zone);
    if (!container) return;

    if (zone.startsWith('coder-') || ['main','researcher','critic','utility','multimodal','doctor'].includes(zone)) {
      container.closest('.room-desk')?.classList.add('active');
    }

    // ... create avatar and append ...

    if (w.status === 'running') counts.running++;
    else if (w.status === 'blocked') counts.blocked++;
    else if (w.status === 'ready' || w.status === 'todo') counts.waiting++;
    else counts.idle++;
  });

  document.getElementById('stat-active').textContent = counts.running;
  document.getElementById('stat-waiting').textContent = counts.waiting;
  document.getElementById('stat-blocked').textContent = counts.blocked;
  document.getElementById('stat-idle').textContent = counts.idle;
}

poll();
setInterval(poll, 3000);
```

## CSS Theme Tokens (Victorian Punk)

```css
:root {
  --burnt-orange: #d97706;
  --rust-red: #dc2626;
  --charcoal: #1c1917;
  --dark-gray: #374151;
  --bone-white: #e5e5e5;
  --electric-yellow: #fbbf24;
  --metal-gray: #6b7280;
  --pipe-color: #44403c;
  --rivet: #a8a29e;
  --deck-wood: #5c4033;
  --hull-dark: #1a1510;
}
```

## Main Agent Highlight Styling

```css
.legend-item.main-agent {
  margin: -4px -6px 14px;
  padding: 8px 6px;
  border: 2px solid #c084fc;
  border-radius: 6px;
  background: linear-gradient(135deg, rgba(192,132,252,0.18), rgba(251,191,36,0.08));
  box-shadow: 0 0 14px rgba(192,132,252,0.2);
}

.legend-item.main-agent .legend-avatar {
  width: 44px;
  height: 44px;
  box-shadow: 0 0 14px rgba(192,132,252,0.45);
}

.main-badge {
  display: inline-block;
  margin-left: 4px;
  padding: 1px 5px;
  border-radius: 2px;
  background: #c084fc;
  color: #17111d;
  font-size: 7px;
  font-weight: 900;
  letter-spacing: .06em;
  vertical-align: 1px;
}
```

## Team Tab Layout Pattern

The `/team` route serves as the comprehensive info dashboard. It uses CSS Grid with `auto-fill` + `minmax()` for responsive card layouts:

```html
<main>
  <!-- Stats bar -->
  <div class="stats-bar">...</div>

  <!-- Active Operations: horizontal cards -->
  <div class="section-title">⚔️ Active Operations</div>
  <div class="ops-grid">
    <div class="op-card">
      <div class="op-avatar">...</div>
      <div class="op-info">
        <div class="op-header">
          <span class="op-persona">Ditto</span>
          <span class="op-assignee">@main</span>
          <span class="status-pill running">RUNNING</span>
        </div>
        <div class="op-role">MAIN AGENT — Captain & Final Approver</div>
        <div class="op-task">Central dispatch and final approval</div>
        <div class="op-model">gpt-5.6-luna</div>
      </div>
    </div>
  </div>

  <!-- Crew Roster: compact grid -->
  <div class="section-title">⚓ Crew Roster</div>
  <div class="crew-grid">
    <div class="crew-card">
      <div class="crew-avatar">...</div>
      <div class="crew-name">Ditto</div>
      <div class="crew-role">MAIN AGENT</div>
      <div class="crew-model">gpt-5.6-luna</div>
      <span class="status-pill idle">IDLE</span>
    </div>
  </div>

  <!-- Scheduled Missions: cards with descriptions -->
  <div class="section-title">🗓️ Scheduled Missions</div>
  <div class="missions-grid">
    <div class="mission-card">
      <div class="mission-header">
        <span class="mission-name">Morning Briefing</span>
        <span class="status-pill scheduled">SCHEDULED</span>
        <span class="status-pill enabled">ON</span>
      </div>
      <div class="mission-desc">Daily morning briefing...</div>
      <div class="mission-meta">
        <span class="runtime-badge">daily 9:00am</span>
        <span class="mission-model">gpt-5.6-luna</span>
      </div>
      <div class="mission-times">Next: ... · Last: ...</div>
    </div>
  </div>
</main>
```

Key CSS classes:
- `.ops-grid` — `grid-template-columns: repeat(auto-fill, minmax(320px, 1fr))`
- `.crew-grid` — `grid-template-columns: repeat(auto-fill, minmax(140px, 1fr))`
- `.missions-grid` — `grid-template-columns: repeat(auto-fill, minmax(300px, 1fr))`
- `.status-pill` — colored pills for running/blocked/waiting/idle/done/enabled/disabled
- `.runtime-badge` — monospace schedule display

Sections only render when they have content. The page auto-refreshes every 30s.

## Debugging Checklist

1. **Edits not showing?** Delete `__pycache__/office_view.cpython-311.pyc` and restart server
2. **Port in use?** `netstat -ano | grep :8765` then `taskkill /PID <pid> /F`
3. **Images not loading?** Verify files exist in `static/` and content-type matches extension
4. **JS errors?** Check browser console for `TypeError: unhashable type` — usually an f-string dict issue
5. **Stale data?** Kanban DB may not update instantly — check `tasks` directly
6. **Ditto not moving?** Check `session_turn_leases` in `state.db` — the lease expires ~5 min after the last message
7. **Persona not callable?** Verify every manifest member has a real `hermes profile show <name>` profile
8. **Wrong model label?** Re-read the exact profile model; do not retain fictional-series metadata