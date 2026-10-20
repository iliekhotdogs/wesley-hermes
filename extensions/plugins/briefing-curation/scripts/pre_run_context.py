"""Pre-run script for cron jobs: injects curation preferences into agent prompt.

This script is run before the agent starts its scheduled run.
It reads the user's curation preferences and injects them as context.

Usage in cron job:
    script: curation/scripts/pre_run_context.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add project root to path for module imports
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent  # curation/ contains modules/
sys.path.insert(0, str(PROJECT_ROOT))


def generate_pre_run_context(user_id: str = "default") -> str:
    """Generate the pre-run context block for the agent prompt."""
    try:
        from modules.preferences import PreferenceStore

        prefs = PreferenceStore(str(Path(os.environ.get("CURATION_STATE", PROJECT_ROOT / "state")) / "preferences.json"))
        return prefs.export_preferences_block(user_id)
    except Exception as e:
        return f"CURATION PREFERENCES ERROR: {e}\n(Using default preferences)"


def generate_post_run_instructions() -> str:
    """Generate instructions for the agent to include curation metadata in output."""
    return """
=== CURATION INSTRUCTIONS ===
After generating the briefing, include a hidden metadata block at the end:
---CURATION_META---
{"section_counts": {"news": N, "ai_tech": N, "priorities": N}, "dedup_removed": N, "total_input": N}
---END_CURATION_META---
This helps the curation pipeline track what was delivered.
=== END CURATION INSTRUCTIONS ===
"""


if __name__ == "__main__":
    # When run as a cron pre-run script, output the context to stdout
    user_id = os.environ.get("CURATION_SCOPE", "")
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    if not user_id:
        raise SystemExit("CURATION_SCOPE required: discord:<channel_id>:<owner_id>")

    context = generate_pre_run_context(user_id)
    instructions = generate_post_run_instructions()

    # Output as JSON for the cron system to capture
    output = {
        "context": context,
        "instructions": instructions,
        "user_id": user_id,
    }
    print(json.dumps(output))
