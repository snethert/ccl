"""Apply source-qualified constructor return paths to the original call sites."""
from functools import partial
from pathlib import Path
import argparse,traceback
from run import read,save,convert,require,load_module,ROOT,integrate
from lexical_run import collect
from constructors import Resolver,model,native_model,controls,shape
from test_lexical import selected


def check_native(raw):
    ops={r['id']:r['name'] for r in raw['snapshot']['operators']};m=native_model(raw)
    expected={'constant-nil':{'FALSE'},'constant-true':{'TRUE'},'constant-conditional':{'FALSE','TRUE'},
              'constant-number':None,'constant-argument':None,'constructor-shadow':None}
    seen=set();results=[]
    for c in raw['captures']:
        name=c['case']
        if name=='constructor-source':continue
        require(name in expected and name not in seen,'CONSTRUCTOR_PROBE_POPULATION');seen.add(name)
        rows=selected(convert(c,ops),partial(Resolver,constructor=m));require(rows,'CONSTRUCTOR_MISSING_CALL')
        wanted=expected[name]
        for r in rows:
            if wanted is None:require(r['status']=='UNRESOLVED','CONSTRUCTOR_UNQUALIFIED_PATH')
            else:
                require(r['status']=='FINITE_EXPRESSION' and all(t['mode']=='captured-function-cell-value' for t in r['targets'])
                    and {m['providers'][n]['id'] for n in wanted}=={t['id'] for t in r['targets']},'CONSTRUCTOR_PROVIDER_SET')
        results.append(dict(case=name,status='PASS'))
    require(seen==expected.keys(),'CONSTRUCTOR_PROBE_COVERAGE')
    return results


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    raw=read(a.native/'native.json');tests=check_native(raw)
    sample=next(iter(read(a.evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))
    ops={int(k):v for k,v in sample['operators'].items()}
    original=read(a.provider_ir)
    definitions=[f for f in read(a.evidence/'2026-09-14-build-flow-r1/functions.json.gz')
                 if f['name']=='COMMON-LISP::CONSTANTLY']
    require(len(definitions)==1 and definitions[0]['event']==original['sequence']
        and definitions[0]['function_id']==original['payload']['function']['function_id'], 'CONSTRUCTOR_BUILD_IDENTITY')
    m=model(original,raw,convert,ops);tests+=controls(original,raw,convert,ops)
    # A compiled DEFUN need not have been installed. Join the actual resident
    # provider through its previously qualified executable-body correspondence.
    histories=read(a.evidence/'2026-09-14-binding-versions-r1/histories.json.gz')
    history=next(h for h in histories if h['symbol_id']==m['constructor']['id'])
    body_input=read(a.bodies/'body-correspondences.json.gz')
    matches={b['bootstrap_code']:b for b in body_input['matches']+body_input['support_matches']}
    correlated=read(a.correlated_ir)
    require(shape(convert(correlated['payload'],ops))==m['source_ir'],'CONSTRUCTOR_RESIDENT_IR')
    provider_bodies=[]
    for code in history['ordinary_codes']:
        b=matches.get(code)
        require(b and not b.get('candidate_only') and not b.get('data_dependencies')
            and not b.get('function_literal_correspondences'),'CONSTRUCTOR_RESIDENT_BODY')
        records=[r for r in b['compiler_records'] if r['before']['event']==correlated['sequence']
            and r['afunc']==correlated['payload']['function']['function_id']]
        require(records,'CONSTRUCTOR_RESIDENT_BODY_EVENT')
        provider_bodies.append(dict(code=code,correspondence=b))
    require(provider_bodies and not history['macro_expander_codes'],'CONSTRUCTOR_PROVIDER_POPULATION')
    m['observed_provider_bodies']=provider_bodies
    calls=read(a.evidence/'2026-09-14-build-flow-r1/calls.json.gz')
    wanted={(r['function_id'],r['site_id']):r for r in calls
        if r['dependency']['category'] in ('function-variable','computed-callee') and not r.get('lexical_bound',{}).get('targets')}
    old={(r['function_id'],r['site_id']):r for r in read(a.finite/'proofs.json.gz')}
    for r in read(a.lookups/'preserved-bounds.json.gz'):
        old[r['function_id'],r['site_id']]=dict(r,status='FINITE_EXPRESSION')
    old.update({(r['function_id'],r['site_id']):r for r in read(a.lookups/'proofs.json.gz')})
    require(old.keys()==wanted.keys(),'CONSTRUCTOR_ORIGINAL_POPULATION')
    proofs,preserved,families=collect(a.finite/'selected-ir.jsonl.gz',wanted,old,ops,partial(Resolver,constructor=m))
    base=read(a.base);delta=integrate.patch(base,proofs,histories);graph=integrate.apply(base,delta)
    integrate.check(base,graph,delta,proofs,histories)
    tests+=integrate.controls(base,graph,delta,proofs,histories)
    errors=load_module('constructor_contract',ROOT/'doc/WASM/tools/check-census.py').validate(graph)
    require(all(e.startswith(('unresolved reachable edge from ','unimplemented reachable node ')) for e in errors),
        'CONSTRUCTOR_GRAPH_STRUCTURE')
    remaining=[r for r in proofs if r['status']=='UNRESOLVED']
    for name,value in [('proofs.json.gz',proofs),('preserved-bounds.json.gz',preserved),('remaining-calls.json.gz',remaining),
                       ('delta.json.gz',delta),('census.json.gz',graph),('controls.json',tests),('constructor.json',m)]:save(a.output/name,value)
    summary=dict(status='PASS',census_status='BLOCKED',new_bounds=len(proofs)-len(remaining),
        preserved_bounds=len(preserved),remaining_computed_calls=len(remaining),compiler_families=families,
        source_controls=4,native_probes=6,copy_path_qualified=False,cell_contents_qualified=False)
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('native','provider-ir','correlated-ir','bodies','finite','lookups','base','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
