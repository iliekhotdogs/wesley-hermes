import base64
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer

from common import allowed, files, modes, pack, unpack, materialize, apply_result


class WorkspaceTests(unittest.TestCase):
    def test_credential_and_runtime_files_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ['code.py', '.env', '.env.example', 'auth.json', 'nested/google_token.json', '.git/config', 'node_modules/pkg.js']:
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('synthetic test data')
            self.assertEqual(set(files(root)), {'code.py'})

    def test_source_symlink_does_not_read_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'selected'
            root.mkdir()
            outside = Path(tmp) / 'outside'
            outside.write_text('synthetic sentinel')
            (root / 'link').symlink_to(outside)
            self.assertEqual(files(root), {})

    def test_unsafe_archive_entries_are_rejected(self):
        for name, kind in [('../outside', tarfile.REGTYPE), ('/outside', tarfile.REGTYPE),
                           ('auth.json', tarfile.REGTYPE), ('link', tarfile.SYMTYPE)]:
            out = io.BytesIO()
            with tarfile.open(fileobj=out, mode='w:gz') as t:
                member = tarfile.TarInfo(name)
                member.type = kind
                if kind == tarfile.SYMTYPE:
                    member.linkname = '/opt/data/auth.json'
                t.addfile(member)
            with self.subTest(name=name), self.assertRaises(ValueError):
                unpack(base64.b64encode(out.getvalue()).decode())

    def test_conflict_rejects_all_changes_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'selected'
            root.mkdir()
            materialize(root, {'a.py': b'original', 'b.py': b'original'})
            before = files(root)
            (root / 'b.py').write_bytes(b'user concurrent edit')
            with self.assertRaises(ValueError):
                apply_result(root, before, {'a.py': b'worker', 'b.py': b'worker'}, Path(tmp) / 'backup')
            self.assertEqual((root / 'a.py').read_bytes(), b'original')

    def test_apply_creates_backup_and_carries_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'selected'
            root.mkdir()
            materialize(root, {'test.sh': b'old'}, {'test.sh': 0o755})
            before = files(root)
            original_modes = modes(root, before)
            encoded = pack({'test.sh': b'new', 'new.py': b'hello'}, {'test.sh': 0o755})
            final_modes = {}
            after = unpack(encoded, final_modes)
            backup = Path(tmp) / 'backup'
            result = apply_result(root, before, after, backup, original_modes, final_modes)
            self.assertEqual((backup / 'test.sh').read_bytes(), b'old')
            self.assertTrue((root / 'test.sh').stat().st_mode & 0o100)
            self.assertEqual(result['changed_files'], ['new.py', 'test.sh'])

    def test_result_cannot_write_through_directory_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, outside = Path(tmp) / 'selected', Path(tmp) / 'outside'
            root.mkdir()
            outside.mkdir()
            (root / 'linked').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                apply_result(root, {}, {'linked/write.py': b'no'}, Path(tmp) / 'backup')
            self.assertFalse((outside / 'write.py').exists())


class ProxyTests(unittest.TestCase):
    def test_denied_requests_never_resolve_real_credentials(self):
        with patch.dict(os.environ, {'INFERENCE_PROXY_TOKEN': 'synthetic-local-test-key'}):
            import inference_proxy as proxy
        server = ThreadingHTTPServer(('127.0.0.1', 0), proxy.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.object(proxy, 'resolve_codex_runtime_credentials') as resolve:
                for path, key, model, expected in [
                    ('/responses', 'wrong', proxy.MODEL, 401),
                    ('/credentials', 'synthetic-local-test-key', proxy.MODEL, 404),
                    ('/responses', 'synthetic-local-test-key', 'unapproved-model', 403),
                ]:
                    req = Request(f'http://127.0.0.1:{server.server_port}' + path,
                                  data=json.dumps({'model': model}).encode(),
                                  headers={'Authorization': 'Bearer ' + key})
                    with self.subTest(path=path, model=model), self.assertRaises(HTTPError) as caught:
                        urlopen(req)
                    self.assertEqual(caught.exception.code, expected)
                resolve.assert_not_called()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
