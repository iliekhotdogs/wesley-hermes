"""Print a Markdown inventory of scheduled jobs across Hermes profiles.

Standard library only. Read-only. Prompt text is never printed (it is private).
"""
import argparse
import json
import os
from pathlib import Path

COLUMNS = ('profile', 'id', 'name', 'enabled', 'schedule', 'timezone', 'deliver', 'script', 'last_status', 'last_run_at', 'Decision')


def default_home():
    if os.environ.get('HERMES_HOME'):
        return Path(os.environ['HERMES_HOME'])
    if os.name == 'nt' and os.environ.get('LOCALAPPDATA'):
        return Path(os.environ['LOCALAPPDATA']) / 'hermes'
    return Path.home() / '.hermes'


def cell(value):
    if isinstance(value, dict):  # schedule may be structured, e.g. {"kind": "cron", "expr": "0 8 * * *"}
        value = value.get('expr') or value.get('display') or value.get('value') or json.dumps(value, sort_keys=True)
    return '' if value is None else str(value).replace('|', '\\|').replace('\n', ' ')


def rows(home):
    stores = [('default', home / 'cron' / 'jobs.json')]
    stores += [(p.parent.parent.name, p) for p in sorted(home.glob('profiles/*/cron/jobs.json'))]
    for profile, path in stores:
        if not path.exists():
            continue
        try:
            jobs = json.loads(path.read_text(encoding='utf-8-sig'))['jobs']
        except (OSError, ValueError, KeyError, TypeError):
            yield {'profile': profile, 'name': 'unreadable jobs.json'}
            continue
        for job in jobs:
            yield {
                'profile': profile, 'id': job.get('id'), 'name': job.get('name'),
                'enabled': job.get('enabled', True), 'schedule': job.get('schedule'),
                'timezone': job.get('timezone') or job.get('tz'),
                'deliver': job.get('deliver') or job.get('destination') or job.get('delivery'),
                'script': job.get('script'), 'last_status': job.get('last_status'), 'last_run_at': job.get('last_run_at'),
            }


def table(home):
    lines = ['| ' + ' | '.join(COLUMNS) + ' |', '|' + '---|' * len(COLUMNS)]
    lines += ['| ' + ' | '.join(cell(row.get(c)) for c in COLUMNS) + ' |' for row in rows(home)]
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--hermes-home', type=Path, default=default_home())
    print(table(parser.parse_args().hermes_home))
