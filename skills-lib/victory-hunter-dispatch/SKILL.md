---
name: victory-hunter-dispatch
description: "Use when spawning Victory Hunter subagents. Kanban dispatch moves sprites."
version: 2.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [victory-hunter, command-center, dispatch, subagent, persona, delegate, kanban]
---

# Victory Hunter Dispatch

When the main agent (Ditto) needs a subagent, this skill auto-categorizes the
task into one of the 9 Command Center roles and creates a **Kanban task** that
triggers the gateway dispatcher. This is what makes the sprite move on the ship.

## Why Kanban, not delegate_task?

`delegate_task` children run inside Ditto's profile. They do NOT create Kanban
tasks, so the office view never sees them and sprites never move.

Kanban dispatch creates a real task in `kanban.db`. The gateway dispatcher
spawns `hermes -p <assignee> chat -q "work kanban task <id>"` — a full Hermes
process in that profile's own model. The office view reads the task and animates
the sprite.

## The 9 Agent Categories

These match the DESKS in `office_view.py` (excluding `main`). `librarian` is a
role alias: dispatch it to the stable installed profile `totoro`, which retains
its historical Kanban assignments. `speed` always dispatches to the installed
`speed` profile.

| Category | Persona | Profile ID | Profile Model | Station | Tagline |
|----------|---------|------------|---------------|---------|---------|
| `multimodal` | Laboon | `multimodal` | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | Lookout Tower | Watches horizons others cannot see |
| `critic` | Calcifer | `critic` | `z-ai/glm-5.2:free` | Furnace Room | Catches bugs before they escape |
| `coder-a` | Heen | `coder-a` | `qwen3-coder-plus` | Rigging Deck | Builds and maintains the codebase |
| `doctor` | Tony Tony Chopper | `doctor` | `z-ai/glm-5.3` | Medical Bay | Patches wounds and mends broken systems |
| `utility` | Pakkun | `utility` | `nvidia/nemotron-3-super-120b-a12b:free` | Armory | Turns long documents into useful answers |
| `researcher` | Gamatatsu | `researcher` | `gpt-5.6-sol` | Chart Room | Charts unknown waters and maps the truth |
| `speed` | Speed | `speed` | `laguna-s-2.1-free` | Signal Room | Handles quick, independent tasks |
| `librarian` | Totoro | `totoro` | `laguna-s-2.1-free` | Archive | Keeps the Obsidian second brain ordered and evidence-backed |

## Categorization Rules

Classify by dominant intent. When a task spans multiple categories, pick the
one that represents the **primary deliverable**.

### multimodal (Laboon)
Keywords: image, photo, screenshot, video, visual, picture, diagram, OCR,
canvas, layout, design, watch, observe, scan, see, inspect visually

### critic (Calcifer)
Keywords: review, audit, check, test, QA, quality, bug, inspect, verify,
validate, critique, lint, security scan, approve, gate, catch

### coder-a (Heen)
Keywords: build, create, implement, write code, develop, feature, fix bug,
refactor, deploy, ship, codebase, main code, production code

### doctor (Tony Tony Chopper)
Keywords: diagnose, health, monitor, repair, heal, patch, fix system,
watchdog, gateway, uptime, broken, wound, mend, emergency, restore

### utility (Pakkun)
Keywords: summarize, condense, extract, compile, format, document, brief,
turn into, distill, organize, notes, report, key points, digest

### researcher (Gamatatsu)
Keywords: research, investigate, find, search, chart, map, compare sources,
discover, unknown, truth, analyze trends, deep dive, what does X say

### librarian (Totoro; dispatch profile `totoro`)
Keywords: Obsidian, second brain, knowledge base, knowledge keeper, vault, note,
archive, preserve, memory gathering, retrieve context, prior decision, evidence,
citation, source paths, index, organize knowledge

Use this role only for durable project knowledge and evidence in Obsidian or the
second brain. Do not use it for Hermes personal-memory changes.

### speed (speed)
Keywords: quick, fast, simple, brief, short, rename, move, copy, delete,
format, convert, calculate, count, list, show, get, set, basic, trivial,
routine, everyday, small, lightweight, instant, rapid, immediate,
parallel coding, independent modules, tests, debugging, documentation,
alternative solutions, experiment, prototype, workshop

## Ambiguous / Multi-category Tasks

