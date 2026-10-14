"""Generate reviewable client settings without touching any client profile."""
import json
from pathlib import Path
from kjdb_local import project_name

SERVER_NAME = 'kjdb_local_memory'

def launch(package, project, data_root=None):
    project_name(project)
    package = Path(package).absolute()
    python = package / 'runtime/python.exe'
    script = package / 'tools/local/kjdb_local.py'
    if not all(p.is_file() for p in (python, script, package / 'native/kjdb_memory.dll')):
        raise FileNotFoundError('Extract the complete KJDB Windows package before generating settings')
    args = ['-I', '-B', str(script), '--project', project]
    if data_root is not None:
        args += ['--data-root', str(Path(data_root).absolute())]
    return {'command': str(python), 'args': args}

def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"

def command_text(tokens):
    return '& ' + ' '.join(ps_quote(x) for x in tokens) + '\n'

def write_new(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: never silently replace a user's proposed or installed settings.
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(content)

def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'
