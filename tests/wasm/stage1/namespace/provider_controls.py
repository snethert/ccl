"""Small state/publication faults, tested against the complete provider check."""
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'bootstrap-validation'))
import common as c
HERE = Path(__file__).resolve().parent


def run(out):
    original = (out / 'runtime/namespace.mjs').read_text()
    faults = {
        'borrow-owner-bytes': ('bytes = new Uint8Array(item.bytes);', 'bytes = item.bytes;'),
        'ignore-digest': ("need(digest === item.sha256, 'DIGEST');", ''),
        'expose-read-view': ('return bytes.slice(', 'return bytes.subarray('),
        'rewind-handle-identity': ('const fd = next++;', 'const fd = handles.size + 1;'),
        'omit-handle-capacity': ('handles.size < limits.handles && next <= limits.ids', 'true'),
        'advance-pread': ("pread: (fd, offset, count) => readAt(handle(fd, 'file'), offset, count),",
                         "pread: (fd, offset, count) => { const h = handle(fd, 'file'); h.position = offset; return readAt(h, offset, count); },"),
    }
    rows = []
    for name, (old, new) in faults.items():
        assert original.count(old) == 1, name
        trial = out / 'controls' / name
        (trial / 'runtime').mkdir(parents=True)
        for dependency in ('sha256.mjs', 'bytes.mjs'):
            shutil.copyfile(out / 'runtime' / dependency, trial / 'runtime' / dependency)
        shutil.copyfile(out / 'native.json', trial / 'native.json')
        (trial / 'runtime/namespace.mjs').write_text(original.replace(old, new))
        with (trial / 'rejection.log').open('w') as log:
            process = subprocess.run([c.NODE, HERE / 'check.mjs', trial], stdout=log, stderr=subprocess.STDOUT)
        text = (trial / 'rejection.log').read_text()
        assert process.returncode != 0 and 'AssertionError' in text, (name, text)
        rows.append(dict(name=name, status='REJECTED', source_sha256=c.sha(trial / 'runtime/namespace.mjs')))
    c.save(out / 'controls.json', dict(status='PASS', faults=rows))
    return rows
