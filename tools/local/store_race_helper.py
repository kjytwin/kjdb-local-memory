"""Testing-only child: pause before publishing, then reopen a published winner."""
import ctypes
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).absolute().parents[2]
sys.path.insert(0, str(ROOT / 'tools/p9'))
from memory_store import MemoryStore

def main(library, directory):
    path = Path(directory)
    lib = ctypes.CDLL(library)
    lib.kjm_test_crash_stage.argtypes = [ctypes.c_int]
    lib.kjm_test_crash_stage(12)
    outcome = {}
    def create():
        try:
            with MemoryStore(library, path, 'test') as store:
                outcome['operations'] = store.status()['committed_operations']
        except Exception as error:
            outcome['error_class'] = type(error).__name__
    worker = threading.Thread(target=create, daemon=True)
    worker.start()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        temporary = list(path.glob('.memory.init.*'))
        if temporary:
            # LockFileEx blocks another handle's reads. Inspect metadata only;
            # stage 12 prevents publication until the explicit release.
            if temporary[0].stat().st_size == 8192:
                break
        if not worker.is_alive():
            raise RuntimeError('Creator stopped before publication barrier')
        time.sleep(0.01)
    else:
        raise RuntimeError('Timed out waiting for initialized private file')
    print('READY', flush=True)
    if sys.stdin.readline().strip() != 'release':
        raise RuntimeError('Expected explicit test release')
    lib.kjm_test_crash_stage(0)
    worker.join(timeout=10)
    if worker.is_alive():
        raise RuntimeError('Creator did not finish after release')
    print(json.dumps(outcome), flush=True)
    return 0 if 'error_class' not in outcome else 1

if __name__ == '__main__':
    raise SystemExit(main(*sys.argv[1:]))
