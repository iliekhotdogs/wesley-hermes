# Character Behavior System — Implementation Reference

## Overview

The office view character behavior system makes crew members act like inhabitants of the ship rather than icons that teleport between fixed zones. Real Hermes events determine operational truth; the visual system translates that into movement, awareness, behavior, personality, and speech.

## Implementation Architecture

The actual implementation uses CSS transitions for movement (not canvas or A*), a simple distance-based awareness system, and a state machine driven by idle timers. This keeps the JS lightweight and maintainable.

```
poll() → updateChar(assignee, status, title)
  → transitionTo() → goToStation() or wander() → moveChar(targetX, targetY)
    → CSS transition on left/top
    → onArriveAtStation() after TRAVEL_DURATION_MS
      → brief pause → transitionTo('working')

requestAnimationFrame(tick)
  → applyAwareness() → adjust targetX/targetY for nearby chars
  → handleWanderPause() → chain wander moves after pausing at POI
```

## Spatial System

The ship is a 100×100 percentage-based space:

```javascript
const WAYPOINTS = {
  'main': {x:50,y:30}, 'multimodal': {x:15,y:52}, 'coder-a': {x:38,y:52},
  'helm': {x:50,y:8}, 'war-room': {x:15,y:30}, 'crew-quarters': {x:50,y:82},
  // ... zones from ROOMS and DESKS
};
const POI = [
  {x:25,y:25}, {x:75,y:25}, {x:50,y:50}, {x:20,y:80},
  {x:80,y:80}, {x:35,y:40}, {x:65,y:40}, {x:50,y:70},
];
```

## Movement

Uses CSS transitions on `left/top` properties with configurable duration:

```javascript
function moveChar(a, tx, ty) {
  const c = ensureChar(a);
  c.targetX = tx; c.targetY = ty;
  const group = getOrCreateGroup(a);
  const dur = (2.5 / c.speed);
  group.style.transition = 'left ' + dur + 's ease-in-out, top ' + dur + 's ease-in-out';
  group.style.left = tx + '%';
  group.style.top = ty + '%';
}
```

Each character has a `speed` (0.8–1.2) that affects transition duration. Slower characters take longer to cross the ship.

## State Machine (Req #5 — Meaningful Transitions)

### State Transition Graph

The bot lifecycle follows a directed graph. Not every state can transition to every other — this prevents jarring instant jumps:

```javascript
const TRANSITIONS = {
  traveling:   ['working', 'resting', 'wandering', 'socializing'],
  working:     ['resting', 'socializing', 'maintaining', 'traveling'],
  resting:     ['wandering', 'socializing', 'working', 'sleeping'],
  wandering:   ['socializing', 'resting', 'traveling', 'reading', 'working'],
  socializing: ['traveling', 'working', 'wandering', 'resting'],
  reading:     ['working', 'resting', 'socializing'],
  maintaining: ['working', 'resting'],
  sleeping:    ['resting', 'working'],
  arriving:    ['working'],  // brief intermediate state
};
```

### Transition Rules

```
Notices assignment → traveling → arrives at station → brief pause → working
                                                    ↓
                              encounters difficulty → resting (blocked)
                                                    ↓
                              task completes → resting → wandering (10s idle)
                                                    ↓
                                               → sleeping (45s idle)
```

### Key Functions

```javascript
// Attempt a transition; warns on invalid but allows it (recovery > stuck)
function canTransition(from, to) {
  var allowed = TRANSITIONS[from] || [];
  return allowed.indexOf(to) !== -1;
}

// Transition with lifecycle hooks (sets behavior, resets timers)
function transitionTo(a, newState, title) { ... }

// Called after CSS travel completes: brief pause → working
function onArriveAtStation(a, title) {
  transitionTo(a, 'arriving');
  setTimeout(function() {
    if (c.state === 'arriving') transitionTo(a, 'working', title);
  }, 800 + Math.random() * 700);  // 0.8–1.5s arrival pause
}
```

### Operational States (from API) → Visual States

| Kanban Status | Visual State Sequence |
|---------------|----------------------|
| `running` | traveling → arriving → working |
| `blocked` | resting (at war room) |
| `ready`/`todo` | traveling → resting |
| `idle`/`done` | resting → wandering (10s) → sleeping (45s) |

## Personality System (Req #3, #9)

### Trait Definitions

