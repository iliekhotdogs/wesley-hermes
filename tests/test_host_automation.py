"""Exercise host-automation reference scripts with temp files and stubs, never a live Hermes or Discord."""
import contextlib
import importlib.util
import io
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / 'extensions' / 'host-automation'


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def has_dotenv():
    return importlib.util.find_spec('dotenv') is not None


def capture(fn, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = fn(*args)
    return code, out.getvalue()


class HostAutomationTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(dir=os.environ.get('TMPDIR')))
        self.addCleanup(shutil.rmtree, self.temp, True)

    def test_completion_log_is_idempotent(self):
        module = load(HOST / 'completion_log.py')
        fixture = self.temp / 'tasks.json'
        fixture.write_text(json.dumps([
            {'id': 't1', 'title': 'Fix login', 'assignee': 'builder', 'status': 'done', 'body': 'x' * 400,
             'latest_summary': 'Shipped', 'created_at': '2026-10-18T10:00:00Z', 'completed_at': '2026-10-18T12:00:00Z',
             'events': [{'kind': 'completed', 'payload': {'changed_resource': 'repo/pr/1', 'verification': 'tests pass'}}]},
            {'id': 't2', 'title': 'Main recovery: creds', 'assignee': 'main', 'status': 'done'},
            {'id': 't3', 'title': 'Stuck', 'assignee': 'builder', 'status': 'blocked'},
        ]), encoding='utf-8')
        log = self.temp / 'completions.jsonl'
        with mock.patch.dict(os.environ, {'COMPLETION_LOG_PATH': str(log)}), \
                mock.patch.object(module, 'command_json', side_effect=AssertionError('CLI must not run')):
            code, first = capture(module.main, ['--fixture', str(fixture), '--dry-run'])
            self.assertEqual((code, log.exists()), (0, False))
            self.assertIn('t1', first)
            capture(module.main, ['--fixture', str(fixture)])
            code, second = capture(module.main, ['--fixture', str(fixture)])
            self.assertEqual((code, second), (0, ''))
            entries = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()]
            self.assertEqual([e['task_id'] for e in entries], ['t1', 't2'])
            self.assertEqual(len(entries[0]['request']), 300)
            self.assertEqual((entries[0]['changed_resource'], entries[0]['evidence']), ('repo/pr/1', 'tests pass'))
            self.assertIsNone(entries[1]['changed_resource'])
            with mock.patch.object(module.time, 'time', return_value=datetime(2026, 10, 19, tzinfo=timezone.utc).timestamp()):
                _, table = capture(module.main, ['--fixture', str(fixture), '--metrics'])
        self.assertIn('| builder | 1 | 1 | 0 | 2.0h |', table)

    def test_block_alert_groups_invalid_grant_and_skips_finished(self):
        module = load(HOST / 'kanban_block_alert.py')
        blocked = [{'id': i, 'title': 'T' + i, 'assignee': 'lib', 'status': 'blocked'} for i in ('a', 'b', 'c', 'd')]
        details = {
            'a': {'events': [{'kind': 'blocked', 'payload': {'reason': 'Google token error: invalid_grant'}}]},
            'b': {'events': [{'kind': 'blocked', 'payload': {'error': 'invalid_grant: Token has been expired'}}]},
            'c': {'status': 'done', 'events': [{'kind': 'blocked', 'payload': {'reason': 'parent pending'}}]},
            'd': {'events': [{'kind': 'blocked', 'payload': {'reason': 'parent pending', 'kind': 'dependency'}}]},
        }
        stub = lambda *args: blocked if args[1] == 'list' else details[args[2]]
        with mock.patch.dict(os.environ, {'KANBAN_BLOCK_ALERT_STATE': str(self.temp / 'state.json')}), \
                mock.patch.object(module, 'command_json', side_effect=stub):
            _, out = capture(module.main)
        self.assertIn('invalid_grant incident: 2 task(s) (a, b)', out)
        self.assertEqual(out.count('invalid_grant'), 1)
        self.assertNotIn('• c', out)
        self.assertIn('• d', out)

    def test_cron_inventory_table(self):
        module = load(ROOT / 'tools' / 'cron_inventory.py')
        jobs = self.temp / 'profiles' / 'cron' / 'cron' / 'jobs.json'
        jobs.parent.mkdir(parents=True)
        jobs.write_text(json.dumps({'jobs': [{'id': 'j1', 'name': 'Morning Briefing', 'enabled': False, 'prompt': 'SECRET PROMPT',
                                              'schedule': {'kind': 'cron', 'expr': '0 8 * * *'}, 'deliver': 'discord:#briefing',
                                              'last_status': 'ok', 'last_run_at': '2026-10-19T08:00:00Z'}]}), encoding='utf-8')
        table = module.table(self.temp)
        self.assertIn('| cron | j1 | Morning Briefing | False | 0 8 * * * |  | discord:#briefing |  | ok | 2026-10-19T08:00:00Z |  |', table)
        self.assertNotIn('SECRET', table)

    def test_cron_health_ignore_env(self):
        module = load(HOST / 'cron_health_check.py')
        jobs = self.temp / 'cron' / 'jobs.json'
        jobs.parent.mkdir(parents=True)
        jobs.write_text(json.dumps({'jobs': [{'id': 'skipme', 'name': 'a', 'last_status': 'error'},
                                             {'id': 'keep', 'name': 'b', 'last_status': 'error'}]}), encoding='utf-8')
        now = datetime.now(timezone.utc)
        with mock.patch.dict(os.environ, {'CRON_HEALTH_IGNORE_IDS': ' skipme ,other'}):
            issues, _ = module.collect(self.temp, now)
        self.assertEqual(issues, ['default/b: last status error'])
        with mock.patch.dict(os.environ, {'CRON_HEALTH_IGNORE_IDS': ''}):
            self.assertEqual(len(module.collect(self.temp, now)[0]), 2)

    def test_gateway_ram_debounce(self):
        module = load(HOST / 'gateway_watchdog.py')
        state = {}
        hold = module.RAM_ALERT_HOLD_MINUTES * 60
        self.assertIsNone(module.ram_notice(state, 95, 0))
        self.assertIsNone(module.ram_notice(state, 95, hold - 1))
        self.assertIn('RAM at 95%', module.ram_notice(state, 95, hold))
        self.assertIsNone(module.ram_notice(state, 95, hold + 60))
        self.assertIn('recovered', module.ram_notice(state, 40, hold + 120))
        self.assertIsNone(module.ram_notice(state, 40, hold + 180))

    @unittest.skipIf(not has_dotenv(), 'python-dotenv not installed')
    def test_thread_cleanup_requires_guild(self):
        with mock.patch.dict(os.environ, {'DISCORD_BOT_TOKEN': 'x', 'DISCORD_GUILD_ID': ''}):
            module = load(HOST / 'thread_cleanup.py')
            module.TOKEN, module.GUILD_ID = 'x', ''
            with mock.patch.object(module, 'api', side_effect=AssertionError('no network')):
                with self.assertRaisesRegex(RuntimeError, 'DISCORD_GUILD_ID'):
                    module.main()


if __name__ == '__main__':
    unittest.main()
