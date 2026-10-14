"""Build an allowlisted offline Windows package using the installed CPython runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
P9_FILES = ('memory_store.py', 'memory_tools.py', 'mcp_server.py')
LOCAL_FILES = ('kjdb_local.py', 'config_helpers.py', 'generate_codex.py', 'generate_claude_desktop.py', 'generate_claude_code.py')
EXCLUDED = {'site-packages', '__pycache__', 'test', 'tests', 'ensurepip', 'idlelib', 'tkinter', 'turtledemo'}

def package(destination, library, python_root, version='0.1.1-preview'):
    destination = Path(destination).resolve()
    zip_path = destination.parent / (destination.name + '.zip')
    if destination.exists() or zip_path.exists():
        raise FileExistsError('Use a new package destination; existing packages are preserved')
    python_root = Path(python_root).resolve()
    required = [python_root / x for x in ('python.exe', 'python314.dll', 'python3.dll', 'LICENSE.txt')]
    if not (ROOT / 'LICENSE').is_file():
        raise FileNotFoundError('KJDB LICENSE is required for packaging')
    if not all(p.is_file() for p in required) or not Path(library).is_file():
        raise FileNotFoundError('CPython 3.14 runtime, its license and native memory DLL are required')
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', 'LICENSE', 'README.md', 'docs', 'src', 'include', 'tools/p9', 'tools/local'],
                   cwd=ROOT, check=True, capture_output=True)
    runtime = subprocess.check_output([str(required[0]), '-I', '-B', '-c',
        'import json,sys,struct; print(json.dumps([sys.version.split()[0],struct.calcsize("P")*8]))'], text=True)
    runtime_version, runtime_bits = json.loads(runtime)
    if runtime_bits != 64:
        raise ValueError('The Windows x64 package requires a 64-bit runtime')
    destination.mkdir(parents=True)
    def copy(source, target):
        target = destination / target
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    copy(ROOT / 'LICENSE', Path('LICENSE'))
    for source in required + list(python_root.glob('vcruntime*.dll')):
        copy(source, Path('runtime') / source.name)
    for base in ('Lib', 'DLLs'):
        for source in (python_root / base).rglob('*'):
            relative = source.relative_to(python_root)
            if not source.is_file() or any(x in EXCLUDED for x in relative.parts):
                continue
            if source.suffix.lower() not in ('.py', '.pyd', '.dll'):
                continue
            copy(source, Path('runtime') / relative)
    # Ignore installed Python and arbitrary PYTHONPATH/site customizations.
    (destination / 'runtime/python314._pth').write_text('Lib\nDLLs\n', encoding='utf-8')
    copy(library, Path('native/kjdb_memory.dll'))
    for name in P9_FILES:
        copy(ROOT / 'tools/p9' / name, Path('tools/p9') / name)
    for name in LOCAL_FILES:
        source = ROOT / 'tools/local' / name
        if source.is_file():
            copy(source, Path('tools/local') / name)
    readme = ROOT / 'tools/local/README.md'
    if readme.is_file():
        copy(readme, Path('README.md'))
    for name in ('CODEX.md', 'CLAUDE_DESKTOP.md', 'CLAUDE_CODE.md'):
        source = ROOT / 'tools/local' / name
        if source.is_file():
            copy(source, Path('guides') / name)
    for name in ('PRIVACY.md', 'VALIDATION.md'):
        copy(ROOT / 'docs' / name, Path('docs') / name)
    (destination / 'package.json').write_text(json.dumps({
        'name': 'kjdb-local-memory', 'version': version,
        'target': 'windows-x64', 'runtime': 'CPython ' + runtime_version,
        'python_license': 'runtime/LICENSE.txt',
        'license': 'MIT', 'kjdb_license': 'MIT', 'kjdb_license_file': 'LICENSE',
        'source_commit': source_commit,
        'supported_surfaces': ['Codex CLI', 'Claude Desktop regular chat', 'Claude Code CLI'],
        'excluded_surfaces': ['Claude Desktop Cowork/embedded Code with shared-store startup'],
        'durability': 'File flush only; Windows directory-entry power-loss durability unqualified',
        'release_status': 'preview; see docs/VALIDATION.md for qualified scope'
    }, indent=2) + '\n', encoding='utf-8')
    files = sorted(p for p in destination.rglob('*') if p.is_file())
    hashes = {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (destination / 'SHA256.json').write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(destination.rglob('*')):
            if p.is_file():
                archive.write(p, p.relative_to(destination))
    print(json.dumps({'package': str(destination), 'zip': str(zip_path), 'files': len(hashes),
                      'sha256': hashlib.sha256(zip_path.read_bytes()).hexdigest()}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--python-root', type=Path, required=True)
    parser.add_argument('--version', default='0.1.1-preview')
    args = parser.parse_args()
    package(args.destination, args.library, args.python_root, args.version)
