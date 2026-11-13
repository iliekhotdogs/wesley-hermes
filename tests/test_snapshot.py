"""Invariants for the shipped snapshot, not exact version/model count snapshots."""
import ast
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
                reference = json.loads((ROOT / 'reference/live-profiles' / name / 'settings.json').read_text(encoding='utf-8'))
                self.assertEqual(config['model'], observed['model'])
                self.assertEqual(config['model'], observed['observed_live_model'])
                self.assertEqual(config['model'], reference['model'])
                self.assertEqual(config['approvals']['mode'], 'manual')
                for key in ['cron_mode', 'single_query_mode', 'unattended_mode']:
                    self.assertEqual(config['approvals'][key], 'deny')
                self.assertFalse(config['plugins']['enabled'])
                self.assertEqual(config['command_allowlist'], [])
                self.assertEqual(config['memory']['memory_enabled'], name in {'lib', 'main'})
                actual = sorted(p.parent.relative_to(ROOT / 'profiles' / name / 'skills').as_posix() for p in (ROOT / 'profiles' / name / 'skills').rglob('SKILL.md'))
                self.assertEqual(actual, sorted(observed['bundled_skill_directories']))
                self.assertEqual(len(actual), observed['bundled_skill_count'])
                self.assertEqual(len(observed['observed_skill_directories']), observed['observed_skill_count'])

    def test_deep_thinking_template_is_analysis_only_without_custom_policy(self):
        config = json.loads((ROOT / 'profiles/deep-thinking/config.yaml').read_text(encoding='utf-8'))
        self.assertEqual(config['agent']['reasoning_effort'], 'high')
        self.assertEqual(config['toolsets'], ['vision'])
        self.assertFalse(config['plugins']['enabled'])
        self.assertFalse(config['memory']['memory_enabled'])
        self.assertFalse(config['delegation']['orchestrator_enabled'])

    def test_all_manifest_json_and_python_payloads_parse(self):
        manifest = json.loads((ROOT / 'bundle-manifest.json').read_text(encoding='utf-8'))
        for rel in manifest['files']:
            path = ROOT / rel
            with self.subTest(path=rel):
                if path.suffix == '.json':
                    json.loads(path.read_text(encoding='utf-8-sig'))
                elif path.suffix == '.py':
                    ast.parse(path.read_text(encoding='utf-8-sig'), filename=rel)

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