1. If a task is "research + write summary" → create two tasks: first
   `researcher`, then `utility` with `--parent <researcher_task_id>`.
2. If a task is "build + review" → first `coder-a`, then `critic` with
   `--parent <coder-a_task_id>`.
3. If truly ambiguous → pick the one that produces the deliverable.
4. If unclear → ask the user which station should handle it.

## Dispatch Protocol (step by step)

### 1. Categorize
Read the task. Match keywords against the categories above.

### 2. Build the persona body
The `--body` field carries the persona context + task details to the worker.
Use this template:

```
You are {PERSONA} — {TAGLINE}.

Your habits: {HABITS}

You are a crew member of the Victory Hunter pirate ship command center.
Your station is the {STATION_NAME}. You work alongside:
- Ditto (Captain, final approver)
- Laboon (Lookout Tower, multimodal)
- Calcifer (Furnace Room, critic)
- Heen (Rigging Deck, coder-a)
- Tony Tony Chopper (Medical Bay, doctor)
- Pakkun (Armory, utility)
- Gamatatsu (Chart Room, researcher)
- Speed (Signal Room, speed)
- Totoro (Archive, librarian; profile `totoro`)

Stay in character. Your responses should reflect your persona's voice and
working style. Be concise and action-oriented.

---

TASK: {task_description}

OUTPUT: Describe what you produced and where it can be found.
```

### 3. Create the Kanban task
Call `hermes kanban create` via terminal:

Before creating the task, resolve the category to the installed profile ID:
`librarian` → `totoro`; every other category, including `speed`, resolves to
itself. Keep `totoro` as the assignee for Librarian cards so historical records
remain stable.

```bash
hermes kanban create "{short_title}" \
  --assignee {resolved_profile_id} \
  --body "{persona_body}" \
  --initial-status running \
  --json
```

### 4. Verify the sprite will move
After creation, the task appears in `kanban.db`. The gateway dispatcher
(tick interval ~60s) spawns a worker and the office view animates the sprite.

### 5. Evidence gate
Do not mark a task complete from a worker summary alone. Before completion, require concrete evidence appropriate to the task: changed-file paths for implementation work, exact test commands and passing output for code, and readback of any external state change. If evidence is missing, contradictory, or the worker lacks the required inspection capability, leave the task blocked and record the precise reason. The captain remains the final approver.

### 6. Report to the user
Tell them which station was activated and the task ID.

## Important Mechanics

- **Dispatcher delay**: The gateway ticks every ~60s. The sprite may take up to
  a minute to start moving. This is normal.
- **Worker model**: The worker runs in the assigned profile with that profile's
  configured model (see table above). This is true model separation.
- **No delegate_task**: Do NOT use `delegate_task` for Victory Hunter dispatch.
  It won't create Kanban tasks and sprites won't move.
- **Gateway must be running**: The dispatcher lives in the gateway process.
  Check with `hermes gateway status`.
- **Office view polling**: The office view polls `/api/subagents` every 3s.
  Once the dispatcher creates the worker, the sprite moves automatically.

## Examples

### Example 1: "Check this screenshot for bugs"

Category: **multimodal** + **critic** (chained)

```bash
hermes kanban create "Analyze screenshot for visual issues" \
  --assignee multimodal \
  --body "You are Laboon — Watches horizons others cannot see..." \
  --initial-status running --json
```

### Example 2: "Write the auth module"

Category: **coder-a**

```bash
hermes kanban create "Build auth module" \
  --assignee coder-a \
  --body "You are Heen — Builds and maintains the codebase..." \
  --initial-status running --json
```

### Example 3: "What are the latest developments in AI agents?"

Category: **researcher**

```bash
hermes kanban create "Research AI agent developments" \
  --assignee researcher \
  --body "You are Gamatatsu — Charts unknown waters and maps the truth..." \
  --initial-status running --json
```

### Example 4: "Summarize this 50-page PDF"

Category: **utility**

```bash
hermes kanban create "Summarize PDF document" \
  --assignee utility \
  --body "You are Pakkun — Turns long documents into useful answers..." \
  --initial-status running --json
```

### Example 5: "Rename file.txt to backup.txt"

Category: **speed**

```bash
hermes kanban create "Rename file" \
  --assignee speed \
  --body "You are Speed — Handles quick, independent tasks..." \
  --initial-status running --json
```
