"""Report executed original definitions separately from target primitives."""
from pathlib import Path
import hashlib,json,sys,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def read(p):return json.loads(p.read_text())
def names(rows):
 return {r['definition'] for r in rows if not r.get('targetOnly') and not r.get('nativeCounterpart') and not r['definition'].startswith('CORE-') and r['definition'] not in {'EQL','FULLTAG','LISPTAG','TYPECODE','ASSQ'}}
def summarize(out,environment,native):
 with tarfile.open(ROOT.parent/'ccl-evidence/2026-09-22-stage1-bootstrap-clos-accessors-r1/artifacts.tar.gz') as a:
  previous=names(json.load(a.extractfile('numeric/compiled/native.json')))
 rows=read(out/'compiled/native.json');originals=names(rows);assert previous<=originals
 executions=read(out/'execution.json')['rows'];assert len(executions)==2
 assert sum(r['comparisons'] for r in executions)==4*len(rows)
 admitted=read(environment/'summary.json')['old_cohort']
 report=read(native/'run.json');assert report['status']=='PASS' and report['registered_tests']['passed']==21843 and report['restored_fasls']==164
 import backend
 for name,text in {backend.BACKEND:backend.generate(),backend.ARCH:backend.arch(),**backend.source_files(ROOT)}.items():
  for directory in [native/'proposal',out/'compiled/proposal',environment/'proposal']:
   assert (directory/'files'/name).read_text()==text,(name,directory)
 for source in HERE.glob('*.lisp'):
  copied=out/'driver'/source.name
  if copied.exists():assert copied.read_bytes()==source.read_bytes(),source.name
 for name in ['check.mjs','bignum-check.mjs']:
  assert (out/name).read_bytes()==(HERE/name).read_bytes(),name
 assert read(out/'istruct-checks.json')['checks']==20
 changed=originals-previous
 dispatch={r['definition'] for r in rows if r['definition'].startswith('CORE-DISPATCH-')}
 assert dispatch=={'CORE-DISPATCH-REBIND','CORE-DISPATCH-EXIT','CORE-DISPATCH-CONTEXT','CORE-DISPATCH-LEXPR-CONTEXT'}
 assert '%%BEFORE-AND-AFTER-COMBINED-METHOD-DCODE' in changed
 assert len([r for r in rows if r['definition']=='%%BEFORE-AND-AFTER-COMBINED-METHOD-DCODE'])==4
 whole=read(out/'compiled/whole-file.json');installed={m['name'] for m in read(out/'compiled/modules.json')}
 proof=[]
 for name in sorted(changed):
  candidates=[r for r in whole if r['name']==name and r['module'] in installed]
  assert len(candidates)==1,(name,candidates)
  proof.append(dict(name=name,file=candidates[0]['file'],module=candidates[0]['module'],cases=sum(r['definition']==name for r in rows)))
 (out/'source-proof.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
 result=dict(status='PASS',original_definitions_executed=len(originals),non_nil_witness=len({r['definition'] for r in rows if r['definition'] in originals and not r.get('caught') and any(v is not None for v in r['values'])}),new_executions=sorted(changed),admitted=admitted['admitted'],denominator=admitted['definitions'],native_rows=len(rows),comparisons=sum(r['comparisons'] for r in executions),bignum_checks=sum(len(r['bignums']) for r in executions),structural_collector_checks=20,collections_during_calls=sum(r['internalCollections'] for r in executions),retry_collections=sum(r['retryCollections'] for r in executions),native_tests=21843,restored_fasls=164,scope='Original Lisp bignum algorithms and before/after method combination execute. Target LAP replacements and dispatch callers receive no original-definition credit. Full CLOS method selection, image initialization and LL15 remain unfinished.')
 (out/'summary.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result))
if __name__=='__main__':summarize(*(Path(x).resolve() for x in sys.argv[1:]))
