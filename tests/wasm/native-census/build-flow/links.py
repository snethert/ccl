"""Add actual build call/code edges without removing any historical widening."""
from collections import Counter, defaultdict, deque
from urllib.parse import quote
from flow import require

SCOPE = 'Native build IR/code identity slice; target qualification and full closure remain open.'
GAP = 'identity:build:gap:build-flow-qualification'


def key(kind, value):
    return 'identity:build:' + kind + ':' + quote(str(value), safe='/@.-_')


def node(ident, evidence, reason, unresolved=False):
    return dict(id=ident, kind='function', disposition='unresolved' if unresolved else 'implemented',
                required=True, implementation=None if unresolved else 'Recorded native build identity',
                evidence=evidence, reason=reason, tests=['S0-LL15-b','S0-LL15-c'])


def edge(owner, targets, evidence, phase='run', complete=True):
    return dict(from_=owner, targets=sorted(set(targets)), phase=phase,
                origin='conservative', resolution='complete' if complete else 'unresolved', evidence=evidence)


def json_edge(e):
    e = dict(e); e['from'] = e.pop('from_'); return e


def call_targets(c):
    d = c['dependency']; bound = c.get('lexical_bound')
    if bound and bound['targets']:
        return [key('afunc', i) for i in bound['targets']], True
    if d['targets'] and all(t['kind'] == 'function' for t in d['targets']):
        return [key('afunc', t['id']) for t in d['targets']], True
    if d['category'] in ('global-binding','builtin'):
        # The callee's binding name/slot is known; its changing callable values
        # still need a bound. A name is not a complete candidate set.
        return [key('flow-binding', t['name']) for t in d['targets']], False
    return [], False


def make(base, fs, calls, base_sha):
    old = {n['id'] for n in base['nodes']}; ns = {}; es = []
    def add(n):
        if n['id'] not in old:
            require(n['id'] not in ns or ns[n['id']] == n, 'NEW_NODE_CONFLICT'); ns[n['id']] = n
    add(node(GAP, 'build-flow/scope', SCOPE, True))
    for f in fs:
        i = f['function_id']; a = key('afunc',i)
        add(node(a, f'build-flow/event/{f["event"]}/afunc/{i}',
                 'Compiler function identity; display name is not an identity join.'))
        es.append(json_edge(edge(a,[GAP],f'build-flow/qualification/{i}')))
        for code in f['emitted']:
            ident = key('code',code['code'])
            add(node(ident, f'build-flow/event/{code["event"]}/code/{code["code"]}',
                     'Materialized callable identity in this build process.'))
            es.append(json_edge(edge(ident,[a],f'build-flow/materialized/{code["code"]}',phase='compile')))
            es.append(json_edge(edge(a,[ident],f'build-flow/emitted/{i}/{code["code"]}',phase='compile')))
        if f['basis'] == 'frontend':
            missing = key('flow-assembly',i)
            add(node(missing,f'build-flow/frontend-only/{i}',
                     'Code existed at front-end return; Lisp pass 2 was bypassed. Native assembly dependencies remain untraversed.',True))
            es.append(json_edge(edge(a,[missing],f'build-flow/assembly-required/{i}',phase='compile')))
    for c in calls:
        for t in c['dependency']['targets']:
            if t['kind'] == 'global-binding':
                add(node(key('flow-binding',t['name']),'build-flow/binding/'+t['name'],
                         'Binding designator observed; callable versions and target profile remain unbounded.',True))
        targets, complete = call_targets(c)
        es.append(json_edge(edge(key('afunc',c['function_id']),targets,
            f'build-flow/call/{c["function_id"]}/{c["site_id"]}',complete=complete)))
    outgoing=defaultdict(set)
    for e in base.get('edges',[])+es:outgoing[e['from']].update(e['targets'])
    reached=set(base['seeds']);pending=deque(reached)
    while pending:
        for target in outgoing[pending.popleft()]-reached:
            reached.add(target);pending.append(target)
    # An observation is not automatically a seed dependency. Keep disconnected
    # bodies in the facts/worklist, instead of creating another module fan-out
    # or marking a required implementation optional just to pass the schema.
    return dict(version=1,base_sha256=base_sha,scope=SCOPE,census_gate_credit=False,
                nodes=[ns[i] for i in sorted(ns) if i in reached],
                edges=[e for e in es if e['from'] in reached],
                unattached_functions=[f['function_id'] for f in fs if key('afunc',f['function_id']) not in reached])


