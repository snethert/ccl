import argparse,importlib.util,json,shutil,sys,subprocess
from pathlib import Path
from backend import generate,HERE,ROOT
from corpus import SOURCES,cases
C=HERE.parent/'constants'
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1200)
def compile(e,out,code=None):
 out.mkdir(parents=True,exist_ok=False);h=out/'driver';shutil.copytree(C,h,ignore=shutil.ignore_patterns('__pycache__','review-followup'))
 for n in ['compile.lisp','class-shapes.lisp']:shutil.copy(HERE/n,h/n)
 sources=dict(SOURCES);rows=cases()
 for row in rows:
  if not row['safe']:
   name=row['function'];row['function']=name+'__unchecked';sources[row['function']]=sources[name]
 save(out/'cases.json',rows)
 (h/'runtime.lisp').write_text("'("+'\n'.join('('+json.dumps(n)+' '+s+')' for n,s in sources.items())+')\n')
 (h/'cases.lisp').write_text('('+ '\n'.join('('+json.dumps(r['function'])+' ('+' '.join(r['args'])+') '+str(r['mask'] if r['safe'] else 0)+')' for r in rows)+')\n')
 p=h/'compile.py';p.write_text(p.read_text().replace("ROOT=HERE.parents[3];REG=HERE.parent/'registration'",'ROOT=Path('+repr(str(ROOT))+');REG=Path('+repr(str(HERE.parent/'registration'))+')'))
 old=sys.path.copy();sys.path.insert(0,str(h));spec=importlib.util.spec_from_file_location('float_compile',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.run(e,out/'compiled',code or generate());sys.path[:]=old
 sys.path.insert(0,str(C));from pool import compile_pool
 sys.path[:]=old
 graph=json.loads((out/'compiled/pools.json').read_text());symbols={};plan=compile_pool(graph,symbols);material=plan.at(786432);save(out/'compiled/materialized.json',dict(base=786432,image=material.image.hex(),roots=material.roots,symbols=symbols))
 native=(out/'compiled/native-results.txt').read_text().splitlines();args=(out/'compiled/native-args.txt').read_text().splitlines();assert len(native)==len(args)==len(rows)
 results=[dict(c,args=a.split(','),expected=line.split(',')) for c,a,line in zip(rows,args,native)]
 save(out/'native-observed.json',results)
 import oracle;save(out/'policy-join.json',oracle.apply(results));save(out/'native.json',results)
def execute(e,out,mode='eager'):
 from derive import execute,loader
 import hashlib
 for n in ['collector-owner.mjs','binary.mjs','allocation-service.mjs','integer-service.mjs','numeric-capabilities.mjs','float-service.mjs','stub.wat']:shutil.copy(ROOT/'runtime/wasm32'/n,out/n)
 for n in ['service.mjs','floating-capabilities.mjs']:shutil.copy(HERE/n,out/n)
 for n in ['float.wasm','detector.wasm']:shutil.copy(e/'2026-09-19-stage1-float-core-r2/execution'/n,out/n)
 save(out/'service-inputs.json',{n:hashlib.sha256((out/(n+'.wasm')).read_bytes()).hexdigest() for n in ['float','detector']})
 (out/'execute.mjs').write_text(execute());(out/'loader.mjs').write_text(loader())
 command(['/usr/local/bin/wat2wasm','--enable-tail-call',out/'stub.wat','-o',out/'stub.wasm'],out/'stub.log')
 command(['/usr/local/bin/node',out/'execute.mjs',out,e/'2026-09-19-stage1-collector-qualification-r1/collector.wasm',e/'2026-09-19-stage1-integer-core-r1/execution/integer.wasm',out/(mode+'.json'),mode],out/(mode+'.log'))
def qualify(e,out):
 execute(e,out,'eager');execute(e,out,'cold')
 assert json.loads((out/'eager.json').read_text())==json.loads((out/'cold.json').read_text())
 import controls;controls.run(e,out,sys.modules[__name__])
 data=json.loads((out/'eager.json').read_text());summary=[r for r in data['rows'] if 'cases' in r]
 save(out/'summary.json',dict(status='PASS',modules=len(data['admission']),native_cases=len(json.loads((out/'native.json').read_text())),comparisons=sum(r['cases'] for r in summary),collections=sum(r['moves'] for r in summary),assurances=sum(r['ensures'] for r in summary),mutants=len(json.loads((out/'controls.json').read_text())['rows']),default_identical=len(json.loads((out/'controls.json').read_text())['default_identical']),cold_identical=True,policy_join=json.loads((out/'policy-join.json').read_text()),gate_credit=False))
 print((out/'summary.json').read_text())
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--qualify',action='store_true');a=p.parse_args();compile(a.evidence.resolve(),a.output.resolve())
 if a.qualify:qualify(a.evidence.resolve(),a.output.resolve())
 elif a.execute:execute(a.evidence.resolve(),a.output.resolve())
