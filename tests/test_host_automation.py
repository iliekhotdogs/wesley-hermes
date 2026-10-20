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
            self.assertEqual(capture(module.main, ['--fixture', str(fixture)]), (0, ''))  # first real run seeds silently
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

    def test_completion_log_caps_output_and_attributes_takeovers(self):
        module = load(HOST / 'completion_log.py')
        log = self.temp / 'completions.jsonl'
        log.write_text('', encoding='utf-8')  # existing log: not a seeding run
        fixture = self.temp / 'tasks.json'
        for size, shown in ((5, 10), (300, 5)):  # line cap, then the 1900-char cap
            fixture.write_text(json.dumps([{'id': f'n{size}-{i}', 'title': 'x' * size, 'assignee': 'builder',
                                            'latest_summary': 'y' * size} for i in range(15)]), encoding='utf-8')
            with mock.patch.dict(os.environ, {'COMPLETION_LOG_PATH': str(log)}):
                _, out = capture(module.main, ['--fixture', str(fixture)])
            self.assertEqual(out.count('✅'), shown)
            self.assertTrue(out.rstrip().endswith(f'+{15 - shown} more'))
            self.assertLess(len(out), 1900)
        done = '2026-10-18T12:00:00Z'
        log.write_text(''.join(json.dumps(e) + '\n' for e in [
            {'task_id': 'a', 'profile': 'main', 'created_by': 'builder:profile-permissions', 'completed_at': done},
            {'task_id': 'b', 'profile': 'main', 'title': 'Main recovery: lib needs creds', 'completed_at': done},
        ]), encoding='utf-8')
        table = module.metrics(module.read_log(log), [], datetime(2026, 10, 19, tzinfo=timezone.utc).timestamp())
        self.assertIn('| builder | 0 | 0 | 1 |', table)
        self.assertIn('| lib | 0 | 0 | 1 |', table)
        self.assertIn('| main | 2 | 0 | 0 |', table)

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
        state = self.temp / 'state.json'
        with mock.patch.dict(os.environ, {'KANBAN_BLOCK_ALERT_STATE': str(state)}), \
                mock.patch.object(module, 'command_json', side_effect=stub):
            _, out = capture(module.main)
        self.assertEqual(sorted(json.loads(state.read_text(encoding='utf-8'))), ['a', 'b', 'd'])
        self.assertIn('3 blocked task(s)', out)
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

    def watchdog(self, details):
        module = load(HOST / 'gateway_watchdog.py')
        for name, value in (('STATE', self.temp / 'state.json'), ('LOG', self.temp / 'watchdog.log'),
                            ('gateway_status', lambda: None), ('ram_percent', lambda: None),
                            ('doctor_status', mock.Mock(side_effect=details))):
            patcher = mock.patch.object(module, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        return module

    def test_gateway_stale_heartbeat_alerts_once(self):
        module = self.watchdog([('heartbeat_stale', 'gateway heartbeat is 130s old'),
                                ('heartbeat_stale', 'gateway heartbeat is 190s old')])
        code, first = capture(module.main, [])
        self.assertEqual((code, first), (1, 'Gateway health: gateway heartbeat is 130s old\n'))
        self.assertEqual(capture(module.main, []), (1, ''))

    def test_gateway_standalone_posts_webhook_without_printing_url(self):
        url = 'https://discord.invalid/api/webhooks/1/SECRET'
        module = self.watchdog([('gateway_not_running', 'gateway not running: down')] * 2)
        sent = []
        def fake_urlopen(request, timeout):
            sent.append((request.full_url, json.loads(request.data), timeout))
            return contextlib.nullcontext()
        err = io.StringIO()
        with mock.patch.dict(os.environ, {'WATCHDOG_WEBHOOK_URL': url}), contextlib.redirect_stderr(err):
            with mock.patch.object(module.urllib.request, 'urlopen', side_effect=OSError('boom ' + url)):
                code, out = capture(module.main, ['--standalone'])
            self.assertEqual(code, 2)
            self.assertFalse((self.temp / 'state.json').exists())  # failed delivery retries next run
            with mock.patch.object(module.urllib.request, 'urlopen', side_effect=fake_urlopen):
                code, out2 = capture(module.main, ['--standalone'])
        self.assertEqual(code, 1)
        self.assertEqual(sent, [(url, {'content': 'Gateway health: gateway not running: down'}, 15)])
        self.assertIn('webhook post failed: OSError', err.getvalue())
        self.assertNotIn('SECRET', out + out2 + err.getvalue())

    def test_thread_cleanup_rejects_bad_delete_days_before_api(self):
        module = load(HOST / 'thread_cleanup.py')
        module.TOKEN, module.GUILD_ID, module.DELETE_AFTER_DAYS = 'x', 'g', 'soon'
        with mock.patch.object(module, 'api', side_effect=AssertionError('no network')):
            with self.assertRaisesRegex(RuntimeError, 'THREAD_DELETE_AFTER_DAYS'):
                module.main()

    def test_thread_cleanup_deletes_by_archive_time_across_pages(self):
        module = load(HOST / 'thread_cleanup.py')
        module.TOKEN, module.GUILD_ID, module.DELETE_AFTER_DAYS = 'x', 'g', '7'
        recent_id = str(int((datetime.now(timezone.utc).timestamp() * 1000 - 1420070400000)) << 22)
        meta = lambda when: {'archive_timestamp': when}
        calls = []
        def api(method, path, body=None):
            calls.append((method, path))
            if path == '/guilds/g/channels':
                return [{'id': 'c', 'type': 0, 'default_auto_archive_duration': 1440}]
            if path == '/guilds/g/threads/active':
                return {'threads': []}
            if path == '/channels/c/threads/archived/public?limit=100':
                return {'has_more': True, 'threads': [{'id': '1', 'thread_metadata': meta(datetime.now(timezone.utc).isoformat())}]}
            if path.startswith('/channels/c/threads/archived/public?limit=100&before='):
                return {'has_more': False, 'threads': [{'id': recent_id, 'thread_metadata': meta('2020-01-01T00:00:00.000000+00:00')}]}
            return {}
        with mock.patch.object(module, 'api', side_effect=api):
            code, out = capture(module.main)
        self.assertEqual(code, 0)
        self.assertEqual([c for c in calls if c[0] == 'DELETE'], [('DELETE', '/channels/' + recent_id)])
        self.assertIn('deleted=1', out)

    def test_thread_cleanup_requires_guild(self):
        with mock.patch.dict(os.environ, {'DISCORD_BOT_TOKEN': 'x', 'DISCORD_GUILD_ID': ''}):
            module = load(HOST / 'thread_cleanup.py')
            module.TOKEN, module.GUILD_ID = 'x', ''
            with mock.patch.object(module, 'api', side_effect=AssertionError('no network')):
                with self.assertRaisesRegex(RuntimeError, 'DISCORD_GUILD_ID'):
                    module.main()


if __name__ == '__main__':
    unittest.main()
