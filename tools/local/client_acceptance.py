"""Shared executable acceptance checks, never shipped as client configuration."""
import json
import subprocess
import uuid

def verify_launch(settings, project):
    init = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
        'protocolVersion': '2025-11-25', 'capabilities': {}, 'clientInfo': {'name': 'config-test', 'version': '1'}}}
    ready = {'jsonrpc': '2.0', 'method': 'notifications/initialized'}
    def exchange(name, args):
        message = {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': name, 'arguments': args}}
        wire = b''.join(json.dumps(x, ensure_ascii=False).encode('utf-8') + b'\n' for x in (init, ready, message))
        out = subprocess.run([settings['command']] + settings['args'], input=wire, capture_output=True, timeout=20)
        if out.returncode:
            raise AssertionError(out.stderr.decode('utf-8', errors='replace'))
        return json.loads(out.stdout.decode('utf-8').splitlines()[-1])['result']['structuredContent']
    text = project + ' 한글 기억 🧠'
    saved = exchange('remember', {'project_id': project, 'request_id': str(uuid.uuid4()), 'text': text})
    assert saved['ok']
    read = exchange('get', {'project_id': project, 'memory_id': saved['result']['memory_id']})
    assert read['result']['data']['text'] == text
    denied = exchange('memory_status', {'project_id': 'unrelated-project'})
    assert not denied['ok'] and denied['error'] == 'scope_denied'
