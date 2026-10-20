"""Discord NLP handler: parse curation intents from Discord messages.

Processes natural language curation commands sent as Discord messages.
These are then applied to the preference store.

Supported intents:
- "hide <topic/story>" — hide for today
- "more <source/topic>" — boost
- "less <source/topic>" — reduce
- "remove <source/topic>" — permanently block
- "undo" — undo last action
- "toggle <section>" — enable/disable section
- "reorder <section1> <section2>..." — set section order
- "status" — show current preferences
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from modules.curator import CurationResult, MorningBriefingCurator


@dataclass
class ParsedIntent:
    """A parsed curation intent."""
    action: str  # hide, more, less, remove, undo, toggle, reorder, status, help
    target: str = ""
    kind: str = ""  # item, source, topic, section
    confidence: float = 1.0  # parsing confidence


# Pattern matchers for each intent
_PATTERNS = {
    "hide": [
        r"^hide\s+(?:the\s+)?(?:story\s+)?(?:about\s+)?(.+)$",
        r"^remove\s+(?:the\s+)?(?:story\s+)?(?:about\s+)?(?:today['']?s?\s+)?(.+)$",
        r"^skip\s+(?:the\s+)?(?:story\s+)?(?:about\s+)?(.+)$",
        r"^don['']?t\s+show\s+(?:the\s+)?(?:story\s+)?(?:about\s+)?(.+)$",
    ],
    "more": [
        r"^more\s+(?:of\s+)?(?:the\s+)?(.+)$",
        r"^(?:i\s+)?like\s+(?:the\s+)?(?:more\s+)?(.+)$",
        r"^boost\s+(?:the\s+)?(.+)$",
        r"^upvote\s+(?:the\s+)?(.+)$",
    ],
    "less": [
        r"^less\s+(?:of\s+)?(?:the\s+)?(.+)$",
        r"^(?:i\s+)?(?:don['']?t\s+)?(?:want\s+)?(?:less|less\s+of)\s+(?:the\s+)?(.+)$",
        r"^reduce\s+(?:the\s+)?(.+)$",
        r"^downvote\s+(?:the\s+)?(.+)$",
    ],
    "remove": [
        r"^block\s+(?:the\s+)?(.+)$",
        r"^ban\s+(?:the\s+)?(.+)$",
        r"^never\s+show\s+(?:the\s+)?(.+)$",
        r"^unsubscribe\s+(?:from\s+)?(?:the\s+)?(.+)$",
    ],
    "undo": [
        r"^undo$",
        r"^undo\s+(?:last|that|my\s+last\s+action)$",
        r"^take\s+(?:that\s+)?back$",
        r"^revert$",
    ],
    "toggle": [
        r"^toggle\s+(?:section\s+)?(.+)$",
        r"^(?:enable|disable)\s+(?:section\s+)?(.+)$",
        r"^(?:turn\s+(?:on|off))\s+(?:section\s+)?(.+)$",
    ],
    "reorder": [
        r"^reorder\s+(?:sections?\s+)?(.+)$",
        r"^order\s+(?:sections?\s+)?(.+)$",
        r"^sections?\s+(?:order\s+)?(?:=|:)\s+(.+)$",
    ],
    "status": [
        r"^status$",
        r"^prefs$",
        r"^preferences$",
        r"^settings$",
        r"^config$",
        r"^show\s+(?:my\s+)?(?:prefs|preferences|settings|config)$",
    ],
    "help": [
        r"^help$",
        r"^commands$",
        r"^what\s+can\s+i\s+do$",
        r"^how\s+do\s+i\s+curation$",
    ],
}


def parse_discord_message(message: str) -> Optional[ParsedIntent]:
    """Parse a Discord message to extract curation intent."""
    text = message.strip().lower()

    # Check each pattern
    for action, patterns in _PATTERNS.items():
        for pattern in patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                target = match.group(1).strip() if match.lastindex else ""
                # Determine kind based on action and target
                kind = _infer_kind(action, target)
                return ParsedIntent(action=action, target=target, kind=kind)

    return None


def _infer_kind(action: str, target: str) -> str:
    """Infer the kind of a target from the action and target text."""
    if action in ("toggle", "reorder"):
        return "section"
    if action in ("hide", "undo", "status", "help"):
        return ""
    if action in ("more", "less", "remove"):
        # If target is a known section or common source/topic pattern, classify
        # Simple heuristic: if it's a multi-word or looks like a topic vs single word source
        if target in ("ai", "tech", "news", "politics", "crypto", "science", "world"):
            return "topic"
        # Check if it's a section name
        if target in ("news", "ai_tech", "priorities"):
            return "section"
        return "source"
    return ""


class DiscordCurationHandler:
    """Handles curation messages from Discord."""

    def __init__(self, preferences_path: Optional[str] = None, user_id: str = "default"):
        self.curator = MorningBriefingCurator(preferences_path, user_id)

    def handle_message(self, message: str) -> str:
        """Handle a Discord message, returning a response string."""
        intent = parse_discord_message(message)
        if intent is None:
            return ""

        try:
            if intent.action == "status":
                return self._handle_status()
            elif intent.action == "help":
                return self._handle_help()
            elif intent.action == "undo":
                result = self.curator.undo()
                return result.message
            elif intent.action == "hide":
                # Hide acts on most recent matching story or just marks keyword
                result = self.curator.hide_today(intent.target.replace(" ", "_"))
                return result.message
            elif intent.action == "more":
                result = self.curator.more_like_this(intent.target, intent.kind)
                return result.message
            elif intent.action == "less":
                result = self.curator.less_like_this(intent.target, intent.kind)
                return result.message
            elif intent.action == "remove":
                result = self.curator.remove(intent.target, intent.kind)
                return result.message
            elif intent.action == "toggle":
                result = self.curator.toggle_section(intent.target)
                return result.message
            elif intent.action == "reorder":
                sections = [s.strip() for s in intent.target.replace(",", " ").split()]
                result = self.curator.reorder_sections(sections)
                return result.message
            else:
                return f"Unknown action: {intent.action}"
        except Exception as e:
            return f"Error: {e}"

    def _handle_status(self) -> str:
        """Show current preferences status."""
        snap = self.curator.prefs.get_snapshot(self.curator.user_id)
        lines = ["**Curation Preferences**"]
        if snap["removed_sources"]:
            lines.append(f"Blocked sources: {', '.join(snap['removed_sources'])}")
        if snap["removed_topics"]:
            lines.append(f"Blocked topics: {', '.join(snap['removed_topics'])}")
        if snap["source_weights"]:
            lines.append(f"Source weights: {snap['source_weights']}")
        if snap["topic_weights"]:
            lines.append(f"Topic weights: {snap['topic_weights']}")
        lines.append(f"Hidden today: {snap['hidden_count']} items")
        return "\n".join(lines)

    def _handle_help(self) -> str:
        """Show available commands."""
        return (
            "**Curation Commands**\n"
            "• `hide <topic>` — hide stories about topic for today\n"
            "• `more <source/topic>` — boost in future briefings\n"
            "• `less <source/topic>` — reduce in future briefings\n"
            "• `remove <source/topic>` — permanently block\n"
            "• `toggle <section>` — enable/disable section\n"
            "• `reorder <s1> <s2>...` — set section order\n"
            "• `undo` — undo last action\n"
            "• `status` — show preferences\n"
            "• `help` — this message"
        )
