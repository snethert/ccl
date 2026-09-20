#!/usr/bin/env python3
"""Rebuild freestanding integer Wasm, compare Python/native CCL, reject faults."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
sys.set_int_max_str_digits(0)
from corpus import cases,OPS
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
CLANG=Path('/usr/local/opt/llvm/bin/clang');NODE=Path('/usr/local/bin/node')
FLAGS=['--target=wasm32','-O2','-nostdlib','-fno-builtin','-Wall','-Wextra','-Werror','-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=65536','-Wl,-z,stack-size=65536','-Wl,--export=integer_calculate','-Wl,--export=integer_workspace_bytes']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,out,env=None):
 save(out.with_suffix('.command.json'),[str(x) for x in args])
 with out.open('w') as f:subprocess.run([str(x) for x in args],stdout=f,stderr=subprocess.STDOUT,env=env,cwd=out.parent,check=True,timeout=300)
def native(e,out,rows):
 kernel=e/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=e/'2026-09-16-stage1-1a-r2/native/baseline.image'
 for p in [kernel,image]:assert p.is_file()
 pins=json.loads((e/'2026-09-16-stage1-1a-r2/packet.json').read_text())['files'];expected=next(x['sha256'] for x in pins if x['path']=='native/baseline.image');assert sha(image)==expected
 assert sha(kernel)==json.loads((e/'2026-09-16-stage1-1a-r2/native/run.json').read_text())['kernel_sha256']
 save(out/'native-inputs.json',{str(p.relative_to(e)):sha(p) for p in [kernel,image]})
 datum='('+ '\n'.join(f'({r["a"]} {r["b"]})' for r in rows)+')'
 (out/'native-input.lisp').write_text(datum+'\n')
 forms=['(lambda (a b) (+ a b))','(lambda (a b) (- a b))','(lambda (a b) (* a b))','(lambda (a b) (ash a b))','(lambda (a b) (declare (ignore b)) (integer-length a))','(lambda (a b) (truncate a b))']
 source='''(let* ((pairs (with-open-file (s (ccl:getenv "INTEGER_INPUT")) (read s)))
                (ops 'OPS) (forms 'FORMS))
 (with-open-file (stream (ccl:getenv "INTEGER_OUTPUT") :direction :output :if-exists :error)
  (dolist (policy '((0 3) (3 0) (3 3)))
   (let ((compiled (mapcar (lambda (form) (compile nil (list* 'lambda (second form)
      (list 'declare (list 'optimize (list 'safety (first policy)) (list 'speed (second policy)) (list 'debug 0))) (cddr form)))) forms)))
    (loop for pair in pairs for op in ops do
     (handler-case
       (let ((*print-base* 10) (*print-radix* nil))
        (format stream "~{~d~^,~}~%" (multiple-value-list (apply (nth op compiled) pair))))
       (division-by-zero () (write-line "division-by-zero" stream))))))))
(format t "INTEGER-NATIVE-PASS~%")
(ccl:quit)
'''.replace('OPS','('+ ' '.join(str(OPS.index(r['op'])) for r in rows)+')').replace('FORMS','('+ ' '.join(forms)+')')
 (out/'native.lisp').write_text(source)
 # Disposable current directory, no init file, no upstream or image mutation.
 env={'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C','LC_ALL':'C','INTEGER_INPUT':str(out/'native-input.lisp'),'INTEGER_OUTPUT':str(out/'native-results.txt')}
 executable=out/'dx86cl64';shutil.copyfile(kernel,executable);executable.chmod(0o755)
 command([executable,'--image-name',image,'--no-init','--batch','--load',out/'native.lisp'],out/'native.log',env)
 got=(out/'native-results.txt').read_text().splitlines();want=[r['expected'] if isinstance(r['expected'],str) else ','.join(r['expected']) for r in rows]*3
 assert len(got)==len(want),(len(got),len(want))
 for i,(a,b) in enumerate(zip(got,want)):assert a==b,(i,rows[i%len(rows)]['name'],a,b)
 save(out/'native.json',dict(status='PASS',cases=len(rows),policies=[dict(safety=0,speed=3),dict(safety=3,speed=0),dict(safety=3,speed=3)],comparisons=len(got)))
def inspect(out):
 # Parse the emitted, name-free WAT, not the C source's intended call graph.
 # All function operands are numeric after wabt decoding. Reject every cycle.
 import re
 command(['/usr/local/bin/wasm2wat',out/'integer.wasm','-o',out/'integer.wat'],out/'decode.log')
 text=(out/'integer.wat').read_text();graph={};current=None
 for line in text.splitlines():
  m=re.match(r'  \(func \(;([0-9]+);\)',line)
  if m:current=int(m[1]);graph[current]=[]
  m=re.match(r'\s+(?:return_)?call ([0-9]+)(?:\s|$)',line)
  if m:
   assert current is not None;graph[current].append(int(m[1]))
 assert graph and all(t in graph for targets in graph.values() for t in targets)
 assert not re.search(r'\b(?:call_indirect|return_call_indirect|memory\.grow)\b',text)
 assert '(start ' not in text and '(data ' not in text and '(elem ' not in text
 def visit(n,active):
  assert n not in active,('recursive numeric fallback',n)
  for target in graph[n]:visit(target,active|{n})
 for n in graph:visit(n,set())
 save(out/'call-graph.json',dict(status='PASS',functions=graph,indirect_calls=0,function_imports=0,cycles=0))
def faults():
 return [
  ('carry','carry=z>>32;}\n r->n=n;', 'carry=0;}\n r->n=n;','add',1,(1<<64)-1),
  ('borrow','borrow=av<bv;','borrow=0;','sub',1<<64,1),
  ('negative-shift','if(a->neg&&discard)increment(r);','if(0&&a->neg&&discard)increment(r);','ash',-3,-1),
  ('masked-count','U words=count/32,part=count%32;W carry=0;','count&=31;U words=count/32,part=count%32;W carry=0;','ash',1,32),
  ('integer-length-negative','if(a.neg){b.n=1;','if(0){b.n=1;','length',-1,0),
  ('quotient-sign','q->neg=a->neg^b->neg;','q->neg=0;','truncate',-3,2),
  ('remainder-sign','trim(q);r->neg=a->neg;','trim(q);r->neg=0;','truncate',-3,2),
  ('fixnum-positive-bound','536870912u:536870911u','536870912u:536870912u','add',536870911,1),
  ('sign-extension','if((x->d[x->n-1]>>31)!=x->neg)','if(0)','ash',1,31),
  ('zero-divisor','if(!b->n)return ZERO_DIVISOR;','if(!b->n)return OK;','truncate',1,0),
  ('truncate-second-value','GET(result+4)=second;','GET(result+4)=0;','truncate',5,2),
  ('atomic-publication','if((W)out+n+m>limit)return CAPACITY;','GET(result)=99;if((W)out+n+m>limit)return CAPACITY;','length',1,0),
 ]
def run(e,out,mutants=True):
 out.mkdir(parents=True,exist_ok=False);rows=cases();save(out/'cases.json',rows)
 shutil.copy(HERE/'integer.c',out/'integer.c');shutil.copy(HERE/'execute.mjs',out/'execute.mjs')
 save(out/'toolchain.json',dict(tools=[dict(path=str(p),sha256=sha(p)) for p in [CLANG.resolve(),NODE.resolve(),Path('/usr/local/bin/wasm-ld').resolve(),Path('/usr/local/bin/wasm2wat').resolve()]],flags=FLAGS))
 command([CLANG,*FLAGS,out/'integer.c','-o',out/'integer.wasm'],out/'build.log')
 command([NODE,out/'execute.mjs',out/'integer.wasm',out/'cases.json',out/'execution.json'],out/'execution.log')
 native(e,out,rows);inspect(out);controls=[]
 if mutants:
  for name,old,new,op,a,b in faults():
   source=(HERE/'integer.c').read_text();assert source.count(old)==1,(name,source.count(old));m=out/name;m.mkdir();(m/'integer.c').write_text(source.replace(old,new))
   command([CLANG,*FLAGS,m/'integer.c','-o',m/'integer.wasm'],m/'build.log')
   from corpus import expected
   values=expected(op,a,b);focus=[dict(name=name+'-probe',op=op,a=str(a),b=str(b),expected=values if isinstance(values,str) else list(map(str,values)))]
   save(m/'focused.json',focus);oracle='no-output-space' if name=='atomic-publication' else name+'-probe @ 1048576:'
   command([NODE,out/'execute.mjs',out/'integer.wasm',m/'focused.json',m/'positive.json'],m/'positive.log')
   try:command([NODE,out/'execute.mjs',m/'integer.wasm',m/'focused.json',m/'execution.json'],m/'execution.log')
   except subprocess.CalledProcessError:
    log=json.loads((m/'execution.json').read_text());assert log['status']=='FAIL' and oracle in log['message'],(name,oracle,log);controls.append(dict(name=name,oracle=oracle,status='REJECTED'))
   else:raise AssertionError('escaped: '+name)
 save(out/'mutants.json',controls);save(out/'summary.json',dict(status='PASS',kind='AUXILIARY_INTEGER_SERVICE',cases=len(rows),native_comparisons=len(rows)*3,target_comparisons=len(rows)*2,chain_comparisons=sum('chain' in r for r in rows)*2,owner_refusals=len(json.loads((out/'execution.json').read_text())['refusals']),mutants=len(controls),gate_credit=False))
 print((out/'summary.json').read_text())
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--no-mutants',action='store_true');a=p.parse_args();run(a.evidence.resolve(),a.output.resolve(),not a.no_mutants)
