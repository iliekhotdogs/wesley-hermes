import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('runtime_health', Path(__file__).resolve().parents[1] / 'extensions/operations/runtime_health.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class HealthTests(unittest.TestCase):
    def test_backup_success_expires_and_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'status.json'
            path.write_text(json.dumps({'ok': True, 'verified_at_epoch': 100}))
            self.assertIsNone(module.backup_issue(path, 200))
            self.assertIsNotNone(module.backup_issue(path, 100 + 37 * 3600))
            path.write_text(json.dumps({'ok': False, 'verified_at_epoch': 200}))
            self.assertIsNotNone(module.backup_issue(path, 200))

    def test_connected_gateway_with_reused_pid_is_unhealthy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); state = root / 'profiles/main'; state.mkdir(parents=True)
            (state / 'gateway_state.json').write_text(json.dumps({'pid': 7, 'start_time': 41, 'gateway_state': 'running', 'updated_at': '2026-10-21T00:00:00+00:00', 'platforms': {'discord': {'state': 'connected'}}}))
            proc = root / 'proc/7'; proc.mkdir(parents=True)
            (proc / 'stat').write_text('7 (name with spaces) S ' + '0 ' * 18 + '42 0')
            result = module.collect(root, module.epoch('2026-10-21T00:00:00+00:00'), root / 'proc')
            self.assertFalse(result['ok'])
            self.assertIn('process_identity', [i['code'] for i in result['issues']])

    def test_timezone_less_schedule_rejected(self):
        with self.assertRaises(ValueError):
            module.epoch('2026-10-21T00:00:00')

    def test_old_transition_timestamp_with_fresh_heartbeat_is_healthy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); home = root / 'profiles/main'; (home / 'state').mkdir(parents=True)
            now = module.epoch('2026-10-21T00:00:00+00:00')
            (home / 'gateway_state.json').write_text(json.dumps({'pid': 7, 'start_time': 42, 'gateway_state': 'running', 'updated_at': '2026-09-01T00:00:00+00:00', 'platforms': {'discord': {'state': 'connected'}}}))
            (home / 'state/gateway.heartbeat').write_text(json.dumps({'pid': 7, 'updated_at': '2026-10-21T00:00:00+00:00'}))
            proc = root / 'proc/7'; proc.mkdir(parents=True)
            (proc / 'stat').write_text('7 (gateway) S ' + '0 ' * 18 + '42 0')
            (root / 'state').mkdir()
            for name in ['backup_verification.json', 'host_backup_verification.json']:
                (root / 'state' / name).write_text(json.dumps({'ok': True, 'verified_at_epoch': now}))
            cron = root / 'profiles/cron/cron'; cron.mkdir(parents=True)
            (cron / 'jobs.json').write_text(json.dumps({'jobs': [{'id': 'test', 'enabled': True}]}))
            for name in ['ticker_heartbeat', 'ticker_last_success']:
                (cron / name).write_text(str(now))
            self.assertTrue(module.collect(root, now, root / 'proc')['ok'])
            (cron / 'jobs.json').unlink()
            result = module.collect(root, now, root / 'proc')
            self.assertFalse(result['ok'])
            self.assertIn('scheduler_missing', [i['code'] for i in result['issues']])
