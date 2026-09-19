"""Default B mode emits exactly the accepted bytes for the same source corpus."""
import json,sys
from pathlib import Path
from run import prepare,command,HERE
from backend import prior

def run(e,out):
 out.mkdir();h=prepare(out/'harness')
 for n in ['compile.lisp','root-contracts.lisp']:
  p=h/n;p.write_text(p.read_text().replace('compile-retrying-call-module','compile-call-module'))
 old=out/'accepted-backend.lisp';old.write_text(prior.generate())
 for name,backend in [('accepted',old),('default',h/'wasm32-backend.lisp')]:
  command([sys.executable,h/'retry_probe.py',e,out/name,backend],out/(name+'.log'))
 files=sorted(p.relative_to(out/'accepted') for p in (out/'accepted').rglob('*') if p.suffix in ('.wat','.wasm') and 'executed-sources' not in p.parts and 'proposal' not in p.parts)
 for n in files:assert (out/'accepted'/n).read_bytes()==(out/'default'/n).read_bytes(),str(n)
 assert (out/'accepted/native.json').read_bytes()==(out/'default/native.json').read_bytes()
 result=dict(status='PASS',identical_files=len(files));(out/'compatibility.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':print(run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
