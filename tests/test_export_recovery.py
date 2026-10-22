import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('export_recovery', Path(__file__).resolve().parents[1] / 'tools/export_recovery.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class ExportTests(unittest.TestCase):
    def test_preflight_failure_invalidates_stale_success(self):
        for existing in (False, True):
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as folder:
                out=Path(folder); (out/'export-status.json').write_text('{"ok":true}')
                calls=[]
                def run(*args):
                    calls.append(args)
                    if args[0]=='inspect':
                        if not existing: raise RuntimeError('Docker unavailable')
                        return '[{"Image":"test"}]'
                    if args[0]=='ps': return 'hermes-recovery-export\n'
                    return ''
                with patch('sys.argv',['export','--output',folder,'--deployment',folder]), patch.object(module,'run',side_effect=run):
                    with self.assertRaises(RuntimeError): module.main()
                self.assertFalse(json.loads((out/'export-status.json').read_text())['ok'])
                self.assertFalse(any(c[0]=='rm' for c in calls))
