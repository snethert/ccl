"""Resolve local startup call expressions without borrowing closure environments."""
from collections import Counter
from pathlib import Path
import sys
from payloads import read,save,require,rows
from bodies import selected_rows
from flow import convert
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'finite-callees'))
from lexical import Resolver as LocalResolver
from finite import Unbounded
from seed_graph import BODY


class Resolver(LocalResolver):
    def __init__(self,capture,entries):
        self.entries=entries
        super().__init__(capture)
    def captured(self,var,owner,stack):
        # A resident nested prototype does not carry the freshly compiled
        # enclosing function's values. Keep all such captures open here.
        raise Unbounded('resident-closure-environment-unqualified')
    def parameter(self,var,owner):
        bound=self.parameters[var]
        if any(f in self.entries for f,_ in bound):raise Unbounded('resident-entry-parameter')
        return super().parameter(var,owner)


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    matches=read(a.bodies/'matches.json.gz');entries={e['afunc'] for m in matches for e in m['compiler_records']}
    wanted={(r['function'],r['site']):r for r in read(a.graph/'computed-calls.json')}
    stream=a.native/'observed/build.jsonl.gz';snap=next(r['payload'] for r in rows(stream) if r['kind']=='snapshot')
    ops={r['id']:r['name'] for r in snap['operators']};proofs=[];seen=set()
    for row in selected_rows(stream,{r['event'] for r in wanted.values()}):
        resolver=Resolver(convert(row['payload'],ops),entries)
        for r in resolver.calls():
            key=(r['function_id'],r['site_id'])
            if key not in wanted:continue
            require(key not in seen and wanted[key]['event']==row['sequence'],'SEED_CALL_IDENTITY');seen.add(key)
            r['event']=row['sequence'];proofs.append(r)
    require(seen==wanted.keys(),'SEED_CALL_COVERAGE')
    graph=read(a.graph/'seed-graph.json.gz');combined=read(a.graph/'census.json.gz');ids={n['id'] for n in graph['nodes']}
    replacements={}
    for r in proofs:
        if r['status']!='FINITE_EXPRESSION':continue
        # This first seed pass discharges only local AFUNC selection. Symbol
        # values require their own binding-time and version proof.
        require(all(t['kind']=='afunc' for t in r['targets']),'SEED_CALL_UNJOINED_SYMBOL')
        targets=[BODY+'afunc:'+str(t['id']) for t in r['targets']]
        require(set(targets)<=ids,'SEED_LOCAL_TARGET_NOT_IN_GRAPH')
        ev=f'{BODY.rstrip(":")}/call/{r["function_id"]}/{r["site_id"]}'
        old=[e for e in graph['edges'] if e['evidence']==ev]
        require(len(old)==1 and old[0]['resolution']=='unresolved' and not old[0]['targets'],'SEED_CALL_OLD_EDGE')
        replacements[ev]=dict(old[0],targets=targets,resolution='complete')
    for current in (graph,combined):
        current['edges']=[replacements.get(e['evidence'],e) for e in current['edges']]
    from support import load_module
    errors=load_module('seed_call_contract',HERE.parents[3]/'doc/WASM/tools/check-census.py').validate(graph)
    require(all(e.startswith(('unresolved reachable edge from ','unimplemented reachable node ')) for e in errors),'SEED_CALL_GRAPH')
    for name,value in [('proofs.json',proofs),('seed-graph.json.gz',graph),('census.json.gz',combined)]:save(a.output/name,value)
    summary=dict(status='PASS',startup_indirect_calls=len(proofs),resolved_local_calls=len(replacements),
                 remaining=len(proofs)-len(replacements),reasons=dict(Counter(r['reason'] for r in proofs if r['status']=='UNRESOLVED')),
                 borrowed_capture_bounds=0,census_status='BLOCKED')
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('native','bodies','graph','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():
            (a.output/'failure.txt').write_text(traceback.format_exc());(a.output/'seed_calls.py').write_bytes(Path(__file__).read_bytes())
        raise
