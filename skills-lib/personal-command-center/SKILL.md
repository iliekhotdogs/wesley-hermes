---
name: personal-command-center
description: "Build a command center for email, calendar, and tasks."
version: 0.1.0
author: Hermes Agent (Wesley)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Dashboard, Morning-Briefing, Automation, Desktop-Plugin, Google-Workspace, Workflow]
    related_skills: [google-workspace, email-inbox-triage, weekly-review-planning, hermes-agent]
---

# Personal Command Center

Build a unified dashboard that aggregates multiple personal data sources (Gmail, Calendar, Tasks, Outlook) into a single morning briefing with visual workflow automation. Runs as a native Hermes Desktop plugin page with optional cron-based scheduled delivery.

## When to Use

- "Build a command center"
- "Morning briefing"
- "Show me everything in one place"
- "What matters today"
- "Aggregate my email, calendar, and tasks"
- "Visual workflow builder"

## Architecture

### Data Flow

```
[Gmail]     →
[Calendar]  → [Normalization] → [Deduplication] → [Ranking] → [Dashboard]
[Tasks]     →
[Outlook]   →
```

### Components

1. **Desktop Plugin Page** — `/command-center` route with sidebar nav
2. **Data Backend** — Python script with OAuth, fetching, caching
3. **Dashboard Server** — Local HTTP server serving live HTML
4. **Workflow Editor** — Visual trigger/source/judgment/output nodes
5. **Cron Job** — Scheduled daily generation

## Implementation Pattern

### 1. Least-Privilege Google OAuth

Start with read-only scopes. Upgrade incrementally without starting over:

```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks.readonly",
]
```

**Token upgrade path**: When adding send or write, append the new scope and re-run `--auth-url` → `--auth-code`. Store tokens per-purpose with restrictive permissions (`chmod 600`).

**Key pitfall**: Google Tasks API is not enabled by default. Direct users to `https://console.developers.google.com/apis/api/tasks.googleapis.com/overview?project=<ID>` before fetching.

### 2. Normalization Contract

Every source item must produce:

```python
{
    "source": "gmail" | "calendar" | "tasks",
    "sourceId": str,        # Unique within source
    "title": str,           # Human-readable label
    "timestamp": str,       # ISO 8601
    "sourceUrl": str,       # Deep link to original
    "detail": str,          # Supporting text
}
```

### 3. Deduplication

Use `source:sourceId` as the dedup key. Keep the newest copy by `updatedAt` or `timestamp`. Never surface the same thread/event twice across sources.

### 4. Receipt Confirmation

**Always confirm after sending an email.** Provide:

```
Email sent.
Message ID: 1a046b12775caf95
Thread ID: 1a046b12775caf95
```

This is non-negotiable. The user needs proof of delivery.

### 5. Permission Handling

If the user explicitly says "just send it" or "don't ask for permission," respect that. Send immediately, then confirm what was done with receipt. Do not re-ask for permission the user already waived.

## Desktop Plugin Structure

```
desktop-plugins/command-center/
├── plugin.js                  # Main SDK entry (routes, nav, palette)
├── google_readonly.py         # Data backend with OAuth + fetching
├── command_center_server.py   # Local HTTP dashboard server
├── google_client_secret.json  # OAuth credentials (restrictive perms)
├── google_readonly_token.json # Auto-refreshing token (restrictive perms)
├── google_briefing_cache.json # Last fetched data (restrictive perms)
├── test_google_readonly.py    # Automated tests
└── plugin.test.mjs            # Workflow validation tests
```

## Workflow Validation

A valid workflow requires:
- At least one **trigger** (schedule, webhook, manual)
- At least one **output** (dashboard, email, notification)

```javascript
export function validateWorkflow(nodes) {
  const active = nodes.filter(n => n.enabled !== false)
  const problems = []
  if (!active.some(n => n.kind === 'trigger')) problems.push('Add a trigger.')
  if (!active.some(n => n.kind === 'output')) problems.push('Add an output.')
  return { valid: problems.length === 0, problems }
}
```

## Source Health Panel

