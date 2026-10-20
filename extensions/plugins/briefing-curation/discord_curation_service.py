#!/usr/bin/env python3
"""Standalone click-to-curate Discord publisher and persistent interaction listener.

Main-owned launcher supplies DISCORD_BOT_TOKEN; never print it. No gateway or cron
configuration is modified by this program. Run --dry-run without a credential.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import discord

from modules.curator import MorningBriefingCurator
from modules.dedup_rank import Story
from modules.preferences import PreferenceStore

ROOT = Path(__file__).resolve().parent
DEFAULT_STATE = ROOT / "state"
ACTIONS = ("view", "hide", "more", "less", "source", "topic", "undo", "section", "up", "down")


def story_key(item: dict) -> str:
    """Stable ID across reruns of the same link, not Python's salted hash."""
    return hashlib.sha256((item.get("url") or item.get("id") or item["title"]).encode()).hexdigest()[:20]


def validate_items(items: list) -> list[dict]:
    if not isinstance(items, list):
        raise ValueError("news input must be a JSON array")
    output = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("title"), str) or not item["title"].strip():
            raise ValueError("each story requires a nonempty title")
        url = item.get("url", "")
        if url and (not isinstance(url, str) or urlparse(url).scheme not in ("http", "https")):
            raise ValueError("story URL must be http(s)")
        source = str(item.get("source") or urlparse(url).hostname or "unknown")[:100]
        topics = item.get("topics", [])
        if not isinstance(topics, list) or not all(isinstance(t, str) for t in topics):
            raise ValueError("topics must be an array of strings")
        output.append({"id": story_key(item), "title": item["title"][:250], "url": url,
                       "source": source, "topics": topics[:10],
                       "summary": str(item.get("summary") or "")[:500],
                       "base_score": float(item.get("base_score", 1))})
    return output


