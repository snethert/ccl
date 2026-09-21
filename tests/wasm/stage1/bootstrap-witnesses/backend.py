from pathlib import Path
import json,shutil,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
PACKET=ROOT.parent/'ccl-evidence/2026-09-21-stage1-bootstrap-dependencies-r1/execution/compiled/proposal'
def generate():
 s=(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text()
 old='    (let ((code (bootstrap-operator ir)))'
 assert s.count(old)==1
 s=s.replace(old,'''    (let ((test (bootstrap-fixnum-test ir)))
      (when test (return-from b-scalar-inner (b-scalar test))))
'''+old)
 return s+'\n'+(HERE/'fixnum-tests.lisp').read_text()
def source_files(src):
 return {r['path']:(ROOT/r['path']).read_text() for r in json.loads((PACKET/'unit.json').read_text())['modified'] if r['path'].startswith('level-0/')}
def proposal(src,out):
 shutil.copytree(PACKET,out)
 m=json.loads((out/'unit.json').read_text())
 for row in m['added']+m['modified']:
  p=out/'files'/row['path'];p.write_bytes((ROOT/row['path']).read_bytes())
  if row['path']=='compiler/WASM32/wasm32-arch.lisp':p.write_text(p.read_text()+'\n'+(HERE/'layouts.lisp').read_text())
  row['sha256' if 'sha256' in row else 'after']=hashlib.sha256(p.read_bytes()).hexdigest()
 (out/'unit.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n');return m
def runtime_files():
 c=(ROOT/'runtime/wasm32/collector.c').read_text()
 o=(ROOT/'runtime/wasm32/collector-owner.mjs').read_text()
 assert c.count('tag==130&&n==6')==1 and o.count('tag===130&&n===6')==1
 return {'collector.c':c.replace('tag==130&&n==6','tag==130&&n>=1'),
         'collector-owner.mjs':o.replace('tag===130&&n===6','tag===130&&n>=1')}

