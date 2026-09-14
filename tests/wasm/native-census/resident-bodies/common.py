"""Small diagnostic utilities, without scanning the evidence archive."""
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
SCOPE='Read-only bootstrap function bytes and literal references; no complete source/IR traversal or runtime candidate bound.'

def require(ok,reason):
    if not ok:raise ValueError(reason)
def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def save(p,x):
    b=(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n').encode()
    p.write_bytes(gzip.compress(b,mtime=0) if p.suffix=='.gz' else b)
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

