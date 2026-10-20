"""Exercise the profile-permissions hook against a temporary home, never a live Hermes home."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

PLUGIN = Path(__file__).resolve().parents[1] / 'extensions' / 'plugins' / 'profile-permissions' / '__init__.py'
spec = importlib.util.spec_from_file_location('profile_permissions', PLUGIN)
permissions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permissions)


class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))).resolve()
        self.addCleanup(shutil.rmtree, self.home, True)
        self.api = self.home / 'scripts' / 'workspace_api.py'
        self.google = self.home / 'skills' / 'productivity' / 'google-workspace' / 'scripts' / 'google_api.py'

    def run_terminal(self, role, command):
        # No session_id kwarg, so a block never reaches the Hermes-only recovery queue.
        return permissions.make_guard(role, self.home)('terminal', {'command': command})

    def request(self, payload):
        path = self.home / 'request.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        return f'python {self.api} --request-file {path}'

    def test_cron_clock_allowed(self):
        self.assertIsNone(self.run_terminal('cron', f'python {self.api} --clock'))

    def test_cron_calendar_request_allowed(self):
        command = self.request({'service': 'calendar', 'version': 'v3', 'resource': ['events'],
                                'method': 'list', 'params': {'calendarId': 'primary'}})
        self.assertIsNone(self.run_terminal('cron', command))

    def test_cron_gmail_send_request_blocked(self):
        command = self.request([{'service': 'gmail', 'version': 'v1', 'resource': ['users', 'messages'],
                                 'method': 'send', 'params': {'userId': 'me'}, 'body': {}}])
        result = self.run_terminal('cron', command)
        self.assertEqual(result['action'], 'block')
        self.assertIn('email sending', result['message'])

    def test_cron_missing_request_blocked(self):
        result = self.run_terminal('cron', f'python {self.api} --request-file {self.home / "missing.json"}')
        self.assertEqual(result['action'], 'block')

    def test_cron_google_api_calendar_list_allowed(self):
        self.assertIsNone(self.run_terminal('cron', f'python {self.google} calendar list'))

    def test_cron_chaining_blocked(self):
        result = self.run_terminal('cron', f'python {self.api} --clock && echo hi')
        self.assertEqual(result['action'], 'block')

    def test_builder_rm_blocked(self):
        self.assertEqual(self.run_terminal('builder', 'rm x')['action'], 'block')

    def test_speedy_role_blocked(self):
        result = permissions.make_guard('speedy', self.home)('read_file', {'path': str(self.home / 'a.txt')})
        self.assertIn('no approved specialist role', result['message'])

    def test_block_log_omits_command(self):
        result = self.run_terminal('builder', 'rm secret-token-value')
        self.assertNotIn('reason', result)
        lines = (self.home / 'state' / 'permission_blocks.jsonl').read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(lines), 1)
        self.assertNotIn('secret-token-value', lines[0])
        entry = json.loads(lines[0])
        self.assertEqual(set(entry), {'ts', 'role', 'tool', 'reason'})
        self.assertEqual((entry['role'], entry['tool']), ('builder', 'terminal'))


if __name__ == '__main__':
    unittest.main()
