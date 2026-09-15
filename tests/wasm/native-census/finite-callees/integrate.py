"""Apply proved expression bounds, preserving distinct cell-value obligations."""
from collections import Counter
from copy import deepcopy
from finite import require

SCOPE='Finite computed expressions; exact symbol cells retain unresolved runtime value bounds.'


def patch(base,proofs,histories):
    existing={n['id'] for n in base['nodes']};hs={h['symbol_id']:h for h in histories}
    nodes={};gaps={};changes=[]
    for r in proofs:
        if r['status']!='FINITE_EXPRESSION':continue
        targets=[]
        for t in r['targets']:
            if t['kind']=='afunc':
                ident='identity:build:afunc:'+str(t['id']);require(ident in existing,'LEXICAL_TARGET_OUTSIDE_GRAPH')
            else:
                descriptor=t.get('descriptor',{})
                require(t['kind']=='symbol' and descriptor.get('kind')=='symbol'
                        and descriptor.get('id')==t['id'],'EXACT_SYMBOL_DESCRIPTOR')
                # Histories cover symbols directly called by the old build.
                # A newly resolved computed name need not be in that set. Its
                # exact IR descriptor still selects a cell, with no value claim.
                if t['id'] in hs:
                    require(descriptor in hs[t['id']]['descriptors'],'EXACT_SYMBOL_DESCRIPTOR')
                ident='identity:build:binding-cell:'+str(t['id'])
                if ident not in existing:
                    nodes[ident]=dict(id=ident,kind='function',required=True,disposition='unresolved',implementation=None,
                        reason='Exact symbol selected by a computed expression; callable values, versions and target dependencies remain unbounded.',
                        evidence='finite-callees/cell/'+str(t['id']),tests=['S0-LL15-b','S0-LL15-c'])
                    gaps[ident]={'from':ident,'targets':[],'phase':'run','origin':'conservative',
                                 'resolution':'unresolved','evidence':'finite-callees/open/'+str(t['id'])}
            targets.append(ident)
        changes.append({'from':'identity:build:afunc:'+str(r['function_id']),
                        'targets':sorted(set(targets)),'phase':'run','origin':'conservative','resolution':'complete',
                        'evidence':f'build-flow/call/{r["function_id"]}/{r["site_id"]}'})
    return dict(scope=SCOPE,nodes=[nodes[k] for k in sorted(nodes)],edges=[gaps[k] for k in sorted(gaps)],
                replacements=sorted(changes,key=lambda e:e['evidence']))


def apply(base,delta):
    replacements={e['evidence']:e for e in delta['replacements']}
    require(len(replacements)==len(delta['replacements']),'REPEATED_PROOF_SITE')
    old={e['evidence']:e for e in base['edges'] if e['evidence'] in replacements}
    require(old.keys()==replacements.keys() and all(e['resolution']=='unresolved' and not e['targets'] for e in old.values()),
            'ORIGINAL_COMPUTED_GAPS')
    return dict(base,nodes=base['nodes']+delta['nodes'],
                edges=[replacements.get(e['evidence'],e) for e in base['edges']]+delta['edges'],
                profile=base['profile']+'; '+SCOPE)


def check(base,graph,delta,proofs,histories):
    require(delta==patch(base,proofs,histories),'EXACT_FINITE_PATCH')
    require(graph==apply(base,delta),'EXACT_FINITE_GRAPH')
    # A symbol reference remains a value gap even if a stored function was
    # obtained much earlier than this call. No current value substitutes for it.
    by_id={n['id']:n for n in graph['nodes']};gaps={e['from'] for e in graph['edges'] if e['resolution']=='unresolved'}
    for r in proofs:
        for t in r['targets']:
            if t['kind']=='symbol':
                ident='identity:build:binding-cell:'+str(t['id'])
                require(by_id[ident]['disposition']=='unresolved' and ident in gaps,'CELL_VALUE_GAP_PRESERVED')


def controls(base,graph,delta,proofs,histories):
    rows=[]
    def reject(name,g,d,expected):
        try:check(base,g,d,proofs,histories)
        except ValueError as e:
            require(str(e)==expected,'INTEGRATION_CONTROL_REASON '+name)
            rows.append(dict(name=name,status='REJECTED'));return
        raise ValueError('INTEGRATION_CONTROL_ESCAPED '+name)
    for name,change in [('omit-bound',lambda d:d['replacements'].pop()),
                        ('invent-bound',lambda d:d['replacements'].append(d['replacements'][0])),
                        ('wrong-target',lambda d:d['replacements'][0].update(targets=['seed-v2:function:1'])),
                        ('wrong-phase',lambda d:d['replacements'][0].update(phase='compile'))]:
        d=deepcopy(delta);change(d);reject(name,graph,d,'EXACT_FINITE_PATCH')
    for name,field in [('erase-root','seeds'),('erase-old-edge','edges'),('erase-old-node','nodes'),('erase-initializer','initializers')]:
        g=dict(graph);g[field]=g[field][1:];reject(name,g,delta,'EXACT_FINITE_GRAPH')
    g=dict(graph,edges=graph['edges']+[graph['edges'][0]])
    reject('insert-edge',g,delta,'EXACT_FINITE_GRAPH')
    g=dict(graph,edges=list(graph['edges']))
    i=next(i for i,e in enumerate(g['edges']) if e['evidence'].startswith('binding-versions/open/'))
    g['edges'][i]=dict(g['edges'][i],resolution='complete')
    reject('claim-complete-cell-contents',g,delta,'EXACT_FINITE_GRAPH')
    return rows
