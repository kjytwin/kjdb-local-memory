import json
import os
from pathlib import Path
import tempfile
import unittest
from client_acceptance import verify_launch
from config_helpers import SERVER_NAME
from generate_claude_code import generate

ROOT = Path(__file__).absolute().parents[2]
PACKAGE = Path(os.environ.get('KJDB_TEST_PACKAGE', ROOT / 'dist/KJDB-Windows-x64-common-v2'))

class ClaudeCodeTests(unittest.TestCase):
    def test_user_registration_and_overwrite_refusal(self):
        base = ROOT / 'build-local/client-tests'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as tmp:
            root = Path(tmp)
            generate(PACKAGE, 'claude-code-memory', root / 'settings', root / 'data')
            command = (root / 'settings/register-claude-code.ps1').read_text(encoding='utf-8')
            self.assertIn("'--scope' 'user'", command)
            self.assertIn("'--'", command)
            with self.assertRaises(FileExistsError):
                generate(PACKAGE, 'claude-code-memory', root / 'settings')
    def test_generated_json_real_persistence(self):
        base = ROOT / 'build-local/client-tests'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as tmp:
            root = Path(tmp)
            generate(PACKAGE, 'claude-code-memory', root / 'settings', root / 'data')
            config = json.loads((root / 'settings/claude-code-mcp.json').read_text(encoding='utf-8'))
            settings = config['mcpServers'][SERVER_NAME]
            self.assertEqual(settings['type'], 'stdio')
            verify_launch(settings, 'claude-code-memory')

if __name__ == '__main__':
    unittest.main(verbosity=2)