```javascript
const TRAITS = {
  meticulous:  { readingChance: 0.4, verifyDelay: 1500, wanderFreq: 0.2 },
  social:      { socialChance: 0.6, socialDuration: 8000, wanderFreq: 0.5 },
  focused:     { workDuration: 30000, interruptResist: 0.7 },
  curious:     { wanderFreq: 0.8, readingChance: 0.5 },
  helpful:     { assistChance: 0.6 },
  methodical:  { maintainFreq: 0.4, readingChance: 0.3 },
  energetic:   { speedMult: 1.5, restDuration: 5000 },
};
```

### Per-Bot Assignments

```javascript
const BOT_PERSONALITY = {
  Ditto:               ['helpful', 'social', 'focused'],
  Laboon:              ['curious', 'methodical'],
  Calcifer:            ['meticulous', 'methodical'],
  Heen:                ['focused', 'methodical'],
  'Tony Tony Chopper': ['helpful', 'social', 'energetic'],
  Pakkun:              ['methodical', 'helpful'],
  Gamatasu:            ['curious', 'meticulous'],
  Totoro:              ['social', 'energetic'],
};
```

### Idle Behavior Selection

```javascript
function pickIdleBehavior(botId) {
  var traits = BOT_PERSONALITY[botId] || [];
  var prefs = IDLE_PREFERENCES[botId];
  var roll = Math.random();
  
  // Trait-weighted choices
  if (traits.indexOf('curious') !== -1 && roll < TRAITS.curious.wanderFreq * 0.5)
    return 'wandering';
  if (traits.indexOf('meticulous') !== -1 && roll < TRAITS.meticulous.readingChance)
    return 'reading';
  if (traits.indexOf('social') !== -1 && roll < TRAITS.social.socialChance * 0.5)
    return 'socializing';
  if (traits.indexOf('methodical') !== -1 && roll < TRAITS.methodical.maintainFreq)
    return 'maintaining';
  
  // Default: preferred idle behavior
  if (prefs && roll < 0.6) return prefs.primary;
  if (prefs && roll < 0.85) return prefs.secondary;
  
  // Fallback distribution
  var r = Math.random();
  if (r < 0.35) return 'resting';
  if (r < 0.55) return 'wandering';
  if (r < 0.70) return 'reading';
  if (r < 0.80) return 'maintaining';
  if (r < 0.90) return 'socializing';
  return 'sleeping';
}
```

### Per-Bot Idle Preferences (Req #9 — Rest Has Multiple Forms)

```javascript
const IDLE_PREFERENCES = {
  Ditto:               { primary: 'socializing', secondary: 'reading' },
  Laboon:              { primary: 'wandering',   secondary: 'reading' },
  Calcifer:            { primary: 'reading',     secondary: 'maintaining' },
  Heen:                { primary: 'maintaining', secondary: 'resting' },
  'Tony Tony Chopper': { primary: 'socializing', secondary: 'wandering' },
  Pakkun:              { primary: 'maintaining', secondary: 'reading' },
  Gamatasu:            { primary: 'reading',     secondary: 'wandering' },
  Totoro:              { primary: 'socializing', secondary: 'wandering' },
};
```

## Speech Bubble System (Req #8 — Thought, Speech, Activity Snippets)

### Function

```javascript
function showSpeechBubble(botId, text) {
  var group = document.getElementById('group-' + botId);
  if (!group) return;
  
  // Remove existing bubble (max one per bot)
  var existing = group.querySelector('.speech-bubble');
  if (existing) existing.remove();
  
  var bubble = document.createElement('div');
  bubble.className = 'speech-bubble';
  bubble.textContent = text;
  group.appendChild(bubble);
  
  // Auto-dismiss after 4s with fade-out
  setTimeout(function() {
    bubble.classList.add('fade-out');
    setTimeout(function() { bubble.remove(); }, 500);
  }, 4000);
}
```

### Per-Bot Phrase Pools

Each bot has 4 contexts (working, blocked, celebrating, idle) with 2-3 phrases each:

