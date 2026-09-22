from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parent
out=Path(sys.argv[1]).resolve()
read=lambda p:json.loads(p.read_text())
native=read(out/'compiled/native.json');execution=read(out/'execution.json')
originals={r['definition'] for r in native if not r.get('targetOnly') and not r['definition'].startswith('CORE-') and r['definition'] not in ('EQL','FULLTAG','LISPTAG','TYPECODE','ASSQ')}
non_nil={r['definition'] for r in native if r['definition'] in originals and not r.get('caught') and any(v is not None for v in r['values'])}
previous={n for n in read(HERE/'executed-before.json') if not n.startswith('CORE-') and n not in ('EQL','FULLTAG','LISPTAG','TYPECODE','ASSQ') and n in originals}
new={'%GENERIC-FUNCTION-NAME','%GENERIC-FUNCTION-METHOD-COMBINATION','%GENERIC-FUNCTION-METHOD-CLASS'}
assert originals-previous==new
assert len(originals)==470 and len(non_nil)==439
for name in ['faults','owner-checks','snapshot-checks','owner-regression','istruct-checks']:assert read(out/(name+'.json'))['status']=='PASS'
summary=dict(status='PASS',original_definitions_executed=len(originals),non_nil_witness=len(non_nil),new_executions=sorted(new),funcallable_cases=sum(r['definition'] in new for r in native),target_comparisons=sum(r['comparisons'] for r in execution['rows']),target_layout_checks=sum(len(r['funcallable']) for r in execution['rows']),installer_checks=sum(len(r['installation']) for r in execution['rows']),snapshot_checks=len(read(out/'snapshot-checks.json')['checks']),image_owner_checks=read(out/'owner-checks.json')['checks'],owner_regression_checks=read(out/'owner-regression.json')['checks'],faults_rejected=sum(r['status']=='REJECTED' for r in read(out/'faults.json')['rows']),scope='Callable layout and immediate access, not method selection or a complete CLOS image. Three original accessors execute on projections of real native generic-function slots. Constructors and setters have additional generated movement checks. Newly closed class-cell operations without a real class fixture remain uncredited.')
(out/'numeric-execution.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
print(json.dumps(summary))
