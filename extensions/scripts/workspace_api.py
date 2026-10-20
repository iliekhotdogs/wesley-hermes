"""Scoped, data-only Google Workspace Discovery API CLI; no OAuth setup surface."""
import argparse
from datetime import datetime, timezone, timedelta
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VERSIONS = {'calendar': 'v3', 'tasks': 'v1', 'gmail': 'v1', 'drive': 'v3',
            'docs': 'v1', 'sheets': 'v4', 'people': 'v1'}
PUBLIC = re.compile(r'^[A-Za-z][A-Za-z0-9]*$')


def vancouver_now(instant=None):
    """BC stays on UTC-7 after the 2026-03-08 DST transition."""
    instant = instant or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError('clock instant must be timezone aware')
    cutoff = datetime(2026, 3, 8, 10, tzinfo=timezone.utc)
    if instant >= cutoff:
        return instant.astimezone(timezone(timedelta(hours=-7), 'America/Vancouver'))
    try:
        return instant.astimezone(ZoneInfo('America/Vancouver'))
    except ZoneInfoNotFoundError:
        # Before the March 2026 change, standard time in Vancouver was UTC-8.
        return instant.astimezone(timezone(timedelta(hours=-8), 'America/Vancouver'))


def build_service(service, version):
    # Load only the established, profile-owned Google wrapper, never a path from JSON.
    home = Path(os.environ.get('HERMES_HOME') or Path(__file__).resolve().parent.parent)
    wrapper = home / 'skills' / 'productivity' / 'google-workspace' / 'scripts' / 'google_api.py'
    spec = importlib.util.spec_from_file_location('workspace_google_api', wrapper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_service(service, version)


def dispatch(item):
    if not isinstance(item, dict) or set(item) - {'service', 'version', 'resource', 'method', 'params', 'body'}:
        raise ValueError('request must be an object with only supported fields')
    service, version = item.get('service'), item.get('version')
    if not isinstance(service, str) or VERSIONS.get(service) != version:
        raise ValueError('unsupported service or version')
    resource, method, params = item.get('resource'), item.get('method'), item.get('params')
    if (not isinstance(resource, list) or not resource or
            not all(isinstance(s, str) and PUBLIC.fullmatch(s) for s in resource) or
            not isinstance(method, str) or not PUBLIC.fullmatch(method) or
            not isinstance(params, dict) or not all(isinstance(k, str) for k in params)):
        raise ValueError('invalid resource path, method, or params')
    if 'body' in item and not isinstance(item['body'], (dict, list)):
        raise ValueError('body must be JSON object or array')
    arguments = dict(params)
    if 'body' in item:
        if 'body' in arguments:
            raise ValueError('body specified twice')
        arguments['body'] = item['body']
    endpoint = build_service(service, version)
    for segment in resource:
        endpoint = getattr(endpoint, segment)()
    return getattr(endpoint, method)(**arguments).execute()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument('--request-file', type=Path)
    options.add_argument('--clock', action='store_true')
    args = parser.parse_args(argv)
    if args.clock:
        print(json.dumps({'now': vancouver_now().isoformat(), 'timeZone': 'America/Vancouver'}))
        return 0
    try:
        payload = json.loads(args.request_file.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        print(json.dumps({'error': {'type': type(exc).__name__, 'message': str(exc)}}))
        return 1
    if not isinstance(payload, (dict, list)):
        print(json.dumps({'error': {'type': 'ValueError', 'message': 'expected request object or list'}}))
        return 1
    batch = isinstance(payload, list)
    results = []
    for index, item in enumerate(payload if batch else [payload]):
        try:
            results.append({'index': index, 'result': dispatch(item)})
        except Exception as exc:
            # Preserve previous successes; halt to avoid unintended later mutations.
            results.append({'index': index, 'error': {'type': type(exc).__name__, 'message': str(exc)}})
            print(json.dumps({'results': results} if batch else results[0]))
            return 1
    print(json.dumps({'results': results} if batch else results[0]['result']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