Always show connection status per source:

```
Gmail      ● connected — 6 items
Calendar   ● connected — 1 item
Tasks      ● connected — 1 item
Outlook    ○ not configured
```

If a source fails, report it honestly. Never fabricate data to fill gaps.

## Pitfalls

- **Asking for permission after the user waived it.** If they said "just send," send.
- **Forgetting the receipt.** Always provide message ID and thread ID after sending email.
- **Enabling APIs late.** Check Google Tasks API is enabled before fetching.
- **Over-requesting scopes.** Start read-only, upgrade incrementally.
- **Deduplication failures.** Use composite `source:sourceId` keys.
- **Hardcoded colors in plugins.** Always use theme variables.
- **Stale Python cache.** If `office_view.py` edits don't take effect, delete `__pycache__/office_view.cpython-311.pyc` manually — the server doesn't auto-reload on Windows.
- **Port conflicts.** Always check `netstat -ano | grep :8765` and `taskkill` stale processes before restarting the server. Multiple lingering instances cause silent failures.
- **f-string dict doubling.** Never nest `{dict}` inside an f-string expression — `{{k: True for k in DESKS.keys()}}` raises `TypeError: unhashable type: 'dict'`. Build the dict first, then pass to `json.dumps()`.
- **f-string JS brace escaping.** When embedding JavaScript inside a Python f-string for HTML generation, every standalone `{` and `}` in the JS must be doubled: `{` → `{{` and `}` → `}}`. Template variables remain single: `{json.dumps(AGENT_COLORS)}`. Using `.includes()` on arrays inside f-strings requires `!== -1` instead of `.includes()` because the curly braces break the Python expression parser. Always use `var` instead of `const`/`let` inside f-strings to avoid parser confusion. This is the single most common source of `SyntaxError: f-string: invalid syntax` errors when extending the office view JS. Additional rules: no template literals (use string concatenation), no arrow functions (use `function() {{ }}`), no async/await at top level (use `.then()` chains), no nested dict comprehensions in expressions.
- **Subagent model fallback is unsupported.** `delegate_task` children inherit the parent model — there is no automatic model rotation when a free model hits its token limit. If the user requests "switch to gpt-5.6-luna when longcat runs out," this cannot be done via `delegate_task`. Either (a) run the work directly in the lead profile, or (b) accept that free-model subagents may get interrupted mid-task and must be completed by the parent.
- **Server must inject `tagline` and `activity`.** `command_center_server.py`'s `read_subagents()` must import `AGENT_TAGLINES` and `activity_label` from `office_view` and include them in each worker dict. Without this, the office view JS has no access to persona names or activity phrases. See `references/debugging-office-view.md` for the injection pattern.
- **Discord message length.** Cron job responses are sent as one Discord message (2,000 char limit). The cron wrapper adds overhead, so keep the actual briefing content under **1,500 characters**. The full output file includes the skill text and is always over the limit — only the `## Response` section counts.
- **`attach_to_session: true` opens threads.** On Discord, this setting makes cron jobs post in a continuable thread on the target channel instead of the main channel. Users see a thread notification but not the message. For one-way delivery (briefings, digests, reports), always use `attach_to_session: false`.
- **Synthetic-main injection.** Do not inject a "synthetic-main" entry in `render_office()` or `render_team()` — `read_workers()` already covers all DESKS agents including main.
- **Idle agents invisible.** `read_workers()` must always return one entry per DESKS key, not just agents with active Kanban tasks. See `references/read-workers-pattern.md`.
- **Re-parenting breaks positioning.** Never move an avatar into a non-positioned container. Always position the parent group (`position: absolute; left:X%; top:Y%`). The group must be the direct child of `.office-floor`.
- **Team page card grid.** Use CSS Grid with `auto-fill` + `minmax()` for responsive wrapping. Sections only render when they have content. See `references/team-page-pattern.md`.

## Office Floor / Bridge View (Subagent Visualization)

The command center includes an animated "ship bridge" view at `/office` that visualizes subagents as crew members stationed across a vessel. This is Wesley's preferred way to monitor the swarm.

