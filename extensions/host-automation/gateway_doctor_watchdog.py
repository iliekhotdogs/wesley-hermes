#!/usr/bin/env python
"""External Windows supervisor for the Hermes Discord gateway.

This runs outside Hermes so it can recover the gateway after a crash or a
wedged event loop. Healthy checks are silent; only recovery/failure events are
written to the log. The gateway's own delivery ledger and resume_pending state
handle unfinished replies/tasks after restart.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import time
from pathlib import Path

HERMES = Path(r"C:\Users\YOUR_USER\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe")
HOME = Path(r"C:\Users\YOUR_USER\AppData\Local\hermes")
HEARTBEAT = HOME / "state" / "gateway.heartbeat"
GATEWAY_STATE = HOME / "gateway_state.json"
LOG = HOME / "logs" / "doctor_gateway_watchdog.log"
LOCK = HOME / "state" / "doctor_gateway_watchdog.lock"
HEARTBEAT_MAX_AGE_S = 120


def record(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")


def acquire_lock() -> bool:
    try:
        fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode("ascii"))
        os.close(fd)
        return True
    except FileExistsError:
        return False
    except OSError as exc:
        record(f"ERROR watchdog lock failed: {type(exc).__name__}")
        return False


def release_lock() -> None:
    try:
        LOCK.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def run(*args: str, timeout: float = 25.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(HERMES), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def read_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def gateway_process_exists(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and f'"{pid}"' in result.stdout


def gateway_is_healthy() -> tuple[bool, str]:
    heartbeat = read_json(HEARTBEAT)
    state = read_json(GATEWAY_STATE)
    if not heartbeat or not state:
        return False, "gateway heartbeat/state missing"

    pid = heartbeat.get("pid")
    updated_at = heartbeat.get("updated_at")
    try:
        age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(updated_at)).total_seconds()
    except (TypeError, ValueError):
        return False, "gateway heartbeat timestamp invalid"

    platform = state.get("platforms", {}).get("discord", {})
    discord_state = str(platform.get("state", "")).lower()
    if state.get("gateway_state") != "running":
        return False, f"gateway state={state.get('gateway_state', 'unknown')}"
    if not gateway_process_exists(pid):
        return False, f"gateway process {pid} is not running"
    if age > HEARTBEAT_MAX_AGE_S:
        return False, f"gateway heartbeat is {age:.0f}s old"
    if discord_state in {"fatal", "disconnected", "unavailable"}:
        return False, f"Discord state={discord_state}"
    return True, f"gateway pid={pid}, Discord state={discord_state or 'unknown'}"


def restart_gateway(reason: str) -> bool:
    record(f"WARNING gateway unhealthy: {reason}; attempting restart")
    try:
        result = run("gateway", "start", timeout=35)
    except (OSError, subprocess.SubprocessError) as exc:
        record(f"CRITICAL gateway restart failed: {type(exc).__name__}")
        return False

    detail = (result.stderr or result.stdout or "").strip().replace("\n", " ")[:500]
    if result.returncode != 0:
        record(f"CRITICAL gateway restart returned {result.returncode}: {detail or 'unknown error'}")
        return False

    # Give the detached service a short, bounded startup window, then verify
    # the real process/heartbeat rather than trusting the CLI return code.
    for _ in range(6):
        time.sleep(5)
        healthy, status = gateway_is_healthy()
        if healthy:
            record(f"RECOVERY gateway restarted successfully: {status}")
            return True
    record("CRITICAL gateway start returned success but health did not recover within 30s")
    return False


def main() -> int:
    if not HERMES.exists():
        record(f"ERROR Hermes executable missing: {HERMES}")
        return 2
    if not acquire_lock():
        return 0
    try:
        healthy, status = gateway_is_healthy()
        if healthy:
            return 0
        return 0 if restart_gateway(status) else 1
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
