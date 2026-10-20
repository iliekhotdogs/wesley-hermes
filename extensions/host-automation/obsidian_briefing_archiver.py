import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path(__file__).resolve().parent.parent))
CRON_ROOT = HERMES_HOME / "cron"
DEFAULT_VAULT = "/opt/data/vault" if os.name != "nt" else r"C:\Users\YOUR_USER\OneDrive\Desktop\thesleyfiles"
VAULT = Path(os.environ.get("OBSIDIAN_VAULT_PATH", DEFAULT_VAULT)).expanduser()
OUTPUT_ROOT = CRON_ROOT / "output"
STATE_PATH = CRON_ROOT / "obsidian_briefing_archive_state.json"
TARGETS = {
    "317656cb145d": "Morning Briefing",
    "33d1edf52c71": "Market Scan",
    "208beac9db1f": "Weekly Market Review",
    "310d1052fa2e": "AI-Tech News Digest",
    "2d8d5d471534": "Weekly Review and Planning",
    "7af1f0e654ec": "Daily Journal",
}


def load_state():
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"files": {}}


def extract_response(text):
    marker = "\n## Response\n"
    if marker not in text:
        return None
    # Cron continuity can embed earlier runs in the same output file.
    # The final response block is the one to archive.
    response = text.rsplit(marker, 1)[1].strip()
    if response.endswith("```"):
        response = response[:-3].rstrip()
    if not response or response == "[SILENT]":
        return None
    return response


def safe_name(name):
    return name.replace("/", "-").replace("\\", "-").replace(":", "-")


def main():
    if not VAULT.is_dir() or not OUTPUT_ROOT.is_dir():
        raise SystemExit(
            f"vault or cron output directory is missing: "
            f"vault={VAULT} exists={VAULT.is_dir()}; "
            f"output={OUTPUT_ROOT} exists={OUTPUT_ROOT.is_dir()}"
        )
    state = load_state()
    archived = state.setdefault("files", {})
    count = 0
    for job_id, title in TARGETS.items():
        job_dir = OUTPUT_ROOT / job_id
        if not job_dir.is_dir():
            continue
        for source in sorted(job_dir.glob("*.md")):
            key = str(source)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if archived.get(key) == digest:
                continue
            response = extract_response(source.read_text(encoding="utf-8", errors="replace"))
            archived[key] = digest
            if response is None:
                continue
            run_date = source.stem[:10]
            try:
                run_dt = datetime.strptime(run_date, "%Y-%m-%d")
                month_dir = VAULT / "pulse" / "briefings" / run_dt.strftime("%Y-%m")
            except ValueError:
                month_dir = VAULT / "pulse" / "briefings" / "unknown-date"
            month_dir.mkdir(parents=True, exist_ok=True)
            note = month_dir / f"{run_date} - {safe_name(title)}.md"
            if note.exists():
                existing = note.read_text(encoding="utf-8")
                if response in existing:
                    continue
                note = month_dir / f"{run_date} - {safe_name(title)} - {source.stem[11:]}.md"
            content = (
                f"---\ntype: automated-briefing\nsource_job: {job_id}\n"
                f"run_file: {source.name}\ncreated: {run_date}\n---\n\n"
                f"# {title} — {run_date}\n\n{response}\n"
            )
            note.write_text(content, encoding="utf-8")
            count += 1
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"archived {count} briefing(s)")


if __name__ == "__main__":
    main()