```javascript
var PHRASES = {
  Ditto: {
    working: ["Reviewing before I approve this.", "Let me check the details.", "Final say is mine to give."],
    blocked: ["This needs a closer look.", "Something doesn't sit right."],
    celebrating: ["Well crew, we did it!", "Smooth sailing, everyone."],
    idle: ["What's next on the horizon?", "Standing by for orders, Captain."]
  },
  Calcifer: {
    working: ["I'll catch what others miss.", "Every ember gets inspected.", "Nothing escapes my gaze."],
    blocked: ["This code has sparks I don't like.", "I refuse to let this pass."],
    celebrating: ["Not a single bug survived.", "Flawless, as expected."],
    idle: ["Let me check the logs.", "I'll verify the last build just in case."]
  },
  // ... similar for Heen, Tony Tony Chopper, Laboon, Pakkun, Gamatasu, Totoro
};

function pickPhrase(botId, context) {
  var pool = PHRASES[botId] && PHRASES[botId][context];
  if (!pool || pool.length === 0) return '';
  return pool[Math.floor(Math.random() * pool.length)];
}
```

### CSS

```css
.speech-bubble {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(37, 37, 37, 0.95);
  border: 2px solid var(--dark-gray);
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 10px;
  color: var(--bone-white);
  white-space: nowrap;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.5);
  animation: pop-in 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  z-index: 10;
}
.speech-bubble::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: var(--dark-gray);
}
.speech-bubble.fade-out {
  animation: fade-out 0.5s ease forwards;
}
```

## Plain-Language Activity Labels (Req #2)

### Python Function

```python
def activity_label(status: str, title: str, assignee: str | None) -> str:
    title_lower = title.lower() if title else ""
    if status == "running":
        if any(kw in title_lower for kw in ("review", "check", "audit", "inspect")):
            return "Reviewing the latest build"
        if any(kw in title_lower for kw in ("build", "create", "implement", "write", "develop")):
            return "Building something new"
        if any(kw in title_lower for kw in ("research", "search", "find", "investigate")):
            return "Comparing sources"
        if any(kw in title_lower for kw in ("fix", "repair", "patch", "heal")):
            return "Mending what is broken"
        if any(kw in title_lower for kw in ("watch", "monitor", "observe")):
            return "Keeping watch"
        return "Working on a task"
    if status == "blocked":
        return "Stuck and thinking"
    if status in ("ready", "todo"):
        return "Waiting for assignment"
    if status in ("done", "completed"):
        return "Just finished a task"
    return "Standing by"
```

### JS Equivalent (for live updates)

```javascript
function activityLabel(status, title) {
  var t = (title || '').toLowerCase();
  if (status === 'running') {
    if (t.indexOf('review') !== -1 || t.indexOf('check') !== -1 || t.indexOf('audit') !== -1 || t.indexOf('inspect') !== -1) return 'Reviewing the latest build';
    if (t.indexOf('build') !== -1 || t.indexOf('create') !== -1 || t.indexOf('implement') !== -1 || t.indexOf('write') !== -1 || t.indexOf('develop') !== -1) return 'Building something new';
    if (t.indexOf('research') !== -1 || t.indexOf('search') !== -1 || t.indexOf('find') !== -1 || t.indexOf('investigate') !== -1) return 'Comparing sources';
    if (t.indexOf('fix') !== -1 || t.indexOf('repair') !== -1 || t.indexOf('patch') !== -1 || t.indexOf('heal') !== -1) return 'Mending what is broken';
    if (t.indexOf('watch') !== -1 || t.indexOf('monitor') !== -1 || t.indexOf('observe') !== -1) return 'Keeping watch';
    return 'Working on a task';
  }
  if (status === 'blocked') return 'Stuck and thinking';
  if (status === 'ready' || status === 'todo') return 'Waiting for assignment';
  if (status === 'done' || status === 'completed') return 'Just finished a task';
  return 'Standing by';
}
```

## Persistent Identity (Req #1)

### New Data Dicts

```python
AGENT_TAGLINES = {
    "main": "Keeps the final say and steers the ship",
    "multimodal": "Watches horizons others cannot see",
    "critic": "Catches bugs before they escape",
    "coder-a": "Builds and maintains the codebase",
    "doctor": "Patches wounds and mends broken systems",
    "utility": "Turns long documents into useful answers",
    "researcher": "Charts unknown waters and maps the truth",
    "coder-b": "Tinkers with experiments in the workshop",
}

AGENT_HABITS = {
    "main": "Reviews everything twice before approving",
    "multimodal": "Looks at pictures when words fail",
    "critic": "Refuses to let flawed code pass",
    "coder-a": "Prefers building over planning",
    "doctor": "Diagnoses before treating",
    "utility": "Summarizes first, details later",
    "researcher": "Compares at least three sources",
    "coder-b": "Safely breaks things to learn",
}
```

