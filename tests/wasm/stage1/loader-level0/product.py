"""Whole-file loader proposal over the accepted loader identity."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'loader'))
import proposal as accepted
import common as c
ACCEPTED_SOURCES = accepted.sources
ACCEPTED_RUNTIME = accepted.prepare_runtime


def sources():
    bodies = ACCEPTED_SOURCES()
    pin = c.read(HERE / 'provenance.json')
    for name, digest in pin['sources'].items():
        assert c.sha(c.ROOT / name) == digest
        if name.endswith('.lisp'):
            bodies[name] = (HERE / 'files' / name).read_text()
    return bodies


def prepare_runtime(out):
    ACCEPTED_RUNTIME(out)
    for path in (HERE / 'files/runtime/wasm32').iterdir():
        (out / path.name).write_bytes(path.read_bytes())
