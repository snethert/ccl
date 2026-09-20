#!/usr/bin/env python3
"""Audit-120 follow-up; derive from and bind every reviewed R1 source."""
import argparse,copy,importlib.util,json,shutil,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE.parents[3]
sys.path.insert(0,str(BASE))
spec=importlib.util.spec_from_file_location('symbols_original_runner',BASE/'run.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
sha=prior.sha;save=prior.save;read=prior.read;command=prior.command
PARENT='2026-09-20-stage1-symbols-r1'
GUARD='if(L(node-2+4*i)>0x10ffffu)return 0;'
REPLACEMENT='if(L(node-2+4*i)>0x10ffffu||(L(node-2+4*i)>=0xd800u&&L(node-2+4*i)<=0xdfffu))return 0;'
def replace(s,old,new,count=1):
 assert s.count(old)==count,(old,s.count(old));return s.replace(old,new)
def overlays():
 c=replace((BASE/'symbols.c').read_text(),GUARD,REPLACEMENT)
 g=(BASE/'generated.mjs').read_text()
 hook=" return {call,invoke(op,a,b=NIL,c=NIL){"
 extra=""" return {call,operationCounts(op){return Object.fromEntries(['fixed_calls','dynamic_calls','direct_calls'].map(n=>[n,adapters[op].exports[n].value]));},
 invokeForm(name,op,a,b=NIL,c=NIL){
 const args=name==='symbol_dynamic'||name==='symbol_indirect'?[operations[op],entries.symbol_receiver.self,a,b,c]:[operations[op],a,b,c];return call(name,args);
 },invoke(op,a,b=NIL,c=NIL){"""
 g=replace(g,hook,extra)
 s=(BASE/'check.mjs').read_text()
 s="import {directed} from './directed.mjs';\n"+s
 s=replace(s,"nextBase=base===4194304?8388608:4194304", "nextBase=base===4194304?2147483648:4194304")
 s=replace(s," let bindingComparisons=0;", " let bindingComparisons=0;const directedRows=[];\n function followup(){owner.memory=memory;directedRows.push(directed({code,raw,service,CONFIG,RESULT,NIL,owner,packages,statuses,expected:read('followup-native.json'),phase:directedRows.length?'after':'before'}));}")
 s=replace(s,' bindings();',' bindings();followup();',2)
 old=" parentPort.postMessage({base,generated,nativeComparisons:"
 s=replace(s,old," assert.equal(directedRows[1].keywordPointer-directedRows[0].keywordPointer,loads[0].to-loads[0].from,'existing keyword identity relocated');\n if(base===4194304)assert.equal(loads[0].to,2147483648,'retained load targets 2 GiB');\n parentPort.postMessage({directedRows,base,generated,nativeComparisons:")
 return c,g,s

def assess(ex,expected):
 assert [(r['base'],r['generated']) for r in ex['rows']]==[(b,g) for b in [4194304,8388608,2147483648] for g in [False,True]],'placements'
 for r in ex['rows']:
  assert [d['phase'] for d in r['directedRows']]==['before','after'],'both phases'
  assert len(r['loads'])==1 and r['loads'][0]['to']==(2147483648 if r['base']==4194304 else 4194304),'high load'
  for d in r['directedRows']:
   assert d['keyword']==expected['keyword'],'existing keyword'
   assert [(x['point'],x['native'],x['status']) for x in d['characters']]==[(p,n,4 if n<0 else 0) for p,n in expected['characters']],'character contract'
   if r['generated']:
    assert [x['native'] for x in d['make']]==expected['make'],'six MAKE forms'
    assert [x['delivery'] for x in d['make']]==[dict(fixed_calls=2 if i<4 else 0,dynamic_calls=2 if i>=4 else 0,direct_calls=2 if i==4 else 0) for i in range(6)],'MAKE delivery'
   else:assert d['make']==[]
 return dict(status='PASS',phases=12,make_form_comparisons=36,character_checks=96,keyword_checks=12,low_to_high_loads=2)

def run(e,out):
 out.mkdir(parents=True,exist_ok=False)
 pins=read(e/PARENT/'source-pins.json')
 for n,h in pins.items():assert sha(ROOT/n)==h,n
 source,g,check=overlays();driver=out/'driver';driver.mkdir()
 for p in BASE.iterdir():
  if p.is_file():shutil.copy(p,driver/p.name)
 (driver/'symbols.c').write_text(source);prior.HERE=driver
 prior.run(e,out/'inherited')
 inherited=out/'inherited'
 for p in (e/PARENT/'execution/compiled').glob('*.wasm'):assert sha(p)==sha(inherited/'compiled'/p.name),p.name
 assert sha(inherited/'adapter.wasm')==sha(e/PARENT/'execution/adapter.wasm')
 probe=out/'directed';probe.mkdir()
 for name in ['symbols.wasm','adapter.wasm','image.mjs','trace.json','native.json','bindings.json']:
  shutil.copy(inherited/name,probe/name)
 shutil.copytree(inherited/'compiled',probe/'compiled',ignore=shutil.ignore_patterns('source','proposal','driver'))
 (probe/'generated.mjs').write_text(g);(probe/'check.mjs').write_text(check);shutil.copy(HERE/'directed.mjs',probe/'directed.mjs');shutil.copy(HERE/'native.lisp',out/'native.lisp')
 kernel=e/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=e/'2026-09-16-stage1-1a-r2/native/baseline.image'
 with tempfile.TemporaryDirectory(prefix='ccl-symbol-followup-') as tmp:
  w=Path(tmp);shutil.copy(kernel,w/'dx86cl64');(w/'dx86cl64').chmod(0o755);shutil.copy(image,w/'dx86cl64.image')
  command([w/'dx86cl64','--no-init','--batch','--load',out/'native.lisp'],out/'native.log')
 log=(out/'native.log').read_text().splitlines()
 parse=lambda prefix:[list(map(int,l.split()[1:])) for l in log if l.startswith(prefix+' ')]
 native=dict(keyword=parse('KEYWORD')[0],make=parse('MAKE'),characters=parse('CHAR'),names=parse('NAME'))
 assert native['keyword']==[1]*6
 assert native['make']==[[i,1 if i in [0,2,3] else 2,1,1,1,1] for i in range(6)]
 assert native['characters']==[[55295,55295],[55296,-1],[56319,-1],[56320,-1],[57343,-1],[57344,57344],[1114111,1114111],[1114112,-2]]
 assert native['names']==[[n,n] for n in [55295,57344,1114111]]
 save(probe/'followup-native.json',native)
 save(probe/'initial-keywords.json',read(inherited/'initial-keywords.json')+['ALLOW-OTHER-KEYS'])
 command([prior.NODE,probe/'check.mjs',probe,probe/'execution.json'],probe/'execution.log')
 report=read(probe/'execution.json');assessment=assess(report,native);save(out/'assessment.json',assessment)
 controls=[]
 faults=[('old-surrogate-guard','symbols.wasm',None,None,'native rejected character 55296'),
 ('missing-existing-keyword','initial-keywords.json',None,None,'pre-existing keyword must be external'),
 ('make-dynamic-zero','adapter.wat','  (local.set $status (call $run', '  (if (i32.and (i32.eq (global.get $op) (i32.const 2)) (i32.ne (local.get $d) (i32.const 0))) (then (local.set $n (i32.const 0))))\n  (local.set $status (call $run','MAKE-SYMBOL symbol_dynamic'),
 ('missing-high-load','check.mjs','nextBase=base===4194304?2147483648:4194304','nextBase=base===4194304?8388608:4194304','retained load targets 2 GiB')]
 for name,file,old,new,why in faults:
  m=out/'controls'/name;shutil.copytree(probe,m,ignore=shutil.ignore_patterns('installed','execution.json','execution.log','*.command.json'))
  if name=='old-surrogate-guard':shutil.copy(e/PARENT/'execution/symbols.wasm',m/'symbols.wasm')
  elif name=='missing-existing-keyword':save(m/file,read(inherited/'initial-keywords.json'))
  else:
   text=(BASE/file if file.endswith('.wat') else probe/file).read_text();(m/file).write_text(replace(text,old,new))
   if file.endswith('.wat'):command(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions',m/file,'-o',m/'adapter.wasm'],m/'build.log')
  try:command([prior.NODE,m/'check.mjs',m,m/'execution.json'],m/'execution.log')
  except subprocess.CalledProcessError:
   assert why in (m/'execution.log').read_text(),(name,(m/'execution.log').read_text()[-2500:])
  else:raise AssertionError(name+' escaped')
  controls.append(dict(name=name,status='REJECTED',diagnostic=why))
 for name,edit,why in [
  ('omit-form',lambda d:d['rows'][1]['directedRows'][0]['make'].pop(),'six MAKE forms'),
  ('omit-keyword',lambda d:d['rows'][0]['directedRows'][0].__setitem__('keyword',[]),'existing keyword'),
  ('omit-character',lambda d:d['rows'][0]['directedRows'][0]['characters'].pop(),'character contract'),
  ('omit-high-load',lambda d:d['rows'][0]['loads'][0].__setitem__('to',8388608),'high load'),
  ('omit-after',lambda d:d['rows'][0]['directedRows'].pop(),'both phases'),
  ('omit-delivery',lambda d:d['rows'][1]['directedRows'][0]['make'][4]['delivery'].__setitem__('direct_calls',0),'MAKE delivery')]:
  d=copy.deepcopy(report);edit(d)
  try:assess(d,native)
  except AssertionError as ex:assert str(ex)==why
  else:raise AssertionError(name+' escaped')
  controls.append(dict(name=name,status='REJECTED',diagnostic=why))
 save(out/'controls.json',controls)
 summary=dict(status='PASS',kind='AUXILIARY_SYMBOLS_REVIEW_FOLLOWUP',inherited=read(inherited/'summary.json'),directed=assessment,controls=len(controls),service_change='Reject surrogate UTF-32 words in the existing string guard; native CODE-CHAR returns NIL.',compiler_and_adapter='BYTE_IDENTICAL_TO_REVIEWED_R1')
 save(out/'summary.json',summary)
 for n,h in pins.items():assert sha(ROOT/n)==h,n
 print(json.dumps(summary,indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--output',type=Path,required=True);v=a.parse_args();run(v.evidence.resolve(),v.output.resolve())
