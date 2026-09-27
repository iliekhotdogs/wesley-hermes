# Inhabited World Implementation Plan

## Overview

Transform the command center from a card-grid dashboard into a living inhabited world where AI agents feel like characters rather than status indicators. This is the comprehensive design for making the pirate ship feel alive.

## The 12-Point Vision

### 1. Persistent Identity

Every bot has a visible identity at all times, not just in a roster card:
- **Name** displayed near the character (e.g., "Calcifer")
- **Role line** — short, human-readable description of what they do
- **Personality trait** — one small preference, habit, or working style that makes two similar bots feel distinct

Example assignments for the current crew:
- **Ditto** — "Decides what gets done and signs off on the final result" — habit: double-checks the work of others before approving
- **Laboon** — "Sees and describes images, video, and visual media" — habit: narrates what it's seeing while working
- **Calcifer** — "Catches bugs before they escape" — habit: refuses to let work pass until it's been verified twice
- **Heen** — "Builds and maintains the codebase" — habit: hums while coding, occasionally talks to the code
- **Tony Tony Chopper** — "Keeps the ship's systems healthy" — habit: panics briefly when something breaks, then fixes it
- **Pakkun** — "Turns long documents into useful answers" — habit: summarizes everything into bullet points
- **Gamatasu** — "Gathers intelligence from across the seas" — habit: always cross-references at least two sources
- **Totoro** — "Tinkers with experimental ideas" — habit: gets distracted by interesting side quests

### 2. Plain-Language Activities

Replace generic states (`ACTIVE`, `IDLE`) with specific present-tense descriptions:

| Old State | New Activity |
|-----------|--------------|
| `RUNNING` | "Reviewing the latest build" / "Comparing three sources" / "Drafting the morning briefing" |
| `BLOCKED` | "Waiting for Wesley's approval" / "Stuck on a missing dependency" |
| `READY` | "Standing by for assignment" |
| `IDLE` | "Taking a short recharge" / "Wandering back to their station" |
| `SLEEP` | "Sleeping" / "Reading" / "Maintaining equipment" |

The technical status is retained as secondary metadata (small pill or tooltip), not the primary label.

### 3. Inhabited Home View

The first screen is the primary living view, not a diagram:
- Each bot has a **station** or home area (already implemented in DESKS)
- Bots **leave their stations** to perform tasks
- **Shared places** exist for meetings (War Room), research (Chart Room), storage (Armory), rest (Crew Quarters), handoffs (Docking Bay)
- Stations can **visibly hold** current work, completed objects, or waiting items

The shift: from **cards placed on a board** to **characters occupying a world**.

### 4. Autonomous Behaviors

Between major tasks, bots perform small autonomous actions:
- Walking to another station
- Looking around or inspecting something
- Organizing their workspace
- Visiting another bot
- Returning home after completing work
- Sleeping or recharging after being inactive
- Reacting when a new assignment arrives

These can be partly cosmetic — they don't all need to represent real system operations.

### 5. Meaningful State Transitions

Avoid instant switches. Show a small lifecycle:

```
Notices assignment → travels to task → starts work → encounters progress or difficulty → delivers result → returns or rests
```

Each transition takes time and is visible. The user perceives that effort occurred.

### 6. Visible Attention and Intention

A character feels alive when you can tell what it's attending to:
- Face or turn toward its current task
- Look toward a bot that is speaking
- Carry or manipulate a symbolic work item
- Pause at a destination before beginning
- React briefly to success, failure, or interruption

Small orientation and timing changes produce more personality than elaborate animation.

### 7. Lightweight Social Behavior

Bots acknowledge one another:
- A researcher hands findings to a writer
- A coder sends a build to the reviewer
- A blocked bot visits the relevant specialist
- Several bots briefly gather for a scheduled mission
- A bot celebrates or acknowledges another bot's completed task

This makes the crew feel like a team rather than isolated processes.

### 8. Thought, Speech, and Activity Snippets

Occasionally expose a short line that explains current intent:

- "I should verify this before sending it."
- "Calcifer may want to review this."
- "Nothing assigned. I'll stay nearby."
- "Finished—bringing this back now."

Use sparingly. Base on actual state. Clarify behavior, don't generate chatter.

### 9. Multiple Rest Forms

"Idle" feels mechanical. Downtime can still reveal character:
- Sleeping
- Reading
- Maintaining equipment
- Practicing a skill
- Chatting with another bot
- Waiting attentively
- Wandering
- Recharging

Each bot gets one or two preferred idle behaviors. This is one of the strongest ways to produce the "own soul" quality.

### 10. Recent Memory

A small memory or history makes each character seem continuous:

