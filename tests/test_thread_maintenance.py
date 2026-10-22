import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('thread_maintenance', Path(__file__).resolve().parents[1] / 'extensions/operations/thread_maintenance.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ThreadMaintenanceTests(unittest.TestCase):
    def test_missing_permissions_stops_before_mutation(self):
        def api(method, path, body=None):
            self.assertEqual(method, 'GET')
            if path == '/users/@me': return {'id': 'bot'}
            if path.endswith('/members/bot'): return {'roles': ['reader']}
            if path.endswith('/roles'): return [{'id': 'guild', 'permissions': '0'}, {'id': 'reader', 'permissions': '1024'}]
            self.fail('Readiness must stop before fetching work')
        with patch.object(module, 'TOKEN', 'test'), patch.object(module, 'GUILD_ID', 'guild'), patch.object(module, 'api', side_effect=api):
            with self.assertRaisesRegex(RuntimeError, 'Manage Channels and Manage Threads'):
                module.main()

    def test_deletion_always_rejected_before_network(self):
        with patch.object(module.urllib.request, 'urlopen') as network:
            with self.assertRaisesRegex(RuntimeError, 'deletion is disabled'):
                module.api('DELETE', '/channels/example')
            network.assert_not_called()
