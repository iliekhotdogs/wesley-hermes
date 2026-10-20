"""Exercise the bundle CLI with real temporary files, never a live Hermes home."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'tools' / 'bundle.py'


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'source'
        self.source.mkdir()
        self.target = self.base / 'home'
        payload = {
            'profiles/main/config.yaml': json.dumps({'model': {'default': 'choose-your-model'}, 'approvals': {'mode': 'manual'}}),
            'profiles/main/SOUL.md': 'Coordinate authorized work.\n',
            'profiles/main/profile.yaml': json.dumps({'description': 'Coordinator'}),
            'profiles/main/skills/demo/SKILL.md': 'A harmless example skill.\n',
        }
        manifest = {}
        for rel, text in payload.items():
            file = self.source / rel
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(text, encoding='utf-8')
            manifest[rel] = hashlib.sha256(file.read_bytes()).hexdigest()
        (self.source / 'bundle-manifest.json').write_text(json.dumps({'profiles': ['main'], 'files': manifest}), encoding='utf-8')

    def call(self, *args):
        return subprocess.run([sys.executable, str(CLI), '--root', str(self.source), *args], capture_output=True, text=True)

    def test_existing_profile_is_never_overwritten(self):
        existing = self.target / 'profiles' / 'main'
        existing.mkdir(parents=True)
        soul = existing / 'SOUL.md'
        soul.write_text('Keep my own setup', encoding='utf-8')
        result = self.call('install', '--target', str(self.target), '--profiles', 'main')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(soul.read_text(encoding='utf-8'), 'Keep my own setup')

    def test_validate_accepts_manifest_hashes(self):
        result = self.call('validate')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_tampered_payload_is_rejected_before_creating_target(self):
        (self.source / 'profiles/main/SOUL.md').write_text('tampered', encoding='utf-8')
        result = self.call('install', '--target', str(self.target), '--profiles', 'main')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.target.exists())

    def test_manifest_cannot_include_runtime_files(self):
        secret = self.source / 'profiles/main' / ('.' + 'env')
        secret.write_text('PRIVATE=not-for-export', encoding='utf-8')
        path = self.source / 'bundle-manifest.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        data['files']['profiles/main/' + '.' + 'env'] = hashlib.sha256(secret.read_bytes()).hexdigest()
        path.write_text(json.dumps(data), encoding='utf-8')
        result = self.call('install', '--target', str(self.target), '--profiles', 'main')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.target.exists())

    def test_unknown_profile_cannot_escape_destination(self):
        result = self.call('install', '--target', str(self.target), '--profiles', '../escape')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.target.exists())

    def test_skills_are_opt_in(self):
        result = self.call('install', '--target', str(self.target), '--profiles', 'main', '--with-skills')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.target / 'profiles/main/skills/demo/SKILL.md').is_file())

    def test_manifest_traversal_is_rejected_before_writes(self):
        path = self.source / 'bundle-manifest.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        outside = self.base / 'outside.md'
        outside.write_text('outside', encoding='utf-8')
        data['files']['../outside.md'] = hashlib.sha256(outside.read_bytes()).hexdigest()
        path.write_text(json.dumps(data), encoding='utf-8')
        result = self.call('install', '--target', str(self.target), '--profiles', 'main')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.target.exists())

    def test_opt_in_skills_copy_only_manifest_declared_files(self):
        cache = self.source / 'profiles/main/skills/demo/__pycache__'
        cache.mkdir()
        (cache / 'local-only.pyc').write_bytes(b'local-only cached content')
        result = self.call('install', '--target', str(self.target), '--profiles', 'main', '--with-skills')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.target / 'profiles/main/skills/demo/__pycache__').exists())

    def test_fresh_install_is_explicit_and_contains_no_runtime_state(self):
        result = self.call('install', '--target', str(self.target), '--profiles', 'main')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        actual = sorted(p.relative_to(self.target).as_posix() for p in self.target.rglob('*') if p.is_file())
        self.assertEqual(actual, ['profiles/main/SOUL.md', 'profiles/main/config.yaml', 'profiles/main/profile.yaml'])


if __name__ == '__main__':
    unittest.main()
