#!/usr/bin/env python3
import argparse,importlib.util,json,shutil,subprocess,sys,os
from pathlib import Path
from backend import generate,replace,base
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'constants'))
p=HERE.parent/'constants/inherited.py'
spec=importlib.util.spec_from_file_location('accepted_harness',p)
harness=importlib.util.module_from_spec(spec);spec.loader.exec_module(harness)
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def prepare(out):
 harness.generate=generate
 h=harness.prepare(out);shutil.copy(HERE/'probe.py',h/'probe.py')
 # The native implicit-error oracle previously classified only function type
 # errors. Classify the actual native TYPE-ERROR condition for list failures.
 p=h/'compile.lisp';text=p.read_text()
 text=replace(text,'(t "UNEXPECTED")','((and *implicit-error-suite* (typep c \'type-error)) "TYPE") (t "UNEXPECTED")')
 text=replace(text,'(cond ((equal v "nil") nil)', '(cond ((equal v "v0") (vector 3 5 7 11)) ((equal v "nil") nil)')
 text=text.replace("(setq values (multiple-value-list (apply (cdr (assoc name *call-functions* :test #'equal)) (mapcar #'decode args))))", "(progn (setq values (multiple-value-list (apply (cdr (assoc name *call-functions* :test #'equal)) (mapcar #'decode args)))) (setq status \"RETURN\"))")
 text=(HERE/'class-shapes.lisp').read_text()+'\n'+text
 p.write_text(text)
 p=h/'conditions.mjs';text=p.read_text()
 text=text.replace("'condition_handlers'", "'condition_handlers','condition_restarts','restart_type','debugger_hook','interrupt_level','gc_service','interrupt_service','expected_function','expected_or','expected_symbol'")
 text=text.replace('set(108,5)', 'set(108,14)').replace('i<5','i<14').replace('length:5','length:14').replace('[243,243,243,243,243]','[243,243,243,243,243,243,243,243,243,243,243,243,243,243]')
 text=text.replace('i===3?NIL:', 'name===\'interrupt_level\'?0:i>=3?NIL:')
 text=replace(text," const specialNames=", """ const restartSymbols=new Map();
 for(const module of compiled.values())for(const imp of WebAssembly.Module.imports(module))if(imp.module==='symbols'&&imp.name.startsWith('restart_name_')&&!restartSymbols.has(imp.name)){
  const address=632006+32*restartSymbols.size;assert(address+26<640000);restartSymbols.set(imp.name,address);symbols[imp.name]=address;
 }
 const specialNames=""")
 text=replace(text,"x==='nil'?NIL","x==='v0'?630006:x==='nil'?NIL")
 text=replace(text,'  store(4096,mods.length+1);',"  for(const address of restartSymbols.values()){store(address-6,1850);for(let i=1;i<8;i++)store(address-6+4*i,NIL);}\n  store(640256,1850);store(640288,1850);for(let j=1;j<8;j++){store(640256+4*j,NIL);store(640288+4*j,NIL);}store(640128,640137);store(640132,640262);store(640136,NIL);store(640140,640294);store(640000,640009);store(640004,symbols.expected_or);store(640008,640017);store(640012,symbols.expected_symbol);store(640016,NIL);store(640020,symbols.expected_function);store(symbols.expected_function+2,640001);\n  store(630000,1274);[3,5,7,11].forEach((v,i)=>store(630004+4*i,v*4));\n  store(4096,mods.length+1);")
 text=replace(text,'   installObjects();for(const',"   installObjects();set(192,c.function.startsWith('d_')?1:0);set(184,0);set(180,0);set(88,920000);set(92,920000);set(96,940000);for(const")
 text=replace(text,"inspect('returned '+c.id);","assert.equal(get(184),0,c.id+': debugger depth restored');assert.equal(get(180),0,c.id+': emergency reserve rearmed');assert.equal(get(88),get(92),c.id+': control stack restored');inspect('returned '+c.id);")
 text=replace(text," const specialNames=", " symbols.error_message=680006;symbols.condition_registry=650006;symbols.expected_proper_list=640129;\n const specialNames=")
 text=replace(text,' for(const m of mods){\n  const codes=',(HERE/'objects.mjs').read_text()+'\n for(const m of mods){\n  const codes=')
 text=replace(text,' function installObjects(){',' function installObjects(){\n installConditionClasses();')
 text=replace(text,"  [1,9,31,39,71,393].forEach((mask,i)=>{const p=620000+16*i;store(p,762);store(p+4,mask*4);store(p+8,i*4);store(p+12,NIL);});",'')
 text=text.replace('620006+16*','620006+64*').replace('x<620102','x<620390').replace('(x-620006)%16','(x-620006)%64').replace('(x-620006)/16','(x-620006)/64')
 text=replace(text,"   const savedArgs=", """   if(c.resources){set(100,c.resources.reserve);if(c.resources.vsp)set(72,start+c.resources.vsp+c.resources.reserve);if(c.resources.tsp)set(84,get(80)+c.resources.tsp+c.resources.reserve);if(c.resources.csp)set(96,get(92)+c.resources.csp+c.resources.reserve);}
   const savedArgs=""")
 text=text.replace('[1,4,5,8,10,12,15].includes(code)', '[1,2,4,5,8,10,12,13,15,18,19,20].includes(code)').replace("status=code===15?", "status=code===2||code===13?'STACK':code>=18&&code<=20?'STORAGE':code===15?")
 text=replace(text,"   if(c.resources)", """   if(c.pending!==undefined){set(36,c.pending);store(symbols.gc_service+2,handles.get('irq_gc'));store(symbols.interrupt_service+2,handles.get('irq_service'));}
   if(c.resources)""")
 text=replace(text,"assert.equal(get(184),0,c.id+': debugger depth restored');", "if(c.pending!==undefined)assert.equal(get(36),c.pendingAfter,c.id+': claimed only interrupt bit');assert.equal(get(184),0,c.id+': debugger depth restored');")
 text=replace(text,"let previous=get(72),depth=0;", """let controls=[];for(let r=get(140);r;r=load(r))controls.push(r);
 if(get(92)){assert.equal(get(88),get(92)+16*controls.length,label+': independent CSP depth');controls.reverse().forEach((r,i)=>{const p=get(92)+16*i;assert.equal(load(p),r,label+': CSP owner');assert.equal(load(p+4),1129533489,label+': CSP marker');});}
 let previous=get(72),depth=0;""")
 text=replace(text,"const conditionRefusals=[];", "let currentControlCase=null,cleanupWitnesses=[];const fatalDiagnostics=[];const conditionRefusals=[];")
 text=replace(text,"internalEntries++;inspect('internal '+m.name);", "internalEntries++;inspect('internal '+m.name);"+(HERE/'observations.mjs').read_text())
 text=replace(text,"for(const c of cases){parentPort", "for(const c of cases){currentControlCase=c;cleanupWitnesses=[];parentPort")
 text=replace(text,"if(e.is(type_error))status='TYPE';", "if(e.is(type_error)){status='TYPE';fatalDiagnostics.push({version:1,stage:get(192)===1?'ordinary-error-service':'bootstrap',function:c.function,kind:'type-error',datum:e.getArg(type_error,0)>>>0,check:e.getArg(type_error,1),transport:'wasm-tag',recoverable:false});}")
 text=replace(text,"const code=e.getArg(call_error,0);", "const code=e.getArg(call_error,0);fatalDiagnostics.push({version:1,stage:get(192)===1?'ordinary-error-service':'bootstrap',function:c.function,kind:'checked-runtime-error',code,transport:'wasm-tag',recoverable:false});")
 text=replace(text,"inspect('returned '+c.id);", "if(observed&&c.function==='o_nested')assert.deepEqual(cleanupWitnesses,[11,13],'source cleanup order');inspect('returned '+c.id);")
 text=replace(text,"parentPort.postMessage({status:'PASS',condition_refusals:", "parentPort.postMessage({status:'PASS',fatal_diagnostics:fatalDiagnostics,condition_refusals:")
 text=replace(text,"['fixnum','nil','header','mask-tag','mask-zero','mask-unknown','outside']", "['fixnum','nil','header','wrapper','unknown-wrapper','slots-header','slots-backlink','registry-header','outside']")
 text=replace(text,"if(fault==='header')store(620000,1018);if(fault==='mask-tag')store(620004,5);if(fault==='mask-zero')store(620004,0);if(fault==='mask-unknown')store(620004,2044);", "if(fault==='header')store(620000,1018);if(fault==='wrapper')store(620008,NIL);if(fault==='unknown-wrapper')store(620008,648006);if(fault==='slots-header')store(620016,0);if(fault==='slots-backlink')store(620020,NIL);if(fault==='registry-header')store(650000,0);")
 p.write_text(text)
 # All inherited runners receive the same new owner metadata. Eager and lazy
 # share this adaptation; none of the semantic expectations are changed.
 from inherited_setup import adapt
 p=h/'conditions.py';p.write_text(p.read_text()+"\nREFUSALS=[r for r in REFUSALS if r[0]!='restart-case']\n")
 for name in ('execute.mjs',):
  p=h/name;p.write_text(adapt(p.read_text()))
 shutil.copy(HERE/'inherited_setup.py',h/'inherited_setup.py');shutil.copy(HERE/'objects.mjs',h/'objects.mjs')
 for name in ('condition_lazy.py','lazy_composition.py'):
  p=h/name;t=p.read_text().replace("'root-contracts.json'", "'root-contracts.json','native-condition-classes.json'")
  if name=='lazy_composition.py':t=t.replace(" (out/'harness.mjs').write_text(harness)", " from inherited_setup import adapt as control_adapt\n harness=control_adapt(harness)\n (out/'harness.mjs').write_text(harness)")
  p.write_text(t)
 p=h/'full_loader.py';t=p.read_text().replace("'root-contracts.json'", "'root-contracts.json','native-condition-classes.json'")
 t=t.replace(" (out/'controls.mjs').write_text(s)", " from inherited_setup import adapt_loader\n s=adapt_loader(s)\n (out/'controls.mjs').write_text(s)")
 p.write_text(t)
 for name in ('loader.mjs','binary.mjs','stub.wat'):
  p=h/name;p.write_text(p.read_text().replace('wasm32-shared-B-exnref-tail-mv-storage-constants-v1','wasm32-shared-B-exnref-control-v1'))
 p=h/'layout.json';layout=json.loads(p.read_text());layout['temporary_results']['profile']='wasm32-shared-B-exnref-control-v1';save(p,layout)
 return h

