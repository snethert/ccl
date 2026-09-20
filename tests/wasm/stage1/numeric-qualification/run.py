"""Compile and execute the adopted LL16 subset using the integrated backend."""
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys
from pathlib import Path
sys.set_int_max_str_digits(0)
sys.modules["ll16_driver"]=sys.modules[__name__]
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]; BASE=HERE.parent/'float-calls'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1200)
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def driver():
 sys.path[:0]=[str(BASE/'review-followup'),str(BASE)]
 r=load('ll16_float_followup',BASE/'review-followup/run.py')
 return r

def prepare(e,out):
 out.mkdir(parents=True,exist_ok=False)
 r=driver();prior=r.prior
 # Independent integer expectations are regenerated from the reviewed Python
 # oracle in its own interpreter so the two fixtures' module names cannot alias.
 source=HERE.parent/'integer-core/review-followup/run.py'
 code='import sys,runpy,json;sys.set_int_max_str_digits(0);sys.path.insert(0,'+repr(str(source.parent))+');m=runpy.run_path('+repr(str(source))+');print(json.dumps(m["cases"]()))'
 command([sys.executable,'-c',code],out/'integer-oracle.json')
 integers=read(out/'integer-oracle.json');sources=dict(prior.SOURCES);rows=r.cases()
 forms={'add':'(+ a b)','sub':'(- a b)','mul':'(* a b)','ash':'(ash a b)','length':'(integer-length a)','truncate':'(handler-case (truncate a b) (division-by-zero () 102))'}
 policies=[(0,3),(3,0),(3,3)]
 for pi,(safety,speed) in enumerate(policies):
  for op,body in forms.items():sources[f'q{pi}_{op}']='(lambda (a b) '+body+')'
  for c in integers:
   rows.append(dict(id=len(rows),function=f'q{pi}_'+c['op'],args=[c['a'],c['b']],mask=7,safe=int(safety>0),policy=False,family=c['op'],oracle=['102'] if c['expected']=='division-by-zero' else c['expected'],native_policy=[safety,speed],origin=c['name']))
 # Timed functions perform 64 operations inside the generated loop, including
 # every rooted call and allocation. Inputs avoid exceptional/subnormal paths.
 for op,body in [('add','(+ a b)'),('sub','(- a b)'),('mul','(* a b)'),('div','(/ a b)'),('single','(float a 1.0s0)'),('mixed','(+ a b)')]:
  name='bench_'+op
  sources[name]='(lambda (a b) (let ((n 64) (x a)) (tagbody again (setq x '+body+') (setq n (- n 1)) (if (eq n 0) (go done) (go again)) done) x))'
  for safe in [0,1]:rows.append(dict(id=len(rows),function=name,args=['7' if op=='mixed' else '1.5d0','2.0d0'],mask=7,safe=safe,policy=False))
 prior.SOURCES=sources;prior.cases=lambda:rows
 prior.generate=lambda:(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text()
 # The native reference is compiled at each explicit policy. Target checking
 # is the accepted compile entry's 0/1 argument, not an OPTIMIZE source extension.
 original_copy=shutil.copy
 def copy(src,dst,*args,**kw):
  result=original_copy(src,dst,*args,**kw)
  if Path(src)==BASE/'compile.lisp':
   p=Path(dst);s=p.read_text();a='(let* ((rows (with-open-file'
   helper='''(defun qualification-native-form (name form)
 (let ((p (cond ((search "q0_" name) '(0 3)) ((search "q1_" name) '(3 0)) ((search "q2_" name) '(3 3)))))
  (if p (list* 'lambda (second form) (list 'declare (list 'optimize (list 'safety (first p)) (list 'speed (second p)) (list 'debug 1))) (cddr form)) form)))
'''
   assert s.count(a)==1;s=s.replace(a,helper+a)
   a='         (second r))))) rows))';assert s.count(a)==1
   s=s.replace(a,'         (qualification-native-form (first r) (second r)))))) rows))');p.write_text(s)
  return result
 try:
  shutil.copy=copy;prior.compile(e,out/'generated')
 finally:shutil.copy=original_copy
 got=read(out/'generated/native.json');witness=[]
 for row in got:
  if 'oracle' in row:
   assert row['expected']==row['oracle'],(row['function'],row['origin'],row['expected'],row['oracle'])
   witness.append({k:row[k] for k in ['id','function','family','origin','native_policy','oracle','expected']})
 save(out/'independent-integers.json',witness)
 # Exact reviewed sources; no proposal derivation or historical /tmp dependency.
 d=out/'generated'
 for p in (ROOT/'runtime/wasm32').glob('*.mjs'):shutil.copy(p,d/p.name)
 shutil.copy(ROOT/'runtime/wasm32/stub.wat',d/'stub.wat')
 s=load('ll16_derive',BASE/'derive.py').execute()
 (d/'execute.mjs').write_text(s)
 for n,source,flags in [('integer',ROOT/'runtime/wasm32/integer.c',HERE.parent/'integer-core/run.py'),('float',ROOT/'runtime/wasm32/float.c',HERE.parent/'float-core/run.py')]:
  # Read build constants without executing the old generator.
  import ast
  constants={}
  for node in ast.parse(flags.read_text()).body:
   if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='FLAGS':constants['FLAGS']=ast.literal_eval(node.value)
  from types import SimpleNamespace
  mod=SimpleNamespace(FLAGS=constants['FLAGS'],CLANG=Path('/usr/local/opt/llvm/bin/clang'));f=mod.FLAGS+(['-Wl,--export=float_calculate_lisp'] if n=='float' else [])
  command([mod.CLANG,*f,source,'-o',d/(n+'.wasm')],out/(n+'-build.log'))
  save(out/(n+'-build.json'),dict(source=str(source.relative_to(ROOT)),source_sha256=sha(source),binary_sha256=sha(d/(n+'.wasm')),flags=f,clang=str(mod.CLANG.resolve()),clang_sha256=sha(mod.CLANG.resolve())))
 # Accepted detector uses a wider memory declaration in the service embedding.
 det=(ROOT/'runtime/wasm32/float-detector.wat').read_text();assert det.count('(memory 1 32769)')==1
 (d/'detector.wat').write_text(det)
 command(['/usr/local/bin/wat2wasm',d/'detector.wat','-o',d/'detector.wasm'],out/'detector-build.log')
 command(['/usr/local/bin/wat2wasm','--enable-tail-call',d/'stub.wat','-o',d/'stub.wasm'],out/'stub-build.log')
 assert sha(d/'integer.wasm')==sha(e/'2026-09-19-stage1-integer-core-r1/execution/integer.wasm')
 assert sha(d/'float.wasm')==sha(e/'2026-09-20-stage1-float-calls-r2/float-lisp.wasm')
 assert sha(d/'detector.wasm')==sha(e/'2026-09-19-stage1-float-core-r2/execution/detector.wasm')
 save(d/'service-inputs.json',{n:sha(d/(n+'.wasm')) for n in ['float','detector']})
 return d

def execute(e,d,mode):
 command(['/usr/local/bin/node',d/'execute.mjs',d,e/'2026-09-19-stage1-collector-qualification-r1/collector.wasm',d/'integer.wasm',d/(mode+'.json'),mode],d/(mode+'.log'))

def run(e,out,bench=True):
 d=prepare(e,out)
 for mode in ['eager','cold']:execute(e,d,mode)
 assert read(d/'eager.json')==read(d/'cold.json')
 command(['/usr/local/bin/node',HERE.parent/'float-core/execute.mjs',d/'float.wasm',d/'detector.wasm',e/'2026-09-19-stage1-float-core-r2/execution/cases.json',out/'raw-float.json'],out/'raw-float.log')
 raw=read(out/'raw-float.json');assert raw['status']=='PASS' and [r['cases'] for r in raw['reports']]==[59083]*3
 from inspect_dispatch import inspect_all
 inspect_all(d,out/'dispatch.json',command)
 from assess import qualify
 result=qualify(out);save(out/'assessment.json',result)
 from qualification_controls import run as controls
 controls(e,out)
 if bench:
  from benchmark import run as benchmark
  benchmark(e,out)
 save(out/'summary.json',dict(status='PASS',**result,controls=len(read(out/'controls.json')),compiler_sha256=sha(ROOT/'compiler/WASM32/wasm32-backend.lisp'),native_R6='REUSED_BY_EXACT_REVIEWED_COMPILER_HASH',benchmark=read(out/'benchmark/summary.json') if bench else None))
 print((out/'summary.json').read_text())
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--no-benchmark',action='store_true');v=a.parse_args();run(v.evidence.resolve(),v.output.resolve(),not v.no_benchmark)
