"""Release gates for capacity preservation and preview data compatibility."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import uuid

from test_local import LIB, MemoryStore, MemoryError


class ReleaseTests(unittest.TestCase):
    def test_capacity_refusal_preserves_data_across_reopen(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'store'
            with MemoryStore(LIB, root, 'capacity') as store:
                first = None
                for index in range(1000):
                    saved = store.remember('capacity', str(uuid.uuid4()), f'capacity record {index}')
                    if first is None:
                        first = saved['memory_id']
                before = Path(temp) / 'before.log'
                after = Path(temp) / 'after.log'
                store.backup(before)
                with self.assertRaises(MemoryError) as refused:
                    store.remember('capacity', str(uuid.uuid4()), 'must be refused')
                self.assertEqual(refused.exception.code, 5)
                store.backup(after)
            self.assertEqual(before.read_bytes(), after.read_bytes())
            self.assertEqual((root / 'memory.log').read_bytes(), before.read_bytes())
            with MemoryStore(LIB, root, 'capacity') as store:
                self.assertEqual(store.status()['active_memories'], 1000)
                self.assertEqual(store.get('capacity', first)['data']['text'], 'capacity record 0')
                store.forget('capacity', str(uuid.uuid4()), first, 1)
                store.remember('capacity', str(uuid.uuid4()), 'replacement after explicit delete')
                self.assertEqual(store.status()['active_memories'], 1000)

    @unittest.skipUnless(os.environ.get('KJDB_UPGRADE_BASELINE'), 'Pinned preview package required for upgrade qualification')
    def test_preview_upgrade_backup_restore_and_rollback(self):
        baseline = Path(os.environ['KJDB_UPGRADE_BASELINE']).resolve()
        helper = '''import json,sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'tools/p9'))
from memory_store import MemoryStore
with MemoryStore(Path(sys.argv[1])/'native/kjdb_memory.dll',Path(sys.argv[2]),'upgrade') as store:
    if sys.argv[3]=='create':
        result=store.remember('upgrade',str(uuid.uuid4()),'preview preserved text')
    else:
        result=store.get('upgrade',sys.argv[3])
print(json.dumps(result))
'''
        def old(root, action):
            out = subprocess.run([str(baseline / 'runtime/python.exe'), '-I', '-B', '-c',
                helper, str(baseline), str(root), action], input=b'', capture_output=True, timeout=30)
            self.assertEqual(out.returncode, 0, out.stderr.decode('utf-8', errors='replace'))
            return json.loads(out.stdout)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'store'
            saved = old(root, 'create')
            mid = saved['memory_id']
            before = (root / 'memory.log').read_bytes()
            backup = Path(temp) / 'before-upgrade.log'
            with MemoryStore(LIB, root, 'upgrade') as store:
                self.assertEqual(store.get('upgrade', mid)['data']['text'], 'preview preserved text')
                store.backup(backup)
            self.assertEqual((root / 'memory.log').read_bytes(), before)
            self.assertEqual(backup.read_bytes(), before)
            with MemoryStore(LIB, root, 'upgrade') as store:
                store.remember('upgrade', str(uuid.uuid4()), 'candidate updated text',
                               memory_id=mid, expected_version=1)
            updated = old(root, mid)
            self.assertEqual(updated['version'], 2)
            self.assertEqual(updated['data']['text'], 'candidate updated text')
            restored = Path(temp) / 'restored'
            restored.mkdir()
            shutil.copyfile(backup, restored / 'memory.log')
            original = old(restored, mid)
            self.assertEqual(original['version'], 1)
            self.assertEqual(original['data']['content_sha256'],
                             hashlib.sha256(b'preview preserved text').hexdigest())
            self.assertEqual((restored / 'memory.log').read_bytes(), before)
