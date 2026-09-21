"""Ordered census and focused semantic controls, using the same disposable U1 driver."""
import importlib.util,json,re,shutil,subprocess,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('values_runner',Path(__file__).with_name('run.py'))
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
from backend import generate

def driver(source,out,text):
 sys.path.insert(0,str(source))
 spec=importlib.util.spec_from_file_location('extra_compile',source/'compile.py')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.run(r.EVIDENCE,out,text)

def run(out):
 phases=[]
 d=out/'measure-driver';shutil.copytree(out/'driver',d,dirs_exist_ok=True)
 (d/'compile.lisp').write_text('''(in-package :wasm32-compiler)
(load (merge-pathnames "measure.lisp" *load-pathname*))
(let ((out (ccl:getenv "POOL_OUTPUT")))
  (with-open-file (s (merge-pathnames "source-chunks.lisp" *load-pathname*))
    (measure-frontend (second (read s)) out)))
(format t "POOL-COMPILE-PASS~%") (ccl:quit)
''')
 for phase,text in [('integrated',(r.ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text()),('constants',generate('constants')),('specials',generate('specials'))]:
  target=out/('phase-'+phase);driver(d,target,text)
  record=json.loads((target/'throughput.json').read_text())
  rows=record['functions']
  for row in rows:
   if row['message']:row['message']=re.sub(r'#x[0-9A-Fa-f]{10,16}(?=>)', '#xOBJECT',row['message'])
  r.save(target/'throughput.json',record)
  phases.append(dict(phase=phase,admitted=sum(x['proposal']=='admitted' for x in rows),functions=len(rows)))
 rows=json.loads((out/'compiled/throughput.json').read_text())['functions']
 phases.append(dict(phase='or',admitted=sum(x['proposal']=='admitted' for x in rows),functions=len(rows)))
 assert phases[0]['admitted']==426 and all(a['admitted']<=b['admitted'] for a,b in zip(phases,phases[1:]))
 r.save(out/'phases.json',phases)
 # Reuse the positive source inventory; do not remeasure it per mutant.
 d=out/'fault-driver';shutil.copytree(out/'driver',d)
 s=(d/'compile.lisp').read_text().replace('(measure-frontend chunks out)', '''(setq *frontend-functions*
    (let ((*package* (find-package "CCL")))
      (with-open-file (s (merge-pathnames "original-definitions.lisp" *frontend-directory*))
        (loop for f = (read s nil nil) while f collect (list "retained" 0 f)))))''')
 (d/'compile.lisp').write_text(s);shutil.copy(out/'compiled/original-definitions.lisp',d/'original-definitions.lisp')
 faults=[
  ('special-global-only','(b-wat "(call $special_read_lisp ~a (local.get $top))" (b-special-symbol (first args)))','(b-wat "(i32.load offset=2 ~a)" (b-special-symbol (first args)))','special_bind'),
  ('quoted-symbol-mask','(and *bootstrap-front-end* (pool-literal-p (first args)))','(and *bootstrap-front-end* (not (eq (first args) \'type-error)) (pool-literal-p (first args)))','quote_symbol'),
  ('or-reversed-test','(if (i32.ne (local.get ~a) (i32.const 77825)) (then ~a) (else ~a))','(if (i32.eq (local.get ~a) (i32.const 77825)) (then ~a) (else ~a))','bitp'),
  ('or-last-primary','(b-multiple (car forms))\n    (let ((value (temporary)))','(b-multiple (make-b-raw-code :text (b-scalar (car forms))))\n    (let ((value (temporary)))','or_values'),
  ('or-repeat-success','(b-multiple (make-b-raw-code :text (b-local value)))','(b-multiple (car forms))','or_values')]
 records=[]
 for name,old,new,case in faults:
  text=generate();assert text.count(old)==1,(name,text.count(old));target=out/('fault-'+name);target.mkdir()
  driver(d,target/'compiled',text.replace(old,new))
  sys.path.insert(0,str(out/'driver'));from pool import compile_pool
  import encode
  encode.Encoder.__init__.__defaults__=(r.ROOT/'doc/WASM/contracts/wasm32-layout.v1.json',16*1024*1024)
  owners=json.loads((target/'compiled/symbols.json').read_text());pool=compile_pool(json.loads((target/'compiled/pools.json').read_text()),{x['id']:600006+32*i for i,x in enumerate(owners)})
  mat=pool.at(2097152);r.save(target/'compiled/materialized.json',dict(image=mat.image.hex(),roots=mat.roots))
  r.save(target/'compiled/moving-pools.json',{str(base):dict(image=pool.at(base).image.hex(),roots=pool.at(base).roots) for base in [262144,2147483648]})
  full=json.loads((target/'compiled/native.json').read_text())
  r.save(target/'compiled/native-all.json',full)
  selected=[row for row in full if row['name']==case];assert selected
  r.save(target/'compiled/native.json',selected)
  from probe import build
  build(target/'compiled')
  for f in ('collector.wasm','install.mjs','check.mjs'):shutil.copy(out/f,target/f)
  with (target/'failure.log').open('w') as log:result=subprocess.run(['/usr/local/bin/node',target/'check.mjs',target,target/'execution.json'],stdout=log,stderr=subprocess.STDOUT)
  assert result.returncode and case in (target/'failure.log').read_text(),(name,case)
  records.append(dict(name=name,expected_case=case,rejected=True))
 r.save(out/'faults.json',records)
if __name__=='__main__':run(Path(sys.argv[1]).resolve())
