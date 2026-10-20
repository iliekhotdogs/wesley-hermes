"""Scoped preference persistence for morning briefing curation.

Zoneinfo-aware: America/Vancouver for day boundaries, durable JSON storage.
Supports per-user scoping, undo history, and section ordering.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("America/Vancouver")
except ImportError:
    _TZ = None  # fallback to UTC+offset


def _now_pacific() -> datetime:
    """Current time in America/Vancouver timezone."""
    if _TZ is not None:
        return datetime.now(_TZ)
    # Fallback: Pacific is UTC-7 (PDT) or UTC-8 (PST)
    return datetime.utcnow() + timedelta(hours=-7)


def _next_midnight_pacific() -> datetime:
    """Next midnight in Pacific timezone."""
    now = _now_pacific()
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)


@dataclass
class CurationAction:
    """A single curation action (for undo history)."""
    action_id: str
    action_type: str  # hide, more, less, remove, toggle, reorder
    target: str
    kind: str  # item, source, topic, section
    timestamp: float
    previous_state: Optional[Dict[str, Any]] = None


@dataclass
class ScopedPreferences:
    """User-scoped preferences."""
    user_id: str
    hidden_ids: Dict[str, str] = field(default_factory=dict)  # id -> label
    hidden_expiry: Dict[str, float] = field(default_factory=dict)  # id -> expiry timestamp
    removed_sources: List[str] = field(default_factory=list)
    removed_topics: List[str] = field(default_factory=list)
    source_weights: Dict[str, int] = field(default_factory=dict)
    topic_weights: Dict[str, int] = field(default_factory=dict)
    sections: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    action_history: List[str] = field(default_factory=list)  # action_ids
    max_history: int = 50


class PreferenceStore:
    """Durable JSON-based preference store with Pacific timezone awareness."""

    def __init__(self, preferences_path: Optional[str] = None):
        if preferences_path is None:
            preferences_path = str(
                Path(__file__).parent.parent / "configs" / "preferences.json"
            )
        self.path = Path(preferences_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = {"users": {}}
        self._last_action_id: Optional[str] = None
        self._load()

    def _load(self) -> None:
        """Load preferences from disk."""
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                if "users" not in self._data:
                    self._data["users"] = {}
            except (json.JSONDecodeError, IOError):
                self._data = {"users": {}}

    def _save(self) -> None:
        """Persist preferences to disk atomically."""
        tmp = self.path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False, default=str)
        tmp.replace(self.path)

    def get_user(self, user_id: str) -> ScopedPreferences:
        """Get or create scoped preferences for a user."""
        uid = str(user_id)
        if uid not in self._data["users"]:
            self._data["users"][uid] = {
                "hidden_ids": {},
                "hidden_expiry": {},
                "removed_sources": [],
                "removed_topics": [],
                "source_weights": {},
                "topic_weights": {},
                "sections": {},
                "action_history": [],
            }
        u = self._data["users"][uid]
        # Prune expired hidden items
        now_ts = time.time()
        expired = [k for k, v in u.get("hidden_expiry", {}).items() if v < now_ts]
        for k in expired:
            u["hidden_ids"].pop(k, None)
            u["hidden_expiry"].pop(k, None)

        return ScopedPreferences(
            user_id=uid,
            hidden_ids=u.get("hidden_ids", {}),
            hidden_expiry=u.get("hidden_expiry", {}),
            removed_sources=u.get("removed_sources", []),
            removed_topics=u.get("removed_topics", []),
            source_weights=u.get("source_weights", {}),
            topic_weights=u.get("topic_weights", {}),
            sections=u.get("sections", {}),
            action_history=u.get("action_history", []),
        )

    def _record_action(self, user_id: str, action: CurationAction) -> None:
        """Record an action for undo support."""
        uid = str(user_id)
        u = self._data["users"][uid]
        history = u.get("action_history", [])
        history.append({"id": action.action_id, "type": action.action_type,
                        "target": action.target, "kind": action.kind,
                        "previous": action.previous_state})
        # Trim history
        if len(history) > 50:
            history = history[-50:]
        u["action_history"] = history
        self._last_action_id = action.action_id

    # ── Hide / Unhide ───────────────────────────────────────────────

    def _ensure_user(self, user_id: str) -> Dict[str, Any]:
        """Auto-create user entry if it doesn't exist."""
        uid = str(user_id)
        if uid not in self._data["users"]:
            self._data["users"][uid] = {
                "hidden_ids": {},
                "hidden_expiry": {},
                "removed_sources": [],
                "removed_topics": [],
                "source_weights": {},
                "topic_weights": {},
                "sections": {},
                "action_history": [],
            }
        return self._data["users"][uid]

    def hide_item(self, user_id: str, item_id: str, label: str = "") -> str:
        """Hide an item until midnight Pacific."""
        uid = str(user_id)
        u = self._ensure_user(user_id)
        expiry = _next_midnight_pacific().timestamp()
        previous = {"hidden": item_id in self.get_hidden_ids(user_id),
                    "label": u["hidden_ids"].get(item_id),
                    "expiry": u["hidden_expiry"].get(item_id)}
        u["hidden_ids"][item_id] = label or item_id
        u["hidden_expiry"][item_id] = expiry

        aid = f"act_{uuid.uuid4().hex[:8]}"
        self._record_action(user_id, CurationAction(
            action_id=aid, action_type="hide", target=item_id, kind="item",
            timestamp=time.time(),
            previous_state=previous
        ))
        self._save()
        return aid

    def unhide_item(self, user_id: str, item_id: str) -> Optional[str]:
        """Unhide an item before midnight."""
        uid = str(user_id)
        u = self._ensure_user(user_id)
        if item_id in u.get("hidden_ids", {}):
            label = u["hidden_ids"].pop(item_id)
            u["hidden_expiry"].pop(item_id, None)
            aid = f"act_{uuid.uuid4().hex[:8]}"
            self._record_action(user_id, CurationAction(
                action_id=aid, action_type="unhide", target=item_id, kind="item",
                timestamp=time.time(),
                previous_state={"hidden": True, "label": label}
            ))
            self._save()
            return aid
        return None

    # ── Source / Topic Weights ──────────────────────────────────────

    def more_of(self, user_id: str, kind: str, target: str) -> str:
        """Boost a source or topic weight."""
        uid = str(user_id)
        u = self._ensure_user(user_id)
        key = f"{kind}_weights"
        weights = u.setdefault(key, {})
        weights[target] = weights.get(target, 0) + 1

        aid = f"act_{uuid.uuid4().hex[:8]}"
        self._record_action(user_id, CurationAction(
            action_id=aid, action_type="more", target=target, kind=kind,
            timestamp=time.time(),
            previous_state={"weight": weights[target] - 1}
        ))
        self._save()
        return aid

    def less_of(self, user_id: str, kind: str, target: str) -> str:
        """Reduce a source or topic weight."""
        uid = str(user_id)
        u = self._ensure_user(user_id)
        key = f"{kind}_weights"
        weights = u.setdefault(key, {})
        weights[target] = weights.get(target, 0) - 1

        aid = f"act_{uuid.uuid4().hex[:8]}"
        self._record_action(user_id, CurationAction(
            action_id=aid, action_type="less", target=target, kind=kind,
            timestamp=time.time(),
            previous_state={"weight": weights[target] + 1}
        ))
        self._save()
        return aid

    def get_source_weight(self, user_id: str, source: str) -> int:
        uid = str(user_id)
        return sum(v for k, v in self._data["users"].get(uid, {}).get("source_weights", {}).items() if k.lower() == source.lower())

    def get_topic_weight(self, user_id: str, topic: str) -> int:
        uid = str(user_id)
        return sum(v for k, v in self._data["users"].get(uid, {}).get("topic_weights", {}).items() if k.lower() == topic.lower())

    # ── Remove Source / Topic ───────────────────────────────────────

    def remove_source(self, user_id: str, source: str) -> str:
        """Permanently remove a source from future output."""
        uid = str(user_id)
        u = self._ensure_user(user_id)
        was_removed = source in u.get("removed_sources", [])
        if source not in u.get("removed_sources", []):
            u.setdefault("removed_sources", []).append(source)
        aid = f"act_{uuid.uuid4().hex[:8]}"
        self._record_action(user_id, CurationAction(
            action_id=aid, action_type="remove", target=source, kind="source",
            timestamp=time.time(), previous_state={"removed": was_removed}
        ))
        self._save()
        return aid

    def remove_topic(self, user_id: str, topic: str) -> str:
        """Permanently remove a topic from future output."""
        uid = str(user_id)
        u = self._ensure_user(user_id)
        was_removed = topic in u.get("removed_topics", [])
        if topic not in u.get("removed_topics", []):
            u.setdefault("removed_topics", []).append(topic)
        aid = f"act_{uuid.uuid4().hex[:8]}"
        self._record_action(user_id, CurationAction(
            action_id=aid, action_type="remove", target=topic, kind="topic",
            timestamp=time.time(), previous_state={"removed": was_removed}
        ))
        self._save()
        return aid

    def restore_source(self, user_id: str, source: str) -> Optional[str]:
        """Restore a previously removed source."""
        uid = str(user_id)
        u = self._data["users"][uid]
        if source in u.get("removed_sources", []):
            u["removed_sources"].remove(source)
            aid = f"act_{uuid.uuid4().hex[:8]}"
            self._record_action(user_id, CurationAction(
                action_id=aid, action_type="restore", target=source, kind="source",
                timestamp=time.time()
            ))
            self._save()
            return aid
        return None

    # ── Undo ────────────────────────────────────────────────────────

    def undo(self, user_id: str, action_id: str = "") -> Optional[str]:
        """Undo the last action (or a specific action_id)."""
        uid = str(user_id)
        u = self._ensure_user(user_id)
        if not u:
            return None

        history = u.get("action_history", [])
        if not history:
            return None

        entry = next((a for a in reversed(history) if isinstance(a, dict) and
                      (not action_id or a["id"] == action_id)), None)
        if entry is None:
            return None
        typ, target, kind = entry["type"], entry["target"], entry["kind"]
        prev = entry.get("previous") or {}
        if typ == "hide":
            if prev.get("hidden"):
                u["hidden_ids"][target] = prev["label"]
                u["hidden_expiry"][target] = prev["expiry"]
            else:
                u["hidden_ids"].pop(target, None)
                u["hidden_expiry"].pop(target, None)
        elif typ in ("more", "less"):
            weights = u[f"{kind}_weights"]
            if prev.get("weight", 0):
                weights[target] = prev["weight"]
            else:
                weights.pop(target, None)
        elif typ == "remove" and not prev.get("removed", False):
            removed = u[f"removed_{kind}s"]
            if target in removed:
                removed.remove(target)
        elif typ == "toggle":
            u["sections"][target]["enabled"] = prev.get("enabled", True)
        else:
            return None
        history.remove(entry)
        self._save()
        return entry["id"]

    # ── Sections ────────────────────────────────────────────────────

    def set_section_enabled(self, user_id: str, section: str, enabled: bool) -> str:
        uid = str(user_id)
        u = self._ensure_user(user_id)
        sections = u.setdefault("sections", {})
        sec = sections.setdefault(section, {})
        previous = sec.get("enabled", True)
        sec["enabled"] = enabled

        aid = f"act_{uuid.uuid4().hex[:8]}"
        self._record_action(user_id, CurationAction(
            action_id=aid, action_type="toggle", target=section, kind="section",
            timestamp=time.time(),
            previous_state={"enabled": previous}
        ))
        self._save()
        return aid

    def set_section_order(self, user_id: str, section: str, order: int) -> None:
        uid = str(user_id)
        u = self._ensure_user(user_id)
        sections = u.setdefault("sections", {})
        sec = sections.setdefault(section, {})
        sec["order"] = order
        self._save()

    def get_section_order(self, user_id: str) -> List[str]:
        uid = str(user_id)
        u = self._data["users"].get(uid, {})
        sections = u.get("sections", {})
        ordered = sorted(sections.items(), key=lambda x: x[1].get("order", 0))
        return [name for name, info in ordered if info.get("enabled", True)]

    # ── Query helpers ───────────────────────────────────────────────

    def get_hidden_ids(self, user_id: str) -> set:
        """Get non-expired hidden IDs."""
        uid = str(user_id)
        u = self._data["users"].get(uid, {})
        now_ts = time.time()
        return {
            k for k, v in u.get("hidden_expiry", {}).items()
            if v >= now_ts
        }

    def get_removed_sources(self, user_id: str) -> set:
        uid = str(user_id)
        return set(self._data["users"].get(uid, {}).get("removed_sources", []))

    def get_removed_topics(self, user_id: str) -> set:
        uid = str(user_id)
        return set(self._data["users"].get(uid, {}).get("removed_topics", []))

    def get_snapshot(self, user_id: str) -> Dict[str, Any]:
        """Get a complete snapshot of user preferences."""
        uid = str(user_id)
        u = self._data["users"].get(uid, {})
        return {
            "removed_sources": list(u.get("removed_sources", [])),
            "removed_topics": list(u.get("removed_topics", [])),
            "source_weights": dict(u.get("source_weights", {})),
            "topic_weights": dict(u.get("topic_weights", {})),
            "sections": dict(u.get("sections", {})),
            "hidden_count": len(u.get("hidden_ids", {})),
            "pacific_time": _now_pacific().isoformat(),
        }

    def export_preferences_block(self, user_id: str) -> str:
        """Export preferences as a formatted context block for the agent prompt."""
        snap = self.get_snapshot(user_id)
        lines = ["=== CURATION PREFERENCES ==="]
        if snap["removed_sources"]:
            lines.append(f"Blocked sources: {', '.join(snap['removed_sources'])}")
        if snap["removed_topics"]:
            lines.append(f"Blocked topics: {', '.join(snap['removed_topics'])}")
        if snap["source_weights"]:
            boosts = [f"{k}(+{v})" for k, v in snap["source_weights"].items() if v > 0]
            cuts = [f"{k}({v})" for k, v in snap["source_weights"].items() if v < 0]
            if boosts:
                lines.append(f"Boosted sources: {', '.join(boosts)}")
            if cuts:
                lines.append(f"Reduced sources: {', '.join(cuts)}")
        if snap["topic_weights"]:
            boosts = [f"{k}(+{v})" for k, v in snap["topic_weights"].items() if v > 0]
            cuts = [f"{k}({v})" for k, v in snap["topic_weights"].items() if v < 0]
            if boosts:
                lines.append(f"Boosted topics: {', '.join(boosts)}")
            if cuts:
                lines.append(f"Reduced topics: {', '.join(cuts)}")
        lines.append(f"Hidden items (today): {snap['hidden_count']}")
        lines.append(f"Current Pacific time: {snap['pacific_time']}")
        lines.append("=== END CURATION PREFERENCES ===")
        return "\n".join(lines)
