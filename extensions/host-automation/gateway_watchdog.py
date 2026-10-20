#!/usr/bin/env python
"""Hermes gateway health check.

Runs as a Hermes cron job every 5-10 minutes. One check covers the gateway
status command, the gateway heartbeat/state record (doctor result) including
Discord connectivity, and host RAM. It never restarts anything: restarts are
the OS service manager's job. Output is printed only when health changes;
healthy unchanged checks are silent.
"""

from __future__ import annotations
import ctypes
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes"))
LOG = HOME / "logs" / "gateway_watchdog.log"
STATE = HOME / "state" / "gateway_watchdog_state.json"
HEARTBEAT = HOME / "state" / "gateway.heartbeat"
GATEWAY_STATE = HOME / "gateway_state.json"
HERMES_EXE = os.environ.get("HERMES_EXE", "hermes")
GATEWAY_PROFILE = os.environ.get("GATEWAY_PROFILE", "main")
HEARTBEAT_MAX_AGE_S = 120
RAM_ALERT_PERCENT = float(os.environ.get("RAM_ALERT_PERCENT", "90"))
RAM_ALERT_HOLD_MINUTES = float(os.environ.get("RAM_ALERT_HOLD_MINUTES", "10"))


def record(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")


def read_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def gateway_status() -> str | None:
    """Return an issue string, or None when the status command reports running."""
    try:
        result = subprocess.run(
            [HERMES_EXE, "-p", GATEWAY_PROFILE, "gateway", "status"],
            capture_output=True, text=True, timeout=20, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"gateway status command failed: {type(exc).__name__}"
    detail = (result.stdout or result.stderr or "").strip().replace("\n", " ")[:300]
    lowered = detail.lower()
    # The status command is authoritative; do not infer health from a random
    # hermes.exe process, because that could be the CLI or desktop app.
    running = result.returncode == 0 and (
        "gateway process detected" in lowered
        or "gateway process running" in lowered
        or "gateway is running" in lowered
    ) and "no gateway process" not in lowered
    return None if running else f"gateway not running: {detail or 'status returned ' + str(result.returncode)}"


def doctor_status() -> str | None:
    """Heartbeat freshness, gateway_state and Discord connectivity from the gateway's own records."""
    heartbeat = read_json(HEARTBEAT)
    state = read_json(GATEWAY_STATE)
    if not heartbeat or not state:
        return "gateway heartbeat/state missing"
    try:
        age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(heartbeat.get("updated_at"))).total_seconds()
    except (TypeError, ValueError):
        return "gateway heartbeat timestamp invalid"
    if state.get("gateway_state") != "running":
        return f"gateway state={state.get('gateway_state', 'unknown')}"
    if age > HEARTBEAT_MAX_AGE_S:
        return f"gateway heartbeat is {age:.0f}s old"
    discord_state = str(state.get("platforms", {}).get("discord", {}).get("state", "")).lower()
    if discord_state in {"fatal", "disconnected", "unavailable"}:
        return f"Discord state={discord_state}"
    return None


def ram_percent() -> float | None:
    """Used physical memory percent; None when the platform gives no stdlib reading."""
    if sys.platform == "win32":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong) for name in ("total", "avail", "pagetotal", "pageavail", "virttotal", "virtavail", "extavail")]
        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(MemoryStatus)
        return float(status.dwMemoryLoad) if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)) else None
    try:
        info = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
        total, available = (int(info[key].split()[0]) for key in ("MemTotal", "MemAvailable"))
        return 100.0 * (total - available) / total
    except (OSError, KeyError, ValueError, ZeroDivisionError):
        return None


def ram_notice(state: dict, percent: float | None, now: float) -> str | None:
    """Alert only after RAM stays high for the hold window; emit recovery once."""
    if percent is not None and percent >= RAM_ALERT_PERCENT:
        state.setdefault("ram_high_since", now)
        if not state.get("ram_alerted") and now - state["ram_high_since"] >= RAM_ALERT_HOLD_MINUTES * 60:
            state["ram_alerted"] = True
            return f"RAM at {percent:.0f}% for {RAM_ALERT_HOLD_MINUTES:g}+ minutes"
        return None
    state.pop("ram_high_since", None)
    if state.pop("ram_alerted", None):
        return "RAM recovered" + (f" ({percent:.0f}%)" if percent is not None else "")
    return None


def main() -> int:
    state = read_json(STATE) or {}
    issues = [issue for issue in (gateway_status(), doctor_status()) if issue]
    lines = []
    if issues != state.get("issues", []):
        lines.extend(f"Gateway health: {issue}" for issue in issues)
        if not issues:
            lines.append("Gateway health recovered.")
    state["issues"] = issues
    notice = ram_notice(state, ram_percent(), time.time())
    if notice:
        lines.append(notice)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE.with_suffix(".tmp")
    temp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temp.replace(STATE)
    for line in lines:
        record(line)
    if lines:
        print("\n".join(lines))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
