"""Behavioral acceptance tests for real native storage and UTF-8 stdio."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/p9'))
from memory_store import MemoryStore, MemoryError

LIB = Path(os.environ.get('KJDB_TEST_LIBRARY', ROOT / 'build-local/native/kjdb_memory.dll'))
ENTRY = ROOT / 'tools/local/kjdb_local.py'
PYTHON = sys.executable

def initialize():
    return {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
        'protocolVersion': '2025-11-25', 'capabilities': {},
        'clientInfo': {'name': 'acceptance', 'version': '1'}}}

def call(i, name, args):
    return {'jsonrpc': '2.0', 'id': i, 'method': 'tools/call', 'params': {'name': name, 'arguments': args}}

def run_stdio(root, messages):
    wire = b''.join(json.dumps(m, ensure_ascii=False).encode('utf-8') + b'\n' for m in messages)
    result = subprocess.run([PYTHON, '-I', str(ENTRY), '--library', str(LIB),
                             '--data-root', str(root), '--project', 'test'],
                            input=wire, capture_output=True, timeout=20)
    if result.returncode:
        raise AssertionError(result.stderr.decode('utf-8', errors='replace'))
    return [json.loads(line) for line in result.stdout.decode('utf-8').splitlines()]

class CommonTests(unittest.TestCase):
    def setUp(self):
        temp_root = ROOT / 'build-local/test-tmp'
        temp_root.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix='kjdb-local-', dir=temp_root)
        self.root = Path(self.tmp.name) / '한글 경로 with spaces'
    def tearDown(self):
        self.tmp.cleanup()
    def test_utf8_restart_retry_and_scope(self):
        text = '한글 기억 🧠\n두 번째 줄'
        args = {'project_id': 'test', 'request_id': str(uuid.uuid4()), 'text': text}
        ready = {'jsonrpc': '2.0', 'method': 'notifications/initialized'}
        out = run_stdio(self.root, [initialize(), ready, call(2, 'remember', args)])
        saved = out[-1]['result']['structuredContent']['result']
        mid = saved['memory_id']
        out = run_stdio(self.root, [initialize(), ready,
            call(2, 'get', {'project_id': 'test', 'memory_id': mid}),
            call(3, 'remember', args),
            call(4, 'get', {'project_id': 'other', 'memory_id': mid})])
        self.assertEqual(out[1]['result']['structuredContent']['result']['data']['text'], text)
        self.assertTrue(out[2]['result']['structuredContent']['result']['duplicate'])
        self.assertEqual(out[3]['result']['structuredContent']['error'], 'scope_denied')
    def test_lock_and_backup(self):
        with MemoryStore(LIB, self.root / 'store', 'test') as store:
            store.remember('test', str(uuid.uuid4()), 'durable')
            with self.assertRaises(MemoryError) as failure:
                MemoryStore(LIB, self.root / 'store', 'test')
            self.assertEqual(failure.exception.code, 4)
            backup = self.root / 'backup.log'
            store.backup(backup)
            with self.assertRaises(MemoryError):
                store.backup(backup)
        target = self.root / 'restored'
        target.mkdir()
        backup.rename(target / 'memory.log')
        with MemoryStore(LIB, target, 'test') as store:
            self.assertEqual(store.search('test', 'durable')['count'], 1)
    def test_corrupt_store_is_preserved(self):
        self.root.mkdir(parents=True)
        path = self.root / 'memory.log'
        original = b'not a KJDB memory log'
        path.write_bytes(original)
        with self.assertRaises(MemoryError):
            MemoryStore(LIB, self.root, 'test')
        self.assertEqual(path.read_bytes(), original)
    @unittest.skipUnless(os.name == 'nt', 'Windows delayed publication qualification')
    def test_delayed_creator_never_overwrites_winner(self):
        fault = Path(os.environ.get('KJDB_TEST_FAULT_LIBRARY', ROOT / 'build-local/fault/kjdb_memory.dll'))
        helper = ROOT / 'tools/local/store_race_helper.py'
        child = subprocess.Popen([PYTHON, '-I', '-B', str(helper), str(fault), str(self.root)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            # Reading the readiness line in a bounded thread prevents a test hang.
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                ready = pool.submit(child.stdout.readline)
                try:
                    line = ready.result(timeout=15)
                    if line.strip() != b'READY':
                        if child.poll() is None:
                            child.kill()
                        _, stderr = child.communicate(timeout=5)
                        self.fail('Publication-barrier child failed: ' + stderr.decode('utf-8', errors='replace'))
                except Exception:
                    child.kill()
                    raise
            self.assertFalse((self.root / 'memory.log').exists())
            with MemoryStore(LIB, self.root, 'test') as winner:
                record = winner.remember('test', str(uuid.uuid4()), 'published winner')
            original = (self.root / 'memory.log').read_bytes()
            stdout, stderr = child.communicate(input=b'release\n', timeout=15)
            self.assertEqual(child.returncode, 0, stderr)
            self.assertEqual(json.loads(stdout)['operations'], 1)
            self.assertEqual((self.root / 'memory.log').read_bytes(), original)
            self.assertEqual(list(self.root.glob('.memory.init.*')), [])
            with MemoryStore(LIB, self.root, 'test') as store:
                self.assertEqual(store.get('test', record['memory_id'])['data']['text'], 'published winner')
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate()
    def test_hardlink_is_rejected(self):
        self.root.mkdir(parents=True)
        target = self.root / 'target.log'
        original = b'do not modify a linked file'
        target.write_bytes(original)
        try:
            os.link(target, self.root / 'memory.log')
        except PermissionError:
            self.skipTest('Sandbox denies hardlink creation; rejection needs external-host validation')
        with self.assertRaises(MemoryError) as failure:
            MemoryStore(LIB, self.root, 'test')
        self.assertEqual(failure.exception.code, 1)
        self.assertEqual(target.read_bytes(), original)
    def test_request_boundary_and_parse_recovery(self):
        wire = b'x' * 65537 + b'\nnot-json\n' + json.dumps(initialize()).encode() + b'\n'
        result = subprocess.run([PYTHON, '-I', '-B', str(ENTRY), '--library', str(LIB),
                                 '--data-root', str(self.root), '--project', 'test'],
                                input=wire, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0)
        replies = [json.loads(x) for x in result.stdout.splitlines()]
        self.assertEqual(replies[0]['error']['code'], -32600)
        self.assertEqual(replies[1]['error']['code'], -32700)
        self.assertIn('result', replies[2])
    def test_process_crash_committed_prefix(self):
        fault = Path(os.environ.get('KJDB_TEST_FAULT_LIBRARY', ROOT / 'build-local/fault/kjdb_memory.dll'))
        self.assertTrue(fault.is_file(), 'Build the --testing DLL for this acceptance test')
        for stage in (1, 2, 3, 4):
            directory = self.root / str(stage)
            with MemoryStore(LIB, directory, 'test') as store:
                store.remember('test', str(uuid.uuid4()), 'base')
            request = str(uuid.uuid4())
            code = ('import sys,ctypes; sys.path.insert(0,sys.argv[1]); '
                    'from memory_store import MemoryStore; '
                    's=MemoryStore(sys.argv[2],sys.argv[3],"test"); '
                    's.lib.kjm_test_crash_stage.argtypes=[ctypes.c_int]; '
                    's.lib.kjm_test_crash_stage(int(sys.argv[4])); '
                    's.remember("test",sys.argv[5],"crash record")')
            result = subprocess.run([PYTHON, '-I', '-B', '-c', code, str(ROOT / 'tools/p9'),
                                     str(fault), str(directory), str(stage), request],
                                    capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 90 + stage)
            with MemoryStore(LIB, directory, 'test') as store:
                self.assertEqual(store.search('test', 'base')['count'], 1)
                if stage in (1, 2):
                    self.assertEqual(store.status()['committed_operations'], 1)
                    self.assertTrue(store.status()['uncommitted_tail'])
                    with self.assertRaises(MemoryError):
                        store.remember('test', str(uuid.uuid4()), 'blocked')
                elif stage == 3:
                    self.assertEqual(store.status()['committed_operations'], 1)
                    self.assertTrue(store.status()['metadata_degraded'])
                    with self.assertRaises(MemoryError):
                        store.recover_uncommitted_tail()
                else:
                    self.assertEqual(store.status()['committed_operations'], 2)
                    self.assertTrue(store.remember('test', request, 'crash record')['duplicate'])
    def test_update_delete_and_conflict(self):
        with MemoryStore(LIB, self.root, 'test') as store:
            request = str(uuid.uuid4())
            item = store.remember('test', request, 'first')
            with self.assertRaises(MemoryError):
                store.remember('test', request, 'different')
            item = store.remember('test', str(uuid.uuid4()), 'second',
                                  memory_id=item['memory_id'], expected_version=1)
            store.forget('test', str(uuid.uuid4()), item['memory_id'], 2)
        with MemoryStore(LIB, self.root, 'test') as store:
            self.assertEqual(store.search('test', 'second')['count'], 0)
            with self.assertRaises(KeyError):
                store.get('test', item['memory_id'])
    def test_interrupted_creation_never_publishes_partial_store(self):
        fault = Path(os.environ.get('KJDB_TEST_FAULT_LIBRARY', ROOT / 'build-local/fault/kjdb_memory.dll'))
        self.assertTrue(fault.is_file())
        code = ('import sys,ctypes; sys.path.insert(0,sys.argv[1]); '
                'from memory_store import MemoryStore; '
                'lib=ctypes.CDLL(sys.argv[2]); lib.kjm_test_crash_stage.argtypes=[ctypes.c_int]; '
                'lib.kjm_test_crash_stage(int(sys.argv[4])); '
                's=MemoryStore(sys.argv[2],sys.argv[3],"test")')
        for stage in range(5, 12):
            with self.subTest(stage=stage):
                directory = self.root / ('creation-' + str(stage))
                result = subprocess.run([PYTHON, '-I', '-B', '-c', code, str(ROOT / 'tools/p9'),
                    str(fault), str(directory), str(stage)], input=b'', capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 90 + stage, result.stderr)
                self.assertEqual((directory / 'memory.log').exists(), stage >= 10)
                leftovers = {p.name: p.read_bytes() for p in directory.glob('.memory.init.*')}
                with MemoryStore(LIB, directory, 'test') as store:
                    self.assertEqual(store.status()['committed_operations'], 0)
                    store.remember('test', str(uuid.uuid4()), 'after interrupted creation')
                with MemoryStore(LIB, directory, 'test') as store:
                    self.assertEqual(store.search('test', 'after interrupted creation')['count'], 1)
                self.assertEqual(leftovers, {p.name: p.read_bytes() for p in directory.glob('.memory.init.*')})
    def test_invalid_project_rejected_before_creation(self):
        result = subprocess.run([PYTHON, '-I', str(ENTRY), '--library', str(LIB),
                                 '--data-root', str(self.root), '--project', '../outside'],
                                capture_output=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.root.exists())
    def test_second_server_reports_busy(self):
        # Claude Desktop 2.37337 starts a second instance per config entry (shared pool).
        with MemoryStore(LIB, self.root / 'test', 'test'):
            result = subprocess.run([PYTHON, '-I', str(ENTRY), '--library', str(LIB),
                                     '--data-root', str(self.root), '--project', 'test'],
                                    input=b'', capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b'')
        self.assertIn(b'store busy', result.stderr)
        self.assertNotIn(str(self.root).encode('utf-8'), result.stderr)
    def test_annotations_and_parse_recovery(self):
        ready = {'jsonrpc': '2.0', 'method': 'notifications/initialized'}
        out = run_stdio(self.root, [initialize(), ready,
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
            call(3, 'memory_status', {'project_id': 'test', 'shell': 'cmd'})])
        tools = {x['name']: x for x in out[1]['result']['tools']}
        self.assertEqual(len(tools), 5)
        self.assertFalse(tools['remember']['annotations']['readOnlyHint'])
        self.assertTrue(tools['forget']['annotations']['destructiveHint'])
        self.assertTrue(out[2]['result']['isError'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
