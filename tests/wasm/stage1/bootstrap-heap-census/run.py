import argparse,hashlib,json,shutil,subprocess,tempfile,sys,copy
from pathlib import Path
from census import HERE,ROOT,parse,validate,table_check,selection
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log,why=None):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:r=subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,timeout=240)
 if why:assert r.returncode and why in log.read_text(),(log,why)
 else:assert r.returncode==0,log

def run(e,out):
 out.mkdir(parents=True);parent=e/'2026-09-20-stage1-bootstrap-tables-review-r1';base=e/'2026-09-20-stage1-bootstrap-tables-r1'
 for n,h in read(parent/'source-pins.json').items():assert sha(ROOT/n)==h,n
 for r in read(parent/'packet.json')['files']:assert sha(parent/r['path'])==r['sha256'],r['path']
 for n in ['policy.mjs','population.mjs','hash.wasm','collector.wasm']:shutil.copy(parent/'execution'/n,out/n)
 shutil.copy(HERE/'census.lisp',out/'census.lisp');shutil.copy(HERE/'population-check.mjs',out/'population-check.mjs')
 (out/'check.mjs').write_text(table_check((parent/'execution/check.mjs').read_text()))
 kernel=e/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=e/'2026-09-16-stage1-1a-r2/native/baseline.image'
 save(out/'inputs.json',{str(p.relative_to(e)):sha(p) for p in [kernel,image,parent/'packet.json',base/'packet.json']})
 controls=[]
 with tempfile.TemporaryDirectory(prefix='ccl-heap-census-') as tmp:
  p=Path(tmp);shutil.copy(kernel,p/'dx86cl64');(p/'dx86cl64').chmod(0o755);shutil.copy(image,p/'dx86cl64.image')
  command([p/'dx86cl64','--no-init','--batch','--load',out/'census.lisp'],out/'native.log')
  for name,a,b,why in [
   ('omit-non-eq',"(hash-table-weak-p o))", "(hash-table-weak-p o) (eq (hash-table-test o) 'eq))",'Failed assertion'),
   ('omit-empty-populations',"((typep o 'population) (push o populations))","((and (typep o 'population) (population-contents o)) (push o populations))",'Failed assertion'),
   ('wrong-closure-identity',"(capture 'ensure-slot-id 'slot-id-hash)","(global '%documentation)",'Failed assertion')]:
   d=out/'faults'/name;d.mkdir(parents=True);s=(out/'census.lisp').read_text();assert s.count(a)==1;(d/'native.lisp').write_text(s.replace(a,b))
   command([p/'dx86cl64','--no-init','--batch','--load',d/'native.lisp'],d/'rejected.log',why);controls.append(dict(name=name,status='REJECTED',diagnostic=why))
 log=(out/'native.log').read_text();census=parse(log);save(out/'census.json',census);save(out/'census-check.json',validate(census,log))
 lookup={r['id']:r for r in selection()};sites=[];measured=[]
 for row in census['tables']:
  site=dict(lookup[row['site']],id=row['id'],constructor=row['site']);sites.append(site)
  measured.append(dict(site=row['id'],constructor=row['site'],count=row['count'],test=row['test'],owners=row['owners']))
 save(out/'selection.json',sites);save(out/'measured.json',measured)
 deps=dict(closure='NOT_ESTABLISHED',equality=[dict(r,status='BLOCKS_BOOTSTRAP',needs='Equality service and wrapper installation; EQ is not a substitute.') for r in census['tables'] if r['test']!='eq'],populations=[r for r in census['populations'] if r['type']&65536],uninstantiated=census['absent'],remaining='Ordinary population accessors and member scanners still need production integration. Observed counts describe this pinned image, not future image/session capacity.')
 save(out/'dependencies.json',deps)
 node='/usr/local/bin/node'
 command([node,out/'check.mjs',out,out/'execution.json'],out/'execution.log');command([node,out/'population-check.mjs',out,out/'populations.json'],out/'populations.log')
 # Matching summaries cannot make a shortened or misattributed census valid.
 for name,mutate in [
  ('drop-table',lambda c:c['tables'].pop()),('drop-population',lambda c:c['populations'].pop()),
  ('wrong-site',lambda c:c['tables'][0].update(site=c['tables'][1]['site'])),
  ('eql-not-blocking',lambda c:next(r for r in c['tables'] if r['test']=='eql' and r['count']).update(disposition='DEFERRED')),
  ('termination-is-list',lambda c:next(r for r in c['populations'] if r['type']&65536).update(type=0)),
  ('under-count',lambda c:next(r for r in c['tables'] if r['count']>60).update(count=1))]:
  bad=copy.deepcopy(census);mutate(bad);bad['totals']={k:v for k,v in zip(['tables','entries','populations','members'],[len(bad['tables']),sum(r['count'] for r in bad['tables']),len(bad['populations']),sum(r['count'] for r in bad['populations'])])}
  d=out/'faults'/name;d.mkdir(parents=True);save(d/'census.json',bad)
  try:validate(bad,log)
  except AssertionError as error:save(d/'rejected.json',dict(status='REJECTED',diagnostic=str(error)))
  else:raise AssertionError(name+' escaped')
  controls.append(dict(name=name,status='REJECTED',diagnostic='census differs from native capture'))
 for name,a,b,why in [('population-end-bound','end>memory.buffer.byteLength','false','population extent'),('population-padding','put(base+12,0)','put(base+12,37)','population padding')]:
  d=out/'faults'/name;d.mkdir(parents=True)
  for n in ['population.mjs','population-check.mjs','collector.wasm','census.json']:shutil.copy(out/n,d/n)
  s=(d/'population.mjs').read_text();assert s.count(a)==1;(d/'population.mjs').write_text(s.replace(a,b));command([node,d/'population-check.mjs',d,d/'result.json'],d/'rejected.log',why);controls.append(dict(name=name,status='REJECTED',diagnostic=why))
 save(out/'controls.json',controls);save(out/'tools.json',{node:sha(Path(node))})
 summary=dict(status='PASS',**census['totals'],oversized_tables=sum(r['count']>60 for r in census['tables']),eq_tables=sum(r['test']=='eq' for r in census['tables']),table_collections=read(out/'execution.json')['collections'],population_collections=read(out/'populations.json')['collections'],controls=len(controls),slot_credit=False);save(out/'summary.json',summary);print(summary)
 for n,h in read(parent/'source-pins.json').items():assert sha(ROOT/n)==h,n
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a=a.parse_args();run(a.evidence.resolve(),a.output.resolve())
