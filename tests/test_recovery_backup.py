import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from contextlib import closing

spec = importlib.util.spec_from_file_location('recovery_backup', Path(__file__).resolve().parents[1] / 'extensions/operations/recovery_backup.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BackupTests(unittest.TestCase):
    def test_restore_contains_committed_wal_and_private_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); data = root / 'data'; data.mkdir()
            db = sqlite3.connect(data / 'state.db')
            self.addCleanup(db.close)
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE evidence(value TEXT)')
            db.execute("INSERT INTO evidence VALUES ('committed')"); db.commit()
            (data / '.env').write_text('TEST_ONLY=not-a-real-secret')
            (data / 'backups').mkdir(); (data / 'backups/old.zip').write_text('excluded')
            archive = root / 'recovery.zip'
            result = module.create({'data': data}, archive, root / 'status.json')
            self.assertTrue(result['ok'])
            self.assertEqual(result['restore_test']['databases'], 1)
            with zipfile.ZipFile(archive) as z:
                self.assertIn('data/.env', z.namelist())
                self.assertNotIn('data/backups/old.zip', z.namelist())
                self.assertNotIn('data/state.db-wal', z.namelist())
                z.extract('data/state.db', root / 'restored')
            with closing(sqlite3.connect(root / 'restored/data/state.db')) as restored:
                self.assertEqual(restored.execute('SELECT value FROM evidence').fetchone()[0], 'committed')
            db.close()

    def test_failure_replaces_stale_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); status = root / 'status.json'
            status.write_text('{"ok": true}')
            with self.assertRaises(ValueError):
                module.create({'data': root / 'missing'}, root / 'archive.zip', status)
            self.assertFalse(json.loads(status.read_text())['ok'])

    def test_tampered_archive_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); data = root / 'data'; data.mkdir()
            (data / 'one').write_text('original')
            archive = root / 'archive.zip'; module.create({'data': data}, archive)
            with zipfile.ZipFile(archive) as z:
                members = {name: z.read(name) for name in z.namelist()}
            members['data/one'] = b'tampered'
            with zipfile.ZipFile(archive, 'w') as z:
                for name, content in members.items(): z.writestr(name, content)
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                module.verify(archive)