- "Just completed the market scan"
- "Last spoke with Heen 8 minutes ago"
- "Waiting on approval for Build 12"
- "Has reviewed this project three times"
- "Next scheduled task: Morning Briefing"

Connects current pose with what happened before and what will happen next.

### 11. Missions Exist Inside the World

Scheduled missions are not separate from the characters:
- Show which bot owns each mission
- Represent upcoming missions at the bot's station
- Have the character physically move when a mission begins
- Show collaborating bots joining the same task area
- Let completed work appear as an object, message, or delivery

The cards remain as the detailed management view; the inhabited view becomes the experiential one.

### 12. Detail Through Interaction

When someone selects a bot, show a focused character panel:
- Name and short description
- Current activity
- Why it is doing that activity
- Current collaborator
- Recent accomplishment
- Next intended action
- Energy, availability, or workload
- Controls: assign, interrupt, inspect work, follow

Preserves the charming world while remaining a useful operational interface.

## Highest-Impact First Version

The minimum viable "alive" version:

1. Put named characters into the first screen (already done)
2. Assign each one a home station (already done)
3. Display a specific activity above them (replace status label)
4. Implement four behaviors: **working, travelling, interacting, sleeping**
5. Connect those behaviors to the real missions shown on the second screen

That alone would make the experience feel dramatically more alive.

## Implementation Architecture

### State Machine Extension

Extend the existing character behavior system with new states:

```
States: working, traveling, sleeping, wandering, socializing, reading, maintaining, waiting
Transitions driven by: API status, idle timer, proximity to other bots, mission events
```

### Personality Data

Add to each agent in `office_view.py`:

```python
AGENT_TRAITS = {
    "main": {"habit": "double-checks others' work", "idle_pref": "reading"},
    "critic": {"habit": "verifies twice", "idle_pref": "maintaining"},
    "coder-a": {"habit": "hums while coding", "idle_pref": "wandering"},
    # ...
}
```

### Activity Label Map

Map Kanban task titles and statuses to plain-language activities:

```python
ACTIVITY_MAP = {
    "running": {
        "default": "Working on their assignment",
        "review": "Reviewing the latest work",
        "build": "Building something new",
        "research": "Gathering intelligence",
    },
    "blocked": "Waiting for approval",
    "idle": "Taking a short recharge",
    # ...
}
```

### Memory System

Track per-character history in a JSON file or in-memory dict:

```python
{
    "assignee": "critic",
    "last_task": "Review live crew movement",
    "last_completed_at": 1788070175,
    "interactions": ["coder-a", "main"],
    "review_count": 3,
}
```

### Social Interaction Triggers

When two bots are near each other and both idle, trigger a brief interaction:

```javascript
function checkSocialInteraction(a1, a2) {
  if (bothIdle(a1, a2) && distance(a1, a2) < 20) {
    showSnippet(a1, getRandomInteraction(a1, a2));
    faceEachOther(a1, a2);
  }
}
```

### Thought Bubbles

CSS-only speech/thought bubbles that appear above a character for 3-5 seconds:

```css
.thought-bubble {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0,0,0,0.8);
  border: 2px solid var(--burnt-orange);
  border-radius: 8px;
  padding: 4px 8px;
  font-size: 9px;
  color: var(--bone-white);
  white-space: nowrap;
  animation: bubble-appear 0.3s ease-out, bubble-fade 0.5s ease-in 4s;
}
```

## Integration with Existing System

This plan extends the current character behavior system without replacing it. The existing spatial system, movement, awareness, and wander chaining all remain. The new layers are:

1. **Identity layer** — names, traits, habits visible at all times
2. **Activity layer** — plain-language descriptions replacing status labels
3. **Social layer** — interactions between nearby characters
4. **Memory layer** — recent history connecting past to present
5. **Mission layer** — connecting Kanban tasks to physical world events
6. **Interaction layer** — click-to-inspect character panel

## Pitfalls

- **Over-animation**: More animation ≠ more alive. Small timing and orientation changes matter more than elaborate keyframes.
- **Constant chatter**: Thought bubbles should be rare (every 30-60s), not constant. They lose meaning if always present.
- **Cosmetic-only feeling**: If autonomous behaviors never connect to real system events, the world feels like a screensaver. Always ground behavior in actual Kanban state.
- **Identity bloat**: One trait per bot is enough. Don't create complex personality systems — a single habit or preference is surprisingly effective.
- **Performance**: 8 bots with CSS transitions and a 10fps awareness loop is already near the limit. Don't add per-frame canvas rendering or physics simulations.
- **Re-parenting**: Never move an avatar element into a different container. Always position the parent group directly.

## Reference

See `references/character-behavior.md` for the existing spatial/movement/awareness system that this plan extends.