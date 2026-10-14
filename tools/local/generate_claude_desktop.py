"""Create a proposed Claude Desktop config; preserve existing unrelated settings."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).absolute().parent))
from config_helpers import SERVER_NAME, launch, write_new, json_text

def merged(existing, settings):
    if type(existing) is not dict or type(existing.get('mcpServers', {})) is not dict:
        raise ValueError('Existing Claude Desktop configuration must contain an object mcpServers')
    servers = dict(existing.get('mcpServers', {}))
    if SERVER_NAME in servers:
        raise ValueError('KJDB server already exists; inspect the existing entry before changing it')
    servers[SERVER_NAME] = settings
    result = dict(existing)
    result['mcpServers'] = servers
    return result

def generate(package, project, output, data_root=None, existing=None):
    settings = launch(package, project, data_root)
    previous = {} if existing is None else json.loads(Path(existing).read_text(encoding='utf-8-sig'))
    proposal = merged(previous, settings)
    output = Path(output)
    if output.exists():
        raise FileExistsError('Use a new output directory; no existing configuration is overwritten')
    output.mkdir(parents=True)
    write_new(output / 'claude_desktop_config.proposed.json', json_text(proposal))
    write_new(output / 'INSTALL.txt',
        'Review the proposed JSON, back up your existing config, then merge the KJDB entry into:\n'
        '%APPDATA%\\Claude\\claude_desktop_config.json\n'
        'Do not replace unrelated settings. Fully quit and restart Claude Desktop.\n'
        'If --existing was provided, the proposal preserves its content; keep that proposal private.\n')
    return settings

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--project', default='claude-desktop-memory')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--data-root', type=Path)
    p.add_argument('--existing', type=Path)
    a = p.parse_args()
    generate(a.package, a.project, a.output, a.data_root, a.existing)