### DOM Elements Added to Each Group

```javascript
// Persona name (bold, colored by bot)
var nameTag = document.createElement('div');
nameTag.className = 'persona-name';
nameTag.textContent = PERSONAS[a];
group.appendChild(nameTag);

// Activity label (italic, muted)
var activityEl = document.createElement('div');
activityEl.className = 'activity-label';
activityEl.textContent = activityLabel('idle', '');
group.appendChild(activityEl);
```

### CSS

```css
.persona-name {
  font-size: 11px;
  font-weight: 800;
  margin-top: 2px;
  letter-spacing: 0.04em;
  text-align: center;
}
.activity-label {
  font-size: 9px;
  color: var(--metal-gray);
  font-style: italic;
  margin-top: 1px;
  max-width: 90px;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

## Awareness

Simple distance-based repulsion (no A* or pathfinding):

```javascript
function applyAwareness() {
  for (const [a1, c1] of chars) {
    if (c1.behavior === 'sleep' || c1.behavior === 'work') continue;
    c1.speed = Math.min(1.2, c1.speed * 1.02); // recovery
    for (const [a2, c2] of chars) {
      if (c2.behavior === 'sleep' || c2.behavior === 'work') continue;
      const dist = Math.sqrt((c1.x-c2.x)**2 + (c1.y-c2.y)**2);
      if (dist < c1.awareness && dist > 0.1) {
        const force = (c1.awareness - dist) / c1.awareness;
        const pushX = (dx / dist) * force * 0.5;
        const pushY = (dy / dist) * force * 0.5;
        c1.targetX += pushX; c1.targetY += pushY;
        c2.targetX -= pushX; c2.targetY -= pushY;
        c1.speed *= 0.95; c2.speed *= 0.95; // slow when crowded
      }
    }
  }
}
```

Working and sleeping characters are excluded from awareness — they don't push or get pushed.

## Wander Chaining

Characters pause at a POI before wandering again:

```javascript
function handleWanderPause(a, dt) {
  const c = ensureChar(a);
  if (c.behavior !== 'wander') return;
  c.wanderPause -= dt;
  if (c.wanderPause <= 0 && c.status !== 'running') {
    if (c.idleTime > 30) c.behavior = 'sleep';
    else wander(a);
  }
}
```

`wanderPause` is set to 5–10s when arriving at a POI. This creates natural-looking movement: move → pause → move → pause → sleep.

## Animation Keyframes

```css
@keyframes pop-in {
  0% { transform: scale(0); opacity: 0; }
  60% { transform: scale(1.15); }
  100% { transform: scale(1); opacity: 1; }
}
@keyframes working-pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); }
  50% { transform: translate(-50%, -50%) scale(1.05); }
}
@keyframes sleeping-breathe {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.7; }
  50% { transform: translate(-50%, -50%) scale(0.95); opacity: 0.9; }
}
```

- `pop-in` — triggered on avatar creation
- `working-pulse` — added when status is 'running'
- `sleeping-breathe` — added when behavior is 'sleep'

## DOM Structure

Each character is a single positioned group containing avatar + name + activity + label + task:

```html
<div id="group-main" class="agent-group status-running"
     style="position:absolute; left:50%; top:30%; transform:translate(-50%,-50%);">
  <div class="agent-avatar large working">
    <img src="/static/ditto.webp" alt="main" />
  </div>
  <div class="persona-name">Ditto</div>
  <div class="activity-label">Reviewing the latest build</div>
  <div class="status-label">RUNNING</div>
  <div class="task-title">Central dispatch</div>
