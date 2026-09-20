import json,shutil,subprocess

def faults():
 return [
  ('stale-mode','const mask=get(tcr+200);','const mask=7;','live-mask','packed status'),
  ('unsafe-checks','result,mask,safe);','result,mask,1);',None,'packed status'),
  ('wrong-operand','stage(get(root+12))','stage(get(root+8))',None,'published value'),
  ('missing-assurance','owner.atSafepoint(o=>o.ensure(size));','void 0;',None,'only allocated results assure'),
  ('stale-heap','if(size){try{owner.atSafepoint','const staleHeap=get(tcr+48);if(size){try{owner.atSafepoint',None,'placeholder'),
  ('unrooted-first','if(size){try{owner.atSafepoint','set(root+8,77825);if(size){try{owner.atSafepoint',None,'operand preserved'),
  ('lost-result','set(root+16,published);','set(root+16,77825);',None,'published value'),
  ('lost-flags','selected|(flags<<5)','selected|(0<<5)',None,'packed status'),
  ('digest-bypass','hash(bytes)!==digest','false','bad-service-digest','Missing expected exception'),
  ('detector-digest-bypass','hash(detectorBytes)!==detectorDigest','false','bad-detector-digest','Missing expected exception'),
  ('owner-tcr-bypass','owner.tcr!==tcr','false','foreign-tcr','Missing expected exception'),
  ('reentrant','busy||op>11','op>11','busy-reentry',None),
 ]
def run(out,driver):
 # Literal focused inputs exercise the service boundary rather than deriving
 # a pass/fail verdict from the source mutation. The full harness also executes
 # growth, state failures and factory admission for every fault.
 base=dict(name='focus',op='add',a=dict(kind='64',bits='3ff0000000000000'),b=dict(kind='64',bits='4000000000000000'),mask=7,safe=1,expected=dict(width=64,value='4008000000000000',flags=0,condition=0,stage=3,a_flags=0,b_flags=0))
 zero=dict(name='unchecked-zero',op='div',a=dict(kind='64',bits='3ff0000000000000'),b=dict(kind='64',bits='0000000000000000'),mask=7,safe=0,expected=dict(width=64,value='7ff0000000000000',flags=0,condition=0,stage=3,a_flags=0,b_flags=0))
 checked=dict(zero,name='checked-zero',safe=1,expected=dict(zero['expected'],value='NIL',condition=2,flags=2))
 positive=out/'focused';positive.mkdir()
 for n in ['execute.mjs','float-service.mjs','collector-owner.mjs','float.wasm','detector.wasm','collector.wasm','inputs.json']:shutil.copy(out/n,positive/n)
 driver.save(positive/'cases.json',[base,zero,checked]);driver.command(['/usr/local/bin/node',positive/'execute.mjs',positive,positive/'execution.json'],positive/'execution.log')
 results=[]
 for name,old,new,case,message in faults():
  p=out/name;p.mkdir()
  for n in ['execute.mjs','collector-owner.mjs','float.wasm','detector.wasm','collector.wasm','inputs.json','cases.json']:shutil.copy(positive/n,p/n)
  source=(out/'float-service.mjs').read_text();assert source.count(old)==1,(name,source.count(old));source=source.replace(old,new)
  if name=='stale-heap':source=source.replace('const heap=get(tcr+48),limit=', 'const heap=staleHeap,limit=');message=None
  (p/'float-service.mjs').write_text(source)
  try:driver.command(['/usr/local/bin/node',p/'execute.mjs',p,p/'execution.json'],p/'execution.log')
  except subprocess.CalledProcessError:
   failure=json.loads((p/'execution.json').read_text());assert failure['status']=='FAIL',failure
   if case:assert failure['case']==case,(name,failure)
   if message:assert message in failure['message'],(name,failure)
   if name=='stale-heap':assert '/moving' in failure['case'] and failure['code']==6,(name,failure)
   if name=='reentrant':assert failure['code']==6,(name,failure)
   results.append(dict(name=name,status='REJECTED',case=failure['case'],diagnostic=failure['message']))
  else:raise AssertionError('escaped '+name)
 driver.save(out/'controls.json',results)
