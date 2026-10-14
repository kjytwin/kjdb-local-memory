"""Generate Claude Code user registration command and reviewable stdio JSON."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).absolute().parent))
from config_helpers import SERVER_NAME, launch, ps_quote, write_new, json_text

def generate(package, project, output, data_root=None):
    settings = dict(type='stdio', **launch(package, project, data_root))
    output = Path(output)
    if output.exists():
        raise FileExistsError('Use a new output directory; no existing configuration is overwritten')
    output.mkdir(parents=True)
    write_new(output / 'claude-code-mcp.json', json_text({'mcpServers': {SERVER_NAME: settings}}))
    write_new(output / 'register-claude-code.ps1',
              '# Review first. This command changes your Claude Code user MCP configuration.\n' +
              '$kjdbClaude = Get-Command claude.exe -ErrorAction SilentlyContinue\n' +
              'if (-not $kjdbClaude) { $kjdbClaude = Get-Command claude.cmd -ErrorAction SilentlyContinue }\n' +
              "if (-not $kjdbClaude) { throw 'Install Claude Code before registration' }\n" +
              '& $kjdbClaude.Source ' + ' '.join(ps_quote(x) for x in
                  ['mcp', 'add', '--transport', 'stdio', '--scope', 'user', SERVER_NAME,
                   '--', settings['command']] + settings['args']) + '\n')
    return settings

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--project', default='claude-code-memory')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--data-root', type=Path)
    a = p.parse_args()
    generate(a.package, a.project, a.output, a.data_root)
