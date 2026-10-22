"""Single-job Builder service. Accepts bounded snapshots, never host paths/commands."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import threading
import uuid

from common import unpack, materialize, pack, files, modes

TOKEN = os.environ['BUILDER_CONTROL_TOKEN']
WORK = Path('/workspaces')
CONTROL = Path('/tmp/builder-jobs')
JOBS = {}
LOCK = threading.Lock()


def execute(job):
    try:
        log = (job['control'] / 'worker.log').open('wb')
        with log:
            proc = subprocess.Popen(['/opt/hermes/.venv/bin/python', '/isolation/agent_runner.py',
                                     str(job['control'] / 'request.json'), str(job['control'] / 'outcome.json')],
                                    cwd=job['workspace'], stdout=log, stderr=subprocess.STDOUT,
                                    start_new_session=True)
            job['process'] = proc
            try:
                proc.wait(timeout=job['timeout'] + 15)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
        path = job['control'] / 'outcome.json'
        outcome = json.loads(path.read_text()) if path.is_file() else {
            'status': 'blocked', 'summary': 'Builder process exited without a completion result.', 'tests': []}
        if job.get('cancelled'):
            outcome = {'status': 'blocked', 'summary': 'Isolated Builder job cancelled.', 'tests': []}
        job['outcome'] = outcome
        content = files(job['workspace'])
        job['snapshot'] = pack(content, modes(job['workspace'], content))
    except Exception as exc:
        job['outcome'] = {'status': 'blocked', 'summary': 'Isolated service failed: ' + type(exc).__name__, 'tests': []}
    finally:
        job['done'] = True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def answer(self, code, value):
        data = json.dumps(value).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def authorized(self):
        return hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + TOKEN)

    def do_GET(self):
        if self.path == '/health':
            return self.answer(200, {'ok': True, 'role': 'isolated-builder'})
        if not self.authorized():
            return self.answer(401, {'error': 'Authorization required'})
        job_id = self.path.removeprefix('/jobs/')
        job = JOBS.get(job_id) if self.path.startswith('/jobs/') else None
        if not job:
            return self.answer(404, {'error': 'Unknown job'})
        result = {'job_id': job_id, 'done': job['done']}
        if job['done']:
            result.update(outcome=job.get('outcome'), snapshot=job.get('snapshot'))
        self.answer(200, result)

    def do_POST(self):
        if not self.authorized():
            return self.answer(401, {'error': 'Authorization required'})
        if self.path.endswith('/cancel') and self.path.startswith('/jobs/'):
            job = JOBS.get(self.path.split('/')[2])
            if not job:
                return self.answer(404, {'error': 'Unknown job'})
            job['cancelled'] = True
            proc = job.get('process')
            if proc and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
            return self.answer(200, {'cancelled': True})
        if self.path != '/jobs':
            return self.answer(404, {'error': 'Unknown endpoint'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > 96 * 1024 * 1024:
                return self.answer(413, {'error': 'Workspace request exceeds limit'})
            data = json.loads(self.rfile.read(length))
            if not re.fullmatch(r't_[a-f0-9]{8,32}', data.get('task_id', '')):
                return self.answer(400, {'error': 'Invalid task identifier'})
            if not isinstance(data.get('context'), str) or len(data['context']) > 100000:
                return self.answer(400, {'error': 'Invalid assigned context'})
            file_modes = {}
            contents = unpack(data['snapshot'], file_modes)
            with LOCK:
                if any(not j['done'] for j in JOBS.values()):
                    return self.answer(409, {'error': 'Builder already has an active job'})
                # Remove only completed service-created job directories before the next assignment.
                for old_id, old in list(JOBS.items()):
                    for parent, path in [(WORK, old['workspace']), (CONTROL, old['control'])]:
                        if path.parent != parent or path.name != old_id or path.is_symlink():
                            raise ValueError('Unsafe old job path')
                        shutil.rmtree(path)
                    del JOBS[old_id]
                job_id = uuid.uuid4().hex
                workspace, control = WORK / job_id, CONTROL / job_id
                workspace.mkdir(parents=True, exist_ok=False)
                control.mkdir(parents=True, exist_ok=False)
                materialize(workspace, contents, file_modes)
                timeout = min(max(int(data.get('timeout', 600)), 30), 1800)
                request = {'workspace': str(workspace), 'context': data['context'], 'timeout': timeout}
                (control / 'request.json').write_text(json.dumps(request))
                job = {'workspace': workspace, 'control': control, 'timeout': timeout, 'done': False}
                JOBS[job_id] = job
                threading.Thread(target=execute, args=(job,), daemon=True).start()
            self.answer(202, {'job_id': job_id})
        except Exception as exc:
            self.answer(400, {'error': 'Rejected workspace job: ' + type(exc).__name__})


if __name__ == '__main__':
    WORK.mkdir(parents=True, exist_ok=True)
    CONTROL.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer(('0.0.0.0', 8765), Handler).serve_forever()
