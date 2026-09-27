# Debugging Empty Office View

When the office view shows empty panels with no avatars, follow this diagnostic sequence.

## Step 1: Verify the Server is Running New Code

```bash
# Check if server is listening
netstat -ano | grep 8765

# Verify the response contains your new code markers
curl -s http://127.0.0.1:8765/office | grep -c "YOUR_NEW_MARKER"

# If count is 0, kill and restart (see Windows Server Management below)
```

## Step 2: Check the API

```bash
# Verify /api/subagents returns data
curl -s http://127.0.0.1:8765/api/subagents | python -m json.tool

# Look for: "active" array non-empty OR "recent" array with 7+ entries
# If all bots are idle, they all sit in Crew Quarters (bottom center panel)
```

## Step 3: Add Debug Overlay

Add this at the very top of the `<script>` tag (after `<script>`, before any other code):

```javascript
console.log("=== OFFICE VIEW JS LOADED ===");
var debugDiv = document.createElement("div");
debugDiv.id = "js-debug";
debugDiv.style.cssText = "position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);color:#0f0;font-size:24px;z-index:9999;background:#000;padding:20px;border:3px solid #0f0;";
debugDiv.textContent = "JS RUNNING";
document.body.appendChild(debugDiv);

fetch("/api/subagents").then(function(r) {{ return r.json(); }}).then(function(data) {{
  debugDiv.innerHTML = "JS RUNNING<br>Active: " + data.active.length + "<br>Recent: " + data.recent.length;
}});
```

If the green box appears, JS is executing. If not, the `<script>` tag has a syntax error.

## Step 4: Extract and Validate JS

```bash
curl -s http://127.0.0.1:8765/office | sed -n '/<script>/,<\/script>/p' | sed '1d;$d' > /tmp/office_view.js
sed -i 's/<\/html$//' /tmp/office_view.js
node --check /tmp/office_view.js
```

## Step 5: Check Function Availability

The office view JS relies on these being defined in order:
1. `PERSONAS`, `COLORS`, `INITIALS`, `IMAGES` (constants from Python `json.dumps`)
2. `TRAITS`, `BOT_PERSONALITY`, `IDLE_PREFERENCES` (behavior config)
3. `chars` object and `ensureChar()` function
4. All behavior functions (`updateChar`, `transitionTo`, `moveChar`, etc.)
5. `poll()` and `tick()` entry points
6. Initialization calls: `poll()`, `setInterval(poll, 3000)`, `requestAnimationFrame(tick)`

## Step 6: Verify Bot Rendering

All idle bots appear in **Crew Quarters** (bottom center, y=82%). Running bots appear at their dedicated station. Blocked bots appear in the War Room. If all 7 idle bots are stacked in the same panel, they may overlap — the awareness system separates them.

## Common Root Causes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Green debug box visible, no avatars | JS error in `poll()` or `updateChar()` | Check browser console for errors |
| No green box at all | Syntax error in JS | `node --check` on extracted JS |
| Avatars in Crew Quarters only | All bots idle | Expected behavior — create a task to activate one |
| Avatars visible but no name/activity | `PERSONAS` not defined in JS | Add `const PERSONAS = {json.dumps(AGENT_PERSONAS)};` |
| Avatars visible but static | `tick()` not running | Check `requestAnimationFrame(tick)` is called |
| Works briefly then breaks | `__pycache__` serving stale code | Delete cache and restart |

## Windows Server Management

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

## Server Injection Pattern for `tagline` and `activity`

`command_center_server.py`'s `read_subagents()` must import from `office_view`:

```python
# At the top of the function or module
from office_view import AGENT_TAGLINES, activity_label

# Inside the worker loop, after building the worker dict:
worker["tagline"] = AGENT_TAGLINES.get(worker.get("assignee", ""), "")
worker["activity"] = activity_label(worker["status"], worker.get("title", ""), worker.get("assignee"))
```

Without this, the office view JS cannot display persona names or activity phrases.
