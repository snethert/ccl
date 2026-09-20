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
 selected=[r for r in read(HERE/'selection.json')['callbacks'] if r['disposition']=='SELECTED_OWNER_CONFIGURATION']
 forms=[f'({json.dumps(r["name"].split("::")[1])} {json.dumps(r["source"])} {r["position"]} {json.dumps(r["module"])})' for r in selected]
 (driver/'selection.lisp').write_text("(in-package :wasm32-compiler)\n(defparameter *config-selection* '("+'\n'.join(forms)+'))\n')
 cases=read(out/'cases.json')
 forms=['('+ ' '.join(map(str,[c['input'][n] for n in ['pageSize','clockTicks','cpuCount','stackSize']]))+' ('+' '.join(map(str,c['input']['defaults']))+'))' for c in cases]
 (driver/'cases.lisp').write_text("(in-package :wasm32-compiler)\n(defparameter *config-cases* '("+'\n'.join(forms)+'))\n')
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
 save(out/'source-bindings.json',dict(snapshot_sha256=sha(snapshot),source_revision=pins['source_revision'],sources=sources,groups=[dict(group=g['group'],count=len(g['functions'])) for g in v['startup_groups']],callbacks=selection['callbacks'],scope='Snapshot namespace only. These IDs are not correlated-build compiler identities; 17 callbacks remain open; 13 earlier literal resets preserved.'))
def expected(c,sentinel):
 x=c['input'];g=[sentinel]*3+x['defaults']+[sentinel]*2;rows=[]
 def step(changes,result):
  for i,v in changes:g[i]=v
  rows.append(dict(values=[result],globals=g.copy()))
 step([(0,x['pageSize'])],x['pageSize'])
 ticks=max(1000,x['clockTicks']);step([(1,ticks)],ticks)
 period=1000000000//ticks;step([(2,period)],period)
 size=x['stackSize'];step([(3,size),(4,size),(5,size//2)] if size>0 else [],size//2 if size>0 else 'nil')
 step([(6,1 if x['cpuCount']==1 else 1024),(7,0)],'CCL::*SPIN-LOCK-TIMEOUTS*')
 return rows

def run(e,out):
 out.mkdir(parents=True,exist_ok=False)
 for n in ['config.mjs','browser-config.mjs','browser.mjs','worker.mjs','assert.mjs']:shutil.copy(HERE/n,out/n)
 (out/'index.html').write_text('<!doctype html><title>Startup configuration</title>')
 tools=read(e/'2026-09-20-stage1-portable-digests-r1/tools.json')
 for name in ['node','browser','playwright']:assert sha(Path(tools[name]))==tools[name+'_sha256']
 command([tools['node'],out/'browser.mjs',out,tools['playwright'],tools['browser'],'probe'],out/'browser-probe.log')
 cases=read(HERE/'cases.json')+[dict(name='browser-observed',input=read(out/'browser-input.json')['input'])]
 save(out/'cases.json',cases);bind_source(e,out);compile_run(e,out)
 for name in read(HERE/'inputs.json')['runtime_modules']:shutil.copy(ROOT/'runtime/wasm32'/name,out/name)
 for name in ['check.mjs','node.mjs','assert.mjs','config.mjs','browser-check.mjs','selection.json']:shutil.copy(HERE/name,out/name)
 shutil.copy(ROOT/'doc/WASM/contracts/tcr.v2.json',out/'tcr.json')
 command(['/usr/local/bin/wat2wasm','--enable-tail-call',ROOT/'runtime/wasm32/stub.wat','-o',out/'stub.wasm'],out/'stub.log')
 answers=[[expected(c,s) for s in [37,91]] for c in read(out/'cases.json')]
 assert read(out/'compiled/native.json')==answers,'Python model vs native source formulas';save(out/'expected.json',answers)
 assets=['cases.json','expected.json','tcr.json','stub.wasm','compiled/modules.json','compiled/native.json','compiled/materialized.json']+['compiled/'+r['name']+'.wasm' for r in read(out/'compiled/modules.json')]
 save(out/'assets.json',assets)
 command(['/usr/local/bin/node',out/'node.mjs',out,out/'execution.json'],out/'execution.log')
 command([tools['node'],out/'browser.mjs',out,tools['playwright'],tools['browser'],'execute'],out/'browser.log')
 command([tools['node'],out/'browser-check.mjs'],out/'browser-check.log')
 for module in ['controls','assess']:
  spec=importlib.util.spec_from_file_location('config_'+module,HERE/(module+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  if module=='controls':m.run(out,command,read,save)
  else:save(out/'assessment.json',m.check(read(out/'execution.json'),out));save(out/'publication-controls.json',m.controls(out,read,save))
 save(out/'summary.json',{**read(out/'assessment.json'),'faults_rejected':len(read(out/'controls.json')),'publication_controls':len(read(out/'publication-controls.json')),'slot_credit':False})
 print(json.dumps(read(out/'summary.json'),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
