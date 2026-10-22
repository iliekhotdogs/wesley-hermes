"""Read-only context for the coordinator; Lib remains the memory writer."""
import json
from contextlib import closing
from pathlib import Path
import sqlite3
from datetime import datetime, timezone

import yaml

ROOT = Path('/opt/data')
JOURNAL = ROOT / 'operations/setup-changes.jsonl'


def status(_args=None, **_kwargs):
    profiles = {}
    for name in ('main', 'builder', 'cowsearcher', 'speedy', 'cron', 'lib'):
        home = ROOT / 'profiles' / name
        cfg = yaml.safe_load((home / 'config.yaml').read_text()) or {}
        profiles[name] = {
            'model': (cfg.get('model') or {}).get('default'),
            'provider': (cfg.get('model') or {}).get('provider'),
            'memory_enabled': (cfg.get('memory') or {}).get('memory_enabled'),
            'discord_toolsets': (cfg.get('platform_toolsets') or {}).get('discord'),
        }
    changes = []
    if JOURNAL.is_file():
        for line in JOURNAL.read_text().splitlines()[-30:]:
            try:
                changes.append(json.loads(line))
            except ValueError:
                pass
    main_cfg = yaml.safe_load((ROOT / 'profiles/main/config.yaml').read_text())
    history_stores = {}
    for name, path in [('default', ROOT / 'state.db'), ('main', ROOT / 'profiles/main/state.db'),
                       ('lib', ROOT / 'profiles/lib/state.db')]:
        if path.is_file():
            with closing(sqlite3.connect(f'file:{path}?mode=ro', uri=True)) as db:
                history_stores[name] = {
                    'sessions': db.execute('SELECT count(*) FROM sessions').fetchone()[0],
                    'messages': db.execute('SELECT count(*) FROM messages').fetchone()[0],
                }
    tasks = []
    board = ROOT / 'kanban.db'
    if board.is_file():
        with closing(sqlite3.connect(f'file:{board}?mode=ro', uri=True)) as db:
            db.row_factory = sqlite3.Row
            tasks = [dict(r) for r in db.execute(
                'SELECT id,title,assignee,status,created_at,last_failure_error '
                'FROM tasks ORDER BY created_at DESC LIMIT 12')]
    return json.dumps({
        'observed_at_utc': datetime.now(timezone.utc).isoformat(),
        'runtime': {'container': Path('/.dockerenv').exists(), 'hermes_code': '/opt/hermes',
                    'persistent_data': str(ROOT), 'vault': '/opt/data/vault',
                    'projects': '/projects', 'timezone': main_cfg.get('timezone'),
                    'host_docker_socket_mounted': Path('/var/run/docker.sock').exists(),
                    'builder_execution': 'isolated hermes-builder service via task-workspace snapshot and inference-only proxy' if Path('/opt/isolation/worker-shim').exists() else 'shared-container workers'},
        'configured_profiles_on_disk': profiles, 'kanban_configuration_on_disk': main_cfg.get('kanban'),
        'configuration_is_loaded_state': False,
        'recorded_setup_changes': changes, 'recent_tasks': tasks,
        'history_stores': history_stores,
        'history': 'Use session_search for prior Main conversations across Discord threads. Older history from before the named-profile split is in profile=default; search that store when Main has no match. Pass profile=lib or another exact profile name when needed.',
        'memory': 'Lib owns durable memory. Read-only shared context is supplied to Main; no memory is written by this tool.',
    })


def register(ctx):
    ctx.register_tool(
        name='hermes_setup_status', toolset='setup_awareness',
        schema={'name': 'hermes_setup_status',
                'description': 'Read-only deployment paths, configured-on-disk profile models/capacity, recent Kanban states, and recorded setup-change journal; entries are authored assertions, not independent verification. Use for questions about Docker, current setup, what changed today, and operational status. Does not change anything.',
                'parameters': {'type': 'object', 'properties': {}}},
        handler=status,
    )
    shared = ROOT / 'profiles/lib/memories'
    for filename, limit in [('USER.md', 1800), ('MEMORY.md', 2600)]:
        path = shared / filename
        if path.is_file():
            ctx.register_system_prompt_section(
                'shared-lib-' + filename.lower().replace('.', '-'),
                f'### Lib shared {filename} (registration snapshot; source mtime={path.stat().st_mtime}; clipped to {limit} characters; ask Lib for current full context)\n' + path.read_text()[:limit],
                position='after_memory', max_chars=limit + 100)
    prompt = '''You are running inside the Hermes Docker container. Code is /opt/hermes; persistent profiles and history are under /opt/data/profiles; vault is /opt/data/vault; projects are /projects. Lack of a Docker daemon socket inside a worker does not mean the gateway is outside Docker.
For questions about prior conversations, earlier decisions, or today's work, search Main's session history directly with session_search. Use profile=main; older history from before the profile split is in profile=default. Search default when Main lacks older context, and other named profiles when their work is relevant. For setup changes and current runtime, call hermes_setup_status. Do not route local setup/history questions to a web research worker. Do not report that history or knowledge is absent before checking these sources. Work performed from Codex or other external applications is visible only when recorded in the setup journal or reflected in files; do not invent unrecorded external work.
Lib remains the only writer of durable memory. The following notes are historical context, not authoritative current configuration: use hermes_setup_status for current models and deployment facts.\n'''
    ctx.register_system_prompt_section('shared-setup-and-memory-context', prompt,
                                       position='after_memory', max_chars=2000)
