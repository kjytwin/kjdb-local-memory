import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
import unittest
import uuid
from config_helpers import SERVER_NAME, ps_quote
from generate_codex import generate, render

ROOT = Path(__file__).absolute().parents[2]
PACKAGE = Path(os.environ.get('KJDB_TEST_PACKAGE', ROOT / 'dist/KJDB-Windows-x64-common-v2'))

class CodexTests(unittest.TestCase):
    def setUp(self):
        tmp_root = ROOT / 'build-local/client-tests'
        tmp_root.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=tmp_root)
        self.root = Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def test_toml_roundtrip_paths_and_no_overwrite(self):
        settings = {'command': "C:\\한글 folder\\it's mine\\python.exe", 'args': ['-I', '-B', 'C:\\space folder\\main.py']}
        self.assertEqual(tomllib.loads(render(settings))['mcp_servers'][SERVER_NAME]['args'], settings['args'])
        self.assertEqual(tomllib.loads(render(settings))['mcp_servers'][SERVER_NAME]['command'], settings['command'])
        self.assertEqual(ps_quote("it's mine"), "'it''s mine'")
        generate(PACKAGE, 'codex-memory', self.root / 'settings', self.root / 'data')
        with self.assertRaises(FileExistsError):
            generate(PACKAGE, 'codex-memory', self.root / 'settings', self.root / 'data')
    def test_generated_command_real_storage(self):
        generate(PACKAGE, 'codex-memory', self.root / 'settings', self.root / 'data')
        settings = tomllib.loads((self.root / 'settings/codex-config.toml').read_text(encoding='utf-8'))['mcp_servers'][SERVER_NAME]
        init = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-11-25', 'capabilities': {}, 'clientInfo': {'name': 'config-test', 'version': '1'}}}
        ready = {'jsonrpc': '2.0', 'method': 'notifications/initialized'}
        def call(name, arguments):
            return {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': name, 'arguments': arguments}}
        def run(message):
            wire = b''.join(json.dumps(x, ensure_ascii=False).encode('utf-8') + b'\n' for x in [init, ready, message])
            out = subprocess.run([settings['command']] + settings['args'], input=wire, capture_output=True, timeout=20)
            self.assertEqual(out.returncode, 0, out.stderr)
            return json.loads(out.stdout.splitlines()[-1])['result']['structuredContent']
        saved = run(call('remember', {'project_id': 'codex-memory', 'request_id': str(uuid.uuid4()), 'text': 'Codex 한글 기억'}))
        read = run(call('get', {'project_id': 'codex-memory', 'memory_id': saved['result']['memory_id']}))
        self.assertEqual(read['result']['data']['text'], 'Codex 한글 기억')

if __name__ == '__main__':
    unittest.main(verbosity=2)
