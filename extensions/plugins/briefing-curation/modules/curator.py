"""Main curation orchestrator: builds, dedups, ranks stories and formats output.

Integrates with the Discord pipeline as the core engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from modules.preferences import PreferenceStore
from modules.dedup_rank import Deduper, Story, raw_to_story


@dataclass
class CurationResult:
    """Result of a curation action."""
    success: bool
    action_id: str = ""
    message: str = ""
    affected_sections: List[str] = field(default_factory=list)
    preferences_snapshot: Optional[Dict[str, Any]] = None


class MorningBriefingCurator:
    """Orchestrates the full curation pipeline for morning briefings."""

    def __init__(self, preferences_path: Optional[str] = None, user_id: str = "default"):
        self.prefs = PreferenceStore(preferences_path)
        self.user_id = user_id
        self._last_action_id: Optional[str] = None

    def build_stories(self, raw_items: List[Dict[str, Any]]) -> List[Story]:
        """Convert raw items to Story objects."""
        return [raw_to_story(item, i) for i, item in enumerate(raw_items)]

    def curate(self, stories: List[Story]) -> List[Story]:
        """Apply dedup, preference filtering, and ranking."""
        removed_sources = self.prefs.get_removed_sources(self.user_id)
        removed_topics = self.prefs.get_removed_topics(self.user_id)
        hidden_ids = self.prefs.get_hidden_ids(self.user_id)

        # Case-insensitive matching: Discord NLP lowercases input but
        # news sources/topics may have proper capitalization.
        removed_sources_lower = {s.lower() for s in removed_sources}
        removed_topics_lower = {t.lower() for t in removed_topics}

        # Filter out removed/hidden
        filtered = [
            s for s in stories
            if s.source.lower() not in removed_sources_lower
            and s.id not in hidden_ids
            and not any(t.lower() in removed_topics_lower for t in s.topics)
        ]

        # Dedup + rank with preferences (case-insensitive)
        engine = Deduper(
            threshold=0.65,
            source_weights={
                s.lower(): self.prefs.get_source_weight(self.user_id, s)
                for s in set(s.source for s in filtered)
            },
            topic_weights={
                t.lower(): self.prefs.get_topic_weight(self.user_id, t)
                for t in set(t for s in filtered for t in s.topics)
            },
            per_source_cap=3,
        )
        return engine.process(filtered)

    # ── Interactive actions ─────────────────────────────────────────

    def hide_today(self, story_id: str) -> CurationResult:
        """Hide a story for the rest of today (Pacific timezone)."""
        aid = self.prefs.hide_item(self.user_id, story_id)
        self._last_action_id = aid
        return CurationResult(
            True, action_id=aid,
            message=f"Item hidden until midnight Pacific."
        )

    def more_like_this(self, target: str, kind: str = "source") -> CurationResult:
        """Boost a source or topic."""
        aid = self.prefs.more_of(self.user_id, kind, target)
        self._last_action_id = aid
        return CurationResult(
            True, action_id=aid,
            message=f"More '{target}' in future briefings."
        )

    def less_like_this(self, target: str, kind: str = "source") -> CurationResult:
        """Reduce a source or topic."""
        aid = self.prefs.less_of(self.user_id, kind, target)
        self._last_action_id = aid
        weight = (
            self.prefs.get_source_weight(self.user_id, target) if kind == "source"
            else self.prefs.get_topic_weight(self.user_id, target)
        )
        msg = f"Less '{target}' in future briefings."
        if weight <= -3:
            msg += f" (Tip: use 'Remove {kind}' to permanently exclude '{target}')"
        return CurationResult(True, action_id=aid, message=msg)

    def remove(self, target: str, kind: str = "source") -> CurationResult:
        """Permanently remove a source or topic."""
        if kind == "source":
            aid = self.prefs.remove_source(self.user_id, target)
        else:
            aid = self.prefs.remove_topic(self.user_id, target)
        self._last_action_id = aid
        return CurationResult(True, action_id=aid, message=f"'{target}' permanently removed.")

    def undo(self, action_id: str = "") -> CurationResult:
        """Undo the last action."""
        aid = self.prefs.undo(self.user_id, action_id)  # simplified
        if aid is None:
            return CurationResult(False, message="Nothing to undo.")
        return CurationResult(True, action_id=aid, message=f"Action undone.")

    def toggle_section(self, section: str) -> CurationResult:
        """Toggle a section on/off."""
        # Check current state
        uid = self.user_id
        sections = self.prefs._data["users"].get(uid, {}).get("sections", {})
        current = sections.get(section, {}).get("enabled", True)
        aid = self.prefs.set_section_enabled(self.user_id, section, not current)
        self._last_action_id = aid
        return CurationResult(
            True, action_id=aid,
            message=f"Section '{section}' {'disabled' if current else 'enabled'}."
        )

    def reorder_sections(self, order: List[str]) -> CurationResult:
        """Set section order from a list of section names."""
        for i, section in enumerate(order):
            self.prefs.set_section_order(self.user_id, section, i)
        return CurationResult(True, message=f"Section order updated: {', '.join(order)}")

    # ── Output formatting ───────────────────────────────────────────

    def format_for_discord(self, stories: List[Story], max_chars: int = 1500) -> str:
        """Format curated stories into a Discord-friendly digest."""
        section_order = self.prefs.get_section_order(self.user_id)
        # Default sections if none configured
        if not section_order:
            section_order = ["news", "ai_tech", "priorities"]

        parts: List[str] = []
        parts.append("Morning Briefing\n")

        if "news" in section_order:
            parts.append("News")
            news_items = stories[:5]
            for s in news_items:
                parts.append(f"  • {s.title} ({s.source})")
            if not news_items:
                parts.append("  (no items)")

        if "ai_tech" in section_order:
            parts.append("AI/Tech")
            ai_stories = [s for s in stories if "ai" in s.topics or "tech" in s.topics]
            for s in ai_stories[:3]:
                parts.append(f"  • {s.title} ({s.source})")
            if not ai_stories:
                parts.append("  (no items)")

        if "priorities" in section_order:
            parts.append("Priorities")
            for i, s in enumerate(stories[:3], 1):
                parts.append(f"  {i}. {s.title}")

        output = "\n".join(parts)
        if len(output) > max_chars:
            output = output[:max_chars - 3] + "..."
        return output

    def get_preferences_context(self) -> str:
        """Get preferences as a context block for injection into the agent prompt."""
        return self.prefs.export_preferences_block(self.user_id)