### Architecture

```
command_center_server.py  →  /office route  →  office_view.render_office()
                                                              ↓
                                                    Kanban DB (tasks table)
                                                              ↓
                                                    HTML with embedded CSS/JS
                                                              ↓
                                                    Polls /api/subagents every 3s
```

### Agent Roster Pattern

Each agent has:
- **Persona** — anime/cartoon character used as the visual identity
- **Model** — the model currently configured for the matching Hermes profile, shown under the character name instead of fictional-series origin
- **Role** — functional specialty (Multimodal, Critic, Coder A, Doctor, Utility, Researcher, Coder B)
- **Station** — dedicated desk/room on the ship where they appear when `status == "running"`
- **Color** — unique hex color for visual identification
- **Initials** — 2-letter abbreviation for fallback display
- **Profile image** — served from `/static/<filename>` (JPEG or WebP)

Treat roster presentation, profile configuration, and live execution as separate data:
- A manifest entry is only a configured visual identity.
- A callable worker requires a real `hermes profile show <name>` profile.
- A running avatar requires a live Kanban/delegation task; an idle avatar must never imply that a process or model is consuming resources.
- Read model identifiers from live profile configuration when practical. If the view uses an `AGENT_MODELS` snapshot, refresh it only after checking `hermes profile list/show`; never infer or abbreviate identifiers.

### Status → Zone Mapping

| Status | Zone | Meaning |
|--------|------|---------|
| `running` | Agent's dedicated station | At work |
| `blocked` / failed execution | War Room | Needs help |
| `ready` / `todo` | Bridge / Helm | Waiting |
| `idle` or completed work | Crew Quarters | No unfinished work |
| anything else | Mess Hall / Galley | Unrecognized or miscellaneous state |

### Live Main-Agent and Crew-State Contract

The API must always return exactly one state for every configured crew member. Do not show only rows that happen to exist in Kanban.

- Main/default agent activity comes from `state.db` by joining `session_turn_leases.conversation_id` to `sessions.id`. An unexpired lease for the default profile and a non-cron session is `running`; when the lease is released or expires, Main returns to `idle`.
- Named specialists follow their highest-priority unfinished Kanban card. Map `running` to the dedicated station, `blocked`/`failed`/`crashed`/`timed_out` to War Room, `ready`/`todo` to Bridge, and no unfinished card to Crew Quarters.
- Exclude `done`/`completed` cards from live occupancy so workers return to Crew Quarters immediately after completion.
- Poll every 3 seconds, clear all avatar containers before rendering, and count `active`, `waiting`, `blocked`, and `idle` independently.
- Use bounded read-only SQLite queries and test active/expired main leases, running specialists, completion-to-idle, missing Kanban, and exact one-entry-per-crew behavior.

### Python Rendering Contract

The `read_workers()` function in `office_view.py` must always return exactly one entry per agent defined in `DESKS` — not just agents with active Kanban tasks. This ensures all crew members are visible in the office view even when idle.

**Pattern**: Build a `task_map` from Kanban, then iterate `DESKS.keys()`:

```python
def read_workers() -> list[dict]:
    task_map = {}
    if KANBAN_DB_PATH.exists():
        try:
            conn = sqlite3.connect(str(KANBAN_DB_PATH), timeout=5)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT ... FROM tasks WHERE assignee IS NOT NULL ...").fetchall()
            conn.close()
            for row in rows:
                task_map[row["assignee"]] = { ... }
        except Exception:
            pass

    workers = []
    for key in DESKS:
        if key in task_map:
            workers.append({ **task_map[key], ...agent_meta(key) })
        else:
            workers.append({
                "id": f"idle-{key}", "title": "Standing by",
                "assignee": key, "status": "idle", "zone": "crew-quarters",
                ...agent_meta(key)
            })
    return workers
```

**Key rules**:
- Never inject a "synthetic-main" entry — the DESKS iteration already covers the main agent.
- Idle agents get `status: "idle"` and `zone: "crew-quarters"`.
- The function must be deterministic: same DESKS + same Kanban = same output.
- Do not filter by `status != "done"` — let the caller decide what to display.

