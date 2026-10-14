import json
import os
from pathlib import Path
import tempfile
import unittest
from config_helpers import SERVER_NAME
from generate_claude_desktop import generate, merged
from client_acceptance import verify_launch

ROOT = Path(__file__).absolute().parents[2]
PACKAGE = Path(os.environ.get('KJDB_TEST_PACKAGE', ROOT / 'dist/KJDB-Windows-x64-common-v2'))

class DesktopTests(unittest.TestCase):
    def test_preserves_settings_and_rejects_collision(self):
        previous = {'preferences': {'theme': 'dark'}, 'mcpServers': {'other': {'command': 'other.exe'}}}
        original = json.dumps(previous)
        result = merged(previous, {'command': 'python.exe', 'args': ['-I']})
        self.assertEqual(result['preferences'], previous['preferences'])
        self.assertEqual(result['mcpServers']['other'], previous['mcpServers']['other'])
        self.assertEqual(json.dumps(previous), original)
        with self.assertRaises(ValueError):
            merged(result, {})
        with self.assertRaises(ValueError):
            merged({'mcpServers': []}, {})
    def test_generated_json_and_exclusive_output(self):
        base = ROOT / 'build-local/client-tests'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as tmp:
            root = Path(tmp)
            settings = generate(PACKAGE, 'claude-desktop-memory', root / 'settings', root / 'data')
            value = json.loads((root / 'settings/claude_desktop_config.proposed.json').read_text(encoding='utf-8'))
            self.assertEqual(value['mcpServers'][SERVER_NAME], settings)
            verify_launch(value['mcpServers'][SERVER_NAME], 'claude-desktop-memory')
            with self.assertRaises(FileExistsError):
                generate(PACKAGE, 'claude-desktop-memory', root / 'settings')

if __name__ == '__main__':
    unittest.main(verbosity=2)