</div>
```

The group itself is positioned, so child elements (name, activity, label, task) don't need absolute positioning. This avoids the re-parenting bug where moving an avatar into a non-positioned container breaks `left/top` percentage resolution.

## Tick Loop

```javascript
let lastTick = 0, lastApply = 0;
function tick(now) {
  const dt = lastTick ? (now - lastTick) / 1000 : 0;
  lastTick = now;
  for (const [a, c] of chars) {
    c.x = parseFloat(c.el.style.left) || c.targetX;
    c.y = parseFloat(c.el.style.top) || c.targetY;
    handleWanderPause(a, dt);
  }
  if (now - lastApply > 100) { // ~10fps
    lastApply = now;
    applyAwareness();
    for (const [a, c] of chars) {
      if (Math.abs(c.x - c.targetX) > 0.3 || Math.abs(c.y - c.targetY) > 0.3) {
        const dur = (2.5 / c.speed);
        c.el.style.transition = 'left ' + dur + 's ease-in-out, top ' + dur + 's ease-in-out';
        c.el.style.left = c.targetX + '%';
        c.el.style.top = c.targetY + '%';
      }
    }
  }
  requestAnimationFrame(tick);
}
```

## Performance Notes

- Awareness runs at ~10fps (throttled to every 100ms)
- DOM updates only happen when position delta > 0.3%
- Working/sleeping characters skip awareness calculations
- All movement is CSS-transition-based — no per-frame DOM manipulation
- Speech bubbles auto-remove after 4s to prevent DOM bloat

## Integration with Existing System

The behavior layer sits between the API poll and the DOM render:

```javascript
async function poll() {
  const data = await fetch('/api/subagents').then(r => r.json());
  const workers = [...data.active, ...data.recent];
  workers.forEach(w => updateChar(w.assignee, w.status, w.title));
}
```

## Extended Behavior Functions

### Autonomous Tick (Req #4)

Runs every animation frame to drive idle behaviors:

```javascript
function autonomousTick(dt) {
  for (var a in chars) {
    var c = chars[a];
    if (!c.el || c.state === 'working' || c.state === 'traveling') continue;
    c.idleTime += dt;
    if (c.idleTime > 10 && c.state === 'resting' && c.behavior !== 'wander') {
      transitionTo(a, 'wandering');
      wander(a);
      showSpeechBubble(a, pickPhrase(PERSONAS[a], 'idle'));
    }
    if (c.idleTime > 30 && c.state === 'wandering') {
      transitionTo(a, 'resting');
      goToStation(a, 'idle');
    }
    if (c.idleTime > 45 && c.state === 'resting') {
      transitionTo(a, 'sleeping');
      showSpeechBubble(a, '💤');
    }
    // Reactive: helpful bots visit stuck bots
    if (BOT_PERSONALITY[PERSONAS[a]] && BOT_PERSONALITY[PERSONAS[a]].indexOf('helpful') !== -1) {
      var stuckBot = findBlockedBot();
      if (stuckBot && c.state !== 'socializing' && c.state !== 'traveling') {
        transitionTo(a, 'traveling');
        moveChar(a, stuckBot.x, stuckBot.y);
        setTimeout(function() {
          transitionTo(a, 'socializing');
          showSpeechBubble(a, pickPhrase(PERSONAS[a], 'working'));
        }, TRAVEL_DURATION_MS);
      }
    }
    // Reactive: social bots join celebrations
    if (BOT_PERSONALITY[PERSONAS[a]] && BOT_PERSONALITY[PERSONAS[a]].indexOf('social') !== -1) {
      var celebrating = findCelebratingBot();
      if (celebrating && c.state !== 'socializing' && c.state !== 'traveling') {
        transitionTo(a, 'traveling');
        moveChar(a, celebrating.x + 5, celebrating.y + 5);
        setTimeout(function() {
          transitionTo(a, 'socializing');
          showSpeechBubble(a, pickPhrase(PERSONAS[a], 'celebrating'));
        }, TRAVEL_DURATION_MS);
      }
    }
  }
}
```

### Task Completion Reaction (Req #6)

```javascript
function onTaskComplete(botId) {
  var bot = chars[botId];
  if (!bot) return;
  transitionTo(botId, 'celebrating');
  showSpeechBubble(botId, pickPhrase(PERSONAS[botId], 'celebrating'));
  var group = document.getElementById('group-' + botId);
  if (group) {
    group.style.animation = 'none';
    group.offsetHeight; // reflow
    group.style.animation = 'celebrate-bounce 0.6s ease-out';
  }
  propagateCelebration(botId);
  setTimeout(function() { transitionTo(botId, 'resting'); }, 2000);
}

function onTaskBlocked(botId) {
  var bot = chars[botId];
  if (!bot) return;
  transitionTo(botId, 'resting');
  showSpeechBubble(botId, pickPhrase(PERSONAS[botId], 'blocked'));
  var av = document.querySelector('#group-' + botId + ' .agent-avatar');
  if (av) av.classList.add('shaking');
}
```

### Social Helpers

```javascript
function findBlockedBot() {
  for (var a in chars) {
    var c = chars[a];
    if (c.status === 'blocked' && c.el) return c;
  }
  return null;
}

