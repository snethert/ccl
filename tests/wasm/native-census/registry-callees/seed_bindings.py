"""Follow exact initial symbol cells from the connected startup bodies.

The initial value is an observed dependency. A second, unresolved edge retains
all later binding versions; a snapshot never becomes an exhaustive call bound.
"""
from collections import Counter,defaultdict
from pathlib import Path
import hashlib,json
from payloads import read,save,require,rows,correspondences,source_key,dependency_body_key
from nested_bodies import closure,pairs,qualify
from deferred import index as deferred_index
from bodies import extract,with_initializers
from seed_graph import BODY
from registry import state_check
from definition_bodies import anchors
from runtime_bodies import join as runtime_bodies


def initial_bindings(stream,functions):
    result={}
    for row in rows(stream):
        if row['kind']!='resident-binding' or row['payload']['stage']!='before':continue
        raw=row['payload']['binding'];ns={n['id']:n for n in raw['objects']};head=ns[raw['root']['ref']]
        require(head['kind']=='cons' and head['expanded'],'STARTUP_BINDING_HEAD')
        symbol=ns[head['car']['ref']];tail=ns[head['cdr']['ref']]
        require(symbol['kind']=='symbol' and tail['kind']=='cons' and tail['expanded'] and tail['cdr']=={'atom':'nil'},
                'STARTUP_BINDING_SHAPE')
        value=ns.get(tail['car'].get('ref'));sid=symbol['id']
        require(sid not in result,'STARTUP_BINDING_DUPLICATE')
        entry=dict(symbol=symbol,event=row['sequence'],value=value,role='NONCALLABLE_OR_UNCLASSIFIED')
        if value and value['kind']=='function':
            require(value['id'] in functions and value['code']==functions[value['id']]['prototype'],'STARTUP_BINDING_FUNCTION')
            entry.update(role='FUNCTION',object=value['id'],prototype=value['code'])
        result[sid]=entry
    return result


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    fs={r['id']:r for r in read(a.bodies/'functions.json.gz')};em={int(k):v for k,v in read(a.bodies/'emissions.json.gz').items()}
    before={int(k):v for k,v in read(a.bodies/'before.json.gz').items()};deferred=read(a.bodies/'deferred.json.gz')
    selection=read(a.bodies/'selection.json');stream=a.native/'observed/build.jsonl.gz';bindings=initial_bindings(stream,fs)
    # Compute a body relation once for the inspected universe. Traversal below
    # selects only dependencies of the actual roots, never all module members.
    population=closure(fs,{fs[i]['prototype'] for i in selection['mapping'].values()})
    asks=dict(bodies=[dict(code=i,payload_sha256=hashlib.sha256(bytes.fromhex(fs[i]['payload_hex'])).hexdigest())
                     for i in sorted(population) if fs[i]['prototype']==i])
    # A missing source note does not erase an exact named definition. Join
    # the initial symbol cell to the real compiler root before comparing code.
    initial=[dict(kind='resident-binding',stage='before',sequence=b['event'],symbol=b['symbol'],
                  value=dict(role='function',code=b['prototype'])) for b in bindings.values() if b['role']=='FUNCTION']
    unknown={i for i in population if fs[i]['prototype']==i and fs[i]['source'] is None}
    keys={dependency_body_key(fs[i],True) for i in unknown};em_by_afunc=defaultdict(list);definition_events=set()
    for i,es in em.items():
        if dependency_body_key(fs[i],True) not in keys:continue
        for e in es:
            if before[e['afunc']]['parent'] is None:
                em_by_afunc[e['afunc']].append((i,e));definition_events.add(before[e['afunc']]['event'])
    from bodies import selected_rows
    witnesses=anchors(initial,unknown,fs,em_by_afunc,before,list(selected_rows(stream,definition_events)))
    wrappers={r['wrapper'] for r in rows(a.native/'observed/registries.jsonl.gz') if r['kind']=='observer-wrapper'}
    ca,_=correspondences(fs,em,wrappers,asks,before,data_dependencies=True,candidate_function_literals=True,
                         deferred=deferred_index(deferred),definition_witnesses=witnesses)
    # Include the separately qualified callback entry; preserve its witness.
    ca += [r for r in read(a.bodies/'candidates.json.gz') if r.get('callback_witnesses')]
    rel,_=pairs(fs,ca);matches=qualify(fs,ca,rel);matched={m['bootstrap_code']:m for m in matches}
    snap=next(r['payload'] for r in rows(stream) if r['kind']=='snapshot');ops={r['id']:r['name'] for r in snap['operators']}
    selected=with_initializers(matches,deferred['placeholders']);families,calls=extract(stream,selected,ops)
    by_owner=defaultdict(list)
    for r in calls:by_owner[r['function']].append(r)
    # Reference expressions must participate, even when no call is made here.
    from flow import convert,functions as families_of
    from bodies import selected_rows
    from function_values import extract as values
    recorded=[]
    for row in selected_rows(stream,{e['before']['event'] for m in selected for e in m['compiler_records']}):
        cap=convert(row['payload'],ops);recorded.extend(dict(f,event=row['sequence']) for f in families_of(cap['function']))
    refs=values(stream,recorded,ops)
    by_ref=defaultdict(list)
    for r in refs:by_ref[r['function']].append(r)
    body_records=defaultdict(set)
    for m in matches:
        body_records[m['bootstrap_code']].update(e['afunc'] for e in m['compiler_records'])
    deferred_owners=defaultdict(set)
    for r in deferred['placeholders']:
        for f in r['owners']:deferred_owners[f].update(e['afunc'] for e in r['compiler_records'])
    checkpoint=read(a.bodies/'checkpoints.json.gz')[0]
    require(checkpoint['stage']=='before','STARTUP_REGISTRY_PHASE')
    registries={r['gf']:r for r in checkpoint['entries']}
    require(len(registries)==len(checkpoint['entries']),'STARTUP_REGISTRY_DUPLICATE')
    todo=[('function',i) for i in selection['requested']];seen=set();cell_uses=defaultdict(list);reached_calls=[]
    while todo:
        kind,i=todo.pop()
        if (kind,i) in seen:continue
        seen.add((kind,i))
        if kind=='function':
            f=fs[i];todo.extend(('function',fs[v['function']]['prototype']) for v in f['literals'] if isinstance(v,dict) and 'function' in v)
            todo.extend(('afunc',v) for v in body_records[i])
            if i in registries:
                state=registries[i];state_check(state,fs)
                if state['status']=='INITIALIZED':
                    todo.append(('registry',i))
                    todo.extend(('function',fs[m['function']]['prototype']) for m in state['methods'])
        elif kind=='registry':continue
        elif kind=='cell':
            if i in bindings and bindings[i]['role']=='FUNCTION':todo.append(('function',bindings[i]['prototype']))
        else:
            require(kind=='afunc','STARTUP_WALK_KIND');todo.extend(('afunc',v) for v in deferred_owners[i])
            for c in by_owner[i]:
                reached_calls.append(c);d=c['dependency']
                if d['category']=='global-binding':
                    sid=c['symbol']['id'];todo.append(('cell',sid));cell_uses[sid].append(dict(kind='call',function=i,site=c['site'],symbol=c['symbol']))
                elif d['targets'] and all(t['kind']=='function' for t in d['targets']):todo.extend(('afunc',t['id']) for t in d['targets'])
            for r in by_ref[i]:
                if r['kind']=='lexical':todo.append(('afunc',r['target']))
                else:
                    sid=r['symbol']['id'];todo.append(('cell',sid));cell_uses[sid].append(dict(kind='capture',function=i,site=r['site'],symbol=r['symbol']))
    joined=[]
    for sid,uses in sorted(cell_uses.items()):
        b=bindings.get(sid)
        if b:require(all(u['symbol']==b['symbol'] for u in uses),'STARTUP_CELL_DESCRIPTOR')
        joined.append(dict(symbol=sid,uses=uses,initial=b,future_versions='UNRESOLVED'))
    reached={i for k,i in seen if k=='function'};missing=sorted(reached-matched.keys())
    runtime,unjoined_runtime=runtime_bodies(fs,read(a.bodies/'assembly.json.gz'),registries,
        read(a.bodies/'runtime-inputs.json')[0],missing)
    accounted={r['function'] for r in runtime};missing=sorted(set(missing)-accounted)
    missing_rows=[dict(function=i,name=fs[i]['name'],source=source_key(fs[i]['source']),source_start=fs[i]['source_start']) for i in missing]
    for name,value in [('bindings.json.gz',joined),('matches.json.gz',matches),('ir.json.gz',dict(functions=families,calls=calls,references=refs)),
                       ('reached.json.gz',[list(x) for x in sorted(seen)]),('missing-bodies.json',missing_rows),('reached-calls.json.gz',reached_calls)]:save(a.output/name,value)
    save(a.output/'registry-snapshots.json.gz',[registries[i] for k,i in sorted(seen) if k=='registry'])
    save(a.output/'definition-witnesses.json.gz',list(witnesses.values()))
    save(a.output/'runtime-bodies.json.gz',runtime)
    save(a.output/'unjoined-runtime.json',unjoined_runtime)
    units=sorted({r['source'] for r in missing_rows if r['source']})
    save(a.output/'needed-sources.json',units)
    summary=dict(status='PASS',reached_initial_functions=len(reached),reached_ir_functions=sum(k=='afunc' for k,i in seen),
        symbol_cells=len(joined),cells_with_initial_functions=sum(r['initial'] is not None and r['initial']['role']=='FUNCTION' for r in joined),
        functions_with_ir=len(reached&matched.keys()),runtime_bodies=dict(Counter(r['kind'] for r in runtime)),
        missing_body_kinds=dict(Counter('SOURCE' if r['source'] else 'NO_SOURCE' for r in missing_rows)),
        sources_needed=len(units),reached_registries=sum(k=='registry' for k,i in seen),
        call_kinds=dict(Counter(c['dependency']['category'] for c in reached_calls)),
        census_status='BLOCKED',exhaustive_binding_versions=False)
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('native','bodies','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():
            (a.output/'failure.txt').write_text(traceback.format_exc());(a.output/'seed_bindings.py').write_bytes(Path(__file__).read_bytes())
        raise
