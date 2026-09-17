#!/usr/bin/env python3
"""Focused follow-up to Claude audit 85; unchanged LL10 compiler and native R6."""
import argparse,hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE.parents[3]
sys.path.insert(0,str(BASE))
import compile as compiler_run
import execute_compiled as executor
from compiler import generate
from compiler_controls import MUTATIONS

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def replace(s,old,new):
 if s.count(old)!=1:raise ValueError('overlay anchor '+old)
 return s.replace(old,new)
def overlay(out):
 out.mkdir()
 for p in BASE.iterdir():
  if p.is_file():shutil.copy(p,out/p.name)
 p=out/'compile.lisp';s=p.read_text()
 s=replace(s,'(modules nil) (native nil))','(modules nil) (native nil) (native-functions nil))')
 s=replace(s,'(cons "character"', '''(cons "same_literal" `(lambda () ',a))
     (cons "distinct_literal" `(lambda () ',b))
     (cons "untouched_seven" `(lambda () ',(cons 7 nil)))
     (cons "identity_join" '(lambda (f g) (eq (funcall f) (funcall g))))
     (cons "character"''')
 s=replace(s,'(vals (cond ((equal (car row) "tail_pool")', '''(vals (cond ((equal (car row) "identity_join") (multiple-value-list (funcall fn (cdr (assoc "string" native-functions :test #'equal)) (cdr (assoc "same_literal" native-functions :test #'equal)))))
                         ((equal (car row) "tail_pool")''')
 s=replace(s,'(push (cons (car row) vals) native)', '(push (cons (car row) fn) native-functions)\n        (push (cons (car row) vals) native)')
 anchor='    (setq modules (nreverse modules) native (nreverse native))'
 s=replace(s,anchor,'''    (with-open-file (s (concatenate 'string out "identity.json") :direction :output :if-exists :error)
      (write-char #\\[ s)
      (loop for (left right) in '(("string" "same_literal") ("string" "distinct_literal") ("same_literal" "distinct_literal")) for i from 0 do
        (unless (zerop i) (write-char #\\, s))
        (let ((answer (funcall (cdr (assoc "identity_join" native-functions :test #'equal))
                              (cdr (assoc left native-functions :test #'equal))
                              (cdr (assoc right native-functions :test #'equal)))))
          (format s "{\\"left\\":~s,\\"right\\":~s,\\"equal\\":~a}" left right (if answer "true" "false"))))
      (write-char #\\] s))
'''+anchor)
 p.write_text(s)
 p=out/'execute_compiled.py';s=p.read_text()
 s=replace(s,"    (out/'expected.json').write_text(json.dumps(expected))", """    (out/'expected.json').write_text(json.dumps(expected))
    # Compose one witnessed mutation by graph identity, before canonical IDs are reassigned.
    import copy
    altered=copy.deepcopy(native);changed={r['id']:r['value'] for r in altered['objects']}
    root_by_name={m['name']:v for m,v in zip(tops,native['roots'])}
    target=nodes[root_by_name['cycle']['ref']]['elements'][0]['ref']
    decoy=nodes[root_by_name['untouched_seven']['ref']]['elements'][0]['ref']
    if target==decoy or changed[target]['car']!={'kind':'integer','value':'7'}:raise ValueError('mutation identity')
    changed[target]['car']={'kind':'integer','value':'11'}
    if changed[decoy]['car']!={'kind':'integer','value':'7'}:raise ValueError('untouched identity')
    restored={m['name']:canonical(altered,changed[v['ref']]['elements']) for m,v in zip(tops,altered['roots'])}
    (out/'expected-restored.json').write_text(json.dumps(restored))
    (out/'mutation.json').write_text(json.dumps({'target':target,'untouched':decoy,'change':{'car':{'before':'7','after':'11'}}}))""")
 p.write_text(s)
 p=out/'execute_compiled.mjs';s=p.read_text()
 s=replace(s,"workerData:{dir,...data}","workerData:{dir,focus:process.argv[3],...data}")
 s=replace(s," const origin=await run({mode:'origin',base:1048576});", " const origin=await run({mode:'origin',base:1048576});\n if(process.argv[3]){console.log(JSON.stringify(origin));process.exit(0);}")
 s=replace(s,' const {dir,mode,base,snapshot}=workerData',' const {dir,mode,base,snapshot,focus}=workerData')
 old=" const expected=read('expected.json'),results=[];\n if(mode==='restore')for(const row of Object.values(expected))for(const obj of row.objects)if(obj.kind==='cons'&&obj.car?.kind==='integer'&&obj.car.value==='7')obj.car.value='11';"
 s=replace(s,old,""" const expected=read(mode==='restore'?'expected-restored.json':'expected.json'),results=[];
 if(focus){
  // Isolate slot indexing, constructor inheritance, rooted SELF and temporary relocation.
  if(focus==='slot-zero')assert.deepEqual(describe(invoke('integer'),'slot-zero'),expected.integer,'slot-zero-value');
  else if(focus==='child-pool'){
   const object=invoke('captured',[68])[0],child=load(object-2)/4-1;
   assert.equal(load(object+18),pool.roots[child],'child-pool-field');
  }else if(focus==='self-root')assert.deepEqual(describe(invoke('string'),'self-root'),expected.string,'self-root-value');
  else if(focus==='temporary-env')assert.deepEqual(describe(invoke('captured_apply',[68]),'temporary-env'),expected.captured_apply,'temporary-env-value');
  else throw new Error('unknown focus');
  parentPort.postMessage({status:'PASS',focus});
 }else{
""")
 s=replace(s,"m.name==='mutate_pool'?[300001]:", "m.name==='identity_join'?[handles.string,handles.same_literal]:m.name==='mutate_pool'?[300001]:")
 s=replace(s,' // Two factory activations share the pool but keep distinct environments.',""" const identities=read('identity.json');
 for(const row of identities){
  assert.deepEqual(invoke('identity_join',[handles[row.left],handles[row.right]]),[row.equal?77838:77825],'cross-function-identity '+row.left+'/'+row.right);
 }
 // Two factory activations share the pool but keep distinct environments.""")
 s=replace(s,'status:\'PASS\',base,modules:mods.length',"status:'PASS',cross_function_comparisons:identities.length,identity_mutation:true,base,modules:mods.length")
 s=s.rstrip()+'\n}\n';p.write_text(s)
 for name in ('execute_compiled.mjs','snapshot.mjs'):
  p=out/name;p.write_text(p.read_text().replace('../../../../doc/WASM/contracts/',(ROOT/'doc/WASM/contracts').as_uri()+'/'))
 return out

