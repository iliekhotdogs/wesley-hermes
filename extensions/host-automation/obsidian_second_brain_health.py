"""Read-only weekly health report for the Obsidian second brain."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

DEFAULT_PROJECT = "/projects/second-brain" if os.name != "nt" else r"C:\Users\YOUR_USER\hermes-projects\second-brain"
DEFAULT_VAULT = "/opt/data/vault" if os.name != "nt" else r"C:\Users\YOUR_USER\OneDrive\Desktop\thesleyfiles"
PROJECT = Path(os.environ.get("SECOND_BRAIN_PROJECT", DEFAULT_PROJECT))
VAULT = Path(os.environ.get("OBSIDIAN_VAULT_PATH", DEFAULT_VAULT))
INDEX = PROJECT / ".data" / "retrieval.sqlite3"
LINK_RE = re.compile(r"\[\[([^\]|#]+)")


def notes():
    return [p for p in VAULT.rglob("*.md") if p.is_file() and ".obsidian" not in p.parts]


def note_stems():
    stems = set()
    for path in notes():
        stems.add(path.stem.casefold())
        stems.add(path.relative_to(VAULT).with_suffix("").as_posix().casefold())
    return stems


def main():
    if not VAULT.is_dir():
        print(f"ERROR: vault missing: {VAULT}")
        return 1
    sys.path.insert(0, str(PROJECT))
    from second_brain.core import index_is_stale

    all_notes = notes()
    pending_inbox = 0
    broken_links = []
    stems = note_stems()
    for path in all_notes:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if path.parent.name == "inbox" and "status: pending" in text:
            pending_inbox += 1
        if "{{" in text:
            continue
        for target in LINK_RE.findall(text):
            target_key = target.strip().casefold()
            if target_key and target_key not in stems and target_key.split("/")[-1] not in stems:
                broken_links.append(f"{path.relative_to(VAULT).as_posix()} -> [[{target.strip()}]]")
    stale = "missing"
    if INDEX.is_file():
        stale = "stale" if index_is_stale(VAULT, INDEX) else "current"
    print(f"vault_notes={len(all_notes)}")
    print(f"index_status={stale}")
    print(f"inbox_pending={pending_inbox}")
    print(f"broken_wikilinks={len(broken_links)}")
    for item in broken_links[:20]:
        print(f"broken: {item}")
    if len(broken_links) > 20:
        print(f"broken: ... {len(broken_links) - 20} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
