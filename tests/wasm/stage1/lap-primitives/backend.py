"""The integrated tree, as the unit applied to a pristine U1 copy.

The LAP entries, their four backend lowerings, the square-root operations
and the L1-CLOS branches are committed on this branch, so the fixture
derives nothing: the compiler, arch file and every Lisp source under
compiler/, level-0/, level-1/, lib/, library/ and xdump/ that differs from
U1 form the unit, exactly as they stand in the checkout.
"""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BACKEND='compiler/WASM32/wasm32-backend.lisp';ARCH='compiler/WASM32/wasm32-arch.lisp'
U1='c994217adc56b3f8a564526cee4695893ac84d86'
SOURCE_DIRS=('compiler','level-0','level-1','lib','library','xdump')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate():return (ROOT/BACKEND).read_text()
def arch():return (ROOT/ARCH).read_text()
def source_files(root):return {}
def runtime_files():return {}
def unit_paths():
    out=subprocess.run(['git','-C',str(ROOT),'diff','--name-status',U1,'HEAD','--',*SOURCE_DIRS],capture_output=True,text=True,check=True).stdout
    rows=[line.split('\t') for line in out.splitlines() if line]
    assert all(r[0] in ('A','M') for r in rows),rows
    return [r[1] for r in rows if r[0]=='A'],[r[1] for r in rows if r[0]=='M']
def proposal(src,out):
    added,modified=unit_paths()
    out.mkdir(parents=True,exist_ok=False)
    for name in added+modified:
        p=out/'files'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    manifest={'source_revision':U1,
              'added':[{'path':n,'sha256':sha(out/'files'/n)} for n in added],
              'modified':[{'path':n,'before':sha(src/n),'after':sha(out/'files'/n)} for n in modified]}
    (out/'unit.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest
