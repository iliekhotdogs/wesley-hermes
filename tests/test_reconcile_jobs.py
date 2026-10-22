import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('reconcile_jobs', Path(__file__).resolve().parents[1] / 'tools/reconcile_jobs.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReconcileTests(unittest.TestCase):
    def test_preserves_later_execution_and_next_fire_without_replay(self):
        target = {'jobs': [{'id': 'one', 'enabled': True, 'script': 'old.py', 'last_run_at': '2026-10-21T22:00:02+00:00', 'last_status': 'ok', 'next_run_at': '2026-10-22T22:00:00+00:00'}]}
        source = {'jobs': [{'id': 'one', 'enabled': True, 'script': 'new.py', 'last_run_at': '2026-10-21T22:00:00+00:00', 'last_status': 'error', 'next_run_at': '2026-10-21T22:00:00+00:00', 'fire_claim': {'pid': 9}}]}
        job = module.reconcile(target, source)['jobs'][0]
        self.assertEqual(job['script'], 'new.py')
        self.assertEqual(job['last_status'], 'ok')
        self.assertEqual(job['next_run_at'], '2026-10-22T22:00:00+00:00')
        self.assertIsNone(job['fire_claim'])
        self.assertEqual(target['jobs'][0]['script'], 'old.py')

    def test_preserves_pauses_and_target_only_jobs(self):
        result = module.reconcile({'jobs': [{'id': 'one', 'enabled': True}, {'id': 'two', 'enabled': False}]}, {'jobs': [{'id': 'one', 'enabled': False}]})
        self.assertFalse(result['jobs'][0]['enabled'])
        self.assertEqual(result['jobs'][1], {'id': 'two', 'enabled': False})

    def test_rejects_ambiguous_timestamp(self):
        with self.assertRaises(ValueError):
            module.timestamp('2026-10-21T22:00:00')
