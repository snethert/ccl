"""Audit-112 coercion boundary qualification over the unchanged compiler."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE.parents[3]
sys.path.insert(0,str(BASE))
sys.path.insert(0,str(HERE))
import corpus,oracle
spec=importlib.util.spec_from_file_location('float_calls_prior',BASE/'run.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
sys.modules[spec.name]=prior
PACK='2026-09-19-stage1-float-calls-r1'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cases():
 rows=corpus.cases()
 def add(name,f,a,b,mask,safe):rows.append(dict(id=len(rows),name=name,function=f,args=[a,b],mask=mask,safe=safe,policy=False))
 for width,exponent,precision,proto in [(32,128,24,'1.0s0'),(64,1024,53,'1.0d0')]:
  limit=1<<exponent;mid=limit-(1<<(exponent-precision-1));maximum=limit-(1<<(exponent-precision))
  for label,n in [('max-finite',maximum),('below-tie',mid-1),('tie',mid),('above-tie',mid+1),('below-limit',limit-1),('limit',limit),('above-limit',limit+1),('inexact',(1<<precision)+1),('native-fixnum-below',(1<<60)-1),('native-fixnum-limit',1<<60),('native-fixnum-edge',(1<<60)+1),('d1-fixnum-below',(1<<29)-1),('d1-fixnum-edge',(1<<29)+1)]:
   for sign in [-1,1]:
    a=str(sign*n)
    for mask in [0,7,16,31]:
     for safe in [0,1]:
      prefix=f'{width}/{label}/{sign}/m{mask}/s{safe}'
      add(prefix+'/convert','h_single' if width==32 else 'h_double',a,'0',mask,safe)
      for op in ['add','sub','mul','div']:
       add(prefix+'/'+op+'-left','h_'+op,a,proto,mask,safe)
       add(prefix+'/'+op+'-right','h_'+op,proto,a,mask,safe)
 # Preserve arithmetic flags AFTER a silent bignum conversion.
 for width,e,precision,one,zero in [(32,128,24,'1.0s0','0.0s0'),(64,1024,53,'1.0d0','0.0d0')]:
  n=str((1<<e)-1);finite=str((1<<e)-(1<<(e-precision)))
  maximum='3.4028234663852886s38' if width==32 else '(ccl::double-float-from-bits #x7fefffff #xffffffff)'
  infinity='(float (ccl::double-float-from-bits #x7ff00000 0) 1.0s0)' if width==32 else '(ccl::double-float-from-bits #x7ff00000 0)'
  for mask in [0,1,2,4,8,16,7,31]:
   for safe in [0,1]:
    for label,f,a,b in [('invalid-mul','h_mul',n,zero),('invalid-sub','h_sub',n,infinity),('overflow','h_add',finite,maximum),('inexact','h_add',str((1<<100)+1),one),('zero-divide','h_div',str((1<<100)+1),zero)]:
     add(f'{width}/arithmetic-{label}/m{mask}/s{safe}',f,a,b,mask,safe)
 return rows

def setup(e):
 for n,h in read(e/PACK/'source-pins.json').items():assert sha(ROOT/n)==h,n
 assert hashlib.sha256(prior.generate().encode()).hexdigest()==sha(e/PACK/'wasm32-backend.lisp')
 prior.cases=cases

def build(out,code=None):
 import primitive
 spec=importlib.util.spec_from_file_location('float_core_builder',BASE.parent/'float-core/run.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
 out.mkdir(parents=True,exist_ok=False);(out/'float.c').write_text(code or primitive.source())
 prior.command([builder.CLANG,*builder.FLAGS,'-Wl,--export=float_calculate_lisp',out/'float.c','-o',out/'float.wasm'],out/'build.log')
 prior.save(out/'toolchain.json',dict(flags=builder.FLAGS+['-Wl,--export=float_calculate_lisp'],compiler=str(builder.CLANG.resolve()),sha256=sha(builder.CLANG.resolve())))

def execute(e,out,binary,owner=None,mode='eager'):
 import primitive
 original=prior.command
 def command(args,log):
  if log.name in ['eager.log','cold.log']:
   shutil.copy(binary,out/'float.wasm');(out/'float-service.mjs').write_text(owner or primitive.owner())
   inputs=read(out/'service-inputs.json');inputs['float']=sha(binary);prior.save(out/'service-inputs.json',inputs)
  return original(args,log)
 try:
  prior.command=command;prior.execute(e,out,mode)
 finally:prior.command=original

def run(e,out):
 setup(e);prior.compile(e,out);build(out/'primitive');execute(e,out,out/'primitive/float.wasm');execute(e,out,out/'primitive/float.wasm',mode='cold')
 assert read(out/'eager.json')==read(out/'cold.json')
 # Original mathematical entry remains available with identical semantics.
 prior.command(['/usr/local/bin/node',BASE.parent/'float-core/execute.mjs',out/'primitive/float.wasm',out/'detector.wasm',e/'2026-09-19-stage1-float-core-r2/execution/cases.json',out/'raw-regression.json'],out/'raw-regression.log')
 import controls;controls.run(e,out,sys.modules[__name__])
 # Compiler bytes are unchanged. Reuse the reviewed R6, compiler faults and
 # default-mode witnesses by their packet identities; native values rerun here.
 for f in (e/PACK/'wasm32-backend.lisp',):assert f.read_text()==prior.generate()
 data=read(out/'eager.json');summaries=[r for r in data['rows'] if 'cases' in r]
 summary=dict(status='PASS',native_cases=len(read(out/'native.json')),comparisons=sum(r['cases'] for r in summaries),collections=sum(r['moves'] for r in summaries),modules=len(data['admission']),cold_identical=True,rejected_controls=len(read(out/'controls.json')),raw_regression_cases=59083,raw_regression_comparisons=177249,native_R6='REUSED_BY_EXACT_COMPILER_HASH',compiler_sha256=sha(e/PACK/'wasm32-backend.lisp'),gate_credit=False)
 prior.save(out/'summary.json',summary);print(json.dumps(summary,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
