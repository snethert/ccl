import argparse,os,hashlib,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
from runtime import collector,owner,ROOT
HERE=Path(__file__).resolve().parent
CLANG='/usr/local/opt/llvm/bin/clang'
FLAGS=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer']
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(argv,log,env=None):
 save(log.with_suffix('.command.json'),list(map(str,argv)))
 with log.open('w') as f:subprocess.run(list(map(str,argv)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600,env=env)
def run(e,out,controls=False):
 out.mkdir(parents=True,exist_ok=False)
 sys.path.insert(0,str(HERE.parent/'constructor-retry'))
 retry=load('qualified_retry',HERE.parent/'constructor-retry/run.py');h=retry.prepare(out/'harness')
 assert (h/'wasm32-backend.lisp').read_bytes()==(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_bytes()
 (out/'collector.c').write_text(collector());(out/'collector-owner.mjs').write_text(owner());shutil.copy(out/'collector-owner.mjs',out/'owner.mjs')
 command([CLANG,*FLAGS,out/'collector.c','-o',out/'collector.wasm'],out/'collector-build.log')
 command([sys.executable,h/'retry_probe.py',e,out/'generated',h/'wasm32-backend.lisp'],out/'generated.log')
 for n in ['execute.mjs','allocation-service.mjs','loader.mjs','binary.mjs']:shutil.copy(HERE.parent/'constructor-retry'/n,out/n)
 command(['/usr/local/bin/wat2wasm','--enable-tail-call',h/'stub.wat','-o',out/'stub.wasm'],out/'stub.log')
 command(['/usr/local/bin/node',out/'execute.mjs',out/'generated',out/'collector.wasm',out/'generated.json'],out/'generated-execution.log')
 command(['/usr/local/bin/node',out/'execute.mjs',out/'generated',out/'collector.wasm',out/'lazy.json'],out/'lazy.log',dict(os.environ,LAZY_OWNER='1'))
 assert json.loads((out/'lazy.json').read_text())==json.loads((out/'generated.json').read_text())
 # Reuse the independent low-level refusal oracle and owner admission matrix.
 shutil.copy(h/'core-check.mjs',out/'core-check.mjs')
 command(['/usr/local/bin/node',out/'core-check.mjs',out/'collector.wasm',out/'core.json'],out/'core.log')
 shutil.copy(HERE.parent/'collector-owner/check.mjs',out/'owner-check.mjs')
 command(['/usr/local/bin/node',out/'owner-check.mjs',out/'collector.wasm',out/'owner.json'],out/'owner.log')
 # Explicit polls exercise live restart/condition/binding and result roots.
 poll=out/'poll-harness';shutil.copytree(h,poll,ignore=shutil.ignore_patterns('__pycache__'))
 shutil.copy(out/'collector.wasm',h/'collector.wasm')
 for name in ['compile.lisp','root-contracts.lisp']:
  p=poll/name;p.write_text(p.read_text().replace('compile-retrying-call-module','compile-call-module'))
 command([sys.executable,poll/'live_probe.py',e,out/'polls',poll/'wasm32-backend.lisp'],out/'polls.log')

 # Native literal identities and payloads, through the unchanged real compiler.
 sys.path.insert(0,str(HERE.parent/'constants'))
 const=load('qualified_constants',HERE.parent/'constants/compile.py')
 const_source=out/'constant-driver';shutil.copytree(HERE.parent/'constants',const_source,ignore=shutil.ignore_patterns('__pycache__','review-followup','development'))
 f=const_source/'compile.lisp';text=f.read_text();anchor='    (dolist (row cases)';assert text.count(anchor)==1
 extra='''    (setq cases (append cases (list
      (cons "bits_33" `(lambda () ',(make-array 33 :element-type 'bit :initial-element 1)))
      (cons "bits_65" `(lambda () ',(make-array 65 :element-type 'bit :initial-element 1)))
      (cons "raw_tag_words" `(lambda () ',(make-array 3 :element-type '(unsigned-byte 32) :initial-contents '(2097158 2147483654 4294967295)))))))
'''
 f.write_text(text.replace(anchor,extra+anchor));const.HERE=const_source
 const.run(e,out/'constants',(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text())
 from pool import compile_pool
 from execute_compiled import canonical
 pools=json.loads((out/'constants/pools.json').read_text());native=json.loads((out/'constants/native.json').read_text());mods=json.loads((out/'constants/modules.json').read_text());nodes={r['id']:r['value'] for r in native['objects']}
 symbols={'WASM32-COMPILER::POOL-OWNER':620006,'WASM32-COMPILER::pool-owner':620038}
 linked=compile_pool(pools,symbols)
 for label,base in [('low',2097152),('high',2147483648),('pinned',1835008)]:
  m=linked.at(base);save(out/'constants'/('materialized-'+label+'.json'),dict(base=base,image=m.image.hex(),roots=m.roots,symbols=symbols,objects=[dict(id=i,offset=o,tag=t) for i,o,t in linked.objects]))
 expected={m['name']:canonical(native,nodes[v['ref']]['elements']) for m,v in zip([m for m in mods if m['top']],native['roots'])};save(out/'constants/expected.json',expected)
 for n in ['literals.mjs','roots.mjs']:shutil.copy(HERE/n,out/n)
 setup=(HERE.parent/'constructor-retry/execute.mjs').read_text()
 a=setup.index('const rows=[];');b=setup.index(" assert.equal(retries,0,'instantiation has no allocation authority');")
 body=setup[setup.index(' const memory=',a):b]
 body=body.replace("['external',4096,16384]","['external',262144,266240]")
 body=body.replace("groups:['module-constants','callbacks','registry','host'].map(kind=>({kind,slots:[]}))","groups:['module-constants','callbacks','registry','host'].map((kind,i)=>({kind,slots:kind==='host'?[262144+4*i,262160]:[262144+4*i]}))")
 body=body.replace(' const owner=CollectorOwner.create', ' for(let i=0;i<5;i++)store(262144+4*i,NIL);\n const owner=CollectorOwner.create')
 setup=setup[:a]+"export function setup(high=false){const scenario={high,empty:true},cap=32768,A=high?2147483648:2097152,B=high?2147516416:2162688,c={args:[],nodes:[],capacity:16};\n"+body+"\n return {get,set,load,store,owner,entries,handles,ROOT,OUT,memory,external:262144,mods};}\n"
 (out/'setup.mjs').write_text(setup)

 command(['/usr/local/bin/node',out/'literals.mjs',out/'constants',out/'collector.wasm',out/'literals.json'],out/'literals.log')
 command(['/usr/local/bin/node',out/'roots.mjs',out/'generated',out/'collector.wasm',out/'roots.json'],out/'roots.log')
 result=dict(status='PASS',generated=json.loads((out/'generated.json').read_text()),core=json.loads((out/'core.json').read_text()),owner=json.loads((out/'owner.json').read_text()),literals=json.loads((out/'literals.json').read_text()),roots=json.loads((out/'roots.json').read_text()),polls=json.loads((out/'polls/execution.json').read_text()))
 if controls:result['controls']=load('qualification_controls',HERE/'controls.py').run(out,command,CLANG,FLAGS)
 save(out/'summary.json',result)
 if controls:load('collector_assessment',HERE/'assessment.py').run(out,out/'assessment')
 print('PASS collector qualification')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--controls',action='store_true');a=p.parse_args();run(a.evidence.resolve(),a.output.resolve(),a.controls)
