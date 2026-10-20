"""Refresh the local second-brain index without modifying vault notes."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

DEFAULT_PROJECT = "/projects/second-brain" if os.name != "nt" else r"C:\Users\YOUR_USER\hermes-projects\second-brain"
DEFAULT_VAULT = "/opt/data/vault" if os.name != "nt" else r"C:\Users\YOUR_USER\OneDrive\Desktop\thesleyfiles"
PROJECT = Path(os.environ.get("SECOND_BRAIN_PROJECT", DEFAULT_PROJECT)).expanduser()
configured_vault = Path(os.environ.get("OBSIDIAN_VAULT_PATH", "")).expanduser()
canonical_vault = Path(os.environ.get("OBSIDIAN_VAULT_PATH", DEFAULT_VAULT))
VAULT = configured_vault if (configured_vault / ".obsidian").is_dir() else canonical_vault

if not PROJECT.is_dir():
    print(f"ERROR: second-brain project is missing: {PROJECT}")
    raise SystemExit(1)
if not VAULT.is_dir():
    print(f"ERROR: Obsidian vault is missing: {VAULT}")
    raise SystemExit(1)

result = subprocess.run(
    [sys.executable, "-m", "second_brain", "--vault", str(VAULT), "index-refresh"],
    cwd=PROJECT,
    capture_output=True,
    text=True,
    timeout=300,
)
output = (result.stdout + result.stderr).strip()
print(output or f"index-refresh exited with status {result.returncode}")
raise SystemExit(result.returncode)
