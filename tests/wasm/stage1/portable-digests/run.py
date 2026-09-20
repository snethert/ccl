import argparse,hashlib,importlib.util,json,shutil,subprocess,tarfile
from pathlib import Path
from derive import derive,ROOT,HERE,replace,sha
E=ROOT.parent/'ccl-evidence'
ARCHIVES=['2026-09-20-stage1-numeric-qualification-r1/execution.tar.gz','2026-09-20-stage1-scalar-floats-r1/execution.tar.gz','2026-09-19-stage1-binding-installation-r1/execution.tar.gz']
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
def extract(archive,dest):
 dest.mkdir()
 with tarfile.open(archive) as t:t.extractall(dest,filter='data')
def binding_browser():
 s=(HERE.parent/'binding-installation/execute.mjs').read_text()
 s=s[s.index(' const {dir,base}=workerData'):]
 s=replace(s,"const {dir,base}=workerData,read=n=>JSON.parse(fs.readFileSync(path.join(dir,n)))","const read=n=>JSON.parse(new TextDecoder().decode(assets['binding/'+n]))")
 s=replace(s,"Buffer.from(material.image,'hex')","unhex(material.image)")
 s=replace(s,"fs.readFileSync(new URL('stub.wasm',import.meta.url))","assets['binding/stub.wasm']")
 s=replace(s,"fs.readFileSync(path.join(dir,m.name+'.wasm'))","assets['binding/'+m.name+'.wasm']")
 s=replace(s,"Buffer.from(new Uint8Array(memory.buffer,p,n)).toString('hex')","hex(new Uint8Array(memory.buffer,p,n))")
 s=replace(s,'parentPort.postMessage({','return ({')
 s=replace(s,"n=>bytes.get(n),imports);for(const b of m.bindings)","n=>{if(!snapshotInputs)return bytes.get(n);if(previousInput)previousInput.fill(0);previousInput=new Uint8Array(bytes.get(n));return previousInput;},imports);for(const b of m.bindings)")
 return '''import {BindingInstaller} from './proposal/installer.mjs';
import {entryRanges} from './proposal/ranges.mjs';
import {PROFILE,sha} from './proposal/loader.mjs';
import {inspect} from './proposal/binary.mjs';
import {hex} from './proposal/bytes.mjs';
const unhex=s=>Uint8Array.from(s.match(/../g)??[],x=>parseInt(x,16));
const same=(a,b)=>Object.is(a,b)||(a&&b&&typeof a==='object'&&typeof b==='object'&&Array.isArray(a)===Array.isArray(b)&&Object.keys(a).length===Object.keys(b).length&&Object.keys(a).every(k=>Object.hasOwn(b,k)&&same(a[k],b[k])));
const assert=(ok,name)=>{if(!ok)throw Error(name??'assert');};
assert.equal=(a,b,n)=>assert(Object.is(a,b),n+': actual='+a+' expected='+b);assert.notEqual=(a,b,n)=>assert(!Object.is(a,b),n);assert.deepEqual=(a,b,n)=>assert(same(a,b),n);
export function bindingCheck(assets,base,snapshotInputs=false){
 let previousInput;
'''+s
def run(e,out,playwright,browser):
 out.mkdir(parents=True,exist_ok=False);proposal=out/'proposal';derive(proposal)
 for n in ['checks.mjs','node-check.mjs','browser.mjs','worker.mjs']:shutil.copy(HERE/n,out/n)
 (out/'binding-browser.mjs').write_text(binding_browser());(out/'index.html').write_text('<!doctype html><title>Portable runtime checks</title>')
 inputs={n:sha(e/n) for n in ARCHIVES}
 for n,h in inputs.items():
  manifest=json.loads((e/n).parent.joinpath('packet.json').read_text())
  assert next(x['sha256'] for x in manifest['files'] if x['path']==Path(n).name)==h,n
 for name,archive in zip(['numeric','scalar','binding'],ARCHIVES):extract(e/archive,out/name)
 g=out/'numeric/generated';ret=out/'scalar'
 shutil.copy(ROOT/'runtime/wasm32/scalar.wasm',g/'scalar.wasm')
 for p in proposal.glob('*.mjs'):shutil.copy(p,g/p.name)
 for n in ['execute.mjs','service-inputs.json']:shutil.copy(ret/'generated'/n,g/n)
 spec=importlib.util.spec_from_file_location('scalar_run',HERE.parent/'scalar-floats/run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 (g/'scalar-service.mjs').write_text(m.pressure_service((proposal/'scalar-service.mjs').read_text()))
 # Current collector contains the accepted hash-vector scanner; all service
 # binaries rebuilt below are matched against their independently pinned bytes.
 import sys
 sys.path.insert(0,str(HERE.parent/'hash-tables'))
 spec=importlib.util.spec_from_file_location('hash_run',HERE.parent/'hash-tables/run.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
 h.build(ROOT/'runtime/wasm32/collector.c',out/'collector.wasm',True)
 assert sha(out/'collector.wasm')==sha(e/'2026-09-20-stage1-hash-tables-r1/execution/collector.wasm')
 for p in proposal.glob('*.mjs'):shutil.copy(p,out/'binding'/p.name)
 assets=out/'assets';assets.mkdir()
 for n in ['float.wasm','detector.wasm','integer.wasm','scalar.wasm']:shutil.copy(g/n,assets/n)
 shutil.copy(out/'collector.wasm',assets/'collector.wasm')
 for p in (out/'binding/compiled').iterdir():
  if p.suffix in ['.wasm','.json']:
   dest=assets/'binding'/p.name;dest.parent.mkdir(exist_ok=True);shutil.copy(p,dest)
 shutil.copy(out/'binding/stub.wasm',assets/'binding/stub.wasm')
 manifest={'version':1,'generation':1,'previous':None,'phase':'boot','modules':[],'functions':[],'bindings':[],'note':'λ😀'}
 (assets/'manifest.utf8').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':')))
 # Every retained/replayed Wasm binary gets a Node-crypto and portable hash join.
 for p in sorted(g.rglob('*.wasm')):
  dest=assets/'numeric'/p.relative_to(g);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest)
 save(out/'hashes.json',{str(p.relative_to(assets)):sha(p) for p in sorted(assets.rglob('*')) if p.is_file()})
 command(['node',out/'node-check.mjs',out],out/'node.log')
 command(['node',out/'browser.mjs',out,playwright,browser],out/'browser.log')
 # Complete existing installer scenarios, using its unchanged Node oracle.
 command(['node',out/'binding/execute.mjs',out/'binding/compiled',out/'binding-replay.json'],out/'binding-replay.log')
 assert sha(out/'binding-replay.json')==sha(out/'binding/execution.json')
 converted=json.loads((out/'node.json').read_text())['binding'];native=json.loads((out/'binding-replay.json').read_text())['rows'];assert converted==native
 for mode in ['eager','cold']:
  command(['node',g/'execute.mjs',g,out/'collector.wasm',g/'integer.wasm',out/(mode+'.json'),mode],out/(mode+'.log'))
  assert sha(out/(mode+'.json'))==sha(ret/(mode+'.json')),mode
 import controls
 faults=controls.run(out)
 sources=[p for p in HERE.iterdir() if p.is_file()]+[p for p in (ROOT/'runtime/wasm32').iterdir() if p.is_file()]+[ROOT/'compiler/WASM32/wasm32-backend.lisp',HERE.parent/'binding-installation/execute.mjs',HERE.parent/'scalar-floats/run.py',HERE.parent/'hash-tables/run.py',HERE.parent/'hash-tables/collector.py']
 save(out/'sources.json',{str(p.relative_to(ROOT)):sha(p) for p in sorted(sources)})
 save(out/'inputs.json',inputs)
 save(out/'tools.json',dict(node=shutil.which('node'),node_sha256=sha(Path(shutil.which('node'))),clang=str(h.CLANG),clang_sha256=sha(h.CLANG),browser=str(browser),browser_sha256=sha(browser),playwright=str(playwright),playwright_sha256=sha(playwright)))
 summary=dict(status='PASS',proposal={p.name:sha(p) for p in sorted(proposal.iterdir())},checks=json.loads((out/'node.json').read_text())['shared']['checks'],random_checks=len(json.loads((out/'node.json').read_text())['random']),binary_inputs=len(list(assets.rglob('*.wasm'))),faults=len(faults),node_browser_equal=True,bindings_equal_retained=True,eager_cold_equal_retained=True,scope='Portable synchronous construction and digest binding; Chromium Worker and Node. No full browser engine qualification, compiler changes or new slot credit.')
 save(out/'summary.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,default=E);p.add_argument('--output',type=Path,required=True);p.add_argument('--playwright',type=Path,required=True);p.add_argument('--browser',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve(),a.playwright.resolve(),a.browser.resolve())