function findCelebratingBot() {
  for (var a in chars) {
    var c = chars[a];
    if (c.state === 'celebrating' && c.el) return c;
  }
  return null;
}

function propagateCelebration(botId) {
  var celebrant = chars[botId];
  if (!celebrant) return;
  for (var id in chars) {
    if (id === botId) continue;
    var bot = chars[id];
    if (!bot.el) continue;
    var dx = celebrant.x - bot.x;
    var dy = celebrant.y - bot.y;
    var dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 40 && bot.state !== 'working' && bot.state !== 'traveling') {
      showSpeechBubble(id, pickPhrase(PERSONAS[id], 'celebrating'));
    }
  }
}
```

### Attention & Facing (Req #5)

```javascript
function updateAttention(botId) {
  var bot = chars[botId];
  if (!bot || !bot.el) return;
  var target = bot.attentionTarget;
  var angle = 0;
  if (target) {
    var targetBot = chars[target];
    if (targetBot) angle = Math.atan2(targetBot.y - bot.y, targetBot.x - bot.x);
  } else {
    angle = Math.atan2(bot.targetY - bot.y, bot.targetX - bot.x);
  }
  var av = bot.el.querySelector('.agent-avatar');
  if (av) {
    var deg = Math.max(-30, Math.min(30, angle * (180 / Math.PI)));
    av.style.transform = 'rotate(' + deg + 'deg)';
    av.style.transition = 'transform 0.3s ease-out';
  }
}

function setAttention(botId, targetId) {
  var bot = chars[botId];
  if (bot) bot.attentionTarget = targetId;
}
```

### Memory System (Req #10)

```javascript
var memories = {};

function addMemory(botId, entry) {
  if (!memories[botId]) memories[botId] = [];
  memories[botId].unshift({
    id: Date.now() + '-' + Math.random().toString(36).slice(2, 8),
    timestamp: Date.now(),
    type: entry.type,
    summary: entry.summary,
    relatedBots: entry.relatedBots || [],
    relatedMission: entry.relatedMission || null,
    location: chars[botId] ? chars[botId].zone : 'unknown',
    significance: entry.significance || 0.5,
  });
  if (memories[botId].length > 50) memories[botId].pop();
}

function timeAgo(ts) {
  var secs = Math.floor((Date.now() - ts) / 1000);
  if (secs < 60) return 'just now';
  if (secs < 3600) return Math.floor(secs / 60) + 'm ago';
  if (secs < 86400) return Math.floor(secs / 3600) + 'h ago';
  return Math.floor(secs / 86400) + 'd ago';
}

function getRecentMemories(botId, count) {
  return (memories[botId] || []).slice(0, count || 5);
}
```

### Idle Variety CSS (Req #11)

```css
.state-reading .agent-avatar { animation: reading-bob 2.5s ease-in-out infinite; }
.state-maintaining .agent-avatar { animation: maintaining-tap 1.2s ease-in-out infinite; }
.state-wandering .agent-avatar { animation: wandering-bob 3s ease-in-out infinite; }
.state-sleeping .agent-avatar { animation: sleeping-breathe 4s ease-in-out infinite; filter: brightness(0.7); }
.state-arriving .agent-avatar { animation: look-around 1s ease-in-out; }
.state-celebrating .agent-avatar { animation: celebrate-bounce 0.6s ease-out; }
.state-socializing .agent-avatar { animation: social-wave 1.5s ease-in-out infinite; }
.shaking { animation: shake 0.5s ease-in-out infinite; }