See `references/read-workers-pattern.md` for the full implementation.

### Main Agent (Ditto) Configuration

The default profile is represented as the Main Agent with persona "Ditto". It uses a distinct purple color (`#c084fc`), the "Captain's Chair" station, and is highlighted in the manifest with a `MAIN AGENT` badge and larger avatar. Configure it like any other agent in the `AGENT_*` dicts and `DESKS`.

### Model Display

Show the exact configured model for each profile under the character name. Read models from `hermes profile show <name>` and cache in `AGENT_MODELS`. Optionally show a backup/fallback model line. Do not display fictional-series origin metadata.

**Live configuration rule:** a rendered team page must prefer the current profile `config.yaml` (or an equivalent live `hermes profile show` result) at render time, with the manifest map only as a fallback. Never leave a stale model snapshot in the page after profiles change. Display the full identifier without abbreviation. Cron mission cards may use their explicit `model_snapshot`, which is separate from crew profile models.

### Team Status Reconciliation

The Team page and Office API must derive status from live execution state, not historical rows:

- Main/default status comes from an unexpired `state.db` session-turn lease for the default profile, excluding cron sessions.
- Named specialists use the highest-priority unfinished Kanban task. Query only `running`, `blocked`, `ready`, `todo`, `failed`, `crashed`, and `timed_out`; completed/done cards must not occupy a crew slot.
- Normalize `failed`, `crashed`, and `timed_out` to `blocked` for display and zone mapping.
- Iterate the configured roster after building the task map so every crew member appears exactly once; missing work means `idle` in Crew Quarters.
- Keep the Team page's counts, cards, and Office page's visual zones on the same normalized state contract.

For the tested implementation and restart/verification recipe, see `references/live-team-roster.md`.

### Design Aesthetic

Wesley prefers themed, stylized interfaces over generic ones. Current theme: **Victorian Punk pirate ship** with:
- Burnt orange, rust red, charcoal black, bone white, electric-yellow accents
- Ship hull background with wood plank lines and rust patches
- Porthole-style circular avatars with profile images
- Ship compartments with rivets, angular clip-paths, heavy borders
- Chain-link decorations, pipe/railing edge effects
- Full crew manifest showing roles and exact current model identifiers under each character name
- Layout reserves the manifest column: move right-side rooms/stations left or use a responsive content boundary so the legend never blocks interactive zones

### Static Image Serving

The server handles `/static/<filename>` routes to serve profile images:

```python
elif parsed.path.startswith("/static/"):
    filename = parsed.path.replace("/static/", "", 1)
    static_dir = Path(__file__).resolve().parent / "static"
    file_path = static_dir / filename
    if file_path.exists() and file_path.is_file():
        content_type = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp",
        }.get(file_path.suffix.lower(), "application/octet-stream")
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
```

Images are stored in `desktop-plugins/command-center/static/` and copied there from user uploads.

### Adding a New Agent

1. Verify or create the matching Hermes profile; do not make a dashboard-only persona look callable.
2. Read the profile's exact configured model with `hermes profile show <name>`.
3. Add entries to `AGENT_PERSONAS`, `AGENT_MODELS`, `AGENT_ROLES`, `AGENT_COLORS`, `AGENT_INITIALS`, `AGENT_IMAGES`, and `DESKS` in `office_view.py`. If this is the default/main profile, also add `AGENT_FALLBACKS`.
4. Add the profile to the API's synthetic idle crew roster so it appears in Crew Quarters when unassigned.
5. Copy the profile image to `static/`.
6. Update `status_to_zone()` and the frontend polling map together; server and browser mappings must agree. Include `'main'` in the desk-active check array.
7. Compile the Python files, kill the old server, delete `__pycache__`, restart, and verify the rendered HTML contains one model label per crew member.

### Team Tab

Add a `/team` route to `command_center_server.py` and a `render_team()` function to `office_view.py`. The team page lists every crew member with name, role, model, fallback model, current task status, and (for cron jobs) schedule/runtime. Data comes from `/api/subagents` plus a new `/api/team` endpoint that merges cron job info from `~/.hermes/cron/jobs.json`. Match the existing Victorian Punk header/nav style and include a stats bar showing active/idle/blocked counts.

