import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).absolute().parents[2]
sys.path.insert(0, str(ROOT / 'tools/p9'))
from memory_store import MemoryStore, MemoryError
LIB = Path(os.environ['KJDB_TEST_LIBRARY'])

class WindowsPathTests(unittest.TestCase):
    def setUp(self):
        temp_root = ROOT / 'build-local/test-tmp'
        temp_root.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix='kjdb-path-', dir=temp_root)
        self.root = Path(self.tmp.name) / 'store with spaces'
    def tearDown(self):
        self.tmp.cleanup()
    @unittest.skipUnless(os.name == 'nt', 'Windows junction semantics')
    def test_project_directory_junction_is_rejected(self):
        target = Path(self.tmp.name) / 'junction-target'
        with MemoryStore(LIB, target, 'test') as store:
            store.remember('test', str(uuid.uuid4()), 'preserve junction target')
        before = (target / 'memory.log').read_bytes()
        env = dict(os.environ, KJDB_TEST_LINK=str(self.root), KJDB_TEST_TARGET=str(target))
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
            "$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path $env:KJDB_TEST_LINK -Target $env:KJDB_TEST_TARGET | Out-Null"],
            env=env, input=b'', capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, 'Junction creation failed; not a qualified rejection')
        try:
            self.assertTrue(self.root.is_junction())
            with self.assertRaises(MemoryError):
                MemoryStore(LIB, self.root, 'test')
            self.assertEqual((target / 'memory.log').read_bytes(), before)
        finally:
            # Remove only this test's junction, never recurse into its target.
            self.root.relative_to(Path(self.tmp.name))
            os.rmdir(self.root)

    @unittest.skipUnless(os.name == 'nt', 'Windows file reparse semantics')
    def test_memory_file_symlink_is_rejected(self):
        self.root.mkdir(parents=True)
        target = Path(self.tmp.name) / 'symlink-target'
        with MemoryStore(LIB, target, 'test') as store:
            store.remember('test', str(uuid.uuid4()), 'preserve symlink target')
        original = (target / 'memory.log').read_bytes()
        link = self.root / 'memory.log'
        try:
            os.symlink(target / 'memory.log', link)
        except OSError as error:
            if error.winerror == 1314:
                self.skipTest('Windows symlink privilege unavailable; file-reparse check unqualified')
            raise
        with self.assertRaises(MemoryError):
            MemoryStore(LIB, self.root, 'test')
        self.assertTrue(link.is_symlink())
        self.assertEqual((target / 'memory.log').read_bytes(), original)

    @unittest.skipUnless(os.name == 'nt', 'Windows directory sharing semantics')
    def test_open_store_pins_directory_against_rename(self):
        moved = self.root.with_name(self.root.name + ' moved')
        self.root.relative_to(Path(self.tmp.name))
        moved.relative_to(Path(self.tmp.name))
        # Establish permission with the same rename before and after the handle.
        self.root.mkdir(parents=True)
        self.root.rename(moved)
        moved.rename(self.root)
        with MemoryStore(LIB, self.root, 'test') as store:
            store.remember('test', str(uuid.uuid4()), 'before blocked rename')
            with self.assertRaises(OSError) as failure:
                self.root.rename(moved)
            self.assertIn(failure.exception.winerror, (5, 32))
            self.assertFalse(moved.exists())
            store.remember('test', str(uuid.uuid4()), 'after blocked rename')
        self.root.rename(moved)
        with MemoryStore(LIB, moved, 'test') as store:
            self.assertEqual(store.search('test', 'blocked rename')['count'], 2)
