"""Main-owned single-gateway bridge for staged curation buttons.
Never starts a gateway or reads credentials. Scope is fixed to the authorized server owner.
"""
import importlib.util
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

OWNER = 0
GUILD = 0
CHANNELS = {0, 0}
ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'state'
LOG = logging.getLogger('briefing-curation')


def load_service():
    path = str(ROOT)
    if path not in sys.path:
        sys.path.insert(0, path)
    spec = importlib.util.spec_from_file_location('briefing_curation_service', ROOT / 'discord_curation_service.py')
    service = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(service)
    return service


def wire(native, adapter):
    service = load_service()
    if getattr(native, '_briefing_curation_wired', False):
        return

    async def on_interaction(interaction):
        data = interaction.data or {}
        match = re.fullmatch(r'cur:([0-9a-f]{20}):(view|hide|more|less|source|topic|undo|section|up|down)', data.get('custom_id', ''))
        if not match:
            return
        if interaction.guild_id != GUILD or interaction.channel_id not in CHANNELS or interaction.user.id != OWNER:
            await interaction.response.send_message('These briefing controls are restricted to the configured owner and briefing/test channels.', ephemeral=True)
            return
        key, action = match.groups()
        channel = interaction.channel_id
        service.STATE = STATE / str(channel)
        service.CHANNEL = channel
        service.OWNER = OWNER
        service.SCOPE = f'discord:{channel}:{OWNER}'
        try:
            if not (service.STATE / 'stories' / f'{key}.json').is_file():
                await interaction.response.send_message('This story is no longer available.', ephemeral=True)
                return
            story = json.loads((service.STATE / 'stories' / f'{key}.json').read_text(encoding='utf-8'))
            if action == 'view':
                text = f"**{story['title']}**\n{story.get('summary', '')}\n{story.get('url', '')}"
                await interaction.response.send_message(text[:1900], ephemeral=True, allowed_mentions=service.discord.AllowedMentions.none())
            else:
                await service.handle_click(interaction, key, action)
                # Immediate visual removal, while retaining controls for View/Undo.
                if action == 'hide':
                    await interaction.message.edit(content='*Hidden for today. Use View to inspect the story or Undo to reverse your latest preference change.*', allowed_mentions=service.discord.AllowedMentions.none())
                elif action == 'undo':
                    prefs = service.PreferenceStore(str(service.STATE / 'preferences.json'))
                    if key not in prefs.get_hidden_ids(service.SCOPE):
                        text = f"**{story['title']}** — {story['source']}\n{story.get('url', '')}"
                        await interaction.message.edit(content=text[:1900], allowed_mentions=service.discord.AllowedMentions.none())
            receipt = {'utc': datetime.now(timezone.utc).isoformat(), 'channel_id': str(channel), 'message_id': str(interaction.message.id), 'story_id': key, 'action': action, 'authorized': True}
            service.STATE.mkdir(parents=True, exist_ok=True)
            with (service.STATE / 'interaction_receipts.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(receipt) + '\n')
        except Exception:
            LOG.exception('Curation action failed: %s', action)
            if not interaction.response.is_done():
                await interaction.response.send_message('The action failed; your briefing jobs are unchanged. Please notify Main.', ephemeral=True)

    native.add_listener(on_interaction, 'on_interaction')
    native._briefing_curation_wired = True
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / 'listener-ready.json').write_text(json.dumps({'utc': datetime.now(timezone.utc).isoformat(), 'gateway_bridge': True, 'single_gateway': True}), encoding='utf-8')
    LOG.info('Single-gateway briefing curation listener ready')
