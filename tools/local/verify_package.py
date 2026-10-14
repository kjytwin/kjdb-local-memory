"""Verify a freshly extracted package with its bundled runtime and real MCP calls."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
import zipfile

ROOT = Path(__file__).absolute().parents[2]
sys.path.insert(0, str(Path(__file__).absolute().parent))

def verify(archive):
    tmp_root = ROOT / 'build-local/package-tests'
    tmp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=tmp_root, prefix='새 컴퓨터 경로 ') as tmp:
        root = Path(tmp)
        package = root / '패키지 with spaces'
        with zipfile.ZipFile(archive) as zipped:
            # This is our own built archive; still reject paths leaving the root.
            for name in zipped.namelist():
                path = Path(name)
                if path.is_absolute() or '..' in path.parts or ':' in name:
                    raise ValueError('Invalid archive path')
            zipped.extractall(package)
        expected = json.loads((package / 'SHA256.json').read_text(encoding='utf-8'))
        actual = {p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()}
        assert actual == set(expected) | {'SHA256.json'}, 'Unexpected package content'
        for name, digest in expected.items():
            assert hashlib.sha256((package / name).read_bytes()).hexdigest() == digest, name
        metadata = json.loads((package / 'package.json').read_text(encoding='utf-8'))
        assert metadata['license'] == metadata['kjdb_license'] == 'MIT'
        assert metadata['kjdb_license_file'] == 'LICENSE'
        assert (package / 'LICENSE').read_bytes() == (ROOT / 'LICENSE').read_bytes()
        assert (package / metadata['python_license']).is_file()
        assert (package / 'docs/PRIVACY.md').is_file()
        assert (package / 'docs/VALIDATION.md').is_file()
        assert not any('memory.log' in name or 'site-packages' in name or '__pycache__' in name for name in actual)
        command = [str(package / 'runtime/python.exe'), '-I', '-B',
                   str(package / 'tools/local/kjdb_local.py'), '--project', 'fresh',
                   '--data-root', str(root / 'private-data')]
        def exchange(messages):
            wire = b''.join(json.dumps(m, ensure_ascii=False).encode('utf-8') + b'\n' for m in messages)
            result = subprocess.run(command, input=wire, capture_output=True, timeout=20)
            assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
            return [json.loads(x) for x in result.stdout.decode('utf-8').splitlines()]
        init = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
            'protocolVersion': '2025-11-25', 'capabilities': {}, 'clientInfo': {'name': 'fresh', 'version': '1'}}}
        ready = {'jsonrpc': '2.0', 'method': 'notifications/initialized'}
        def call(name, args):
            return {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': name, 'arguments': args}}
        text = '새 패키지의 한글 기억 🧠'
        saved = exchange([init, ready, call('remember', {
            'project_id': 'fresh', 'request_id': str(uuid.uuid4()), 'text': text})])[-1]['result']['structuredContent']
        assert saved['ok']
        read = exchange([init, ready, call('get', {
            'project_id': 'fresh', 'memory_id': saved['result']['memory_id']})])[-1]['result']['structuredContent']
        assert read['result']['data']['text'] == text
        # Execute each real packaged generator through isolated bundled Python.
        import tomllib
        for app, project in (('codex', 'codex-memory'), ('claude_desktop', 'claude-desktop-memory'),
                             ('claude_code', 'claude-code-memory')):
            output = root / (app + '-setup')
            result = subprocess.run([str(package / 'runtime/python.exe'), '-I', '-B',
                str(package / 'tools/local' / ('generate_' + app + '.py')),
                '--package', str(package), '--output', str(output), '--data-root', str(root / 'client-data')],
                capture_output=True, timeout=20)
            assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
            if app == 'codex':
                settings = tomllib.loads((output / 'codex-config.toml').read_text(encoding='utf-8'))['mcp_servers']['kjdb_local_memory']
            else:
                name = 'claude_desktop_config.proposed.json' if app == 'claude_desktop' else 'claude-code-mcp.json'
                settings = json.loads((output / name).read_text(encoding='utf-8'))['mcpServers']['kjdb_local_memory']
            from client_acceptance import verify_launch
            verify_launch(settings, project)
        print(json.dumps({'package_integrity': True, 'bundled_runtime': True,
                          'utf8_restart_persistence': True,
                          'packaged_generators_and_generated_commands': ['codex', 'claude_desktop', 'claude_code'],
                          'clean_other_windows_machine': 'not tested'}))

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive', type=Path)
    verify(p.parse_args().archive)