@keyframes reading-bob {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  25% { transform: translateY(-2px) rotate(-2deg); }
  75% { transform: translateY(-1px) rotate(2deg); }
}
@keyframes maintaining-tap {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}
@keyframes wandering-bob {
  0%, 100% { transform: translateY(0) translateX(0); }
  25% { transform: translateY(-1px) translateX(1px); }
  75% { transform: translateY(-1px) translateX(-1px); }
}
@keyframes look-around {
  0% { transform: rotate(0deg); }
  25% { transform: rotate(-10deg); }
  75% { transform: rotate(10deg); }
  100% { transform: rotate(0deg); }
}
@keyframes celebrate-bounce {
  0% { transform: translateY(0) scale(1); }
  30% { transform: translateY(-12px) scale(1.1); }
  50% { transform: translateY(-6px) scale(1.05); }
  70% { transform: translateY(-10px) scale(1.08); }
  100% { transform: translateY(0) scale(1); }
}
@keyframes social-wave {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(3deg); }
  75% { transform: rotate(-3deg); }
}
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-2px); }
  40% { transform: translateX(2px); }
  60% { transform: translateX(-2px); }
  80% { transform: translateX(2px); }
}
@keyframes fade-out {
  from { opacity: 1; transform: translateX(-50%) scale(1); }
  to { opacity: 0; transform: translateX(-50%) scale(0.8); }
}
```

### State Class Management

```javascript
function removeStateClasses(group) {
  var classes = group.className.split(' ');
  var filtered = classes.filter(function(c) { return !c.startsWith('state-'); });
  group.className = filtered.join(' ');
}
```

Called in `updateGroupVisual()` before adding the new state class to prevent stale animations.

### Required JS Constants

The following must be injected alongside `COLORS`, `INITIALS`, `IMAGES`:

```javascript
const PERSONAS = {json.dumps(AGENT_PERSONAS)};
const TAGLINES = {json.dumps(AGENT_TAGLINES)};
```

`PERSONAS` is required for `pickPhrase()`, `BOT_PERSONALITY[]` lookups, and persona name display. Without it, speech bubbles and personality-driven behaviors fail silently.

## Windows Server Management

The command center server runs as a Python background process. On Windows, changes to `office_view.py` do NOT take effect until the server is restarted. Python's `__pycache__` persists stale bytecode.

### Proper Restart Procedure

```bash
# 1. Kill any existing server on port 8765
taskkill /F /PID $(netstat -ano | grep 8765 | awk '{print $5}') 2>/dev/null

# 2. Clear Python bytecode cache
rm -rf /c/Users/wesle/AppData/Local/hermes/desktop-plugins/command-center/__pycache__

# 3. Start the server (foreground recommended for debugging)
cd /c/Users/wesle/AppData/Local/hermes/desktop-plugins/command-center
python command_center_server.py