def run(evidence,out,qualify=False):
 out.mkdir(parents=True,exist_ok=False);h=prepare(out/'harness')
 backend=generate();(out/'wasm32-backend.lisp').write_text(backend)
 controls=[]
 from mutants import variants
 from resources import run as resources
 jobs=[('positive',backend,None,None)]+(list(variants(backend,replace)) if qualify else [])
 for name,source,focus,resource in jobs:
  p=out/(name+'.lisp');p.write_text(source)
  command=[sys.executable,str(h/'probe.py'),str(evidence),str(out/name),str(p)]
  environment=dict(os.environ)
  if focus:environment['LL19_CASES']=focus
  save(out/(name+'-command.json'),{'argv':command,'LL19_CASES':focus})
  with (out/(name+'.log')).open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=300,env=environment)
  if name=='positive':
   if r.returncode:raise ValueError('positive failed: '+str(out/'positive.log'))
   if qualify:resources(out/name/'compiled',out/name/'harness.mjs',out/'resources')
  else:
   if resource:
    if r.returncode:raise ValueError('resource mutant must first pass ordinary execution: '+name)
    try:resources(out/name/'compiled',out/name/'harness.mjs',out/(name+'-resource'),resource)
    except ValueError:pass
    else:raise ValueError('resource mutant escaped: '+name)
    log=(out/(name+'-resource')/'execution.log').read_text()
   else:
    if r.returncode==0:raise ValueError('mutant escaped: '+name)
    log=(out/name/'execution.log').read_text()
   if 'AssertionError' not in log or 'native/logical result' not in log and not any(x in log for x in ('depth restored','stack restored','reserve rearmed','claimed only interrupt','independent CSP','CSP owner')):raise ValueError('wrong rejection: '+name)
   controls.append({'name':name,'status':'REJECTED','focus':focus,'resource':resource,'diagnostic':log.splitlines()[0]})
 save(out/'controls.json',controls)
 summary=json.loads((out/'positive/summary.json').read_text())
 save(out/'summary.json',{'status':'PASS','modules':summary['modules'],'comparisons':summary['comparisons'],'controls':controls,'scope':'Generated LL19 corpus; publication additionally requires inherited replay and native R6/R6a.'})
 print(json.dumps(json.loads((out/'summary.json').read_text())))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');p.add_argument('--output',type=Path,required=True);p.add_argument('--qualify',action='store_true');a=p.parse_args();run(a.evidence.resolve(),a.output.resolve(),a.qualify)
