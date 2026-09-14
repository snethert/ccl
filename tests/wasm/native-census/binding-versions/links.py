"""One unresolved callable-value edge per actual symbol, retaining every call site."""
from collections import defaultdict
from common import require, SCOPE

PREFIX='identity:build:'


def key(kind,i): return PREFIX+kind+':'+str(i)
def node(ident,evidence,reason,unresolved=False):
    return dict(id=ident,kind='function',disposition='unresolved' if unresolved else 'implemented',
                required=True,implementation=None if unresolved else 'Recorded native build identity',
                evidence=evidence,reason=reason,tests=['S0-LL15-b','S0-LL15-c'])
def edge(owner,targets,evidence,complete=True,phase='run'):
    return {'from':owner,'targets':sorted(set(targets)),'phase':phase,'origin':'conservative',
            'resolution':'complete' if complete else 'unresolved','evidence':evidence}


def make(base,histories,calls):
    ids={n['id'] for n in base['nodes']};hs={h['symbol_id']:h for h in histories}
    expected={};replacements=[];cells=set()
    for c in calls:
        if c['dependency']['category']!='global-binding':continue
        i=c['global_symbol']['id'];cells.add(i)
        ev=f'build-flow/call/{c["function_id"]}/{c["site_id"]}'
        require(ev not in expected,'DUPLICATE_CALL_EVIDENCE')
        # The prior targets are name placeholders, never symbol identity joins.
        from urllib.parse import quote
        targets=[PREFIX+'flow-binding:'+quote(t['name'],safe='/@.-_') for t in c['dependency']['targets']]
        expected[ev]=edge(key('afunc',c['function_id']),targets,ev,False)
        replacements.append(dict(evidence=ev,target=key('binding-cell',i)))
    actual={}
    for e in base['edges']:
        if e['evidence'] in expected:
            require(e['evidence'] not in actual,'DUPLICATE_BASE_CALL');actual[e['evidence']]=e
    require(actual==expected,'BASE_CALL_RECORDS')
    ns={};es=[];code_origins=defaultdict(set);codes=set()
    for i in sorted(cells):
        h=hs[i];cell=key('binding-cell',i)
        require(cell not in ids,'PREEXISTING_BINDING_CELL')
        ns[cell]=node(cell,f'binding-versions/symbol/{i}',h['obligation'],True)
        targets=[key('code',c) for c in h['ordinary_codes']]
        # This remains unresolved even with zero gaps and an ordinary function
        # at both checkpoints: observation cannot bound later redefinition.
        es.append(edge(cell,targets,f'binding-versions/open/{i}',False))
        for o in h['observations']:
            v=o['value']
            if v['role']!='function':continue
            code=v['code'];codes.add(code);origin=v['origin']
            if 'afunc' in origin and key('afunc',origin['afunc']) in ids:
                code_origins[code].add(origin['afunc'])
    for code in sorted(codes):
        ident=key('code',code)
        if ident not in ids:
            ns[ident]=node(ident,f'binding-versions/code/{code}',
                'Observed ordinary function prototype; binding versions and source bodies are separate obligations.')
        targets=[key('afunc',i) for i in sorted(code_origins[code])]
        es.append(edge(ident,targets,f'binding-versions/body/{code}',bool(targets),'compile'))
    # Retire only name-only placeholders whose last incoming call is replaced.
    # Builtin calls keep their placeholders: their snapshot has names/indices,
    # not these exact symbol descriptors. No unrelated node is discarded.
    name_ids={t for e in expected.values() for t in e['targets']}
    still_used=set(base['seeds'])
    for e in base['edges']:
        still_used.add(e['from'])
        if e['evidence'] not in expected:still_used.update(e['targets'])
    removed=sorted(name_ids-still_used)
    return dict(version=1,scope=SCOPE,census_gate_credit=False,replacements=replacements,
                removed_name_nodes=removed,nodes=[ns[k] for k in sorted(ns)],edges=es)


def check(delta,base,histories,calls):
    require(set(delta)=={'version','scope','census_gate_credit','replacements','removed_name_nodes','nodes','edges'}
            and delta['version']==1 and delta['scope']==SCOPE and delta['census_gate_credit'] is False,'PATCH_SCOPE')
    # The expected patch is derived from immutable call identities and the
    # separately checked histories, never from the claimed resulting graph.
    wanted=make(base,histories,calls)
    for field in ('replacements','removed_name_nodes','nodes','edges'):
        require(delta[field]==wanted[field],'PATCH_'+field.upper())


def apply(base,delta):
    replacements={r['evidence']:r['target'] for r in delta['replacements']}
    require(len(replacements)==len(delta['replacements']),'REPLACEMENT_DUPLICATE')
    changed=set();es=[]
    for e in base['edges']:
        if e['evidence'] in replacements:
            require(e['evidence'] not in changed,'BASE_EVIDENCE_DUPLICATE');changed.add(e['evidence'])
            e=dict(e,targets=[replacements[e['evidence']]],resolution='complete')
        es.append(e)
    require(changed==set(replacements),'REPLACEMENT_COVERAGE')
    removed=set(delta['removed_name_nodes'])
    return dict(base,nodes=[n for n in base['nodes'] if n['id'] not in removed]+delta['nodes'],
                edges=es+delta['edges'],profile=base['profile']+'; '+SCOPE)