# 4. Verify the new code is being served
curl -s http://127.0.0.1:8765/office | grep -c "NEW_MARKER"
```

### What NOT to Do

- **Don't use `pythonw`** — it detaches and you lose visibility into errors. Use `python` in a background terminal instead.
- **Don't use `nohup ... &`** — MSYS bash job control doesn't work in Hermes terminal; the process hangs.
- **Don't skip cache clearing** — stale `__pycache__/*.pyc` files serve old code even after restart.
- **Don't assume the server picked up changes** — always verify with `curl | grep` for a unique marker from your edit.

## f-string JS Escaping Rules (Expanded)

The single most common source of `SyntaxError: f-string: invalid syntax` errors when extending the office view JS is incorrect brace escaping. The Python f-string parser interprets `{` and `}` as template variables unless doubled.

### The Complete Rules

1. **All standalone JS braces must be doubled**: `{` → `{{`, `}` → `}}`
2. **Template variables stay single**: `{json.dumps(AGENT_COLORS)}`
3. **Use `var` not `const`/`let`**: The parser sometimes misidentifies `const`/`let` keywords inside f-strings. Always use `var`.
4. **Use `.indexOf() !== -1` not `.includes()`**: Array `.includes()` inside f-strings breaks the Python expression parser.
5. **Use `function() {}` not arrow functions**: `() =>` becomes `() => {{` which is invalid JS.
6. **No template literals**: Backtick strings `` `text ${var}` `` fail because `${` is interpreted as a Python f-string expression. Use string concatenation: `'text ' + var`.
7. **No nested dicts in expressions**: `{k: True for k in DESKS.keys()}` raises `TypeError: unhashable type: 'dict'`. Build the dict first, then pass to `json.dumps()`.
8. **No async/await at top level**: Top-level `await` is not allowed in `<script>` tags. Use `.then()` chains instead.

### Examples

```python
# GOOD: Doubled braces, var, indexOf, function
f"""function test(a) {{
  var x = arr.indexOf('foo');
  if (x !== -1) {{ return x; }}
  function helper() {{ return 1; }}
}}"""

# BAD: Single braces, const, includes, arrow function
f"""function test(a) {{
  const x = arr.includes('foo');  # Breaks parser
  const fn = () => {{ return 1; }};  # Arrow breaks
}}"""
```

## Debugging Empty Office View

When the office view shows empty panels with no avatars, follow this diagnostic sequence:

### Step 1: Verify the Server is Running New Code

```bash
# Check if server is listening
netstat -ano | grep 8765

# Verify the response contains your new code markers
curl -s http://127.0.0.1:8765/office | grep -c "YOUR_NEW_MARKER"

# If count is 0, kill and restart (see Windows Server Management above)
```

### Step 2: Check the API

```bash
# Verify /api/subagents returns data
curl -s http://127.0.0.1:8765/api/subagents | python -m json.tool

# Look for: "active" array non-empty OR "recent" array with 7+ entries
# If all bots are idle, they all sit in Crew Quarters (bottom center panel)
```

### Step 3: Check for JS Errors

Add a debug overlay at the very top of the `<script>` tag (after `<script>`, before any other code):

```javascript
// Debug: verify JS is running
console.log("=== OFFICE VIEW JS LOADED ===");
var debugDiv = document.createElement("div");
debugDiv.id = "js-debug";
debugDiv.style.cssText = "position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);color:#0f0;font-size:24px;z-index:9999;background:#000;padding:20px;border:3px solid #0f0;";
debugDiv.textContent = "JS RUNNING";
document.body.appendChild(debugDiv);
```

If the green box appears, JS is executing. If not, the `<script>` tag has a syntax error — extract the JS and run `node --check` on it.

### Step 4: Extract and Validate JS

```bash
# Save JS to a file
curl -s http://127.0.0.1:8765/office | sed -n '/<script>/,<\/script>/p' | sed '1d;$d' > /tmp/office_view.js

# Remove trailing </html> if present
sed -i 's/<\/html$//' /tmp/office_view.js

# Check syntax
node --check /tmp/office_view.js
```

### Step 5: Check for Function Availability

The office view JS relies on these being defined in order:
1. `PERSONAS`, `COLORS`, `INITIALS`, `IMAGES` (constants from Python `json.dumps`)
2. `TRAITS`, `BOT_PERSONALITY`, `IDLE_PREFERENCES` (behavior config)
3. `chars` object and `ensureChar()` function
4. All behavior functions (`updateChar`, `transitionTo`, `moveChar`, etc.)
5. `poll()` and `tick()` entry points
6. Initialization calls at the bottom: `poll()`, `setInterval(poll, 3000)`, `requestAnimationFrame(tick)`

If any are missing or out of order, the page renders nothing.

### Step 6: Verify Bot Rendering

All idle bots appear in the **Crew Quarters** panel (bottom center, y=82%). Running bots appear at their dedicated station. Blocked bots appear in the War Room. If all 7 idle bots are stacked in the same panel, they may overlap — use the awareness system to separate them.

### Common Root Causes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Green debug box visible, no avatars | JS error in `poll()` or `updateChar()` | Check browser console for errors |
| No green box at all | Syntax error in JS | `node --check` on extracted JS |
| Avatars in Crew Quarters only | All bots idle | Expected behavior — create a task to activate one |
| Avatars visible but no name/activity | `PERSONAS` not defined in JS | Add `const PERSONAS = {json.dumps(AGENT_PERSONAS)};` |
| Avatars visible but static | `tick()` not running | Check `requestAnimationFrame(tick)` is called |
| Works briefly then breaks | `__pycache__` serving stale code | Delete cache and restart |

## Debug Overlay Pattern

When debugging office view issues, add a temporary visible indicator that JS is running:

```javascript
var debugDiv = document.createElement("div");
debugDiv.id = "js-debug";
debugDiv.style.cssText = "position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);color:#0f0;font-size:24px;z-index:9999;background:#000;padding:20px;border:3px solid #0f0;";
debugDiv.textContent = "JS RUNNING";
document.body.appendChild(debugDiv);

// Update with status info
fetch("/api/subagents").then(function(r) {{ return r.json(); }}).then(function(data) {{
  debugDiv.innerHTML = "JS RUNNING<br>Active: " + data.active.length + "<br>Recent: " + data.recent.length;
}});
```

Place this immediately after `<script>`, before any other code. Remove before deploying. The green-on-black box is visible even on dark backgrounds.
