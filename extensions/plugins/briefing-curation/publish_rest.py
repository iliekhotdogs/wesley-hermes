"""Main-only REST publisher. Uses existing credential helper; opens NO gateway.
Never retry a failed/partial publish blindly. Inspect the durable receipt/pending ledger.
"""
import argparse
import asyncio
import importlib.util
import json
from pathlib import Path

import main_gateway_bridge as bridge


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--channel-id', type=int, required=True)
    parser.add_argument('--limit', type=int, default=1, choices=range(1, 11))
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.channel_id not in bridge.CHANNELS:
        parser.error('Only configured briefing or test channel allowed')
    service = bridge.load_service()
    state = bridge.STATE / str(args.channel_id)
    scope = f'discord:{args.channel_id}:{bridge.OWNER}'
    items = service.validate_items(json.loads(args.input.read_text(encoding='utf-8')))
    stories = service.curate(items, state / 'preferences.json', scope)[:args.limit]

    async def components(key):
        return service.StoryView(key).to_components()

    if args.dry_run:
        print(json.dumps({'scope': scope, 'count': len(stories), 'components_per_story': [sum(len(row['components']) for row in asyncio.run(components(s['id']))) for s in stories], 'messages_posted': 0}))
        return
    helper = Path(__file__).resolve().parents[2] / 'scripts' / 'discord_rest.py'
    spec = importlib.util.spec_from_file_location('main_discord_rest', helper)
    rest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rest)
    channel = rest.request('GET', f'/channels/{args.channel_id}')
    if channel.get('guild_id') != str(bridge.GUILD):
        raise RuntimeError('Channel guild mismatch')
    if not (bridge.STATE / 'listener-ready.json').is_file():
        raise RuntimeError('Start existing gateway with curation plugin before publishing')
    ledger_file = state / 'delivery-ledger.json'
    ledger = json.loads(ledger_file.read_text(encoding='utf-8')) if ledger_file.exists() else {}
    for story in stories:
        key = story['id']
        if key in ledger:
            record = ledger[key]
            if not record.get('message_id'):
                raise RuntimeError('Prior pending delivery: inspect Discord before retry')
            actual = rest.request('GET', f"/channels/{args.channel_id}/messages/{record['message_id']}")
            print(json.dumps({'already_delivered': True, 'message_id': actual['id'], 'channel_id': actual['channel_id']}))
            continue
        service.persist_json(state / 'stories' / f'{key}.json', story)
        ledger[key] = {'status': 'pending', 'input': str(args.input)}
        service.persist_json(ledger_file, ledger)
        text = f"**{service.discord.utils.escape_markdown(story['title'])}** — {service.discord.utils.escape_markdown(story['source'])}\n{story['url']}"
        payload = {'content': text[:1900], 'components': asyncio.run(components(key)), 'allowed_mentions': {'parse': [], 'users': [], 'roles': [], 'replied_user': False}, 'tts': False}
        actual = rest.request('POST', f'/channels/{args.channel_id}/messages', payload, 'User-approved isolated interactive briefing test')
        ledger[key] = {'status': 'posted', 'message_id': actual['id'], 'channel_id': actual['channel_id']}
        service.persist_json(ledger_file, ledger)
        checked = rest.request('GET', f"/channels/{args.channel_id}/messages/{actual['id']}")
        count = sum(len(row['components']) for row in checked.get('components', []))
        if checked['channel_id'] != str(args.channel_id) or count != 10:
            raise RuntimeError('Exact message readback did not match button payload')
        ledger[key]['status'] = 'verified_readback'
        service.persist_json(ledger_file, ledger)
        print(json.dumps({'message_id': checked['id'], 'channel_id': checked['channel_id'], 'button_count': count, 'readback': True, 'live_click': False}))


if __name__ == '__main__':
    main()
