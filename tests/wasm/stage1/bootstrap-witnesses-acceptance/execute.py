"""Execute the original fixture with its reviewed runtime in this interpreter."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

fixture = Path(__file__).resolve().parent.parent / 'bootstrap-witnesses'
packet = Path(sys.argv[2]).resolve()
manifest = json.loads((packet / 'packet.json').read_text())
sources = {}
for name in ('collector.c', 'collector-owner.mjs'):
    relative = 'execution/runtime/' + name
    entry, = [row for row in manifest['files'] if row['path'] == relative]
    data = (packet / relative).read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry['sha256']
    sources[name] = data.decode()
sys.path.insert(0, str(fixture))
import backend
backend.runtime_files = lambda: sources
runpy.run_path(str(fixture / 'execute.py'), run_name='__main__')
