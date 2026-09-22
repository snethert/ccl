from pathlib import Path
import json,sys,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def summarize(out):
 read=lambda p:json.loads(p.read_text())
 native=read(out/'compiled/native.json');execution=read(out/'execution.json')
 excluded={'EQL','FULLTAG','LISPTAG','TYPECODE','ASSQ'}
 def names(rows):return {r['definition'] for r in rows if not r.get('targetOnly') and not r.get('nativeCounterpart') and not r['definition'].startswith('CORE-') and r['definition'] not in excluded}
 with tarfile.open(ROOT.parent/'ccl-evidence/2026-09-22-stage1-bootstrap-funcallable-r1/artifacts.tar.gz') as a:previous=names(json.load(a.extractfile('numeric/compiled/native.json')))
 originals=names(native);assert previous<=originals,sorted(previous-originals)
 non_nil={r['definition'] for r in native if r['definition'] in originals and not r.get('caught') and any(v is not None for v in r['values'])}
 counterparts={r['definition'] for r in native if r.get('nativeCounterpart')}
 assert read(out/'istruct-checks.json')['status']=='PASS'
 summary=dict(status='PASS',original_definitions_executed=len(originals),non_nil_witness=len(non_nil),new_executions=sorted(originals-previous),
   architecture_counterparts=sorted(counterparts),architecture_counterpart_definitions=len(counterparts),
   target_comparisons=sum(r['comparisons'] for r in execution['rows']),keyword_refusals=sum(len(r['keywordMetadata']) for r in execution['rows']),
   scope='Native original definitions and 32-bit destructive single-float definitions checked against 64-bit non-destructive counterparts are separate. Slot-definition getters use projected native fields. A separate class/wrapper graph preserves selected fields and cycles through movement; unobserved class/metaclass fields are omitted, so this is not a complete CLOS image. No method dispatch or READY credit.')
 (out/'numeric-execution.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n');print(json.dumps(summary),flush=True)
if __name__=='__main__':summarize(Path(sys.argv[1]).resolve())
