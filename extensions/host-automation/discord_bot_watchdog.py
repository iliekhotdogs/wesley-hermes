#!/usr/bin/env python
"""Discord Bot Auto-Restart Script

Checks if the Discord bot process is running and restarts it if crashed.
Runs as a Hermes cron job every 5 minutes.
"""

from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path

LOG = Path(r"C:\Users\YOUR_USER\AppData\Local\hermes\logs\discord_bot_watchdog.log")


def record(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")


def find_discord_bot_process() -> dict | None:
    """Find the Discord bot process and its details."""
    try:
        # Check for node processes running from the poopyclaw directory
        result = subprocess.run(
            ["tasklist", "/FO", "LIST", "/NH"],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.split("\n")
        pids = []
        titles = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped:
                pids.append(int(line_stripped) if line_stripped.isdigit() else None)
                titles.append(line_stripped if i + 1 < len(lines) and lines[i + 1].strip().isdigit() else "")

        # Look for processes related to poopyclaw/next.js
        for i, pid in enumerate(pids):
            if pid and "next" in titles[i].lower():
                # Check if it's from the poopyclaw directory
                try:
                    cmd_result = subprocess.run(
                        ["wmic", "process", "where", f"processid={pid}", "get", "commandline"],
                        capture_output=True, text=True, timeout=5
                    )
                    if "poopyclaw" in cmd_result.stdout.lower() or "next" in cmd_result.stdout.lower():
                        return {
                            "pid": pid,
                            "status": "running",
                            "detail": f"Process {pid} is running: {titles[i]}"
                        }
                except:
                    pass

        # Also check via hermes gateway status
        try:
            hermes_result = subprocess.run(
                [r"C:\Users\YOUR_USER\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe", "gateway", "status"],
                capture_output=True, text=True, timeout=15
            )
            output = hermes_result.stdout.lower()
            if "gateway process running" in output:
                return {"pid": None, "status": "gateway_ok", "detail": "Hermes gateway is running"}
        except:
            pass

        return {"pid": None, "status": "not_running", "detail": "Discord bot process not found"}

    except (OSError, subprocess.SubprocessError) as exc:
        record(f"ERROR finding Discord bot process: {type(exc).__name__}")
        return {"pid": None, "status": "error", "detail": str(exc)}


def restart_discord_bot() -> dict:
    """Attempt to restart the Discord bot."""
    record("Attempting Discord bot restart")

    try:
        # Change to poopyclaw directory and start
        result = subprocess.run(
            ["cmd.exe", "/c", "cd C:\\Users\\YOUR_USER\\poopyclaw && timeout 10 npm run start >nul 2>&1 || true"],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        if result.returncode == 0 or "already running" in (result.stdout + result.stderr).lower():
            record("RECOVERY Discord bot start command succeeded (may already be running)")
            return {"status": "started", "detail": "Discord bot restart initiated"}
        else:
            detail = (result.stderr or result.stdout or "unknown error").strip().replace("\n", " ")[:500]
            record(f"CRITICAL Discord bot restart returned {result.returncode}: {detail}")
            return {"status": "failed", "detail": f"restart returned {result.returncode}"}

    except (OSError, subprocess.SubprocessError) as exc:
        record(f"CRITICAL Discord bot restart failed: {type(exc).__name__}")
        return {"status": "error", "detail": str(exc)}


def main() -> int:
    record("Starting Discord bot watchdog check")

    status = find_discord_bot_process()
    current_status = status.get("status", "unknown")

    if current_status in ("running", "gateway_ok"):
        record(f"INFO Discord bot check: {status.get('detail', 'ok')}")
        return 0

    record(f"WARNING Discord bot not running: {status.get('detail', 'unknown')}")

    # Attempt restart
    result = restart_discord_bot()
    new_status = result.get("status", "unknown")

    if new_status == "started":
        record("RECOVERY Discord bot restart successful")
        return 0

    record(f"CRITICAL Discord bot restart failed: {result.get('detail', 'unknown')}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())