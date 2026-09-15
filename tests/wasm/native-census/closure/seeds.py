"""Revision-2 seeds retain their own inspected-object namespace and open bridges."""
from collections import deque
import hashlib
from support import canonical,require

PREFIX='seed-v2:'
TESTS=['S0-LL15-b','S0-LL15-c']

def function(i): return PREFIX+'function:'+str(i)

def node(i,kind,evidence,reason,open_=False):
    return dict(id=i,kind=kind,required=True,disposition='unresolved' if open_ else 'implemented',
                implementation=None if open_ else 'Recorded native snapshot identity, not a qualified target implementation',
                evidence=evidence,reason=reason,tests=TESTS)

def edge(owner,targets,phase,evidence,complete=True):
    return dict(from_=owner,targets=targets,phase=phase,origin='observed' if complete else 'conservative',
                resolution='complete' if complete else 'unresolved',evidence=evidence)

def make(v,pins,tools):
    spec=v['seeds'];image=v['seed_image'];candidate=v['seed_candidates']
    require(spec['version']==2 and spec['review_disposition']=='REVIEWED_APPROVED','SEED_REVIEW')
    require(candidate['seed_revision']==spec['revision'],'SEED_REVISION')
    kernel=tools['candidates'].kernel_inputs(image,spec)
    functions={r['id']:r for r in image['functions']}
    require(len(functions)==len(image['functions']),'SEED_FUNCTION_IDS')
    joined=[];roots=[];nodes=[];edges=[]
    for entry in spec['entrypoints']:
        rows=kernel['callbacks'] if entry['binding_kind']=='callback' else [r for r in image['bindings'] if r['namespace']=='function']
        found=[r for r in rows if r['name']==entry['name']]
        require(len(found)==1 and found[0]['function'] in functions,'SEED_BINDING '+entry['name'])
        joined.append(dict(entry,native_function=found[0]['function']))
        roots.append(function(found[0]['function']))
    require(joined==candidate['seeds'],'SEED_ENTRY_RECORDS')
    require(kernel==candidate['kernel_entries'] and kernel['toplevel_methods']==candidate['method_seeds'],'KERNEL_WITNESS')
    roots += [function(r['function']) for r in kernel['toplevel_methods']]
    required=set(int(r.rsplit(':',1)[1]) for r in roots)
    for field,phase in [('callbacks','load'),('builtins','run')]:
        i=PREFIX+field;roots.append(i)
        nodes.append(node(i,'store','seed-v2/kernel/'+field,canonical(kernel[field])))
        targets=sorted({r['function'] for r in kernel[field] if r['function'] is not None})
        required.update(targets)
        edges.append(edge(i,[function(t) for t in targets],phase,'seed-v2/kernel/'+field))
    require(sorted(required)==candidate['root_functions'],'ROOT_UNION')
    require(candidate['startup_groups']==image['startup_groups'],'STARTUP_GROUPS')
    for index,group in enumerate(image['startup_groups']):
        i=PREFIX+'startup-group:'+str(index);roots.append(i)
        nodes.append(node(i,'store','seed-v2/startup-group/'+str(index),canonical(group)))
        targets=[r['function'] for r in group['functions']];required.update(targets)
        if targets: edges.append(edge(i,[function(t) for t in targets],'load','seed-v2/startup-group/'+str(index)))
    # Traverse only observed function literals from required roots, not the
    # entire resident universe. Each visited body still has an unresolved edge.
    pending=deque(sorted(required));seen=set()
    while pending:
        i=pending.popleft()
        if i in seen:continue
        require(i in functions,'SEED_LITERAL_TARGET');seen.add(i)
        pending.extend(functions[i]['literal_functions'])
    for i in sorted(seen):
        r=functions[i];n=function(i)
        nodes.append(node(n,'function','seed-v2/image/functions/'+str(i),canonical(r)))
        targets=sorted(set(r['literal_functions']))
        if targets:edges.append(edge(n,[function(t) for t in targets],'run','seed-v2/literals/'+str(i)))
        edges.append(edge(n,[],'run','seed-v2/unqualified-body/'+str(i),False))
    gaps={
      'execution-bridge':'Connect this seed inspection to qualified body/effect observations by actual identity witnesses. No alias to native:, boot: or identity:build: is inferred.',
      'vector-lifetime':'Post-restore vectors do not prove image-save equality or a bound on later registrations.',
      'required-effects':'Revision-2 compile/load-time effects need qualified correspondence with the separately observed build and boot initializers.',
      'target-qualification':'The source-wide survey and registry witnesses remain unqualified native observations; required target services, lowering, stores, traps and profile dispositions remain open.',
      'widening':'Historical module membership and execution fan-outs remain. Retaining their roots is conservative, not a qualified revision-2 closure or omission proof.'}
    for name,reason in gaps.items():
        i=PREFIX+'gap:'+name;roots.append(i)
        nodes.append(node(i,'store','seed-v2/gap/'+name,reason,True))
    for e in edges:e['from']=e.pop('from_')
    return dict(version=1,namespace=PREFIX,nodes=nodes,edges=edges,roots=sorted(set(roots)),
                specification=spec,entry_bindings=joined,root_functions=candidate['root_functions'],
                kernel_entries=kernel,startup_groups=image['startup_groups'],
                snapshot_functions=sorted(seen),
                historical_roots_policy='Retain previous roots separately as conservative development roots until execution bridges and widening replacements qualify.',
                inputs={k:pins['inputs'][k]['sha256'] for k in ('seeds','seed_review','seed_image','seed_candidates')})

def apply(base,delta):
    require(not {n['id'] for n in base['nodes']} & {n['id'] for n in delta['nodes']},'SEED_NODE_COLLISION')
    return dict(base,nodes=base['nodes']+delta['nodes'],edges=base['edges']+delta['edges'],
                seeds=base['seeds']+delta['roots'],
                seed_review='Accepted revision-2 specification; execution bridge and historical-root retirement NOT QUALIFIED',
                inputs_sha256=hashlib.sha256(canonical(dict(base=base['inputs_sha256'],seed_inputs=delta['inputs'])).encode()).hexdigest(),
                profile=base['profile']+'; revision-2 seed snapshot in separate namespace; historical roots retained conservatively')

def check(base,graph,delta,expected):
    require(delta==expected,'EXACT_SEED_RECORDS')
    require(graph.keys()==base.keys(),'GRAPH_FIELDS')
    require(graph['seeds']==base['seeds']+expected['roots'],'EXACT_ROOTS')
    n=len(base['nodes']);e=len(base['edges'])
    require(graph['nodes'][:n]==base['nodes'] and graph['nodes'][n:]==expected['nodes'],'EXACT_NODE_RECORDS')
    require(graph['edges'][:e]==base['edges'] and graph['edges'][e:]==expected['edges'],'EXACT_EDGE_RECORDS')
    expected_meta=apply(base,expected)
    for field in graph.keys()-{'nodes','edges','seeds'}:
        require(graph[field]==expected_meta[field],'GRAPH_METADATA '+field)
