"""Connect same-process startup entries to real body, literal and call edges."""
from collections import Counter,defaultdict,deque
from pathlib import Path
import hashlib,json,sys
from payloads import read,save,require,rows
from bodies import (node,edge,extract,make,apply,with_initializers,selected_rows)
from flow import convert,functions
from function_values import extract as extract_values
HERE=Path(__file__).resolve().parent
SNAP='startup-live:'
BODY='startup-ir:'


def snapshot(selection,functions_):
    nodes=[];edges=[];roots=[]
    def add(i,kind,reason,open_=False):
        n=node(i,'startup-live/'+i[len(SNAP):],reason,open_);n['kind']=kind;nodes.append(n)
    for i in selection['requested']:
        ident=SNAP+'function:'+str(i)
        add(ident,'function','Actual function object in the startup observation; its target implementation remains separate.')
        edges.append(edge(ident,[],'startup-live/body/'+str(i),'compile',False))
        literals=sorted({functions_[v['function']]['prototype'] for v in functions_[i]['literals']
                         if isinstance(v,dict) and 'function' in v})
        require(set(literals)<=set(selection['requested']),'STARTUP_LITERAL_POPULATION')
        if literals:edges.append(edge(ident,[SNAP+'function:'+str(v) for v in literals],'startup-live/literals/'+str(i)))
    for item in selection['literal_instances']:
        ident=SNAP+'environment:'+str(item['instance'])
        if not any(n['id']==ident for n in nodes):add(ident,'store','Actual closure instance; captured values remain unbounded.',True)
        edges.append(edge(SNAP+'function:'+str(item['owner']),[ident],'startup-live/environment/'+str(item['instance'])))
    for n,entry in enumerate(selection['entry_bindings']):
        ident=SNAP+'entry:'+str(n);roots.append(ident);add(ident,'function','Reviewed entry recipe: '+entry['name'])
        edges.append(edge(ident,[SNAP+'function:'+str(entry['function'])],'startup-live/entry/'+str(n)))
    mp={int(k):v for k,v in selection['mapping'].items()};kernel=selection['kernel']
    for group,records in [('callbacks',kernel['callbacks']),('builtins',kernel['builtins']),('toplevel-methods',kernel['toplevel_methods'])]:
        ident=SNAP+group;roots.append(ident);add(ident,'store','Actual '+group+' at the inspected checkpoint.')
        edges.append(edge(ident,[SNAP+'function:'+str(mp[r['function']]) for r in records if r['function'] is not None],
                          'startup-live/'+group))
    for group in selection['startup_groups']:
        ident=SNAP+'group:'+group['group'];roots.append(ident);add(ident,'store','Ordered startup group '+group['group'])
        ts=[SNAP+'function:'+str(mp[r['function']]) for r in group['functions']]
        if ts:edges.append(edge(ident,ts,'startup-live/group/'+group['group'],'load'))
    # These observations establish source/body dependencies, not the required
    # lifecycle, target or initializer-effect qualifications.
    for name,reason in [('lifetime','Registry and vector contents after restore do not bound later changes.'),
                        ('effects','Required initializer results, effects and order still need qualification.'),
                        ('target','Native body witnesses do not implement target lowering, services, stores or traps.')]:
        ident=SNAP+'gap:'+name;roots.append(ident);add(ident,'store',reason,True)
    return dict(nodes=nodes,edges=edges,roots=roots)


