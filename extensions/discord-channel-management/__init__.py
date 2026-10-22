"""Guild-scoped channel tool with an enforced human gate for destructive work."""
import hashlib
import json
import os
import uuid
from tools.discord_tool import DiscordAPIError, _discord_request, _get_bot_token

TYPES = {'text': 0, 'voice': 2, 'category': 4}
SCHEMA = {'name': 'discord_channels', 'description': 'Create or edit channels in the configured guild. Deletion and category changes require fresh interactive human approval.', 'parameters': {'type': 'object', 'properties': {'action': {'type': 'string', 'enum': ['create', 'edit', 'delete']}, 'channel_id': {'type': 'string'}, 'name': {'type': 'string'}, 'topic': {'type': 'string'}, 'parent_id': {'type': 'string'}, 'channel_type': {'type': 'string', 'enum': list(TYPES)}}, 'required': ['action'], 'additionalProperties': False}}


def identifier(value):
    value = str(value or '')
    return value if value.isdecimal() and 15 <= len(value) <= 22 else None


def approve(action, guild, channel, body):
    from tools.approval import request_tool_approval
    from tools.approval_context import _get_approval_mode
    # Smart/off policies must not silently convert an explicit-consent operation
    # into a model decision. Main is configured manual; cron/unattended deny.
    if _get_approval_mode() != 'manual':
        return False
    details = json.dumps({'action': action, 'guild': guild, 'channel': channel, 'changes': body}, sort_keys=True)
    key = 'discord_channels:' + hashlib.sha256(details.encode()).hexdigest()[:24] + ':' + uuid.uuid4().hex
    result = request_tool_approval('discord_channels', 'Approve this exact Discord operation: ' + details, rule_key=key)
    return result.get('approved') is True


def _run(args, **_):
    try:
        guild = identifier(os.environ.get('DISCORD_GUILD_ID'))
        if not guild:
            return json.dumps({'error': 'Configure DISCORD_GUILD_ID before channel management.'})
        action = args.get('action')
        channel = identifier(args.get('channel_id'))
        kind = args.get('channel_type', 'text')
        if action not in ('create', 'edit', 'delete') or (action != 'create' and not channel):
            return json.dumps({'error': 'Invalid action or channel_id.'})
        body = {}
        if 'name' in args:
            name = str(args['name']).strip()
            if not 1 <= len(name) <= 100:
                return json.dumps({'error': 'Channel name must have 1–100 characters.'})
            body['name'] = name
        if action == 'create':
            if 'name' not in body or kind not in TYPES:
                return json.dumps({'error': 'Create requires name and a valid channel_type.'})
            body['type'] = TYPES[kind]
        if 'topic' in args:
            body['topic'] = str(args['topic'])[:1024]
        if 'parent_id' in args:
            parent = args['parent_id']
            if parent and not identifier(parent):
                return json.dumps({'error': 'Invalid parent_id.'})
            body['parent_id'] = str(parent) if parent else None
        if action == 'edit' and not body:
            return json.dumps({'error': 'Edit requires a changed field.'})
        # Gate before token retrieval or any network access. No model argument
        # can bypass this; old confirm_delete values carry no authority.
        sensitive = action == 'delete' or 'parent_id' in body
        if sensitive and not approve(action, guild, channel, body):
            return json.dumps({'error': 'Blocked: fresh human approval is required for this exact operation.'})
        token = _get_bot_token()
        if not token:
            return json.dumps({'error': 'Discord token unavailable.'})
        if action != 'create':
            current = _discord_request('GET', '/channels/' + channel, token)
            if current.get('guild_id') != guild:
                return json.dumps({'error': 'Channel is outside the configured guild.'})
            if 'topic' in body and current.get('type') != 0:
                return json.dumps({'error': 'Topics require a text channel.'})
        elif 'topic' in body and kind != 'text':
            return json.dumps({'error': 'Topics require a text channel.'})
        if body.get('parent_id'):
            parent = _discord_request('GET', '/channels/' + body['parent_id'], token)
            if parent.get('guild_id') != guild or parent.get('type') != 4:
                return json.dumps({'error': 'Parent must be a category in the configured guild.'})
        if action == 'delete':
            _discord_request('DELETE', '/channels/' + channel, token)
            return json.dumps({'success': True, 'deleted_channel_id': channel})
        method, path = ('POST', '/guilds/' + guild + '/channels') if action == 'create' else ('PATCH', '/channels/' + channel)
        result = _discord_request(method, path, token, body=body)
        return json.dumps({'success': True, 'channel_id': result['id'], 'name': result.get('name')})
    except DiscordAPIError as exc:
        return json.dumps({'error': 'Discord HTTP ' + str(exc.status)})
    except Exception as exc:
        return json.dumps({'error': 'Channel operation failed: ' + type(exc).__name__})


def register(ctx):
    ctx.register_tool(name='discord_channels', toolset='discord_channels', schema=SCHEMA, handler=_run, description=SCHEMA['description'], emoji='🗂️')
