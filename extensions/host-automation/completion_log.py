#!/usr/bin/env python3
"""Append completed Kanban tasks to a JSONL log and print Discord-ready lines for new ones.

Silent when nothing is new. The first run (log absent) seeds the log with every current done task
silently instead of posting history; later runs print at most 10 lines plus "+N more". `--metrics` prints per-profile counts for the last 7 days.
`--fixture FILE` reads a JSON task list instead of calling the CLI (each task doubles as
its own `show` detail); `--dry-run` prints without writing the log.

Assumed `hermes kanban ... --json` fields (read defensively; any may be absent):
  list: [{id, title, assignee, status, created_by, created_at}]  (completed status = "done")
  show: {status, body|description, latest_summary, created_by, created_at, completed_at,
         changed_resource, verification|evidence, follow_up,
         events: [{kind, created_at, payload: {...same optional keys...}}]}
Timestamps may be epoch seconds or ISO-8601.

The log is appended before the printed lines are delivered: Hermes posts stdout after this
process exits, so a failed post cannot be detected here and those tasks will not be re-posted.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

COMPLETED_STATUS = "done"
WEEK = 7 * 86400
MAX_LINES = 10


def log_path() -> Path:
    override = os.environ.get("COMPLETION_LOG_PATH")
    if override:
        return Path(override)
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes"))
    return hermes_home / "profiles" / "lib" / "completion_log" / "completions.jsonl"


def command_json(*args: str) -> object:
    result = subprocess.run(["hermes", *args, "--json"], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "command failed")
    return json.loads(result.stdout)


def timestamp(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).timestamp()


def find(detail: dict, *keys: str) -> object:
    """First value for any key on the detail, else on the newest event payload carrying it."""
    for key in keys:
        if detail.get(key):
            return detail[key]
    for event in reversed(detail.get("events") or []):
        payload = event.get("payload") or {}
        for key in keys:
            if payload.get(key):
                return payload[key]
    return None


def entry(task: dict, detail: dict) -> dict:
    completed = detail.get("completed_at") or next(
        (e.get("created_at") for e in reversed(detail.get("events") or []) if e.get("kind") in {"completed", "done"}), None)
    summary = detail.get("latest_summary") or task.get("latest_summary")
    return {
        "task_id": str(task["id"]),
        "title": task.get("title") or detail.get("title") or "Untitled",
        "request": str(detail.get("body") or detail.get("description") or "")[:300],
        "profile": task.get("assignee") or detail.get("assignee") or "unassigned",
        "result": summary,
        "changed_resource": find(detail, "changed_resource"),
        "evidence": find(detail, "verification", "evidence") or summary,
        "completed_at": completed,
        "follow_up": find(detail, "follow_up"),
        "created_at": task.get("created_at") or detail.get("created_at"),
        "created_by": task.get("created_by") or detail.get("created_by"),
    }


def read_log(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except ValueError:
            continue  # A torn line must not block later appends.
    return entries


def is_takeover(item: dict) -> bool:
    return "profile-permissions" in str(item.get("created_by") or "") or str(item.get("title") or "").startswith("Main recovery")


def helped_role(item: dict, fallback: object) -> str:
    """The specialist a takeover helped: `<role>:profile-permissions` or `Main recovery: <role> needs ...`."""
    match = re.match(r"([\w-]+):profile-permissions", str(item.get("created_by") or "")) \
        or re.match(r"Main recovery: ([\w-]+) needs\b", str(item.get("title") or ""))
    return match.group(1) if match else str(fallback or "unassigned")


def metrics(entries: list[dict], blocked: list[dict], now: float) -> str:
    rows: dict = {}
    def row(profile: str) -> dict:
        return rows.setdefault(profile or "unassigned", {"completed": 0, "blocked": 0, "takeovers": 0, "elapsed": []})
    for item in entries:
        done = timestamp(item.get("completed_at"))
        if done is None or now - done > WEEK:
            continue
        stats = row(item.get("profile"))
        stats["completed"] += 1
        if is_takeover(item):
            row(helped_role(item, item.get("profile")))["takeovers"] += 1
        start = timestamp(item.get("created_at"))
        if start is not None and done >= start:
            stats["elapsed"].append(done - start)
    for task in blocked:
        row(task.get("assignee"))["blocked"] += 1
        if is_takeover(task):
            row(helped_role(task, task.get("assignee")))["takeovers"] += 1
    lines = ["| profile | completed | blocked | main takeovers | median elapsed |", "|---|---|---|---|---|"]
    for profile, stats in sorted(rows.items()):
        median = f"{statistics.median(stats['elapsed']) / 3600:.1f}h" if stats["elapsed"] else "n/a"
        lines.append(f"| {profile} | {stats['completed']} | {stats['blocked']} | {stats['takeovers']} | {median} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--metrics", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="print without writing the log")
    parser.add_argument("--fixture", type=Path, help="JSON task list to use instead of the hermes CLI")
    args = parser.parse_args(argv)

    fixture = json.loads(args.fixture.read_text(encoding="utf-8")) if args.fixture else None

    def tasks(status: str) -> list[dict]:
        found = [t for t in fixture if (t.get("status") or COMPLETED_STATUS) == status] if fixture is not None \
            else command_json("kanban", "list", "--status", status)
        return [t for t in found if isinstance(t, dict) and t.get("id")] if isinstance(found, list) else []

    path = log_path()
    seeding = not path.exists() and not args.dry_run
    entries = read_log(path)
    if args.metrics:
        print(metrics(entries, tasks("blocked"), time.time()))
        return 0

    seen = {str(item.get("task_id")) for item in entries}
    new = []
    for task in tasks(COMPLETED_STATUS):
        if str(task["id"]) in seen:
            continue
        if fixture is not None:
            detail = task
        else:
            try:
                detail = command_json("kanban", "show", str(task["id"]))
            except Exception:
                detail = {}  # Log what the listing has; the task is still complete.
        new.append(entry(task, detail if isinstance(detail, dict) else {}))
        seen.add(str(task["id"]))
    if not new and not seeding:
        return 0
    if not args.dry_run:
        # shortcut: logged before stdout is delivered (after exit), so a failed post is not retried; needs a delivery ack to fix.
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.writelines(json.dumps(item, sort_keys=True) + "\n" for item in new)
    if seeding or not new:
        return 0  # First run records history silently instead of posting it all.
    lines: list[str] = []
    for item in new[:MAX_LINES]:
        line = f"✅ {item['task_id']} — {str(item['title'])[:120]} ({item['profile']}): {str(item['result'] or 'no summary')[:200]}"
        if sum(len(x) + 1 for x in lines) + len(line) > 1850:
            break  # Whole lines only, leaving room for the "+N more" footer under Discord's limit.
        lines.append(line)
    if len(new) > len(lines):
        lines.append(f"+{len(new) - len(lines)} more")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
