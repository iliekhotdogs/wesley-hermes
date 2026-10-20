#!/usr/bin/env python3
"""Emit a Discord-ready alert when Kanban blocked tasks change."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

FINISHED = {"done", "completed", "cancelled", "canceled", "archived"}


def state_path() -> Path:
    override = os.environ.get("KANBAN_BLOCK_ALERT_STATE")
    if override:
        return Path(override)
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes"))
    return hermes_home / "kanban_block_alert_state.json"


def command_json(*args: str) -> object:
    result = subprocess.run(["hermes", *args, "--json"], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "command failed")
    return json.loads(result.stdout)


def reason_and_fix(detail: dict) -> tuple[str, str]:
    events = detail.get("events") or []
    event = next((item for item in reversed(events) if item.get("kind") in {"blocked", "block_loop_detected", "gave_up", "crashed"}), None)
    payload = (event or {}).get("payload") or {}
    reason = str(payload.get("reason") or payload.get("error") or detail.get("latest_summary") or "No reason recorded")
    kind = str(payload.get("kind") or "")
    text = f"{kind} {reason}".lower()
    if kind == "needs_input" or "credential" in text or "authorization" in text or "api_server_key" in text:
        fix = "Main recovery: inspect the exact credential or workspace dependency first. Ask the user only for missing information or external consent; never expose credentials."
    elif kind == "capability" or "read-only" in text or "cannot implement" in text:
        fix = "Recovery: main must perform the privileged prerequisite or take over; do not reassign to a retired profile or unblock unchanged work."
    elif "crash" in text or "pid " in text or "provider" in text or "http 400" in text:
        fix = "Recovery: retry once with a supported worker model/provider; if it repeats, inspect the worker log and reassign."
    elif kind == "dependency" or "parent" in text:
        fix = "Wait for the parent task(s) to complete; the dispatcher should promote this task automatically."
    else:
        fix = "Inspect the task log and latest worker summary before deciding whether to unblock, reassign, or archive."
    return reason, fix


def main() -> int:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(previous, dict):
            previous = {}
    except (FileNotFoundError, json.JSONDecodeError):
        previous = {}

    tasks = command_json("kanban", "list", "--status", "blocked")
    current = {
        str(task.get("id")): {
            "title": task.get("title", "Untitled"),
            "assignee": task.get("assignee") or "unassigned",
            "status": task.get("status", "blocked"),
        }
        for task in tasks if isinstance(tasks, list) and task.get("id")
    }
    changed = [(task_id, info) for task_id, info in current.items() if previous.get(task_id) != info]
    lines: list[str] = []
    oauth: list[str] = []
    for task_id, info in changed:
        try:
            detail = command_json("kanban", "show", task_id)
            detail = detail if isinstance(detail, dict) else {}
            if str(detail.get("status") or "").lower() in FINISHED:
                del current[task_id]  # Resolved since listing; neither alert nor record it as blocked.
                continue
            reason, fix = reason_and_fix(detail)
        except Exception as exc:
            reason, fix = f"Could not read task details: {exc}", "Run hermes kanban show " + task_id
        if "invalid_grant" in reason.lower():
            oauth.append(task_id)
            continue
        lines.extend([
            f"\n• {task_id} — {info['title']} ({info['assignee']})",
            f"  Reason: {reason[:500]}",
            f"  Suggested fix: {fix}",
        ])
    # Saved after filtering so finished tasks are not remembered (or counted) as blocked.
    path.write_text(json.dumps(current, sort_keys=True, indent=2), encoding="utf-8")
    if oauth:
        # One expired Google grant blocks many tasks; report it as one incident.
        lines.insert(0, f"\n• Google OAuth invalid_grant incident: {len(oauth)} task(s) ({', '.join(oauth)})\n"
                        "  Suggested fix: re-authorize the Google account once, then unblock these tasks.")
    if not lines:
        return 0
    lines.insert(0, f"⚠️ Hermes Kanban: {len(current)} blocked task(s).")
    lines.append("\nOpen Kanban or run: hermes kanban list --status blocked")
    print("\n".join(lines)[:1900])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
