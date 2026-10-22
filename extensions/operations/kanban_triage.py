"""Read-only task triage. Suggest prerequisites; never replay external effects."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3


def recommendation(task):
    error = str(task.get('last_failure_error') or '').lower()
    if task.get('block_recurrences', 0) >= 3:
        return 'needs_input', 'Repeated block: keep stopped until an owner verifies the missing capability and prior external effects.'
    if task.get('block_kind') in ('needs_input', 'capability'):
        return task['block_kind'], 'Preserve existing boundary; require the exact missing input or capability before any retry.'
    if 'protocol violation' in error:
        return 'needs_input', 'Inspect saved artifacts/run summary; reconcile partial work and report a terminal outcome before retrying.'
    if 'budget' in error or 'iteration' in error:
        return 'needs_input', 'Split the assignment into bounded stages, preserve partial outputs, and reserve turns for terminal reporting.'
    if 'exited' in error or 'crash' in error:
        return 'needs_input', 'Inspect worker failure and partial effects; require a verified repair before one targeted retry.'
    return 'needs_input', 'Identify the exact prerequisite and any prior external effects; no automatic replay.'


def collect(board):
    with closing(sqlite3.connect(Path(board).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        tasks = [dict(r) for r in db.execute("SELECT id,title,assignee,status,block_kind,block_recurrences,last_failure_error FROM tasks WHERE status IN ('blocked','todo','triage')")]
    for task in tasks:
        task['recommended_kind'], task['prerequisite'] = recommendation(task)
    return tasks


def run(home):
    home = Path(home).resolve()
    root = home.parent.parent if home.parent.name == 'profiles' else home
    tasks = collect(root / 'kanban.db')
    state = home / 'state/kanban_triage.json'
    state.parent.mkdir(parents=True, exist_ok=True)
    try:
        prior = json.loads(state.read_text())
    except (OSError, ValueError):
        prior = None
    if prior == tasks:
        return '[SILENT]'
    temp = state.with_suffix('.tmp')
    temp.write_text(json.dumps(tasks, indent=2), encoding='utf-8')
    temp.chmod(0o600); temp.replace(state)
    return ('Task triage changed: ' + str(len(tasks)) + ' unresolved cards. '
            'Inspect the local triage report; no work was automatically replayed.')


if __name__ == '__main__':
    # Contains private task titles. Store privately; do not publish this output.
    print(json.dumps(collect('/opt/data/kanban.db'), indent=2))
