"""Join finite function-name lookups without closing their cell-value gaps."""
from pathlib import Path
import argparse
from run import read,save,convert,require,load_module,ROOT,integrate
from lexical_run import collect
from lookups import Resolver
from test_lookups import check


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    checks=check(read(a.native),convert)
    calls=read(a.evidence/'2026-09-14-build-flow-r1/calls.json.gz')
    wanted={(r['function_id'],r['site_id']):r for r in calls
            if r['dependency']['category'] in ('function-variable','computed-callee')
            and not r.get('lexical_bound',{}).get('targets')}
    old={(r['function_id'],r['site_id']):r for r in read(a.finite/'proofs.json.gz')}
    old.update({(r['function_id'],r['site_id']):r for r in read(a.lexical/'proofs.json.gz')})
    require(old.keys()==wanted.keys(),'LOOKUP_ORIGINAL_POPULATION')
    sample=next(iter(read(a.evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))
    ops={int(k):v for k,v in sample['operators'].items()}
    proofs,preserved,families=collect(a.finite/'selected-ir.jsonl.gz',wanted,old,ops,Resolver)
    histories=read(a.evidence/'2026-09-14-binding-versions-r1/histories.json.gz')
    base=read(a.base);delta=integrate.patch(base,proofs,histories);graph=integrate.apply(base,delta)
    integrate.check(base,graph,delta,proofs,histories)
    checks['integration']=integrate.controls(base,graph,delta,proofs,histories)
    errors=load_module('lookup_contract',ROOT/'doc/WASM/tools/check-census.py').validate(graph)
    require(all(e.startswith(('unresolved reachable edge from ','unimplemented reachable node ')) for e in errors),
            'LOOKUP_GRAPH_STRUCTURE')
    remaining=[r for r in proofs if r['status']=='UNRESOLVED']
    for name,value in [('proofs.json.gz',proofs),('preserved-bounds.json.gz',preserved),
                       ('remaining-calls.json.gz',remaining),('delta.json.gz',delta),
                       ('census.json.gz',graph),('controls.json',checks)]:save(a.output/name,value)
    summary=dict(status='PASS',census_status='BLOCKED',native_probes=checks['native_probes'],
        compiler_families=families,preserved_bounds=len(preserved),new_bounds=len(proofs)-len(remaining),
        remaining_computed_calls=len(remaining),cell_contents_qualified=False)
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native','finite','lexical','base','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        import traceback
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
