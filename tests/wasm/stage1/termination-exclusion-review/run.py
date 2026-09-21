import argparse,shutil,sys,json,hashlib,subprocess
from pathlib import Path
from derive_unit import HERE,PARENT,ROOT,SCENARIOS,entries,compile_source,native,old,replace,module
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def run(e,out):
 out.mkdir(parents=True);stage=out/'driver';stage.mkdir()
 prior=e/'2026-09-20-stage1-termination-exclusion-r1'
 for n,h in read(prior/'source-pins.json').items():assert sha(ROOT/n)==h,n
 for n in ['admission.mjs','admission-check.mjs','bindings.json']:shutil.copy(PARENT/n,stage/n)
 (stage/'entries.lisp').write_text(entries());(stage/'native.lisp').write_text(native())
 # Reuse R1 runner's unchanged admission controls and three compiled faults.
 # Redirect its source reads to the explicit derived driver, with repository
 # dependencies still resolved to their original sibling paths.
 s=(PARENT/'run.py').read_text()
 s=replace(s,'from derive import HERE,BASE,SCENARIOS,compile_source,check_source','from derive_unit import PARENT as BASE,SCENARIOS,compile_source,check_source')
 s=replace(s,'ROOT=HERE.parents[3]',f'ROOT=Path({str(ROOT)!r});HERE=Path({str(stage)!r})')
 s=s.replace("HERE.parent/'startup-runtime-review/conditions.mjs'", "ROOT/'tests/wasm/stage1/startup-runtime-review/conditions.mjs'").replace("HERE.parent/'startup-joined'", "ROOT/'tests/wasm/stage1/startup-joined'")
 s=replace(s,"'(if automatic_termination_enabled (termination_drain) nil)'", "'(if automatic_termination_enabled (error termination_unavailable) nil)'")
 (stage/'run.py').write_text(s)
 inherited=module(stage/'run.py','termination_review_runner');inherited.run(e,out/'execution')
 x=out/'execution';lines=(x/'native.log').read_text().splitlines()
 assert 'EMPTY-NATIVE|21|NIL-one-value' in lines
 assert len([l for l in lines if l.startswith('FILE-CLOSE|') and l.endswith('|flushed,closed')])==4
 save(x/'empty-native.json',dict(status='PASS',exact_nil_answers=21,file_closes=4,oracle='untouched native CCL functions; real stream close rerun with corrected replacements'))
 # Pin the actual consumer ordering; the generated caller models this selected
 # cancellation -> flush -> close path, not stream buffers or fd implementation.
 source=(ROOT/'level-1/l1-streams.lisp').read_text();a=source.index('(defun fd-stream-close ');b=source.index('\n(defun ',a+1);body=source[a:b]
 assert body.index('(cancel-terminate-when-unreachable s)')<body.index('(stream-force-output s)')<body.index('(fd-close fd)')
 (x/'native-close-source.lisp').write_text(body+'\n')
 controls=read(x/'controls.json');node='/usr/local/bin/node'
 sys.path.insert(0,str(HERE.parent/'startup-joined'));from compile import compile_source as build
 for name,entry,args,body,scenario,why in [
  ('cancel-still-errors','cancel','object &optional callback','(locally (declare (special termination_unavailable)) (error termination_unavailable))','fd-close-path','termination_fd_close_path: checked 15'),
  ('lookup-still-errors','lookup','object','(locally (declare (special termination_unavailable)) (error termination_unavailable))','lookup-direct','termination_lookup: checked 15'),
  ('drain-still-errors','drain','','(locally (declare (special termination_unavailable)) (error termination_unavailable))','drain-direct','termination_drain: checked 15'),
  ('cancel-reports-found','cancel','object &optional callback','t','cancel-default','Lisp result'),
 ]:
  d=x/'faults'/name;d.mkdir(parents=True)
  forms=replace(entries(),f'("termination_{entry}" (lambda ({args}) nil))',f'("termination_{entry}" (lambda ({args}) {body}))')
  m=build(e,d/'compile',compile_source(forms),None)
  for n in ['owner.mjs','sha256.mjs','bytes.mjs','collector.wasm','conditions.mjs','check.mjs']:shutil.copy(x/n,d/n)
  save(d/'scenarios.json',[r for r in SCENARIOS if r[0]==scenario])
  shutil.copytree(m,d/'compiled',ignore=shutil.ignore_patterns('source','proposal','compile-input','compiler.dx64fsl'))
  shutil.copy(x/'compiled/native.json',d/'compiled/native.json')
  inherited.command([node,d/'check.mjs',d,d/'execution.json'],d/'rejected.log',why)
  controls.append(dict(name=name,status='REJECTED',diagnostic=why))
 save(x/'controls.json',controls)
 result=read(x/'summary.json');result.update(controls=len(controls),native_empty_checks=21,native_file_closes=4);save(x/'summary.json',result);save(out/'summary.json',result)
 for n,h in read(prior/'source-pins.json').items():assert sha(ROOT/n)==h,n
 print(result)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
