"""Local utilities; all identities remain in the original rich-build namespace."""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCOPE = 'Observed native build binding versions; neither exhaustive runtime bounds nor target qualification.'


def require(ok, reason):
    if not ok: raise ValueError(reason)


def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':'))
def read(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())
def save(path, value):
    raw = (canonical(value) + '\n').encode()
    path.write_bytes(gzip.compress(raw, mtime=0) if path.suffix == '.gz' else raw)
def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
