import argparse,hashlib,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def command(argv,log):
 with log.open('w') as f:subprocess.run(list(map(str,argv)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
def run(e,out):
 out.mkdir(parents=True,exist_ok=False)
 fields=json.loads((ROOT/'doc/WASM/contracts/tcr.v2.json').read_text())['fields']
 tagged=[(f['name'],f['offset'],f['width']) for f in fields if f['classification']=='tagged-root']
 assert tagged==[('next_method_context',188,4)],tagged
 (out/'schema-roots.json').write_text(json.dumps(tagged,indent=2)+'\n')
 # Compile using the accepted proposal only, in the same disposable-U1 path.
 sys.path.insert(0,str(HERE.parent/'collector-live'))
 live=load('owner_live',HERE.parent/'collector-live/run.py');h=live.prepare(out/'harness')
 accepted=e/'2026-09-19-stage1-collector-live-r1'
 assert (h/'wasm32-backend.lisp').read_bytes()==(accepted/'wasm32-backend.lisp').read_bytes()
 assert (h/'collector.c').read_bytes()==(accepted/'collector.c').read_bytes()
 assert (h/'collector.wasm').read_bytes()==(accepted/'collector.wasm').read_bytes()
 shutil.copy(HERE/'probe.py',h/'owner_probe.py')
 command([sys.executable,h/'owner_probe.py',e,out/'generated',h/'wasm32-backend.lisp'],out/'generated.log')
 for n in ('owner.mjs','check.mjs'):shutil.copy(HERE/n,out/n)
 command(['/usr/local/bin/node',out/'check.mjs',h/'collector.wasm',out/'owner.json',out/'generated/compiled'],out/'owner.log')
 controls=load('owner_controls',HERE/'controls.py').run(out/'controls',h/'collector.wasm',out/'generated/compiled')
 result=dict(mutants=len(controls['mutants']),status='PASS',owner_checks=json.loads((out/'owner.json').read_text())['checks'],generated=json.loads((out/'generated/execution.json').read_text())['comparisons'])
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