def check(delta, base, fs, calls, base_sha):
    require(set(delta)=={'version','base_sha256','scope','census_gate_credit','nodes','edges','unattached_functions'}
            and delta['version']==1 and delta['base_sha256']==base_sha and delta['scope']==SCOPE
            and delta['census_gate_credit'] is False,'FRAGMENT_SCOPE')
    by_id={n['id']:n for n in delta['nodes']}; base_ids={n['id'] for n in base['nodes']}
    require(len(by_id)==len(delta['nodes']) and not set(by_id)&base_ids,'FRAGMENT_NODE_IDENTITY')
    expected={GAP:node(GAP,'build-flow/scope',SCOPE,True)}
    expected_edges=Counter()
    def want(source,targets,evidence,phase='run',complete=True):
        expected_edges[(source,tuple(sorted(set(targets))),phase,'conservative',
                        'complete' if complete else 'unresolved',evidence)]+=1
    for f in fs:
        ident=f['function_id']; a=key('afunc',ident)
        expected[a]=node(a,f'build-flow/event/{f["event"]}/afunc/{ident}',
                         'Compiler function identity; display name is not an identity join.')
        want(a,[GAP],f'build-flow/qualification/{ident}')
        for code in f['emitted']:
            c=key('code',code['code'])
            expected[c]=node(c,f'build-flow/event/{code["event"]}/code/{code["code"]}',
                             'Materialized callable identity in this build process.')
            want(c,[a],f'build-flow/materialized/{code["code"]}','compile')
            want(a,[c],f'build-flow/emitted/{ident}/{code["code"]}','compile')
        if f['basis']=='frontend':
            g=key('flow-assembly',ident)
            expected[g]=node(g,f'build-flow/frontend-only/{ident}',
                'Code existed at front-end return; Lisp pass 2 was bypassed. Native assembly dependencies remain untraversed.',True)
            want(a,[g],f'build-flow/assembly-required/{ident}','compile')
    for c in calls:
        d=c['dependency']; bound=c.get('lexical_bound'); targets=[]; complete=False
        if bound and bound['targets']:
            targets=[key('afunc',i) for i in bound['targets']]; complete=True
        else:
            for t in d['targets']:
                if t['kind']=='function': targets.append(key('afunc',t['id'])); complete=True
                else:
                    ident=key('flow-binding',t['name']); targets.append(ident)
                    expected[ident]=node(ident,'build-flow/binding/'+t['name'],
                        'Binding designator observed; callable versions and target profile remain unbounded.',True)
        want(key('afunc',c['function_id']),targets,f'build-flow/call/{c["function_id"]}/{c["site_id"]}',complete=complete)
    # Independently compute the fixed point over fact-derived edge tuples and
    # old edges. It determines attachment only, never a claim of dead code.
    all_edges=[(e['from'],e['targets'])for e in base.get('edges',[])]
    all_edges.extend((e[0],e[1])for e in expected_edges)
    reached=set(base['seeds'])
    while True:
        added={t for source,targets in all_edges if source in reached for t in targets}-reached
        if not added:break
        reached.update(added)
    require(delta['unattached_functions']==[f['function_id'] for f in fs if key('afunc',f['function_id']) not in reached],
            'UNATTACHED_FUNCTION_SET')
    expected_edges=Counter({e:n for e,n in expected_edges.items() if e[0] in reached})
    require(by_id=={i:n for i,n in expected.items() if i not in base_ids and i in reached},'FRAGMENT_NODE_RECORDS')
    actual=Counter(); all_ids=base_ids|set(by_id)
    for e in delta['edges']:
        require(set(e)=={'from','targets','phase','origin','resolution','evidence'},'FRAGMENT_EDGE_SHAPE')
        require(e['from'].startswith('identity:build:') and all(t.startswith('identity:build:') for t in e['targets']),
                'CROSS_PROCESS_EDGE')
        require(e['targets']==sorted(set(e['targets'])),'FRAGMENT_TARGET_SET')
        require(e['from'] in all_ids and set(e['targets'])<=all_ids,'FRAGMENT_ENDPOINT')
        actual[(e['from'],tuple(e['targets']),e['phase'],e['origin'],e['resolution'],e['evidence'])]+=1
    require(actual==expected_edges,'FRAGMENT_EDGE_RECORDS')


def apply(base, delta):
    graph=dict(base)
    graph['nodes']=base['nodes']+delta['nodes']; graph['edges']=base['edges']+delta['edges']
    graph['profile']+='; '+SCOPE
    # These are the only mutations. Seeds, scopes, dispositions, initializers,
    # old edges (including every widening) and trace mappings are preserved.
    return graph
