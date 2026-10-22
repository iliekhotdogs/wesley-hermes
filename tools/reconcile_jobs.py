"""Offline reconciliation of scheduler definitions; never execute or replay jobs.

Prefer reviewed source definitions, preserve target execution history, and carry
the later next-run time across the cutover. Caller must stop the owning gateway.
The output contains private prompts/routing and must never be committed.
"""
import argparse
import copy
import json
from datetime import datetime
from pathlib import Path

HISTORY = ('last_run_at', 'last_status', 'last_error', 'last_delivery_error',
           'failure_streak', 'last_dispatch', 'effectiveness_failure_streak')


def timestamp(value):
    if not value:
        return float('-inf')
    result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Refusing ambiguous timezone-less scheduler timestamp')
    return result.timestamp()


def reconcile(target, source):
    result = copy.deepcopy(target)
    existing = {job['id']: job for job in target['jobs']}
    merged = []
    for source_job in source['jobs']:
        job = copy.deepcopy(source_job)
        old = existing.pop(job['id'], None)
        if old:
            recent = max((old, source_job), key=lambda j: timestamp(j.get('last_run_at')))
            for key in HISTORY:
                if key in recent:
                    job[key] = copy.deepcopy(recent[key])
            if job.get('enabled'):
                job['next_run_at'] = max((old.get('next_run_at'), job.get('next_run_at')), key=timestamp)
            # Runtime claims cannot be transferred between schedulers.
            job['fire_claim'] = None
        merged.append(job)
    # Preserve target-only jobs and their current paused/enabled state.
    merged.extend(copy.deepcopy(list(existing.values())))
    result['jobs'] = merged
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must be a new file; review it before deployment')
    data = reconcile(json.loads(args.target.read_text(encoding='utf-8-sig')),
                     json.loads(args.source.read_text(encoding='utf-8-sig')))
    args.output.write_text(json.dumps(data, indent=2), encoding='utf-8')
    print(json.dumps({'jobs': len(data['jobs']), 'enabled': sum(bool(j.get('enabled')) for j in data['jobs']), 'executed': False}))


if __name__ == '__main__':
    main()
