import argparse,hashlib,importlib.util,json,shutil,subprocess,sys,gzip
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def read(p):return json.loads(p.read_text())
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
def inherited():
 sys.path.insert(0,str(HERE.parent/'materialization'))
 spec=importlib.util.spec_from_file_location('materialization_run',HERE.parent/'materialization/run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def run(e,out,measure=True):
 out.mkdir(parents=True,exist_ok=False);m=inherited();packet=e/'2026-09-20-stage1-materialization-r1';code=(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text()
 assert code==(packet/'wasm32-backend.lisp').read_text(),'accepted compiler identity'
 for tool in read(packet/'toolchain.json')['tools']:assert sha(Path(tool['path']))==tool['sha256'],'accepted engine/tool join'
 m.compile(e,out/'templates',code,True)
 mods=read(out/'templates/modules.json');assert len(mods)==16
 for p in (out/'templates').glob('*.wasm'):assert p.read_bytes()==(packet/'execution/templates'/p.name).read_bytes(),p.name
 # Same production compiler, three real revisions of the optional default.
 # Native CCL is recompiled by this driver for each revision as well.
 original=(HERE.parent/'callable-metadata/compile.lisp').read_text()
 # Compile via an isolated copy of the LL21-a driver, replacing its source input.
 variants=[]
 for generation,value in [(2,99),(3,101),(4,103)]:
  h=out/('revision-'+str(generation));h.mkdir();source=original.replace('(y 7)) (values x y)',f'(y {value})) (values x y)');assert source!=original
  source=source.replace('(ccl:quit)',f'''(with-open-file (s (concatenate 'string (ccl:getenv "POOL_OUTPUT") "revision-native.json") :direction :output :if-exists :error)
 (let* ((symbol (gensym "REDEFINITION")) (old (compile nil '(lambda (x &optional (y 7)) (values x y)))))
  (setf (symbol-function symbol) old)
  (setf (symbol-function symbol) (compile nil '(lambda (x &optional (y {value})) (values x y))))
  (assert (equal (multiple-value-list (funcall old 3)) '(3 7)))
  (multiple-value-bind (a b) (funcall (symbol-function symbol) 3) (format s "[~d,~d]" a b))))
(ccl:quit)''')
  # m.compile reads compile.lisp by path; derive a private copy with explicit path.
  src=(HERE.parent/'materialization/run.py').read_text().replace("(HERE.parent/'callable-metadata/compile.lisp').read_text()",repr(source))
  src=src.replace('from backend import HERE,ROOT,generate,replace',f'from backend import generate,replace\nHERE=Path({str(HERE.parent/"materialization")!r});ROOT=Path({str(ROOT)!r})')
  driver=h/'driver.py';driver.write_text(src);spec=importlib.util.spec_from_file_location('revision_driver',driver);rm=importlib.util.module_from_spec(spec);spec.loader.exec_module(rm)
  rm.compile(e,h/'compiled',code,True)
  name='plain_g'+str(generation);shutil.copy(h/'compiled/plain.wasm',out/'templates'/(name+'.wasm'));shutil.copy(h/'compiled/plain.wat',out/'templates'/(name+'.wat'))
  variants.append(dict(name=name,top=True,captures=0,generation=generation,native=read(h/'compiled/revision-native.json')))
  assert variants[-1]['native']==[3,value]
 allmods=mods+[{k:v for k,v in x.items() if k!='native'} for x in variants];save(out/'modules.json',allmods);save(out/'revisions.json',variants)
 for name in ['materializer.mjs','binary.mjs','bytes.mjs','sha256.mjs','ranges.mjs']:shutil.copy(ROOT/'runtime/wasm32'/name,out/name)
 for name in ['bundle.mjs','check.mjs','bench.mjs','prepare.mjs','retention.mjs']:shutil.copy(HERE/name,out/name)
 save(out/'classifications.json',{x['name']:m.classify(out/'templates'/(x['name']+'.wasm')) for x in allmods})
 shutil.copy(packet/'execution/policy.json',out/'policy.json')
 assert sha(out/'materializer.mjs')==read(out/'policy.json')['materializer']['sha256']
 save(out/'versions.json',dict(abi=dict(name='B',version=1,decision_sha256=sha(packet/'abi-decision.json')),layout=dict(version=1,sha256=sha(ROOT/'doc/WASM/contracts/wasm32-layout.v1.json'))))
 command(['/usr/local/bin/node',out/'prepare.mjs',out],out/'prepare.log');command(['/usr/local/bin/node',out/'check.mjs',out],out/'check.log')
 # Reuse the independently native-checked metadata/closure/snapshot oracle;
 # add three live code generations, with the original function kept callable.
 m.execute_harness(out)
 for n in ['modules.json','materialized.json','native-metadata.json','native-behavior.json']:shutil.copy(out/'templates'/n,out/'full'/n)
 shutil.copy(out/'materialization.json',out/'full/materialization.json');shutil.copy(out/'bundle.json',out/'full/bundle.json');shutil.copy(out/'expected.json',out/'full/expected.json');shutil.copy(out/'revisions.json',out/'full/revisions.json')
 s=(HERE.parent/'materialization/harness-installer.mjs').read_text()
 s="import {validate} from './bundle.mjs';\n"+s
 s=s.replace('constructor(o){this.o=o;',"constructor(o){validate(JSON.parse(fs.readFileSync(o.directory+'/bundle.json')),JSON.parse(fs.readFileSync(o.directory+'/expected.json')),n=>o.readBytes(n));this.o=o;")
 (out/'harness-installer.mjs').write_text(s)
 s=(out/'execute.mjs').read_text().replace("mods=read('modules.json'),NIL", "mods=read('modules.json'),revisions=read('revisions.json'),NIL")
 s=s.replace('mods.length+1','mods.length+revisions.length+1')
 s=s.replace("const binaries=new Map(mods.map", "const allmods=[...mods,...revisions];const binaries=new Map(allmods.map")
 s=s.replace('const catalog=mods.map', 'const catalog=allmods.map')
 s=s.replace('version:4,signature:17', 'version:4*(m.generation??1),signature:17')
 anchor=' set(48,top);'
 assert anchor in s
 s=s.replace(anchor,''' const revisionHandles=[];
 for(let j=0;j<revisions.length;j++){
  const rev=revisions[j],i=mods.length+j+1,row=4104+16*i;
  [i,4*rev.generation,17,23].forEach((v,k)=>put(row+4*k,v));
  let self;if(!snapshot){const p=top;top+=32;new Uint8Array(memory.buffer,p,32).set(new Uint8Array(memory.buffer,handles.plain-6,32));put(p+4,4*i);put(p+12,4*rev.generation);objects.push({id:'revision-'+j,offset:p-base,tag:6});self=p+6;}
  else self=roots[roots.length-revisions.length+j];
  revisionHandles.push(self);functions.set(rev.name,loader.defer(rev.name,{env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},codes,symbols:importsSymbols,keywords}).host_entry);
 }
'''+anchor)
 s=s.replace("closures=roots.slice(mods.length+Object.keys(handles).length);", "closures=roots.slice(mods.length+Object.keys(handles).length,-revisions.length);")
 anchor=' const faultSelf=handles.plain'
 assert anchor in s
 s=s.replace(anchor,''' const revisionObservations=[];
 for(let j=0;j<revisions.length;j++){
  const rev=revisions[j],slot=mods.length+j+1;
  assert.equal(table.get(slot),null);loader.install(slot);
  const old=invoke('plain',[12]),current=invoke(rev.name,[12],revisionHandles[j]);
  assert.deepEqual(old,[12,28]);assert.deepEqual(current,rev.native.map(x=>4*x));
  // The owner-selected live binding changes; saved old objects keep old code.
  const binding=630000;put(binding,revisionHandles[j]);assert.equal(get(binding),revisionHandles[j]);
  functions.set('live_binding',(...args)=>table.get(get(4104+16*(get(get(binding)-2)/4)))(...args));
  assert.deepEqual(invoke('live_binding',[12],get(binding)),current);
  revisionObservations.push({generation:rev.generation,old,current,retained:slot});
 }
 if(!snapshot)roots.push(...revisionHandles);
'''+anchor)
 s=s.replace('parentPort.postMessage({status:', 'parentPort.postMessage({revisionObservations,status:')
 (out/'execute.mjs').write_text(s)
 command(['/usr/local/bin/node',out/'execute.mjs',out/'full',out/'execution.json','full'],out/'execution.log')
 spec=importlib.util.spec_from_file_location('bundle_controls',HERE/'controls.py');controls=importlib.util.module_from_spec(spec);spec.loader.exec_module(controls)
 save(out/'faults.json',controls.run(out))
 sizes=[]
 for x in allmods:
  p=out/'full'/(x['name']+'.wasm');sizes.append(dict(name=x['name'],bytes=p.stat().st_size,gzip_bytes=len(gzip.compress(p.read_bytes(),mtime=0))))
 save(out/'sizes.json',sizes)
 if measure:
  cold=[]
  for trial in range(30):
   log=out/f'cold-{trial:02}.json';command(['/usr/local/bin/node','--expose-gc',out/'bench.mjs',out,'cold'],log);cold.append(read(log))
  save(out/'cold.json',cold)
  command(['/usr/local/bin/node','--expose-gc',out/'bench.mjs',out,'warm'],out/'warm.json')
  import re
  retention=[]
  for tier,flags in [('default',[]),('eager_liftoff',['--no-wasm-lazy-compilation','--liftoff-only'])]:
   for generation in range(1,5):
    log=out/f'retention-{tier}-{generation}.log'
    command(['/usr/local/bin/node','--print-wasm-offheap-memory-size',*flags,out/'retention.mjs',out,str(generation)],log)
    text=log.read_text();row=json.loads(text.splitlines()[0]);native_sizes=[int(n) for n in re.findall(r'Off-heap memory size of NativeModule: (\d+)',text)]
    assert len(native_sizes)==row['unique_binaries'],(tier,generation,len(native_sizes),row)
    retention.append(dict(tier=tier,generation=generation,**row,native_module_offheap_bytes=sum(native_sizes),scope='Engine-reported NativeModule off-heap bytes at shutdown while all module references remain retained; excludes shared WasmEngine overhead.'))
  save(out/'retention.json',retention)
  import statistics
  fields=['compile_ms','instantiate_ms','publish_ms'];summary={k:dict(median_ms=statistics.median(sum(r[k] for r in t['rows']) for t in cold),trials=30) for k in fields}
  warm=read(out/'warm.json')
  for metric in ['instantiate','validated_install']:summary['warm_'+metric]=dict(median_ms=statistics.median(r['ms_per_bundle'] for r in warm['rows'] if r['metric']==metric),trials=30,warmup_ms=1000,sample_ms=250)
  save(out/'timing-summary.json',dict(status='DESCRIPTIVE_NO_RANKING',metrics=summary,host=warm['host'],retained_memory='Process RSS/heap/external counters are whole-process observations, not isolated Wasm executable-code sizes.',retained_encoded_bytes=sum(x['bytes'] for x in sizes)))
 save(out/'summary.json',dict(status='PASS',modules=len(allmods),base_modules=len(mods),code_generations=4,worker_placements=[1048576,2097152,2147483648],redefinition_observations=sum(len(x['revisionObservations']) for x in [read(out/'execution.json')['origin'],*read(out/'execution.json')['restored']]),controls=len(read(out/'checks.json')['controls']),faults=len(read(out/'faults.json')),compiler_sha256=sha(ROOT/'compiler/WASM32/wasm32-backend.lisp'),packaging='one-generated-function-per-module-v1',bytes=sum(x['bytes'] for x in sizes)))
 print(json.dumps(read(out/'summary.json')))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--no-timing',action='store_true');a=p.parse_args();run(a.evidence.resolve(),a.output.resolve(),not a.no_timing)
