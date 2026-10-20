#!/usr/bin/env python
"""Hermes Gateway Auto-Restart Watchdog

Runs as a Hermes cron job every 5-10 minutes.
Checks if the gateway process is running and restarts it if crashed.
"""

from __future__ import annotations
import datetime as dt
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(r"C:\Users\YOUR_USER\AppData\Local\hermes")
LOG = HOME / "logs" / "gateway_watchdog.log"
HERMES_EXE = HOME / "hermes-agent" / "venv" / "Scripts" / "hermes.exe"


def record(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")


def find_gateway_process() -> dict | None:
    """Find the Hermes gateway process."""
    try:
        # Check via hermes gateway status command
        result = subprocess.run(
            [str(HERMES_EXE), "gateway", "status"],
            capture_output=True, text=True, timeout=15
        )
        output = result.stdout.lower()

        if "gateway process running" in output:
            # Extract PID if available
            import re
            pid_match = re.search(r"PID: (\d+)", output)
            pid = int(pid_match.group(1)) if pid_match else None
            return {
                "pid": pid,
                "status": "gateway_running",
                "detail": f"Hermes gateway is running" + (f" (PID: {pid})" if pid else "")
            }

        # Also check tasklist for hermes.exe
        task_result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq hermes.exe", "/FO", "LIST", "/NH"],
            capture_output=True, text=True, timeout=10
        )
        hermes_pids = []
        for line in task_result.stdout.split("\n"):
            if "Hermes.exe" in line:
                hermes_pids.append(line.strip())

        if hermes_pids:
            return {
                "pid": None,
                "status": "gateway_running",
                "detail": "Hermes gateway processes found via tasklist"
            }

        return {
            "pid": None,
            "status": "gateway_not_running",
            "detail": "Hermes gateway process not found"
        }
    except (OSError, subprocess.SubprocessError) as exc:
        record(f"ERROR finding gateway process: {type(exc).__name__}")
        return {"pid": None, "status": "error", "detail": str(exc)}


def restart_gateway() -> dict:
    """Attempt to restart the Hermes gateway."""
    record("Attempting Hermes gateway restart")

    try:
        # Kill any existing gateway processes first (clean restart)
        record("Killing existing gateway processes")
        try:
            # Find and kill existing hermes.exe processes
            task_kill_result = subprocess.run(
                ["taskkill", "/F", "/IM", "hermes.exe"],
                capture_output=True, text=True, timeout=10
            )
            record(f"Kill result: returncode={task_kill_result.returncode}")
        except Exception as e:
            record(f"Kill attempt note: {e}")

        # Wait a moment for processes to terminate
        time.sleep(2)

        # Start a fresh gateway in the background
        record("Starting fresh Hermes gateway process")
        workdir = str(HOME)

        # Start gateway run in background - use start command
        result = subprocess.run(
            ["cmd.exe", "/c", f"start /B \"\" \"{HERMES_EXE}\" gateway run"],
            capture_output=True, text=True, timeout=30,
            cwd=workdir,
        )

        record(f"Gateway start initiated, returncode={result.returncode}")
        record(f"Gateway start stdout: {result.stdout[-200:] if len(result.stdout) > 200 else result.stdout}")
        record(f"Gateway start stderr: {result.stderr[-200:] if len(result.stderr) > 200 else result.stderr}")

        # Wait a moment and check if it's running
        time.sleep(5)

        # Check status again
        status = find_gateway_process()
        return status

    except (OSError, subprocess.SubprocessError) as exc:
        record(f"CRITICAL Gateway restart failed: {type(exc).__name__}")
        return {"status": "error", "detail": str(exc)}


def main() -> int:
    record("Starting Hermes gateway watchdog check")

    status = find_gateway_process()
    current_status = status.get("status", "unknown")

    record(f"INFO Gateway check: {status.get('detail', 'unknown')}")

    if current_status in ("gateway_running",):
        record("INFO Gateway is running - no action needed")
        return 0

    record(f"WARNING Gateway not running - attempting restart")

    # Attempt restart
    result = restart_gateway()
    new_status = result.get("status", "unknown")

    if new_status == "gateway_running":
        record("RECOVERY Gateway restart successful")
        return 0

    record(f"CRITICAL Gateway restart failed: {result.get('detail', 'unknown')}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())