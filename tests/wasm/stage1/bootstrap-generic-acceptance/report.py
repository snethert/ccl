"""Recount the fixed cohort without crediting target replacement definitions."""
import collections,json,subprocess,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASE=ROOT.parent/'ccl-evidence/2026-09-21-stage1-bootstrap-recipes-r1/execution'
MACROS={'NUMBER-CASE','%IMAGPART','%REALPART','INVOKE-TYPE-METHOD','WITH-NEGATED-BIGNUM-BUFFERS','WITH-ONE-NEGATED-BIGNUM-BUFFER','WITH-XP-REGISTERS-AND-GPR-OFFSET','HTVEC','HTCOUNT','HTLIMIT','APPLY-KEY','%CHAR-NEEDS-ESCAPE-P','%WRITE-ESCAPED-CHAR'}
NUMERIC={'l0-numbers','l0-float','l0-bignum32','l1-numbers'}
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def source(p):return p.replace('ccl:','').replace(';','/').removesuffix('.newest')
def report(out):
    rows=json.loads((out/'results.json').read_text())
    old=json.loads((BASE/'compiled/worklist-throughput.json').read_text())['functions']
    previous=json.loads((ROOT.parent/'ccl-evidence/2026-09-22-stage1-bootstrap-dispatch-acceptance/recount/results.json').read_text())
    baseline={(source(row['file']),d['name']):d for row in previous for d in row['definitions']}
    before={(r['file'],r['name']):baseline.get((r['file'],r['name']),dict(name=r['name'],outcome='TARGET-EXCLUDED')) for r in old}
    assert len(before)==len(old)
    by_key={};records={}
    for row in rows:
        for d in row['definitions']:
            key=(source(row['file']),d['name']);assert key not in by_key,key
            by_key[key]=d
        for r in row['records']:
            if r['definition'] is not None:records[(source(row['file']),r['name'])]=r
            assert not MACROS.intersection(r['dependencies']),(row['file'],r['name'])
    exclusions=json.loads((HERE.parent/'bootstrap-lexpr-spread/exclusions.json').read_text())
    excluded={(f,n.upper()) for f,names in exclusions.items() for n in names}
    absent=before.keys()-by_key.keys()
    replaced={('level-1/l1-clos-boot.lisp','COMPUTE-DCODE'):
              'level-0/WASM32/w32-prims.lisp'}
    assert absent<=excluded|replaced.keys(),sorted(absent-excluded-replaced.keys())
    assert replaced.keys()<=absent, 'replacement no longer excluded at original site'
    for (name,symbol),replacement in replaced.items():
        assert '#-wasm32-target\n(defun '+symbol.lower() in (ROOT/name).read_text()
        assert '(defun '+symbol.lower() in (ROOT/replacement).read_text()
        assert (replacement,symbol) in by_key, 'target replacement missing from file records'
    save(out/'target-replacements.json',[
        dict(file=k[0],name=k[1],replacement=replaced[k],previous=before[k]['outcome'],
             outcome='TARGET-REPLACED',original_definition_credit=False)
        for k in sorted(replaced)])
    # Keep the historical cohort fixed. Withdrawn native entries gain no credit.
    for k in absent:
        by_key[k]=dict(name=k[1],outcome='TARGET-REPLACED' if k in replaced else 'TARGET-EXCLUDED')
        records[k]=dict(message='Original native dcode construction replaced by target Lisp; no original-definition credit.'
                       if k in replaced else 'Native pointer/FFI entry excluded; callers remain explicit dependencies.')
    save(out/'target-exclusions.json',[dict(file=k[0],name=k[1],previous=before[k]['outcome']) for k in sorted(absent)])
    assert before.keys()<=by_key.keys(), sorted(before.keys()-by_key.keys())
    changes=[dict(file=k[0],name=k[1],before=v['outcome'],after=by_key[k]['outcome'],message=records[k]['message']) for k,v in before.items() if v['outcome'].upper()!=by_key[k]['outcome']]
    save(out/'cohort-changes.json',changes)
    diagnostic=json.loads((BASE/'compiled/throughput.json').read_text())['functions']
    suspects=[r for r in diagnostic if r['proposal']=='admitted' and any(c[1] in MACROS for c in r['callees'])]
    fixes=[]
    for r in suspects:
        k=(r['file'],r['name'])
        actual=records.get(k)
        fixes.append(dict(file=k[0],name=k[1],fake_callees=sorted({c[1] for c in r['callees']} & MACROS),outcome=actual['outcome'] if actual else 'TARGET-EXCLUDED',message=actual['message'] if actual else 'Outside the target file list or excluded by its target reader conditional',macros=actual['macros'] if actual else []))
    assert len(fixes)==57 and sum(x['outcome']=='TARGET-EXCLUDED' for x in fixes)==6
    save(out/'audit156-cohort.json',fixes)
    numeric={};assembled=[]
    for row in rows:
        name=Path(source(row['file'])).stem
        if name not in NUMERIC:continue
        assert row['complete'],row
        directory=out/'files'/name
        for wat in sorted(directory.glob('*.wat')):
            with wat.with_suffix('.wabt.log').open('w') as log:
                subprocess.run(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',str(wat),'-o',str(wat.with_suffix('.wasm'))],check=True,stdout=log,stderr=subprocess.STDOUT)
            assembled.append(str(wat.relative_to(out)))
        numeric[name]=dict(definitions=len(row['definitions']),admitted=sum(d['outcome']=='ADMITTED' for d in row['definitions']),refusals=dict(collections.Counter(d['outcome'] for d in row['definitions'] if d['outcome']!='ADMITTED')))
    extra=[dict(file=k[0],**v) for k,v in by_key.items() if k not in before]
    save(out/'additional-definitions.json',extra)
    summary=dict(status='PASS',new_execution_credit=0,files=len(rows),complete=sum(r['complete'] for r in rows),old_cohort=dict(definitions=len(before),before_admitted=sum(r['outcome']=='ADMITTED' for r in before.values()),admitted=sum(by_key[k]['outcome']=='ADMITTED' for k in before)),all_file_definitions=dict(encountered=len(by_key),admitted=sum(r['outcome']=='ADMITTED' for r in by_key.values()),additional=len(extra),additional_admitted=sum(r['outcome']=='ADMITTED' for r in extra)),numeric=numeric,numeric_assembled_modules=len(assembled),audit156_suspects=len(fixes),refusals=dict(collections.Counter(r['outcome'] for r in by_key.values() if r['outcome']!='ADMITTED')),scope='File compilation is not dependency closure, execution, or a ready image. Keep the historical cohort comparable; macro-generated, compound-name and newly reached definitions are separate. File stops remain explicit. Execution is measured separately. Target replacements earn no original-definition admission credit.')
    save(out/'summary.json',summary)
    print(json.dumps(summary,indent=2),flush=True)