def hacker_news(limit: int = 30) -> list[dict]:
    """Real public HN input; caller may instead pass existing pipeline JSON via --input."""
    def get(url):
        req = urllib.request.Request(url, headers={"User-Agent": "BriefingCuration/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.load(resp)
    ids = get("https://hacker-news.firebaseio.com/v0/topstories.json")[:limit]
    items = []
    for ident in ids:
        try:
            item = get(f"https://hacker-news.firebaseio.com/v0/item/{int(ident)}.json")
            if item and item.get("title") and item.get("type") == "story":
                url = item.get("url") or f"https://news.ycombinator.com/item?id={ident}"
                items.append({"id": str(ident), "title": item["title"], "url": url,
                              "source": urlparse(url).hostname or "Hacker News",
                              "topics": ["ai_tech"], "base_score": item.get("score", 0) / 100})
        except (OSError, ValueError, TypeError):
            continue
    if not items:
        raise RuntimeError("no live news items fetched")
    return validate_items(items)


def persist_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def curate(items: list[dict], preferences_path: Path, scope: str) -> list[dict]:
    engine = MorningBriefingCurator(str(preferences_path), scope)
    stories = engine.curate(engine.build_stories(items))
    sections = engine.prefs.get_snapshot(scope)["sections"]
    stories = sorted(stories, key=lambda s: min((sections.get(t.lower(), {}).get("order", 0) for t in s.topics), default=0))
    return [{"id": s.id, "title": s.title, "url": s.url, "source": s.source,
             "topics": s.topics, "summary": s.summary} for s in stories
            if all(sections.get(t, {}).get("enabled", True) for t in s.topics)]


class StoryView(discord.ui.View):
    def __init__(self, key: str):
        super().__init__(timeout=None)
        for action, label, style in (
            ("view", "View", discord.ButtonStyle.link if False else discord.ButtonStyle.secondary),
            ("hide", "Hide today", discord.ButtonStyle.secondary),
            ("more", "More like this", discord.ButtonStyle.success),
            ("less", "Less like this", discord.ButtonStyle.secondary),
            ("source", "Block source", discord.ButtonStyle.danger),
            ("topic", "Block topic", discord.ButtonStyle.danger),
            ("undo", "Undo", discord.ButtonStyle.secondary),
            ("section", "Toggle section", discord.ButtonStyle.secondary),
            ("up", "Section ↑", discord.ButtonStyle.secondary),
            ("down", "Section ↓", discord.ButtonStyle.secondary),
        ):
            button = discord.ui.Button(label=label, style=style, custom_id=f"cur:{key}:{action}", row=0 if action in ("view", "hide", "more", "less", "source") else 1)
            async def clicked(interaction: discord.Interaction, chosen=action):
                await handle_click(interaction, key, chosen)
            button.callback = clicked
            self.add_item(button)


STATE: Path = DEFAULT_STATE
SCOPE = ""
OWNER = 0
CHANNEL = 0


async def handle_click(interaction: discord.Interaction, key: str, action: str) -> None:
    if interaction.channel_id != CHANNEL or interaction.user.id != OWNER:
        await interaction.response.send_message("Only the configured briefing owner in this channel may curate.", ephemeral=True)
        return
    if action not in ACTIONS:
        await interaction.response.send_message("Unknown action.", ephemeral=True)
        return
    file = STATE / "stories" / f"{key}.json"
    if not file.is_file():
        await interaction.response.send_message("This story is no longer available.", ephemeral=True)
        return
    story = json.loads(file.read_text(encoding="utf-8"))
    prefs = PreferenceStore(str(STATE / "preferences.json"))
    scope = SCOPE
    if action == "view":
        answer = story.get("url") or story["title"]
    elif action == "undo":
        answer = "Previous action reversed." if prefs.undo(scope) else "Nothing to undo."
    elif action == "hide":
        prefs.hide_item(scope, key, story["title"])
        answer = "Hidden until midnight America/Vancouver."
    elif action in ("more", "less"):
        # Source is available on every story; topic is separately blockable.
        getattr(prefs, "more_of" if action == "more" else "less_of")(scope, "source", story["source"].lower())
        answer = f"{'Boosted' if action == 'more' else 'Reduced'} source {story['source']}."
    elif action in ("source", "topic"):
        target = story["source"].lower() if action == "source" else (story.get("topics") or [None])[0]
        if not target:
            answer = "No topic on this story."
        else:
            getattr(prefs, "remove_source" if action == "source" else "remove_topic")(scope, target.lower())
            answer = f"Blocked {action} {target}."
    else:
        section = (story.get("topics") or ["news"])[0].lower()
        snap = prefs.get_snapshot(scope)["sections"]
        if action == "section":
            enabled = not snap.get(section, {}).get("enabled", True)
            prefs.set_section_enabled(scope, section, enabled)
            answer = f"Section {section} {'enabled' if enabled else 'disabled'}."
        else:
            order = snap.get(section, {}).get("order", 0)
            prefs.set_section_order(scope, section, order + (-1 if action == "up" else 1))
            answer = f"Section {section} order now {order + (-1 if action == 'up' else 1)}."
    await interaction.response.send_message(answer, ephemeral=True)


class CurationClient(discord.Client):
    async def setup_hook(self):
        # Register persistent views for all known stories before gateway connection.
        for file in (STATE / "stories").glob("*.json"):
            if len(file.stem) == 20:
                self.add_view(StoryView(file.stem))


async def run(args, items):
    global STATE, SCOPE, OWNER, CHANNEL
    STATE = Path(args.state).resolve()
    OWNER = args.owner_id
    CHANNEL = args.channel_id
    SCOPE = f"discord:{CHANNEL}:{OWNER}"
    if not OWNER or not CHANNEL:
        raise ValueError("--owner-id and --channel-id required")
    if args.publish and items is None:
        raise ValueError("--publish needs --input or --hn")
    if items is not None:
        stories = curate(validate_items(items), STATE / "preferences.json", SCOPE)
        if not stories:
            raise ValueError("curation left no stories to publish")
        if args.dry_run:
            print(json.dumps({"scope": SCOPE, "count": len(stories), "stories": stories[:10]}, ensure_ascii=False))
            return
    if args.dry_run:
        raise ValueError("--dry-run needs --input or --hn")
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN missing")
    client = CurationClient(intents=discord.Intents.default())
    async with client:
        if args.publish:
            async def publish_once():
                await client.wait_until_ready()
                try:
                    channel = await client.fetch_channel(CHANNEL)
                    for story in stories[:10]:
                        key = story["id"]
                        persist_json(STATE / "stories" / f"{key}.json", story)
                        client.add_view(StoryView(key))
                        text = f"**{story['title']}** — {story['source']}\n{story['url']}"
                        msg = await channel.send(text[:1900], view=StoryView(key), allowed_mentions=discord.AllowedMentions.none())
                        print(json.dumps({"message_id": msg.id, "story_id": key, "channel_id": CHANNEL}))
                finally:
                    if args.publish_only:
                        await client.close()
            asyncio.create_task(publish_once())
        await client.start(token)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--channel-id", type=int, required=True)
    p.add_argument("--owner-id", type=int, required=True)
    p.add_argument("--state", default=str(DEFAULT_STATE))
    p.add_argument("--input", type=Path, help="JSON array of normalized news from existing pipeline")
    p.add_argument("--hn", action="store_true", help="fetch live Hacker News top stories")
    p.add_argument("--publish", action="store_true")
    p.add_argument("--publish-only", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if args.hn and args.input:
        p.error("choose only one input")
    items = hacker_news() if args.hn else json.loads(args.input.read_text(encoding="utf-8")) if args.input else None
    asyncio.run(run(args, items))


if __name__ == "__main__":
    main()
