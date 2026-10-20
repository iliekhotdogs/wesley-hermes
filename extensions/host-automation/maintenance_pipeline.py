#!/usr/bin/env python3
"""Run the lightweight Kanban/Obsidian maintenance jobs in one serial lane.

The pipeline itself runs every five minutes. Expensive stages retain their
original cadence through per-stage success timestamps, so the second-brain
index refresh still runs at most once every 30 minutes.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
HERMES_HOME = Path(os.environ.get("HERMES_HOME", SCRIPT_DIR.parent))
STATE_PATH = HERMES_HOME / "state" / "maintenance_pipeline_state.json"
LOCK_PATH = HERMES_HOME / "state" / "maintenance_pipeline.lock"
LOCK_STALE_SECONDS = 20 * 60

STAGES = (
    # Recovery runs before alerting so automatically recoverable blocks do not
    # create noisy notifications.
    {"name": "kanban_recovery", "script": "kanban_recovery.py", "interval": 5 * 60, "surface": True},
    {"name": "kanban_block_alert", "script": "kanban_block_alert.py", "interval": 5 * 60, "surface": True},
    {"name": "obsidian_briefing_archive", "script": "obsidian_briefing_archiver.py", "interval": 5 * 60, "surface": False},
    {"name": "second_brain_index_refresh", "script": "second_brain_index_refresh.py", "interval": 30 * 60, "surface": False},
)


def load_state() -> dict:
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(STATE_PATH)


def acquire_lock() -> int | None:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        if LOCK_PATH.exists() and time.time() - LOCK_PATH.stat().st_mtime > LOCK_STALE_SECONDS:
            LOCK_PATH.unlink(missing_ok=True)
        descriptor = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        return descriptor
    except FileExistsError:
        return None


def main() -> int:
    descriptor = acquire_lock()
    if descriptor is None:
        return 0

    now = time.time()
    deadline = time.monotonic() + 150
    state = load_state()
    notices: list[str] = []
    failed = False
    try:
        for stage in STAGES:
            remaining = deadline - time.monotonic()
            if remaining < 5:
                break  # Defer remaining stages to the next scheduled tick.
            record = state.setdefault(stage["name"], {})
            last_success = float(record.get("last_success", 0) or 0)
            if now - last_success < stage["interval"]:
                continue

            script_path = SCRIPT_DIR / stage["script"]
            try:
                result = subprocess.run(
                    [sys.executable, str(script_path)],
                    cwd=SCRIPT_DIR,
                    capture_output=True,
                    text=True,
                    timeout=min(90, remaining),
                )
                output = (result.stdout + result.stderr).strip()
                record.update(
                    last_attempt=now,
                    last_exit_code=result.returncode,
                    last_output=output[-2000:],
                )
                if result.returncode == 0:
                    record["last_success"] = now
                    record.pop("last_error", None)
                    if stage["surface"] and output:
                        notices.append(output)
                else:
                    failed = True
                    message = output or f"exit code {result.returncode}"
                    record["last_error"] = message[-2000:]
                    notices.append(f"Maintenance stage {stage['name']} failed: {message}")
            except Exception as exc:
                failed = True
                record.update(last_attempt=now, last_error=str(exc)[-2000:])
                notices.append(f"Maintenance stage {stage['name']} failed: {exc}")
            finally:
                save_state(state)

        # Routine archive/index success stays local. Alerts, recovery actions,
        # and failures are emitted for the cron delivery channel.
        if notices:
            print("\n".join(notices)[:1900])
        return 1 if failed else 0
    finally:
        os.close(descriptor)
        LOCK_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