def node(directory,harness,focus=None,expected=None):
 command=['/usr/local/bin/node',str(harness/'execute_compiled.mjs'),str(directory)]
 if focus:command.append(focus)
 r=subprocess.run(command,capture_output=True,text=True,timeout=150)
 log=r.stdout+r.stderr
 (directory/('focus-'+focus+'.log' if focus else 'control.log')).write_text(log)
 if expected:
  if r.returncode==0 or expected not in log:raise ValueError('control expected '+expected+' in '+str(directory))
 else:
  if r.returncode:raise ValueError(str(directory)+' '+log[-1500:])
 return r

def inputs(evidence):
 parent=evidence/'2026-09-17-stage1-ll10-r1';record=read(parent/'source-pins.json')
 # Audit follow-up leaves the entire original implementation and its replay available.
 for name,h in record.items():
  if sha(ROOT/name)!=h:raise ValueError('reviewed source changed: '+name)
 backend=generate();proposal=parent/'positive/proposal/files/compiler/WASM32/wasm32-backend.lisp'
 if proposal.read_text()!=backend:raise ValueError('reviewed compiler changed')
 return {'parent_packet_sha256':sha(parent/'packet.json'),'reviewed_backend_sha256':sha(proposal),'runner_sha256':sha(Path(__file__)),'parent':'2026-09-17-stage1-ll10-r1','review_commit':'a8dbfb59','native_R6_R6a':'Reused unchanged reviewed compiler and registration; no new native rebuild.'}

