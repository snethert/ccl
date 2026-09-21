"""Only l0-symbol gains a new reader conditional; reuse the other 51 joins."""
import json,os,subprocess,sys,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def run(source,proposal,out):
    out.mkdir()
    script=out/'readers.lisp'
    original=ROOT/'tests/wasm/stage1/bootstrap-core-acceptance/readers.lisp'
    text=original.read_text();old='(\"l0-def\" \"l0-pred\" \"l0-utils\")';assert text.count(old)==1
    script.write_text(text.replace(old,'(\"l0-symbol\")'))
    env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(source)+'/',READER_U1=str(source)+'/',READER_PROPOSAL=str(proposal)+'/',READER_OUTPUT=str(out)+'/')
    command=[str(source/'dx86cl64'),'--no-init','--batch','--load',str(ROOT/'tests/wasm/native-census/observer.lisp'),'--load',str(script)]
    with (out/'run.log').open('w') as log:subprocess.run(command,cwd=source,env=env,stdout=log,stderr=log,check=True,timeout=60)
    rows=json.loads((out/'readers.json').read_text())['rows'];assert len(rows)==17 and all(x['equal'] for x in rows)
    (out/'summary.json').write_text(json.dumps(dict(status='PASS',new_reader_comparisons=17,source_sha256=sha(proposal/'level-0/l0-symbol.lisp'),reused_reader_packet='2026-09-21-stage1-bootstrap-core-accepted',reused_reader_comparisons=51),indent=2)+'\n')
if __name__=='__main__':run(*(Path(x).resolve() for x in sys.argv[1:]))
