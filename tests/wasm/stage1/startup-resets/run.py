#!/usr/bin/env python3
import argparse,gzip,hashlib,importlib.util,json,shutil,sys,tarfile,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
def compile_run(e,out):
 driver=out/'driver';shutil.copytree(HERE.parent/'constants',driver,ignore=shutil.ignore_patterns('__pycache__'))
 shutil.copy(HERE/'compile.lisp',driver/'compile.lisp')
 selected=[r for r in read(HERE/'selection.json')['callbacks'] if r['disposition']=='SELECTED_LITERAL_RESET']
 forms=[]
 for r in selected:
  value='nil' if r['value']=='nil' else 't' if r['value']=='t' else str(r['value'])
  forms.append(f'({json.dumps(r["name"].split("::")[1])} {json.dumps(r["source"])} {r["position"]} {value} {json.dumps(r["module"])})')
 (driver/'selection.lisp').write_text('(in-package :wasm32-compiler)\n(defparameter *reset-selection* \'('+ '\n'.join(forms)+'))\n')
 p=driver/'compile.py';p.write_text(p.read_text().replace("ROOT=HERE.parents[3];REG=HERE.parent/'registration'",f"ROOT=Path({str(ROOT)!r});REG=ROOT/'tests/wasm/stage1/registration'"))
 sys.path.insert(0,str(driver));spec=importlib.util.spec_from_file_location('reset_compile',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.run(e,out/'compiled',(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text())
 import encode
 encode.Encoder.__init__.__defaults__=(ROOT/'doc/WASM/contracts/wasm32-layout.v1.json',16*1024*1024)
 from pool import compile_pool
 material=compile_pool(read(out/'compiled/pools.json')).at(2097152)
 save(out/'compiled/materialized.json',dict(image=material.image.hex(),roots=material.roots))
 shutil.copy(driver/'selection.lisp',out/'selection.lisp')
def bind_source(e,out):
 selection=read(HERE/'selection.json');snapshot=e/selection['snapshot']
 packet=read(snapshot.parent/'packet.json');r=next(r for r in packet['files'] if r['path']==snapshot.name);assert sha(snapshot)==r['sha256']
 v=json.loads(gzip.decompress(snapshot.read_bytes()));fs={r['id']:r for r in v['functions']}
 expected=[(g['group'],i,c['function'],c['name']) for g in v['startup_groups'] for i,c in enumerate(g['functions'])]
 assert [(r['group'],r['ordinal'],r['function'],r['name']) for r in selection['callbacks']]==expected
 pins=read(e/'macos-u1-inputs/pins.json');sources={}
 with tarfile.open(e/'macos-u1-inputs/source.tar') as t:
  for r in selection['callbacks']:
   f=fs[r['function']];assert f['source_position']==r['position'];assert f['name']==r['name']
   parts=f['source'].split(';');dr=parts[0].split(':')[1];assert str(Path({'l1':'level-1'}.get(dr,dr))/parts[1].removesuffix('.newest'))==r['source']
   data=t.extractfile(r['source']).read();assert data==(ROOT/r['source']).read_bytes();sources[r['source']]=hashlib.sha256(data).hexdigest()
 assert sha(e/'macos-u1-inputs/source.tar')==pins['inputs']['source.tar']
 save(out/'source-bindings.json',dict(snapshot_sha256=sha(snapshot),source_revision=pins['source_revision'],sources=sources,groups=[dict(group=g['group'],count=len(g['functions'])) for g in v['startup_groups']],callbacks=selection['callbacks'],scope='Snapshot namespace only. These IDs are not correlated-build compiler identities; 22 callbacks remain open.'))
def run(e,out,cache=None):
 out.mkdir(parents=True,exist_ok=False);bind_source(e,out);compile_run(e,out)
 inputs=read(HERE/'inputs.json')
 for name in inputs['runtime_modules']:shutil.copy(ROOT/'runtime/wasm32'/name,out/name)
 for name in ['check.mjs','install.mjs','selection.json']:shutil.copy(HERE/name,out/name)
 shutil.copy(ROOT/'doc/WASM/contracts/tcr.v2.json',out/'tcr.json')
 command(['/usr/local/bin/wat2wasm','--enable-tail-call',ROOT/'runtime/wasm32/stub.wat','-o',out/'stub.wasm'],out/'stub.log')
 selected=[r for r in read(HERE/'selection.json')['callbacks'] if r['disposition']=='SELECTED_LITERAL_RESET'];values=[r['value'] for r in selected]
 expected=[[dict(values=[v],globals=values[:i+1]+[sentinel]*(len(values)-i-1)) for i,v in enumerate(values)] for sentinel in [37,91]]
 assert read(out/'compiled/native.json')==expected,'literal oracle vs real U1 callbacks';save(out/'expected.json',expected)
 command(['/usr/local/bin/node',out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 for module in ['controls','assess']:
  spec=importlib.util.spec_from_file_location('reset_'+module,HERE/(module+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  if module=='controls':m.run(out,command,read,save)
  else:save(out/'assessment.json',m.check(read(out/'execution.json'),out/'compiled'));save(out/'publication-controls.json',m.controls(out,read,save))
 save(out/'summary.json',{**read(out/'assessment.json'),'faults_rejected':len(read(out/'controls.json')),'publication_controls':len(read(out/'publication-controls.json')),'slot_credit':False})
 command([sys.executable,HERE/'census.py','--evidence',e,'--output',out/'queries','--cache',cache or out/'capture.sqlite'],out/'census.log')
 print(json.dumps(read(out/'summary.json'),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',type=Path);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve(),a.cache.resolve() if a.cache else None)
