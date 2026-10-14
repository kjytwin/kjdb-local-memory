"""Create Codex stdio settings and a registration command for manual review."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).absolute().parent))
from config_helpers import SERVER_NAME, launch, command_text, write_new

def render(settings):
    return ('[mcp_servers.' + SERVER_NAME + ']\n'
            'command = ' + json.dumps(settings['command'], ensure_ascii=False) + '\n'
            'args = ' + json.dumps(settings['args'], ensure_ascii=False) + '\n'
            'startup_timeout_sec = 30\ntool_timeout_sec = 30\n')

def generate(package, project, output, data_root=None):
    settings = launch(package, project, data_root)
    output = Path(output)
    if output.exists():
        raise FileExistsError('Use a new output directory; no existing configuration is overwritten')
    output.mkdir(parents=True)
    write_new(output / 'codex-config.toml', render(settings))
    write_new(output / 'register-codex.ps1',
              '# Review first. This command changes your Codex MCP configuration.\n' +
              command_text(['codex', 'mcp', 'add', SERVER_NAME, '--', settings['command']] + settings['args']))
    return settings

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--project', default='codex-memory')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--data-root', type=Path)
    a = p.parse_args()
    generate(a.package, a.project, a.output, a.data_root)
