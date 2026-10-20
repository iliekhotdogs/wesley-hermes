"""workspace_api.py re-checks the cron policy itself; Google is never called here."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('workspace_api', ROOT / 'extensions' / 'scripts' / 'workspace_api.py')
workspace_api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workspace_api)
POLICY = ROOT / 'extensions' / 'plugins' / 'profile-permissions' / 'policy.json'


class WorkspaceApiPolicyTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))).resolve()
        self.addCleanup(shutil.rmtree, self.home, True)
        self.calls = []
        built = mock.MagicMock()
        built.events.return_value.list.return_value.execute.return_value = {'items': []}
        patcher = mock.patch.object(workspace_api, 'build_service', side_effect=lambda *a: self.calls.append(a) or built)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_request(self, payload, policy=str(POLICY)):
        path = self.home / 'request.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        out = io.StringIO()
        env = {'HERMES_HOME': str(self.home), 'HERMES_PERMISSION_POLICY': policy}
        with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(out):
            code = workspace_api.main(['--request-file', str(path)])
        return code, json.loads(out.getvalue())

    def test_calendars_clear_rejected_before_google(self):
        code, out = self.run_request({'service': 'calendar', 'version': 'v3', 'resource': ['calendars'],
                                      'method': 'clear', 'params': {'calendarId': 'primary'}})
        self.assertEqual((code, out['error']['type']), (1, 'PermissionError'))
        self.assertEqual(self.calls, [])

    def test_events_list_dispatched(self):
        code, out = self.run_request({'service': 'calendar', 'version': 'v3', 'resource': ['events'],
                                      'method': 'list', 'params': {'calendarId': 'primary'}})
        self.assertEqual((code, out), (0, {'items': []}))
        self.assertEqual(self.calls, [('calendar', 'v3')])

    def test_missing_policy_fails_closed(self):
        code, out = self.run_request({'service': 'calendar', 'version': 'v3', 'resource': ['events'],
                                      'method': 'list', 'params': {}}, policy=str(self.home / 'missing.json'))
        self.assertEqual((code, out['error']['type']), (1, 'PermissionError'))
        self.assertEqual(self.calls, [])

    def test_policy_without_checker_fails_closed(self):
        (self.home / 'policy.json').write_text(POLICY.read_text(encoding='utf-8'), encoding='utf-8')
        code, out = self.run_request({'service': 'calendar', 'version': 'v3', 'resource': ['events'],
                                      'method': 'list', 'params': {}}, policy=str(self.home / 'policy.json'))
        self.assertIn('unavailable', out['error']['message'])
        self.assertEqual((code, self.calls), (1, []))


if __name__ == '__main__':
    unittest.main()
