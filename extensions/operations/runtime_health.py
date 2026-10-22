"""Read-only Hermes readiness checks; never confuse checker success with health."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import time


def epoch(value):
    if isinstance(value, (int, float)):
        return float(value)
    parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp has no timezone')
    return parsed.timestamp()


def backup_issue(path, now):
    try:
        data = json.loads(path.read_text())
        if not data.get('ok'):
            return 'last export/verification failed'
        verified = float(data['verified_at_epoch'])
        if not 0 <= now - verified <= 36 * 3600:
            return 'verified recovery point is stale or future-dated'
    except (OSError, ValueError, KeyError, TypeError):
        return 'verified recovery point is missing or unreadable'
    return None


def collect(root=Path('/opt/data'), now=None, proc=Path('/proc')):
    now = time.time() if now is None else now
    issues = []
    def add(code, detail, severity='critical'):
        issues.append({'code': code, 'detail': detail, 'severity': severity})
    try:
        gateway = json.loads((root / 'profiles/main/gateway_state.json').read_text())
        if gateway.get('gateway_state') != 'running' or gateway.get('platforms', {}).get('discord', {}).get('state') != 'connected':
            add('transport', 'Main gateway or Discord is disconnected')
        pid = int(gateway['pid'])
        # /proc stat comm can contain spaces/parentheses; split after its last ).
        fields = (proc / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()
        if int(fields[19]) != int(gateway['start_time']):
            add('process_identity', 'Gateway PID was reused or state belongs to another process')
        # gateway_state updated_at changes on transitions, not on every tick.
        # Freshness belongs to the dedicated owning-profile heartbeat.
        heartbeat = json.loads((root / 'profiles/main/state/gateway.heartbeat').read_text())
        if int(heartbeat['pid']) != pid or not 0 <= now - epoch(heartbeat['updated_at']) <= 180:
            add('gateway_freshness', 'Gateway heartbeat is stale or belongs to another PID')
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        add('gateway_state', 'Gateway identity/state cannot be validated')
    for label, name in [('local_backup', 'backup_verification.json'), ('host_backup', 'host_backup_verification.json')]:
        issue = backup_issue(root / 'state' / name, now)
        if issue:
            add(label, issue)
    jobs_seen = 0
    if not (root / 'profiles/cron/cron/jobs.json').is_file():
        add('scheduler_missing', 'Authoritative Cron registry is missing')
    for registry in sorted(root.glob('profiles/*/cron/jobs.json')):
        profile = registry.parent.parent
        try:
            jobs = json.loads(registry.read_text())['jobs']
            enabled = [j for j in jobs if j.get('enabled')]
            if not enabled:
                continue
            for name in ['ticker_heartbeat', 'ticker_last_success']:
                stamp = float((registry.parent / name).read_text())
                if not 0 <= now - stamp <= 180:
                    add('scheduler', profile.name + ': stale ' + name)
            for job in enabled:
                jobs_seen += 1
                label = profile.name + '/' + job['id']
                status = job.get('last_status')
                if status and status not in ('ok', 'success', 'silent', 'completed', 'skipped'):
                    add('job_failure', label + ': ' + str(status))
                if job.get('last_delivery_error') or job.get('last_delivery_unverified'):
                    add('delivery', label + ': delivery failed or unverified')
                if job.get('script') and not (profile / 'scripts' / job['script']).is_file():
                    add('script_missing', label + ': configured script missing')
                if job.get('next_run_at') and now - epoch(job['next_run_at']) > 600:
                    add('overdue', label + ': scheduled fire overdue')
        except (OSError, ValueError, KeyError, TypeError):
            add('scheduler_state', profile.name + ': scheduler state unreadable')
    if not jobs_seen:
        add('scheduler_empty', 'No enabled scheduled jobs were found')
    board = root / 'kanban.db'
    counts = {}
    if board.exists():
        try:
            with closing(sqlite3.connect(board.as_uri() + '?mode=ro', uri=True)) as db:
                counts = dict(db.execute('SELECT status,COUNT(*) FROM tasks GROUP BY status'))
                for task_id, stamp in db.execute("SELECT id,last_heartbeat_at FROM tasks WHERE status='running'"):
                    if stamp is None or now - epoch(stamp) > 900:
                        add('stalled_task', task_id + ': running without fresh heartbeat')
                unresolved = sum(counts.get(s, 0) for s in ('blocked', 'triage'))
                if unresolved:
                    add('task_attention', str(unresolved) + ' tasks require triage/input; do not blindly replay', 'warning')
        except (sqlite3.Error, ValueError, TypeError):
            add('kanban_state', 'Task state cannot be read')
    issues.sort(key=lambda item: (item['code'], item['detail']))
    return {'ok': not any(i['severity'] == 'critical' for i in issues), 'observed_at': datetime.fromtimestamp(now, timezone.utc).isoformat(), 'issues': issues, 'enabled_jobs': jobs_seen, 'task_counts': counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/opt/data'))
    args = parser.parse_args()
    result = collect(args.root.resolve())
    print(json.dumps(result))
    raise SystemExit(0 if result['ok'] else 1)


if __name__ == '__main__':
    main()
