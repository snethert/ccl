#!/usr/bin/env python3
import argparse,importlib.util,json,hashlib,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
def run(e,out):
 out.mkdir(parents=True,exist_ok=False)
 # Reuse the accepted pristine-U1 compile path, with a new Lisp corpus only.
 # Its unused adapter assembly is removed in this private driver copy.
 text=(HERE.parent/'symbols/generated.py').read_text()
 text=text[:text.index(" command(['/usr/local/bin/wat2wasm'")]
 helper=out/'compile-helper.py';helper.write_text(text.replace("HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]",f"HERE=Path({str(HERE)!r});ROOT=Path({str(ROOT)!r})"))
 spec=importlib.util.spec_from_file_location('schedule_compile',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.run(e,out,command)
 for n in read(HERE/'inputs.json')['runtime_modules']:shutil.copy(ROOT/'runtime/wasm32'/n,out/n)
 for n in ['schedule.mjs','check.mjs']:shutil.copy(HERE/n,out/n)
 shutil.copy(ROOT/'doc/WASM/contracts/tcr.v2.json',out/'tcr.json')
 command(['/usr/local/bin/wat2wasm','--enable-tail-call',ROOT/'runtime/wasm32/stub.wat','-o',out/'stub.wasm'],out/'stub.log')
 # Independent literal oracle: never obtain expected state from the manifest.
 expected=[dict(values=[i,100+i],state=i,mode=0 if i==1 else 1 if i<8 else 2,output=[9,2] if i==9 else [0,0]) for i in range(1,10)]
 assert read(out/'compiled/native.json')==expected,'native phase effects'
 save(out/'expected.json',expected)
 command(['/usr/local/bin/node',out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 spec=importlib.util.spec_from_file_location('schedule_controls',HERE/'controls.py');controls=importlib.util.module_from_spec(spec);spec.loader.exec_module(controls);controls.run(out,command,read,save)
 spec=importlib.util.spec_from_file_location('schedule_assess',HERE/'assess.py');assess=importlib.util.module_from_spec(spec);spec.loader.exec_module(assess)
 save(out/'assessment.json',assess.check(read(out/'execution.json')));save(out/'publication-controls.json',assess.controls(out,read,save))
 x=read(out/'execution.json');save(out/'summary.json',dict(status='PASS',modules=len(read(out/'compiled/modules.json')),workers=len(x['rows']),initializers=9,generated_invocations=sum(r['invocations'] for r in x['rows']),refusals=sum(len(r['refusals']) for r in x['rows']),mutants=len(read(out/'controls.json')),publication_controls=len(read(out/'publication-controls.json')),native_comparisons=9*len(x['rows']),scope='Generated phase/completion protocol prerequisite, not selected native bootstrap membership or LL15 credit.'))
 print(json.dumps(read(out/'summary.json'),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