def run(evidence,out):
 binding=inputs(evidence);out.mkdir(parents=True,exist_ok=False);save(out/'inputs.json',binding);shutil.copy(__file__,out/'run.py')
 harness=overlay(out/'harness');compiler_run.HERE=harness
 # Import the overlaid executor so its independent native-graph transformation runs.
 import importlib.util
 spec=importlib.util.spec_from_file_location('followup_executor',harness/'execute_compiled.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
 positive=out/'positive';compiler_run.run(evidence,positive);ex.run(positive)
 controls=[]
 targets={'header-as-slot-zero':('slot-zero','value-tag slot-zero'),'lost-child-pool':('child-pool','child-pool-field'),'wrong-self-root':('self-root','string: call_error 4'),'temporary-environment-overwrites-pool':('temporary-env','temporary-env-value')}
 for name,(focus,diagnostic) in targets.items():
  node(positive,harness,focus)
  old,new=MUTATIONS[name];base=generate();assert base.count(old)==1
  dest=out/name;compiler_run.run(evidence,dest,base.replace(old,new))
  # Reuse only target-independent preparation; execution is the focused mechanism.
  save(dest/'materialized.json',read(positive/'materialized.json'));save(dest/'expected.json',read(positive/'expected.json'))
  shutil.copy(positive/'lazy-stub.wasm',dest/'lazy-stub.wasm')
  node(dest,harness,focus,diagnostic);controls.append({'name':name,'focus':focus,'diagnostic':diagnostic,'status':'REJECTED'})
  save(out/'controls.json',controls)
 # The formerly broad oracle must now fail specifically on the unrelated cons.
 for name in ('broad-restore-oracle','split-cross-function-literal'):
  dest=out/name;dest.mkdir()
  for p in positive.iterdir():
   if p.suffix=='.wasm' or p.name in ('modules.json','materialized.json','expected.json','expected-restored.json','identity.json'):shutil.copy(p,dest/p.name)
  if name=='broad-restore-oracle':
   bad=read(dest/'expected-restored.json')
   for row in bad.values():
    for obj in row['objects']:
     if obj['kind']=='cons' and obj['car']=={'kind':'integer','value':'7'}:obj['car']['value']='11'
   save(dest/'expected-restored.json',bad);diagnostic='untouched_seven'
  else:
   m=read(dest/'materialized.json');mods=read(dest/'modules.json');data=bytearray.fromhex(m['image']);import struct
   def word(at):return struct.unpack_from('<I',data,at-m['base'])[0]
   def literal(n):return word(m['roots'][next(i for i,r in enumerate(mods) if r['name']==n)]-2)
   slot=m['roots'][next(i for i,r in enumerate(mods) if r['name']=='same_literal')]-2
   struct.pack_into('<I',data,slot-m['base'],literal('distinct_literal'));m['image']=data.hex();save(dest/'materialized.json',m);diagnostic='identity_join'
  node(dest,harness,expected=diagnostic);controls.append({'name':name,'diagnostic':diagnostic,'status':'REJECTED'});save(out/'controls.json',controls)
 execution=read(positive/'execution.json');assert execution['modules']==91 and execution['native_comparisons']==245,execution
 assert read(positive/'identity.json')==[{'left':'string','right':'same_literal','equal':True},{'left':'string','right':'distinct_literal','equal':False},{'left':'same_literal','right':'distinct_literal','equal':False}]
 assert binding==inputs(evidence),'source changed'
 summary={'status':'PASS','generated_modules':91,'native_comparisons':245,'additional_cross_function_comparisons':9,'compiler_mutants':4,'semantic_controls':2,'compiler_unchanged':True,'native_R6_R6a_reused':True,'scope':'Audit 85 follow-up; no acceptance or shared integration.'};save(out/'summary.json',summary);print(json.dumps(summary))

def retain(run,out):
 out.mkdir(parents=True,exist_ok=False)
 for n in ('summary.json','inputs.json','controls.json','run.py'):shutil.copy(run/n,out/n)
 with tarfile.open(out/'execution.tar.gz','w:gz') as t:
  for p in sorted(run.rglob('*')):
   if p.is_file():t.add(p,arcname=str(p.relative_to(run)))
 save(out/'packet.json',{'id':'STAGE1-LL10-REVIEW-FOLLOWUP-R1','review_disposition':'NOT_REVIEWED','files':[{'path':p.name,'sha256':sha(p)} for p in sorted(out.iterdir())]})

def verify(evidence,packet,out):
 for r in read(packet/'packet.json')['files']:
  if sha(packet/r['path'])!=r['sha256']:raise ValueError('packet hash '+r['path'])
 if read(packet/'inputs.json')!=inputs(evidence):raise ValueError('inputs')
 run(evidence,out)
 with tarfile.open(packet/'execution.tar.gz') as t:
  count=0
  for member in t.getmembers():
   p=Path(member.name)
   if p.suffix in ('.wasm','.wat','.dx64fsl') or p.name in ('summary.json','controls.json','native.json','identity.json','expected.json','expected-restored.json','mutation.json','execution.json','snapshot.json'):
    if t.extractfile(member).read()!=(out/member.name).read_bytes():raise ValueError('replay '+member.name)
    count+=1
 print('FOLLOWUP-VERIFIED',count,'deterministic files')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['run','retain','verify']);p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');p.add_argument('--output',type=Path,required=True);p.add_argument('--run',type=Path);p.add_argument('--packet',type=Path);a=p.parse_args()
 if a.mode=='run':run(a.evidence.resolve(),a.output.resolve())
 elif a.mode=='retain':retain(a.run.resolve(),a.output.resolve())
 else:verify(a.evidence.resolve(),a.packet.resolve(),a.output.resolve())
