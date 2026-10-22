import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('lane_lock', Path(__file__).resolve().parents[1] / 'extensions/operations/lane_lock.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class LockTests(unittest.TestCase):
    def test_competing_runner_is_rejected_and_release_allows_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / 'lane.lock')
            first, second = module.FileLock(path), module.FileLock(path)
            first.acquire()
            try:
                with self.assertRaises(module.Timeout): second.acquire()
            finally:
                first.release()
            second.acquire(); second.release()