### Page Split: Visual vs Info

Wesley prefers a strict separation:

- **Office (`/office`)** = pure visual. Ship floor + avatars only. No legend, no stats bar, no room labels, no text. Just crew members moving around the ship.
- **Team (`/team`)** = comprehensive info dashboard. Stats bar + Active Operations cards + Crew Roster grid + Scheduled Missions grid, all in one scrollable view with task descriptions, models, and run times.

When asked to "update the command center" or "what else has to be completed," default to this split: office shows status visually, team shows everything else as data.

### Team Page Layout Pattern

The `/team` route uses a card-grid layout:

1. **Stats bar** (top) — Active/Waiting/Blocked/Idle counts
2. **Active Operations** — Horizontal cards for running/blocked agents with avatar, role, task title, model, status pill
3. **Crew Roster** — Compact grid of idle/background agents with avatar, name, role, model, status pill
4. **Scheduled Missions** — Cards for each cron job with name, description, schedule badge, model, next/last run times

All sections use CSS Grid with `auto-fill` + `minmax()` for responsive wrapping. Sections only render when they have content.

### Character Behavior System

The office view includes a character behavior layer that makes crew members move and act like inhabitants rather than icons following fixed routes. This system includes:

- **Spatial system**: 100×100 percentage-based ship space with waypoints for each zone and points of interest (POI) for wandering.
- **Movement**: CSS transitions on `left/top` with configurable duration based on character speed. Smooth gliding between coordinates.
- **States**: Independent operational states (from API) map to visual behavior states (work, travel, wander, sleep). Characters wander to random POIs after ~10s idle, sleep after ~30s idle.
- **Awareness**: Characters detect nearby characters within ~15% radius and apply repulsive force to maintain personal space. Working/sleeping characters are excluded from awareness.
- **Wander chaining**: Characters pause at a POI for 5-10s before wandering again, creating natural-looking movement patterns.
- **Animation**: `pop-in` keyframe on creation, `working-pulse` when running, `sleeping-breathe` when asleep. `requestAnimationFrame` tick loop updates positions and throttles DOM updates to ~10fps.

See `references/character-behavior.md` for the full specification and implementation pattern.

### Inhabited World Vision

The long-term design extends the behavior system into a fully inhabited world where bots have persistent identities, plain-language activities, social interactions, memory, and meaningful state transitions. The 12-point plan covers: identity, activities, home view, autonomous behaviors, transitions, attention, social behavior, thought snippets, rest forms, memory, missions in the world, and interaction panels.

The highest-impact first version: named characters + home stations + specific activity labels + four behaviors (working, travelling, interacting, sleeping) connected to real missions.

See `references/inhabited-world-plan.md` for the full design.

### Inhabited World Implementation Status

The following phases have been implemented and verified (syntax-checked, server running):

| Phase | Status | What's in |
|-------|--------|-----------|
| 1 — Identity & Activity | ✅ Done | `AGENT_TAGLINES`, `AGENT_HABITS`, `activity_label()` in Python + JS. Each bot shows **name** + **present-tense activity** above avatar |
| 2 — State Machine | ✅ Done | `TRANSITIONS` graph (10 states), `transitionTo()`, `onArriveAtStation()` with 0.8–1.5s arrival pause, `TRAVEL_DURATION_MS = 2500` |
| 3 — Personality | ✅ Done | `TRAITS` (7 traits), `BOT_PERSONALITY` (2-3 per bot), `IDLE_PREFERENCES`, `pickIdleBehavior()` with trait-weighted selection |
| 4 — Autonomous Behaviors | ✅ Done | `autonomousTick()` — wander after 10s, rest after 30s, sleep after 45s, helpful bots visit stuck bots, social bots join celebrations |
| 5 — Attention & Facing | ✅ Done | `updateAttention()` — bots face movement direction or target bot (±30° head turn) |
| 6 — Reactions | ✅ Done | `onTaskComplete()` (celebrate bounce + propagate), `onTaskBlocked()` (shake + phrase) |
| 7 — Speech Bubbles | ✅ Done | `showSpeechBubble()` with pop-in animation, 4s auto-dismiss, `PHRASES` (4 contexts × 2-3 per bot) |
| 8 — Memory | ✅ Done | `addMemory()`, `getRecentMemories()`, `timeAgo()` — 50-entry capped log per bot |
| 11 — Idle Variety CSS | ✅ Done | 7 `@keyframes` animations: reading-bob, maintaining-tap, wandering-bob, sleeping-breathe, look-around, celebrate-bounce, social-wave, shake |

