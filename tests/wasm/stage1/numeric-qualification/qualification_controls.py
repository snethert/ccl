"""Semantic and publication controls; original execution stays immutable."""
import copy,json,shutil,subprocess
from pathlib import Path
from ll16_driver import ROOT,BASE,read,save,command,execute
from assess import check

def run(e,out):
 d=out/'generated';data=[read(d/'cases.json'),read(out/'integer-oracle.json'),read(d/'native.json'),read(d/'eager.json'),read(d/'cold.json')];rows=[]
 edits=[('failed-execution',lambda x:(x[3].update(status='FAIL'),x[4].update(status='FAIL'))),('missing-input',lambda x:x[0].pop()),('missing-oracle',lambda x:x[1].pop()),('missing-native',lambda x:x[2].pop()),('missing-execution',lambda x:x[3]['rows'].pop(0)),('wrong-generated-result',lambda x:x[3]['rows'][0]['values'].append('42')),('different-cold',lambda x:x[4].update(status='FAIL')),('missing-native-policy',lambda x:x[0].__setitem__(5000,dict(x[0][5000],function='q0_add')))]
 for name,edit in edits:
  bad=copy.deepcopy(data);edit(bad)
  try:check(*bad)
  except AssertionError as ex:rows.append(dict(name=name,status='REJECTED',diagnostic=str(ex)))
  else:raise AssertionError(name+' escaped')
 # Re-run focused real cases with damaged compiled code, keeping the same
 # native observations. Mutations change executable WAT, not expectations.
 for name,module,old,new in [
  ('integer-operation','q1_add','(call $integer (i32.const 0)','(call $integer (i32.const 1)'),
  ('shift-operation','q1_ash','(call $integer (i32.const 3)','(call $integer (i32.const 4)'),
  ('two-result-operation','q1_truncate','(call $integer (i32.const 5)','(call $integer (i32.const 2)'),
  ('floating-operation','f_add','(call $float_slow (i32.const 0)','(call $float_slow (i32.const 1)')]:
  p=out/'faults'/name;p.mkdir(parents=True)
  original=(d/'compiled'/(module+'.wat')).read_text();assert original.count(old)==1,(name,original.count(old))
  (p/(module+'.wat')).write_text(original.replace(old,new))
  command(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',p/(module+'.wat'),'-o',p/(module+'.wasm')],p/'assemble.log')
  target=d/'compiled'/(module+'.wasm');before=target.read_bytes();script=d/'execute.mjs';saved=script.read_text()
  try:
   target.write_bytes((p/(module+'.wasm')).read_bytes())
   script.write_text(saved.replace("native=read('native.json')", "native=read('native.json').filter(c=>c.function==="+json.dumps(module)+")"))
   try:execute(e,d,'fault')
   except subprocess.CalledProcessError as ex:
    log=(d/'fault.log').read_text();assert 'AssertionError' in log and module+'/' in log,(name,log[-1000:])
    rows.append(dict(name=name,status='REJECTED',module=module,returncode=ex.returncode))
   else:raise AssertionError(name+' escaped')
   shutil.copy(d/'fault.log',p/'execution.log');shutil.copy(d/'fault.command.json',p/'execution.command.json')
  finally:target.write_bytes(before);script.write_text(saved)
 # Table poisoning exercises fallback independence with every ordinary value
 # row of the six numeric primitives. A semantic callback would throw, rather
 # than being hidden by a fuel bound or depth counter.
 s=(d/'execute.mjs').read_text();a=' for(const c of native){';assert s.count(a)==1
 s=s.replace(a," for(let i=1;i<table.length;i++){table.set(i,null);tail_table.set(i,null);}\n"+a)
 old="native=read('native.json')";assert s.count(old)==1
 s=s.replace(old,old+".filter(c=>c.function.startsWith('q')&&!(c.family==='truncate'&&c.args[1]==='0'))")
 # The reduced native population makes each report's case count exact; the
 # independent join below requires every selected id at all four settings.
 p=out/'poison';p.mkdir();shutil.copytree(d,p/'generated',ignore=shutil.ignore_patterns('driver','source','proposal','*.log','*.command.json','eager.json','cold.json'))
 (p/'generated/execute.mjs').write_text(s);execute(e,p/'generated','poison')
 got=read(p/'generated/poison.json');actual={(r['high'],r['collect'],r['id']) for r in got['rows'] if 'id' in r};native=read(d/'native.json')
 want={(h,c,r['id']) for h in [False,True] for c in [False,True] for r in native if r['function'].startswith('q') and not (r.get('family')=='truncate' and r['args'][1]=='0')}
 assert actual==want and actual,'poisoned dispatch membership'
 assert all(r['cases']==len(want)//4 for r in got['rows'] if 'cases' in r),'poisoned case counts'
 save(out/'fallback-execution.json',dict(status='PASS',comparisons=len(actual),generated_table_entries='all null',selected_ids=sorted({i for h,c,i in actual})))
 rows.append(dict(name='poisoned-generated-dispatch',status='PASS',comparisons=len(actual)))
 save(out/'controls.json',rows)
