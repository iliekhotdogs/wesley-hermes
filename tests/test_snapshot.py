"""Invariants for the shipped snapshot, not exact version/model count snapshots."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SnapshotTests(unittest.TestCase):
    def test_installable_model_choices_match_the_observed_inventory(self):
        inventory = json.loads((ROOT / 'inventory.json').read_text(encoding='utf-8'))
        for name, observed in inventory['profiles'].items():
            with self.subTest(profile=name):
                config = json.loads((ROOT / 'profiles' / name / 'config.yaml').read_text(encoding='utf-8'))
                self.assertEqual(config['model'], observed['model'])
                self.assertEqual(config['approvals']['mode'], 'manual')
                for key in ['cron_mode', 'single_query_mode', 'unattended_mode']:
                    self.assertEqual(config['approvals'][key], 'deny')
                self.assertFalse(config['plugins']['enabled'])
                self.assertEqual(config['command_allowlist'], [])
                self.assertEqual(config['memory']['memory_enabled'], name == 'lib')
                actual = sorted(p.parent.relative_to(ROOT / 'profiles' / name / 'skills').as_posix() for p in (ROOT / 'profiles' / name / 'skills').rglob('SKILL.md'))
                self.assertEqual(actual, sorted(observed['bundled_skill_directories']))
                self.assertEqual(len(actual), observed['bundled_skill_count'])
                self.assertEqual(len(observed['observed_skill_directories']), observed['observed_skill_count'])

    def test_automation_examples_have_no_active_jobs(self):
        examples = json.loads((ROOT / 'examples/automation.json').read_text(encoding='utf-8'))
        self.assertEqual(examples['active_jobs'], [])
        self.assertTrue(all(t['enabled'] is False for t in examples['templates']))

    def test_optional_extension_python_is_parseable_without_importing_or_running_it(self):
        for path in (ROOT / 'extensions').rglob('*.py'):
            with self.subTest(file=path.relative_to(ROOT).as_posix()):
                compile(path.read_text(encoding='utf-8-sig'), path.name, 'exec')


if __name__ == '__main__':
    unittest.main()
