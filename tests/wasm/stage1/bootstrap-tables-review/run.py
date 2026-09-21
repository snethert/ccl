import argparse,hashlib,json,shutil,subprocess,tempfile,sys
from pathlib import Path
from derive import HERE,PARENT,ROOT,policy,check
sys.path.insert(0,str(PARENT));from selection import selection
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def read(p):return json.loads(p.read_text())
def command(args,log,why=None):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:r=subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,timeout=240)
 if why:assert r.returncode and why in log.read_text(),(log,why)
 else:assert r.returncode==0,log

def run(e,out):
 out.mkdir(parents=True);parent=e/'2026-09-20-stage1-bootstrap-tables-r1'
 for n,h in read(parent/'source-pins.json').items():assert sha(ROOT/n)==h,n
 for record in read(parent/'packet.json')['files']:assert sha(parent/record['path'])==record['sha256'],record['path']
 save(out/'selection.json',selection());(out/'policy.mjs').write_text(policy());(out/'check.mjs').write_text(check())
 for n in ['population.mjs','population-check.mjs','admission.mjs','statistics-check.mjs','native.lisp']:shutil.copy(HERE/n,out/n)
 for n in ['hash.wasm','collector.wasm']:shutil.copy(parent/'execution'/n,out/n)
 stats=e/'2026-09-20-stage1-startup-runtime-review-r1'
 manifest=read(stats/'packet.json');source=stats/'execution/execution/service.mjs'
 assert sha(source)==next(r['sha256'] for r in manifest['files'] if r['path']=='execution/execution/service.mjs')
 shutil.copy(source,out/'statistics-service.mjs')
 kernel=e/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=e/'2026-09-16-stage1-1a-r2/native/baseline.image'
 save(out/'inputs.json',{str(p.relative_to(e)):sha(p) for p in [kernel,image,parent/'packet.json',stats/'packet.json']})
 with tempfile.TemporaryDirectory(prefix='ccl-tables-review-') as tmp:
  work=Path(tmp);shutil.copy(kernel,work/'dx86cl64');(work/'dx86cl64').chmod(0o755);shutil.copy(image,work/'dx86cl64.image')
  command([work/'dx86cl64','--no-init','--batch','--load',out/'native.lisp'],out/'native.log')
 tableSites={'%SETF-FUNCTION-NAMES%':'level-1/l1-aprims.lisp:262','%SETF-FUNCTION-NAME-INVERSES%':'level-1/l1-aprims.lisp:263','%LAMBDA-LISTS%':'level-1/l1-utils.lisp:689','*COMBINED-METHODS*':'level-1/l1-dcode.lisp:919'}
 measured=[]
 for line in (out/'native.log').read_text().splitlines():
  if line.startswith('POPULATION '):
   _,name,count,test=line.split();measured.append(dict(name=name,site=tableSites[name],count=int(count),test=test.lower()))
 assert len(measured)==4;assert all(x['count']>64 for x in measured[:3]);assert measured[3]['count']>0 and measured[3]['test']=='equal';save(out/'measured.json',measured)
 assert all('POPULATION-API '+t+' PASS' in (out/'native.log').read_text() for t in ['LIST','ALIST'])
 deps={'closure':'NOT_ESTABLISHED','equal':dict(measured[3],status='BLOCKS_BOOTSTRAP',needs='EQUAL service and wrapper installation; cannot substitute EQ'),'other_tables':'Measure the actual selected image population before owner construction; unmeasured fixture rows are one-entry scenarios, not measured bootstrap capacities.','capacity':'max(source hint, live count + max(16, ceil(live count / 4))), rounded to power of two; refuse >16384 before construction. FULL after installation remains checked status 4, with no write or eviction.','populations':[
  dict(source='level-0/nfasload.lisp',line=1212,name='%system-locks%',disposition='STRONG_SUBSTITUTE_AUTHORIZED'),
  dict(source='level-1/l1-lisp-threads.lisp',line=240,name='thread population',disposition='STRONG_SUBSTITUTE_AUTHORIZED'),
  dict(source='level-1/l1-dcode.lisp',line=392,name='%all-gfs%',disposition='STRONG_SUBSTITUTE_AUTHORIZED'),
  dict(source='lib/misc.lisp',line=710,name='make-population constructor (not proof of a fourth live instance)',disposition='STRONG_SUBSTITUTE_AUTHORIZED')], 'population_installation':'Strong vector/cons proposal, no weak header admitted. Native population accessors and callers must be lowered to this representation before installation. Real lock/thread/GF object scanners remain separate dependencies.'}
 save(out/'dependencies.json',deps)
 node='/usr/local/bin/node'
 for script,name in [('check.mjs','execution'),('admission.mjs','admission'),('population-check.mjs','populations'),('statistics-check.mjs','statistics')]:command([node,out/script,out,out/(name+'.json')],out/(name+'.log'))
 controls=[]
 faults=[('population-count','policy.mjs','capacity!==required','false','capacity-population'),('alignment','policy.mjs','base%8','false','alignment preflight'),('end-bound','policy.mjs','end>memory.buffer.byteLength','false','end-bound preflight'),('service-size','policy.mjs','service.ht_size(capacity)!==bytes','false','Missing expected exception'),('init-status','policy.mjs','service.ht_init(base,end,capacity)!==0','(service.ht_init(base,end,capacity),false)','Missing expected exception'),('weak-validity','policy.mjs',"!['key','value'].includes(site.weak)",'false','Missing expected exception'),('retention-label','policy.mjs',"retention:'keys-and-values'","retention:'keys'",'keys-and-values')]
 for name,file,a,b,why in faults:
  d=out/'faults'/name;d.mkdir(parents=True)
  for n in ['policy.mjs','selection.json','hash.wasm','admission.mjs']:shutil.copy(out/n,d/n)
  s=(d/file).read_text();assert s.count(a)==1,(name,a);(d/file).write_text(s.replace(a,b));command([node,d/'admission.mjs',d,d/'result.json'],d/'rejected.log',why);controls.append(dict(name=name,status='REJECTED',diagnostic=why))
 for name,a,b,why in [('population-policy','policy!==POPULATION_POLICY','false','Missing expected exception'),('population-value','put(cursor,member[1])','put(cursor,NIL)','population live bytes'),('population-type',"type==='list'?0:4","0",'population type')]:
  d=out/'faults'/name;d.mkdir(parents=True)
  for n in ['population.mjs','population-check.mjs','collector.wasm']:shutil.copy(out/n,d/n)
  s=(d/'population.mjs').read_text();assert s.count(a)==1;(d/'population.mjs').write_text(s.replace(a,b));command([node,d/'population-check.mjs',d,d/'result.json'],d/'rejected.log',why);controls.append(dict(name=name,status='REJECTED',diagnostic=why))
 for name,expression in [('omitted-tail','[NIL,NIL]'),('wrong-count','[NIL,NIL,2,0]'),('wrong-rehash','[NIL,NIL,1,1]')]:
  d=out/'faults'/('statistics-'+name);d.mkdir(parents=True);shutil.copy(out/'statistics-check.mjs',d/'statistics-check.mjs')
  source=(out/'statistics-service.mjs').read_text();a='if(!owner.statistics.timingValid){[NIL,NIL,1,0]';assert source.count(a)==1;(d/'statistics-service.mjs').write_text(source.replace(a,'if(!owner.statistics.timingValid){'+expression))
  command([node,d/'statistics-check.mjs',d,d/'result.json'],d/'rejected.log','NIL snapshot publication');controls.append(dict(name='statistics-'+name,status='REJECTED',diagnostic='NIL snapshot publication'))
 save(out/'controls.json',controls);save(out/'tools.json',{node:sha(Path(node))})
 summary=dict(status='PASS',measured=measured,table_collections=read(out/'execution.json')['collections'],population_collections=sum(r['collections'] for r in read(out/'populations.json')['rows']),owner_checks=len(read(out/'admission.json')['checks']),faults=len(controls),slot_credit=False);save(out/'summary.json',summary);print(summary)
 for n,h in read(parent/'source-pins.json').items():assert sha(ROOT/n)==h,n
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a=a.parse_args();run(a.evidence.resolve(),a.output.resolve())
