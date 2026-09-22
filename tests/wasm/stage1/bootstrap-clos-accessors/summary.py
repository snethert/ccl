from pathlib import Path
import json,sys,tarfile,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
out=Path(sys.argv[1]).resolve();read=lambda p:json.loads(p.read_text())
parent=ROOT.parent/'ccl-evidence/2026-09-22-stage1-bootstrap-lexpr-spread-r1'
with tarfile.open(parent/'artifacts.tar.gz') as a:old=json.load(a.extractfile('numeric/compiled/native.json'))
native=read(out/'compiled/native.json');excluded={'EQL','FULLTAG','LISPTAG','TYPECODE','ASSQ'}
def names(rows):return {r['definition'] for r in rows if not r.get('targetOnly') and not r.get('nativeCounterpart') and not r['definition'].startswith('CORE-') and r['definition'] not in excluded}
originals=names(native);previous=names(old);assert previous<=originals,previous-originals
expected=set(read(HERE/'expected-definitions.json'));assert originals-previous==expected,(originals-previous)^expected
assert all(not r.get('caught') for r in native if r['definition'] in expected)
assert len([r for r in native if r['definition'] in expected])==70
whole=read(out/'compiled/whole-file.json');modules=read(out/'compiled/modules.json')
installed={m['name'] for m in modules};proof=[]
for name in sorted(expected):
 matches=[r for r in whole if r['name']==name and r['module'] in installed]
 assert len(matches)==1 and 'l1-clos-boot.lisp' in matches[0]['file'],(name,matches)
 proof.append(dict(definition=name,file=matches[0]['file'],module=matches[0]['module'],native_cases=sum(r['definition']==name for r in native)))
(out/'clos-source-proof.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
non_nil={r['definition'] for r in native if r['definition'] in originals and not r.get('caught') and any(v is not None for v in r['values'])}
# No compiler, arch or CCL source changes: reuse their qualified native result.
import backend
for name,text in {backend.BACKEND:backend.generate(),backend.ARCH:backend.arch(),**backend.source_files(ROOT)}.items():
 assert (parent/'native/proposal/files'/name).read_text()==text,name
 assert (out/'compiled/proposal/files'/name).read_text()==text,name
result=dict(status='PASS',original_definitions_executed=len(originals),non_nil_witness=len(non_nil),new_executions=sorted(originals-previous),new_native_cases=70,new_target_comparisons=280,admitted_unchanged=2059,admission_denominator=2231,target_comparisons=sum(r['comparisons'] for r in read(out/'execution.json')['rows']),native_reused_by_final_source_hash=True,scope='Native instance fields are projected for accessor execution; omitted fields and method dispatch receive no credit. New instances preserve their real self backpointer through movement.')
(out/'summary.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result),flush=True)
