from pathlib import Path
import shutil,subprocess
from run import HERE,read,save,sha,replace,command,build,NODE

def run(e,out,proposal):
 d=out/'probes';shutil.copytree(out/'raw',d)
 service=(proposal/'scalar-service.mjs').read_text();wat=(proposal/'scalar.wat').read_text()
 poisoned=replace(service,'const fallback=(op,root,safe)=>{try{return slow(op,root,safe);}finally{refresh();}};',"const fallback=()=>{throw Error('SCALAR_SLOW_POISON');};")
 full=(d/'execute.mjs').read_text();prefix=full[:full.index('try{\n for(const high of [false,true])')]
 suffix=full[full.index('}catch(e){fs.writeFileSync(outputFile'):]
 checks=prefix+'try{\n'+(HERE/'fast-checks.mjs').read_text()+"\nfs.writeFileSync(outputFile,JSON.stringify({status:'PASS',checks:rows.length,rows},null,2)+'\\n');\n"+suffix
 (d/'execute.mjs').write_text(checks);save(d/'cases.json',[]);(d/'scalar-service.mjs').write_text(poisoned)
 command([NODE,d/'execute.mjs',d,d/'positive.json'],d/'positive.log')
 controls=[]
 faults=[
 ('wrong-add','(f64.add (local.get $a) (local.get $b))','(f64.sub (local.get $a) (local.get $b))','fast-double-add'),
 ('ignore-full-mask','(i32.and (local.get $mask) (i32.const 24))','(i32.and (local.get $mask) (i32.const 0))','full-mask-fallback'),
 ('unowned-operand','(br_if $miss (i32.or (i32.eq (local.get $ak) (i32.const -1))',None,'stack-operand-fallback'),
 ('ignore-shortage','(br_if $miss (i32.eqz (call $inside (local.get $heap) (local.get $size) (call $t (i32.const 56)) (call $t (i32.const 52)))))','', 'shortage-fallback'),
 ('ignore-boundary','(i32.or (i32.eqz (global.get $eligible)) (global.get $boundary))','(i32.eqz (global.get $eligible))','owner-boundary-fallback'),
 ('copy-identity','(if (i32.eq (local.get $ak) (local.get $width))','(if (i32.const 0)','fast-identity'),
 ('wrong-single-width','(select (i32.const 64) (i32.const 32) (i32.or (i32.eq (local.get $ak) (i32.const 64)) (i32.eq (local.get $bk) (i32.const 64))))','(i32.const 64)','fast-single-add'),
 ]
 for name,a,b,diagnostic in faults:
  md=out/name;shutil.copytree(d,md)
  if name=='unowned-operand':
   start=wat.index(' (func $owned');end=wat.index(' (func $number',start)
   mutant=wat[:start]+' (func $owned (param i32 i32) (result i32) (i32.const 1))\n'+wat[end:]
  else:mutant=replace(wat,a,b)
  (md/'scalar.wat').write_text(mutant);build(md/'scalar.wat',md/'scalar.wasm',md/'build.log');inputs=read(md/'inputs.json');inputs['scalar_sha256']=sha(md/'scalar.wasm');save(md/'inputs.json',inputs)
  try:command([NODE,md/'execute.mjs',md,md/'execution.json'],md/'execution.log')
  except subprocess.CalledProcessError:
   result=read(md/'execution.json');assert result['case']==diagnostic,(name,result)
  else:raise AssertionError('escaped '+name)
  controls.append(dict(name=name,status='REJECTED',case=diagnostic))
 # Geometry refresh cannot be justified just by final values: stale geometry
 # silently delegates every later call. The instrumented slow import counts it.
 for name,omit in [('growth-positive',False),('stale-geometry',True)]:
  md=out/name;shutil.copytree(out/'raw',md);save(md/'cases.json',[])
  counted="export const scalarProbeCounts={fallback:0};\n"+replace(service,'try{return slow(op,root,safe);}','try{scalarProbeCounts.fallback++;return slow(op,root,safe);}')
  if omit:counted=replace(counted,'finally{refresh();}','finally{}')
  (md/'scalar-service.mjs').write_text(counted)
  s=full.replace("import {scalarFloatService as floatService}","import {scalarFloatService as floatService,scalarProbeCounts}")
  anchor='rows.push({name:current,grown:true,resultMoved:true});'
  s=replace(s,anchor,anchor+"\n  current='fast-after-growth';owner.ensure=n=>{ensures++;return ensure(n);};const slowBefore=scalarProbeCounts.fallback;put(ROOT+8,get(ROOT+16));put(ROOT+16,N);invoke({...row,expected:{...row.expected,value:'4014000000000000'}});assert.equal(scalarProbeCounts.fallback,slowBefore,current);rows.push({name:current});")
  if not omit:
   anchor=" fs.writeFileSync(outputFile,JSON.stringify({status:'PASS',comparisons:"
   extra=" current='forced-reentry';setup(false,32);reset(row);let reentries=0;const retryEnsure=owner.ensure.bind(owner);owner.ensure=n=>{ensures++;reentries++;assert.throws(()=>calculate(0,ROOT,1),e=>e instanceof WebAssembly.Exception&&e.is(callError)&&e.getArg(callError,0)===41);return retryEnsure(n);};invoke(row);assert.equal(reentries,1,current);rows.push({name:current});\n"
   s=replace(s,anchor,extra+anchor)
  (md/'execute.mjs').write_text(s)
  try:command([NODE,md/'execute.mjs',md,md/'execution.json'],md/'execution.log')
  except subprocess.CalledProcessError:
   assert omit and read(md/'execution.json')['case']=='fast-after-growth'
  else:assert not omit,'escaped stale geometry'
  if omit:controls.append(dict(name=name,status='REJECTED',case='fast-after-growth'))
 md=out/'sticky-boundary';shutil.copytree(d,md)
 s=(md/'collector-owner.mjs').read_text();s=replace(s,'this.#scalarBoundary.value=0;','');(md/'collector-owner.mjs').write_text(s)
 try:command([NODE,md/'execute.mjs',md,md/'execution.json'],md/'execution.log')
 except subprocess.CalledProcessError:assert read(md/'execution.json')['case']=='boundary-restored-fast'
 else:raise AssertionError('escaped sticky boundary')
 controls.append(dict(name='sticky-boundary',status='REJECTED',case='boundary-restored-fast'))
 md=out/'overlap-bypass';shutil.copytree(d,md)
 s=(md/'scalar-service.mjs').read_text();s=replace(s,"region.disjoint&&!region.rows.some(r=>pair.some(s=>r.start<s.end&&s.start<r.end))","region.disjoint");(md/'scalar-service.mjs').write_text(s)
 try:command([NODE,md/'execute.mjs',md,md/'execution.json'],md/'execution.log')
 except subprocess.CalledProcessError:assert read(md/'execution.json')['case']=='overlap-active-fallback'
 else:raise AssertionError('escaped active overlap')
 controls.append(dict(name='overlap-bypass',status='REJECTED',case='overlap-active-fallback'))
 save(out/'controls.json',dict(faults=controls,no_js_checks=read(d/'positive.json')['checks']))
