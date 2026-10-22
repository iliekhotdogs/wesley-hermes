"""Inference-only gateway. Raw rotating OAuth credentials stay in this service."""
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
import sys
import threading

sys.path.insert(0, '/opt/hermes')
import httpx
from hermes_cli.auth_codex import resolve_codex_runtime_credentials

TOKEN = os.environ['INFERENCE_PROXY_TOKEN']
MODEL = os.environ.get('BUILDER_MODEL', 'gpt-5.6-luna')
UPSTREAM = 'https://chatgpt.com/backend-api/codex/responses'
INFERENCE_SLOTS = threading.BoundedSemaphore(2)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *_):
        pass

    def answer(self, status, value):
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/health':
            self.answer(200, {'ok': True, 'service': 'inference-only'})
        else:
            self.answer(404, {'error': 'Only inference is available.'})

    def do_POST(self):
        if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + TOKEN):
            return self.answer(401, {'error': 'Proxy authorization required.'})
        if self.path not in ('/responses', '/v1/responses'):
            return self.answer(404, {'error': 'Only Responses inference is available.'})
        if not INFERENCE_SLOTS.acquire(blocking=False):
            return self.answer(429, {'error': 'Inference concurrency limit reached.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > 16 * 1024 * 1024:
                return self.answer(413, {'error': 'Invalid inference request size.'})
            body = json.loads(self.rfile.read(length))
            if body.get('model') != MODEL:
                return self.answer(403, {'error': 'Model is not allowed by this proxy.'})
            body['store'] = False
            creds = resolve_codex_runtime_credentials()
            access = creds['api_key']
            headers = {'Authorization': 'Bearer ' + access, 'Content-Type': 'application/json',
                       'Accept': 'text/event-stream', 'User-Agent': 'codex-cli',
                       'OpenAI-Beta': 'responses=experimental'}
            try:
                payload = access.split('.')[1]
                claims = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
                account = claims.get('https://api.openai.com/auth', {}).get('chatgpt_account_id')
                if account:
                    headers['ChatGPT-Account-Id'] = account
            except (ValueError, IndexError):
                pass
            for name in ('session_id', 'conversation_id', 'originator'):
                value = self.headers.get(name)
                if value:
                    headers[name] = value[:200]
            with httpx.Client(timeout=httpx.Timeout(300, connect=20), follow_redirects=False) as client:
                with client.stream('POST', UPSTREAM, json=body, headers=headers) as upstream:
                    self.send_response(upstream.status_code)
                    self.send_header('Content-Type', upstream.headers.get('content-type', 'application/json'))
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    self.close_connection = True
                    for chunk in upstream.iter_bytes():
                        self.wfile.write(chunk)
                        self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:
            # No upstream headers, tokens, or raw request content in logs/errors.
            print('inference request failed:', type(exc).__name__, flush=True)
            try:
                self.answer(502, {'error': 'Trusted inference upstream unavailable.'})
            except (BrokenPipeError, ConnectionResetError):
                pass
        finally:
            INFERENCE_SLOTS.release()


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8766), Handler).serve_forever()
