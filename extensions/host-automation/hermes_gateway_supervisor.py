"""Independent Windows supervisor for Hermes gateway recovery.

Runs outside Hermes so it remains alive when Hermes gateway/cron is stopped.
Checks the supported gateway status command and starts the installed gateway
only when it is down. Healthy checks are silent.
"""
from __future__ import annotations

import datetime as dt
import os
import subprocess
import time
from pathlib import Path

HOME = Path(r"C:\Users\YOUR_USER\AppData\Local\hermes")
HERMES = HOME / "hermes-agent" / "venv" / "Scripts" / "hermes.exe"
GATEWAY_PROFILE = "main"
LOG = HOME / "logs" / "gateway_supervisor.log"
LOCK = HOME / "state" / "gateway_supervisor.lock"


def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {message}\n")


def run(*args: str, timeout: float = 35.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(HERMES), "-p", GATEWAY_PROFILE, *args],
        cwd=str(HOME),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def acquire_lock() -> bool:
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode("ascii"))
        os.close(fd)
        return True
    except FileExistsError:
        return False
    except OSError as exc:
        log(f"ERROR could not create lock: {type(exc).__name__}")
        return False


def release_lock() -> None:
    try:
        LOCK.unlink()
    except (FileNotFoundError, OSError):
        pass


def gateway_running() -> tuple[bool, str]:
    result = run("gateway", "status", timeout=20)
    detail = (result.stdout or result.stderr or "").strip().replace("\n", " ")[:500]
    lowered = detail.lower()
    # The status command is authoritative; do not infer health from a random
    # hermes.exe process, because that could be the CLI or desktop app.
    running = result.returncode == 0 and (
        "gateway process detected" in lowered
        or "gateway process running" in lowered
        or "gateway is running" in lowered
    ) and "no gateway process" not in lowered
    return running, detail or f"status returned {result.returncode}"


def restart() -> bool:
    log("WARNING gateway is down; starting installed gateway")
    try:
        result = run("gateway", "start")
    except (OSError, subprocess.SubprocessError) as exc:
        log(f"CRITICAL gateway start failed: {type(exc).__name__}")
        return False
    detail = (result.stdout or result.stderr or "").strip().replace("\n", " ")[:500]
    if result.returncode != 0:
        log(f"CRITICAL gateway start returned {result.returncode}: {detail or 'unknown error'}")
        return False
    # Verify the supported status after the detached service has had time to
    # initialize. This also prevents a false recovery log on a failed start.
    for _ in range(6):
        time.sleep(5)
        healthy, status = gateway_running()
        if healthy:
            log(f"RECOVERY gateway is running: {status}")
            return True
    log("CRITICAL gateway start returned success but status stayed down for 30s")
    return False


def main() -> int:
    if not HERMES.exists():
        log(f"ERROR Hermes executable missing: {HERMES}")
        return 2
    if not acquire_lock():
        return 0
    try:
        healthy, detail = gateway_running()
        if healthy:
            return 0
        return 0 if restart() else 1
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