Remaining phases (not yet implemented): Phase 9 (mission objects as physical items), Phase 10 (click-to-open detail panel), Phase 6 full (social handoff chains — partial via reactive behaviors).

### Inhabited World Patterns

The following patterns emerged from implementing the 12-point inhabited world plan. Each is a class-level technique applicable to any character behavior system.

See `references/character-behavior.md` for the full specification including autonomous behaviors, social interactions, memory, idle variety CSS, and state class management.

#### f-string JS Embedding Rules

When embedding JavaScript inside Python f-strings for HTML generation:

1. **Double all standalone braces**: `{` → `{{`, `}` → `}}`
2. **Template variables stay single**: `{json.dumps(AGENT_COLORS)}`
3. **Use `var` not `const`/`let`**: `var x = 1` not `const x = 1`
4. **Use `.indexOf() !== -1` not `.includes()`**: `arr.indexOf('x') !== -1`
5. **Use `function() {}` not arrow functions**: `function() {{ ... }}` not `() => {{ ... }}`
6. **No template literals**: `'text ' + var` not `` `text ${var}` ``
7. **No nested dicts in expressions**: Build dicts first, pass to `json.dumps()`

#### State Machine Pattern

```javascript
const TRANSITIONS = {{
  traveling:   ['working', 'resting', 'wandering', 'socializing'],
  working:     ['resting', 'socializing', 'maintaining', 'traveling'],
  resting:     ['wandering', 'socializing', 'working', 'sleeping'],
  wandering:   ['socializing', 'resting', 'traveling', 'reading', 'working'],
  socializing: ['traveling', 'working', 'wandering', 'resting'],
  reading:     ['working', 'resting', 'socializing'],
  maintaining: ['working', 'resting'],
  sleeping:    ['resting', 'working'],
  arriving:    ['working'],
}};

function canTransition(from, to) {{
  var allowed = TRANSITIONS[from] || [];
  return allowed.indexOf(to) !== -1;
}}

function transitionTo(a, newState, title) {{
  var c = ensureChar(a);
  if (c.state === newState) return;
  if (!canTransition(c.state, newState) && c.state !== 'idle') {{
    console.warn('Invalid transition: ' + c.state + ' -> ' + newState);
  }}
  c.state = newState;
  // State entry hooks set behavior, reset timers
  if (newState === 'working') {{ c.behavior = 'work'; c.idleTime = 0; c.workingSince = Date.now(); }}
  else if (newState === 'resting') {{ c.behavior = 'rest'; c.sleepTime = 0; }}
  else if (newState === 'sleeping') {{ c.behavior = 'sleep'; }}
  else if (newState === 'wandering') {{ c.behavior = 'wander'; }}
  else if (newState === 'socializing') {{ c.behavior = 'social'; }}
  else if (newState === 'reading') {{ c.behavior = 'read'; }}
  else if (newState === 'maintaining') {{ c.behavior = 'maintain'; }}
}}

function onArriveAtStation(a, title) {{
  transitionTo(a, 'arriving');
  setTimeout(function() {{
    var c = ensureChar(a);
    if (c.state === 'arriving') transitionTo(a, 'working', title);
  }}, 800 + Math.random() * 700);
}}
```

#### Personality System