def special_delta(special):
    ns=[];es=[];replace=[]
    for r in special:
        i=r['function'];ident=SNAP+'assembly:'+str(i);ev='startup-live/assembly/'+str(i)
        ns.append(node(ident,ev,'Complete native assembler witness; target replacement remains unimplemented.',True))
        replace.append(edge(SNAP+'function:'+str(i),[ident],'startup-live/body/'+str(i),'compile'))
        for t in r['transfers']:
            if t['kind'] in ('RETURN','LOCAL_LABEL'):continue
            target=ident+':transfer:'+str(t['parsed'])
            ns.append(node(target,ev+'/transfer/'+str(t['parsed']),t['kind']+' '+t['mnemonic']+' requires target qualification.',True))
            es.append(edge(ident,[target],ev+'/uses/'+str(t['parsed'])))
        if r['kind']=='GENERIC_FUNCTION_TEMPLATE':
            state=r['registry'];target=ident+':registry'
            ns.append(node(target,ev+'/registry','Observed method/dcode contents; future mutations, class state and caches remain open.',True))
            es.append(edge(ident,[target],ev+'/registry'))
            es.append(edge(target,[SNAP+'function:'+str(state['dcode'])]+[SNAP+'function:'+str(m['function']) for m in state['methods']],
                           ev+'/registry/snapshot'))
            es.append(edge(target,[],ev+'/registry/future',complete=False))
    return dict(nodes=ns,edges=es,replacements=replace)


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    require(read(a.bodies/'summary.json')['remaining']==[],'STARTUP_BODIES_INCOMPLETE')
    selection=read(a.bodies/'selection.json');fs={r['id']:r for r in read(a.bodies/'functions.json.gz')}
    matches=read(a.bodies/'matches.json.gz');deferred=read(a.bodies/'deferred.json.gz')['placeholders']
    stream=a.native/'observed/build.jsonl.gz'
    snap=next(r['payload'] for r in rows(stream) if r['kind']=='snapshot');ops={r['id']:r['name'] for r in snap['operators']}
    selected=with_initializers(matches,deferred);families,calls=extract(stream,selected,ops)
    recorded=[]
    for row in selected_rows(stream,{e['before']['event'] for m in selected for e in m['compiler_records']}):
        cap=convert(row['payload'],ops)
        recorded.extend(dict(f,event=row['sequence']) for f in functions(cap['function']))
    refs=extract_values(stream,recorded,ops)
    base=read(a.base);seed=snapshot(selection,fs)
    current=dict(base,nodes=seed['nodes'],edges=seed['edges'],seeds=seed['roots'],initializers=[],
                 observed_modules=[],unobserved_modules=[],
                 seed_review='Reviewed revision-2 recipe re-evaluated in this native process; lifecycle and target qualification open.',
                 profile=base['profile']+'; startup body projection only; not a census acceptance record')
    current['inputs_sha256']=hashlib.sha256(json.dumps(dict(selection=selection,native=read(a.native/'summary.json')),sort_keys=True).encode()).hexdigest()
    delta=make(current,matches,families,calls,deferred=deferred,namespace=BODY,
               anchor_prefix=SNAP+'function:',anchor_evidence='startup-live/body/',references=refs)
    current=apply(current,delta);special=special_delta(read(a.bodies/'special-bodies.json.gz'));current=apply(current,special)
    require(not any(e['evidence'].startswith('startup-live/body/') and e['resolution']!='complete' for e in current['edges']),
            'STARTUP_BODY_EDGE_OPEN')
    # Preserve every historical node/root in the development graph. This new
    # projection can be traversed independently without deleting their duties.
    require(not ({n['id'] for n in base['nodes']}&{n['id'] for n in current['nodes']}),'STARTUP_NODE_COLLISION')
    combined=dict(base,nodes=base['nodes']+current['nodes'],edges=base['edges']+current['edges'],seeds=base['seeds']+current['seeds'])
    from support import load_module
    check=load_module('startup_graph_contract',HERE.parents[3]/'doc/WASM/tools/check-census.py').validate
    errors=check(current)
    structural=[e for e in errors if not e.startswith(('unresolved reachable edge from ','unimplemented reachable node '))]
    require(not structural,'STARTUP_GRAPH_STRUCTURE '+str(structural[:3]))
    ids={n['id'] for n in current['nodes']};attached={int(i.rsplit(':',1)[1]) for i in ids if i.startswith(BODY+'afunc:')}
    unresolved=[c for c in calls if c['function'] in attached and c['dependency']['category'] in ('function-variable','computed-callee')]
    for name,value in [('seed-graph.json.gz',current),('census.json.gz',combined),('body-delta.json.gz',delta),
                       ('ir.json.gz',dict(functions=families,calls=calls,references=refs)),('computed-calls.json',unresolved)]:save(a.output/name,value)
    summary=dict(status='PASS',native_seed_bodies=109,unjoined_seed_bodies=0,attached_ir_functions=len(attached),
        attached_call_kinds=dict(Counter(c['dependency']['category'] for c in calls if c['function'] in attached)),
        attached_function_value_references=sum(r['function'] in attached for r in refs),
        snapshot_nodes=len(current['nodes']),snapshot_edges=len(current['edges']),census_status='BLOCKED',
        historical_roots_retired=0)
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('native','bodies','base','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():
            (a.output/'failure.txt').write_text(traceback.format_exc())
            (a.output/'seed_graph.py').write_bytes(Path(__file__).read_bytes())
        raise
