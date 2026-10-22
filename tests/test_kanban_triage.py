import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('kanban_triage', Path(__file__).resolve().parents[1] / 'extensions/operations/kanban_triage.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class TriageTests(unittest.TestCase):
    def test_repeated_capability_is_not_retried(self):
        kind, reason = module.recommendation({'block_recurrences': 33, 'block_kind': 'capability'})
        self.assertEqual(kind, 'needs_input'); self.assertIn('prior external effects', reason)

    def test_protocol_failure_requires_reconciliation(self):
        kind, reason = module.recommendation({'last_failure_error': 'rc=0 protocol violation'})
        self.assertEqual(kind, 'needs_input'); self.assertIn('partial work', reason)

    def test_capability_boundary_preserved(self):
        self.assertEqual(module.recommendation({'block_kind': 'capability'})[0], 'capability')
