"""Emit a compact deterministic Hermes systems summary."""
from __future__ import annotations
import json, os, re, sqlite3, subprocess
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData/Local/hermes"))

def run(*args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=25).stdout.strip()
    except Exception as e:
        return f"unavailable ({type(e).__name__})"

def main():
    jobs = []
    try:
        jobs = json.loads((HOME / "cron/jobs.json").read_text(encoding="utf-8"))
    except Exception: pass
    if isinstance(jobs, dict): jobs = jobs.get("jobs", [])
    active = [j for j in jobs if j.get("enabled", True) and not j.get("paused", False)]
    reminders = [j.get("name", "unnamed") for j in active if re.search(r"remind", (j.get("name", "") + " " + j.get("prompt", "")), re.I)]
    failed = [j.get("name", j.get("id", "unnamed")) for j in active if j.get("last_status") not in (None, "ok")]
    db = HOME / "cron/executions.db"
    if not db.exists(): failed.append("execution DB unavailable")
    try:
        tasks = json.loads(run("hermes", "kanban", "list", "--json"))
        live = [f"{t.get('id')} {t.get('title')}" for t in tasks if t.get("status") in ("running", "blocked")]
    except Exception: live = ["Kanban unavailable"]
    gw = run("hermes", "gateway", "status").replace("\n", " ")
    chrome = Path.home() / ".agent-browser" / "browsers"
    browser = "installed" if chrome.exists() and any(chrome.rglob("chrome.exe")) else "runtime missing"
    print("SYSTEMS SUMMARY")
    print(f"Gateway: {gw[:180]}")
    print(f"Browser: {browser}")
    print("Cron failures: " + (", ".join(failed[:5]) if failed else "none detected"))
    print("Kanban live: " + ("; ".join(live[:5]) if live else "none"))
    print("Reminders: " + (", ".join(reminders[:5]) if reminders else "none configured"))
    print(f"Cron active: {len(active)}")

if __name__ == "__main__": main()