```javascript
var TRAITS = {{
  meticulous:  {{ readingChance: 0.4, wanderFreq: 0.2 }},
  social:      {{ socialChance: 0.6, wanderFreq: 0.5 }},
  focused:     {{ workDuration: 30000, interruptResist: 0.7 }},
  curious:     {{ wanderFreq: 0.8, readingChance: 0.5 }},
  helpful:     {{ assistChance: 0.6 }},
  methodical:  {{ maintainFreq: 0.4, readingChance: 0.3 }},
  energetic:   {{ speedMult: 1.5, restDuration: 5000 }},
}};

var BOT_PERSONALITY = {{
  Ditto:               ['helpful', 'social', 'focused'],
  Laboon:              ['curious', 'methodical'],
  Calcifer:            ['meticulous', 'methodical'],
  Heen:                ['focused', 'methodical'],
  'Tony Tony Chopper': ['helpful', 'social', 'energetic'],
  Pakkun:              ['methodical', 'helpful'],
  Gamatasu:            ['curious', 'meticulous'],
  speed:              ['social', 'energetic'],
}};

var IDLE_PREFERENCES = {{
  Ditto:               {{ primary: 'socializing', secondary: 'reading' }},
  Laboon:              {{ primary: 'wandering',   secondary: 'reading' }},
  Calcifer:            {{ primary: 'reading',     secondary: 'maintaining' }},
  Heen:                {{ primary: 'maintaining', secondary: 'resting' }},
  'Tony Tony Chopper': {{ primary: 'socializing', secondary: 'wandering' }},
  Pakkun:              {{ primary: 'maintaining', secondary: 'reading' }},
  Gamatasu:            {{ primary: 'reading',     secondary: 'wandering' }},
  speed:              {{ primary: 'socializing', secondary: 'wandering' }},
}};

function pickIdleBehavior(botId) {{
  var traits = BOT_PERSONALITY[botId] || [];
  var prefs = IDLE_PREFERENCES[botId];
  var roll = Math.random();
  if (traits.indexOf('curious') !== -1 && roll < TRAITS.curious.wanderFreq * 0.5) return 'wandering';
  if (traits.indexOf('meticulous') !== -1 && roll < TRAITS.meticulous.readingChance) return 'reading';
  if (traits.indexOf('social') !== -1 && roll < TRAITS.social.socialChance * 0.5) return 'socializing';
  if (traits.indexOf('methodical') !== -1 && roll < TRAITS.methodical.maintainFreq) return 'maintaining';
  if (prefs && roll < 0.6) return prefs.primary;
  if (prefs && roll < 0.85) return prefs.secondary;
  var r = Math.random();
  if (r < 0.35) return 'resting';
  if (r < 0.55) return 'wandering';
  if (r < 0.70) return 'reading';
  if (r < 0.80) return 'maintaining';
  if (r < 0.90) return 'socializing';
  return 'sleeping';
}}
```

#### Speech Bubble System

```javascript
function showSpeechBubble(botId, text) {{
  var group = document.getElementById('group-' + botId);
  if (!group) return;
  var existing = group.querySelector('.speech-bubble');
  if (existing) existing.remove();
  var bubble = document.createElement('div');
  bubble.className = 'speech-bubble';
  bubble.textContent = text;
  group.appendChild(bubble);
  setTimeout(function() {{
    bubble.classList.add('fade-out');
    setTimeout(function() {{ bubble.remove(); }}, 500);
  }}, 4000);
}}

var PHRASES = {{
  Ditto: {{
    working: ["Reviewing before I approve this.", "Let me check the details."],
    blocked: ["This needs a closer look.", "Something doesn't sit right."],
    celebrating: ["Well crew, we did it!", "Smooth sailing, everyone."],
    idle: ["What's next on the horizon?", "Standing by for orders, Captain."]
  }},
  // ... similar for all 8 bots
}};

function pickPhrase(botId, context) {{
  var pool = PHRASES[botId] && PHRASES[botId][context];
  if (!pool || pool.length === 0) return '';
  return pool[Math.floor(Math.random() * pool.length)];
}}
```

#### Memory System

