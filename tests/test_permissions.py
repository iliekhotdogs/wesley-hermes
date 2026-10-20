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

    def test_cron_google_api_attendees_blocked(self):
        self.assert_blocked('cron', f'python {self.google} calendar create --summary x --attendees a@b.c')

    def test_cron_chaining_blocked(self):
        result = self.run_terminal('cron', f'python {self.api} --clock && echo hi')
        self.assertEqual(result['action'], 'block')

    def assert_blocked(self, role, command):
        result = self.run_terminal(role, command)
        self.assertIsNotNone(result, command)
        self.assertEqual(result['action'], 'block')
        return result

    def test_cron_workspace_non_routine_blocked(self):
        cases = [
            {'service': 'calendar', 'version': 'v3', 'resource': ['calendars'], 'method': 'clear', 'params': {'calendarId': 'primary'}},
            {'service': 'drive', 'version': 'v3', 'resource': ['files'], 'method': 'update', 'params': {'fileId': 'x'}, 'body': {'trashed': True}},
            {'service': 'gmail', 'version': 'v1', 'resource': ['users', 'messages'], 'method': 'batchModify',
             'params': {'userId': 'me'}, 'body': {'ids': ['a'], 'addLabelIds': ['TRASH']}},
            {'service': 'sheets', 'version': 'v4', 'resource': ['spreadsheets', 'values'], 'method': 'batchClear', 'params': {'spreadsheetId': 'x'}, 'body': {}},
            {'service': 'tasks', 'version': 'v1', 'resource': ['tasks'], 'method': 'clear', 'params': {'tasklist': 'x'}},
            {'service': 'calendar', 'version': 'v3', 'resource': ['events'], 'method': 'insert',
             'params': {'calendarId': 'primary', 'sendUpdates': 'all'}, 'body': {'attendees': [{'email': 'a@b.c'}]}},
            {'service': 'calendar', 'version': 'v3', 'resource': ['events'], 'method': 'insert',
             'params': {'calendarId': 'primary', 'sendUpdates': 'all'}, 'body': {'summary': 'x'}},
            {'service': 'drive', 'version': 'v3', 'resource': ['files'], 'method': 'update', 'params': {'fileId': 'x', 'addParents': 'y'}},
            {'service': 'drive', 'version': 'v3', 'resource': ['changes'], 'method': 'watch', 'params': {'pageToken': '1'}, 'body': {'address': 'https://x'}},
            {'service': 'calendar', 'version': 'v3', 'resource': ['events'], 'method': 'move',
             'params': {'calendarId': 'primary', 'eventId': 'e', 'destination': 'other'}},
            {'service': 'docs', 'version': 'v1', 'resource': ['documents'], 'method': 'batchUpdate',
             'params': {'documentId': 'x'}, 'body': {'requests': [{'deleteContentRange': {'range': {}}}]}},
            {'service': 'drive', 'version': 'v3', 'resource': ['files'], 'method': 'update',
             'params': {'fileId': 'x'}, 'body': {'writersCanShare': True}},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                self.assertIn('email sending', self.assert_blocked('cron', self.request(payload))['message'])

    def test_cron_workspace_routine_writes_allowed(self):
        command = self.request([
            {'service': 'calendar', 'version': 'v3', 'resource': ['events'], 'method': 'insert',
             'params': {'calendarId': 'primary', 'sendUpdates': 'none'}, 'body': {'summary': 'x'}},
            {'service': 'sheets', 'version': 'v4', 'resource': ['spreadsheets', 'values'], 'method': 'append',
             'params': {'spreadsheetId': 'x', 'range': 'A1'}, 'body': {'values': [[1]]}},
            {'service': 'people', 'version': 'v1', 'resource': ['people', 'connections'], 'method': 'list',
             'params': {'resourceName': 'people/me'}},
        ])
        self.assertIsNone(self.run_terminal('cron', command))

    def test_cron_spoofed_interpreter_blocked(self):
        for exe in ('C:/tmp/python.bat', '/tmp/python_evil', 'python.bat', '/usr/bin/python3'):
            with self.subTest(exe=exe):
                self.assert_blocked('cron', f'{exe} {self.api} --clock')
                self.assert_blocked('cron', f'{exe} {self.google} calendar list')
        self.assertIsNone(self.run_terminal('cron', f'python3.11.exe {self.api} --clock'))

    def test_non_cron_google_helpers_blocked(self):
        for role in ('builder', 'cowsearcher', 'lib'):
            with self.subTest(role=role):
                self.assert_blocked(role, f'cd {self.home} && python scripts\\workspace_api.py --request-file x')
                self.assert_blocked(role, f'python {self.google} gmail search x')

    def test_builder_cd_hermes_home_blocked(self):
        for target in ('~/.hermes', '%LOCALAPPDATA%\\hermes', 'C:\\Users\\u\\AppData\\Local\\hermes', '$HERMES_HOME', str(self.home)):
            with self.subTest(target=target):
                self.assert_blocked('builder', f'cd {target} && python scripts/other.py')
        self.assertIsNone(self.run_terminal('builder', 'cd src && python build.py'))

    def test_memory_destructive_actions_blocked(self):
        guard = permissions.make_guard('lib', self.home)
        for action in ('remove', 'forget', 'purge', 'prune', 'Delete'):
            with self.subTest(action=action):
                self.assertEqual(guard('memory', {'action': action})['action'], 'block')

    def test_recovery_key(self):
        from datetime import datetime, timezone
        prefix = permissions._recovery_key('cron', 'cron:abc')
        self.assertRegex(prefix, r'^profile-permission:[0-9a-f]{24}$')
        self.assertNotEqual(prefix, permissions._recovery_key('lib', 'cron:abc'))
        key = permissions._recovery_key('cron', 'cron:abc', datetime(2026, 10, 19, 8, 5, 59, tzinfo=timezone.utc))
        self.assertEqual(key, prefix + ':20261019T0805Z')

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
