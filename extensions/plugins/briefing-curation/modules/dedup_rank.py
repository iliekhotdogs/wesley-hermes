"""Story deduplication and ranking for morning briefing curation.

Uses TF-IDF-like text similarity for dedup and preference-weighted ranking.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class Story:
    """A single news story / item."""
    id: str
    title: str
    summary: str = ""
    url: str = ""
    source: str = "unknown"
    topics: List[str] = field(default_factory=list)
    published_at: Optional[str] = None
    base_score: float = 1.0

    def text_for_similarity(self) -> str:
        """Combined text for dedup comparison."""
        return f"{self.title} {self.summary}".lower()


def _tokenize(text: str) -> List[str]:
    """Simple tokenization for similarity comparison."""
    return re.findall(r'\b[a-z]{3,}\b', text.lower())


def _cosine_similarity(a_tokens: List[str], b_tokens: List[str]) -> float:
    """Cosine similarity between two token lists."""
    if not a_tokens or not b_tokens:
        return 0.0

    a_set = set(a_tokens)
    b_set = set(b_tokens)
    common = a_set & b_set
    if not common:
        return 0.0

    # IDF-weighted overlap
    a_counts: Dict[str, int] = {}
    b_counts: Dict[str, int] = {}
    for t in a_tokens:
        a_counts[t] = a_counts.get(t, 0) + 1
    for t in b_tokens:
        b_counts[t] = b_counts.get(t, 0) + 1

    dot = sum(a_counts.get(t, 0) * b_counts.get(t, 0) for t in common)
    mag_a = math.sqrt(sum(v**2 for v in a_counts.values()))
    mag_b = math.sqrt(sum(v**2 for v in b_counts.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class Deduper:
    """Deduplicate and rank stories based on preferences."""

    def __init__(
        self,
        threshold: float = 0.65,
        source_weights: Optional[Dict[str, int]] = None,
        topic_weights: Optional[Dict[str, int]] = None,
        per_source_cap: int = 3,
    ):
        self.threshold = threshold
        # Normalize to lowercase for case-insensitive matching
        self.source_weights = {k.lower(): v for k, v in (source_weights or {}).items()}
        self.topic_weights = {k.lower(): v for k, v in (topic_weights or {}).items()}
        self.per_source_cap = per_source_cap

    def _similarity(self, a: Story, b: Story) -> float:
        """Compute similarity between two stories."""
        return _cosine_similarity(
            _tokenize(a.text_for_similarity()),
            _tokenize(b.text_for_similarity())
        )

    def dedup(self, stories: List[Story]) -> List[Story]:
        """Remove near-duplicate stories, keeping the higher-scored one."""
        if not stories:
            return []

        kept: List[Story] = []
        for story in stories:
            is_dup = False
            for existing in kept:
                if self._similarity(story, existing) >= self.threshold:
                    is_dup = True
                    break
            if not is_dup:
                kept.append(story)
        return kept

    def _compute_score(self, story: Story) -> float:
        """Compute preference-adjusted score for a story."""
        score = story.base_score

        # Source weight (case-insensitive)
        weight = self.source_weights.get(story.source.lower(), 0)
        score += weight * 0.5

        # Topic weights (case-insensitive)
        for topic in story.topics:
            t_weight = self.topic_weights.get(topic.lower(), 0)
            score += t_weight * 0.3

        return score

    def rank(self, stories: List[Story]) -> List[Story]:
        """Rank stories by preference-adjusted score."""
        scored = [(self._compute_score(s), s) for s in stories]
        scored.sort(key=lambda x: x[0], reverse=True)

        # Apply per-source cap
        source_counts: Dict[str, int] = {}
        result: List[Story] = []
        for _, story in scored:
            src = story.source
            if source_counts.get(src, 0) >= self.per_source_cap:
                continue
            source_counts[src] = source_counts.get(src, 0) + 1
            result.append(story)

        return result

    def process(self, stories: List[Story]) -> List[Story]:
        """Dedup then rank stories."""
        deduped = self.dedup(stories)
        return self.rank(deduped)


def raw_to_story(item: Dict[str, Any], index: int = 0) -> Story:
    """Convert a raw item dict to a Story object."""
    return Story(
        id=item.get("id", f"story_{index}_{hash(item.get('title', '')) % 10000}"),
        title=item.get("title", "Untitled"),
        summary=item.get("summary", ""),
        url=item.get("url", ""),
        source=item.get("source", "unknown"),
        topics=item.get("topics", []),
        published_at=item.get("published_at"),
        base_score=item.get("base_score", 1.0),
    )