```javascript
var memories = {{}};

function addMemory(botId, entry) {{
  if (!memories[botId]) memories[botId] = [];
  memories[botId].unshift({{
    id: Date.now() + '-' + Math.random().toString(36).slice(2, 8),
    timestamp: Date.now(),
    type: entry.type,
    summary: entry.summary,
    relatedBots: entry.relatedBots || [],
    relatedMission: entry.relatedMission || null,
    location: chars[botId] ? chars[botId].zone : 'unknown',
    significance: entry.significance || 0.5,
  }});
  if (memories[botId].length > 50) memories[botId].pop();
}}

function timeAgo(ts) {{
  var secs = Math.floor((Date.now() - ts) / 1000);
  if (secs < 60) return 'just now';
  if (secs < 3600) return Math.floor(secs / 60) + 'm ago';
  if (secs < 86400) return Math.floor(secs / 3600) + 'h ago';
  return Math.floor(secs / 86400) + 'd ago';
}}
```

#### Attention & Facing

```javascript
function updateAttention(botId) {{
  var bot = chars[botId];
  if (!bot || !bot.el) return;
  var target = bot.attentionTarget;
  var angle = 0;
  if (target) {{
    var targetBot = chars[target];
    if (targetBot) angle = Math.atan2(targetBot.y - bot.y, targetBot.x - bot.x);
  }} else {{
    angle = Math.atan2(bot.targetY - bot.y, bot.targetX - bot.x);
  }}
  var av = bot.el.querySelector('.agent-avatar');
  if (av) {{
    var deg = Math.max(-30, Math.min(30, angle * (180 / Math.PI)));
    av.style.transform = 'rotate(' + deg + 'deg)';
    av.style.transition = 'transform 0.3s ease-out';
  }}
}}
```

#### Autonomous Tick

```javascript
function autonomousTick(dt) {{
  for (var a in chars) {{
    var c = chars[a];
    if (!c.el || c.state === 'working' || c.state === 'traveling') continue;
    c.idleTime += dt;
    if (c.idleTime > 10 && c.state === 'resting') {{
      transitionTo(a, 'wandering');
      wander(a);
      showSpeechBubble(a, pickPhrase(PERSONAS[a], 'idle'));
    }}
    if (c.idleTime > 30 && c.state === 'wandering') {{
      transitionTo(a, 'resting');
      goToStation(a, 'idle');
    }}
    if (c.idleTime > 45 && c.state === 'resting') {{
      transitionTo(a, 'sleeping');
      showSpeechBubble(a, '💤');
    }}
    // Reactive: helpful bots visit stuck bots
    if (BOT_PERSONALITY[PERSONAS[a]] && BOT_PERSONALITY[PERSONAS[a]].indexOf('helpful') !== -1) {{
      var stuckBot = findBlockedBot();
      if (stuckBot && c.state !== 'socializing' && c.state !== 'traveling') {{
        transitionTo(a, 'traveling');
        moveChar(a, stuckBot.x, stuckBot.y);
        setTimeout(function() {{
          transitionTo(a, 'socializing');
          showSpeechBubble(a, pickPhrase(PERSONAS[a], 'working'));
        }}, TRAVEL_DURATION_MS);
      }}
    }}
  }}
}}
```

#### Idle Variety CSS

```css
.state-reading .agent-avatar {{ animation: reading-bob 2.5s ease-in-out infinite; }}
.state-maintaining .agent-avatar {{ animation: maintaining-tap 1.2s ease-in-out infinite; }}
.state-wandering .agent-avatar {{ animation: wandering-bob 3s ease-in-out infinite; }}
.state-sleeping .agent-avatar {{ animation: sleeping-breathe 4s ease-in-out infinite; filter: brightness(0.7); }}
.state-arriving .agent-avatar {{ animation: look-around 1s ease-in-out; }}
.state-celebrating .agent-avatar {{ animation: celebrate-bounce 0.6s ease-out; }}
.state-socializing .agent-avatar {{ animation: social-wave 1.5s ease-in-out infinite; }}
.shaking {{ animation: shake 0.5s ease-in-out infinite; }}
```

See `references/character-behavior.md` for the full specification.
