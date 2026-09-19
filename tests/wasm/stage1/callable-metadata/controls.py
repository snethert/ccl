"""Executable compiler faults with distinct literal oracles; no count-only checks."""
import json,subprocess
from backend import generate
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
MUTANTS=[
 ('closure-arity','(metadata-child-load afunc 0)','"(i32.const 77825)"','arity identity'),
 ('closure-debug','(metadata-child-load afunc 1)','"(i32.const 77825)"','debug identity'),
 ('arity-count','(vector 1 (length (first args))','(vector 1 (1+ (length (first args)))','plain native arity'),
 ('key-alias-collapse','(copy-seq (or (fifth keys) #()))','(remove-duplicates (copy-seq (or (fifth keys) #())))','aliases native keys'),
 ('capture-name','(metadata-symbol (ccl::var-name (ccl::nx-root-var v)))','(metadata-symbol \'wrong-capture)','source capture names'),
 ('capture-slot','(loop for v in vars for i from 0 collect','(loop for v in (reverse vars) for i from 0 collect','debug slot resolves captured value'),
 ('truncated-self','(call $object_base (i32.load offset=40 (local.get $context)) (i32.const 32) (i32.const 1578))','(i32.sub (i32.load offset=40 (local.get $context)) (i32.const 6))','truncated-header'),
]
def run(e,out,execute):
 out.mkdir();rows=[]
 for name,old,new,oracle in MUTANTS:
  code=generate();start=code.index('(defun metadata-entry') if name=='truncated-self' else 0
  head,body=code[:start],code[start:];assert body.count(old)==1,(name,body.count(old));code=head+body.replace(old,new)
  (out/(name+'.lisp')).write_text(code)
  try:execute(e,out/name,code)
  except subprocess.CalledProcessError:
   log=out/name/'execution.log';assert log.exists(),name+' must compile and execute'
   text=log.read_text();assert 'AssertionError' in text and oracle in text,(name,text[-2500:])
  else:raise AssertionError(name+' escaped')
  rows.append(dict(name=name,status='REJECTED',oracle=oracle))
 save(out/'controls.json',rows);return rows
