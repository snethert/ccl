"""Produce actionable, identity-bearing worklists from the composed graph."""
from collections import Counter,defaultdict,deque
from support import require


def reachable(graph):
    outgoing=defaultdict(list)
    for e in graph['edges']:outgoing[e['from']].extend(e['targets'])
    seen=set(graph['seeds']);pending=deque(graph['seeds'])
    while pending:
        for target in outgoing[pending.popleft()]:
            if target not in seen:seen.add(target);pending.append(target)
    return seen


def analyze(base,graph,v,seed_delta,tools):
    errors=sorted(tools['contract'].validate(graph))
    prefixes=('unresolved reachable edge from ','unimplemented reachable node ')
    structural=[e for e in errors if not e.startswith(prefixes)]
    require(not structural,'GRAPH_STRUCTURE '+str(structural[:3]))
    # This command composes unqualified input records. It must never convert a
    # successful schema check, native snapshot or diagnostic PASS into LL15.
    require(v['survey']['census_acceptance']=='BLOCKED' and v['registry']['census_gate_credit'] is False,
            'QUALIFICATION_INPUT_SCOPE')
    seen=reachable(graph);by_id={n['id']:n for n in graph['nodes']}
    open_edges=[];open_nodes=[];edge_index={};fanout=Counter();members=[]
    for i,e in enumerate(graph['edges']):
        if e['evidence'].startswith(('build-flow/call/','binding-versions/open/','binding-versions/body/')):
            require(e['evidence'] not in edge_index,'DUPLICATE_WORK_EDGE')
            edge_index[e['evidence']]=e
        if e['from'] in seen and e['resolution']!='complete':
            open_edges.append(dict(index=i,owner=e['from'],phase=e['phase'],evidence=e['evidence'],
                                   candidate_count=len(e['targets'])))
        fanout[e['from']]+=len(e['targets'])
        if 'member' in e['evidence']:
            members.append(dict(index=i,owner=e['from'],evidence=e['evidence'],targets=len(e['targets'])))
    for n in graph['nodes']:
        if n['id'] in seen and (n['disposition']=='unresolved' or not n['implementation']):
            open_nodes.append({k:n[k] for k in ('id','kind','evidence','reason')})
    require(len(open_edges)==sum(e.startswith(prefixes[0]) for e in errors)
            and len(open_nodes)==sum(e.startswith(prefixes[1]) for e in errors),'CONTRACT_RECOUNT')

    histories=[h for h in v['histories'] if h['call_count']]
    cells=[];missing=[]
    for h in histories:
        ident='identity:build:binding-cell:'+str(h['symbol_id'])
        e=edge_index['binding-versions/open/'+str(h['symbol_id'])]
        require(e['from']==ident and e['resolution']=='unresolved' and by_id[ident]['disposition']=='unresolved',
                'BINDING_OBLIGATION')
        r=dict(node=ident,symbol_id=h['symbol_id'],descriptors=h['descriptors'],call_sites=h['call_count'],
               observed_prototypes=h['ordinary_codes'],value_witness=bool(h['observations']),bound='UNRESOLVED')
        cells.append(r)
        if not h['observations']:missing.append(r)
    calls=[];bounded=0;categories=Counter();global_counts=Counter()
    for c in v['calls']:
        d=c['dependency'];category=d['category']
        if category=='global-binding':global_counts[c['global_symbol']['id']]+=1
        if category not in ('function-variable','computed-callee'):continue
        evidence=f'build-flow/call/{c["function_id"]}/{c["site_id"]}'
        e=edge_index[evidence]
        targets=c.get('lexical_bound',{}).get('targets',[])
        require(e['resolution']==('complete' if targets else 'unresolved'),'COMPUTED_OBLIGATION')
        if targets:bounded+=1;continue
        categories[category]+=1
        calls.append(dict(function_id=c['function_id'],site_id=c['site_id'],caller_name=c['name'],
                          node=e['from'],evidence=evidence,dependency=d,local_proof=c.get('lexical_bound')))
    require(global_counts==Counter({h['symbol_id']:h['call_count'] for h in histories}),'GLOBAL_SITE_ACCOUNTING')
    bodies={b['code']:b for b in v['bodies']['bodies']}
    origins={r['code']:r for r in v['origins']['prototypes']}
    body_rows=[]
    for e in v['bindings']['edges']:
        if not e['evidence'].startswith('binding-versions/body/') or e['resolution']=='complete':continue
        require(edge_index[e['evidence']]==e,'BODY_OBLIGATION')
        code=int(e['evidence'].rsplit('/',1)[1]);b=bodies.get(code);o=origins.get(code)
        require((b is not None)!=(o is not None),'BODY_PROVENANCE_PARTITION')
        body_rows.append(dict(code=code,node=e['from'],evidence=e['evidence'],dependency_status='UNRESOLVED',
            payload_witness=None if b is None else {k:b[k] for k in ('description','source_end','payload_sha256')},
            origin_category=None if o is None else o['category']))
    require({r['code'] for r in body_rows}==bodies.keys()|origins.keys(),'BODY_WORKLIST_SET')
    body_rows.sort(key=lambda r:r['code'])
    counts=dict(graph_nodes=len(graph['nodes']),graph_edges=len(graph['edges']),reachable_nodes=len(seen),
                unresolved_edges=len(open_edges),unimplemented_nodes=len(open_nodes),
                called_symbol_cells=len(cells),unwitnessed_symbol_cells=len(missing),
                unwitnessed_symbol_call_sites=sum(r['call_sites'] for r in missing),
                original_body_obligations=len(body_rows),resident_payload_witnesses=len(bodies),
                resident_source_ranges=sum(b['source_end'] is not None and b['description']['position'] is not None for b in bodies.values()),
                original_computed_sites=bounded+len(calls),local_bounds=bounded,open_computed_sites=len(calls),
                open_computed_categories=dict(sorted(categories.items())),
                unattached_assembly_functions=len(v['flow']['unattached_functions']),
                reviewed_seed_prototype_union=len(seed_delta['root_functions']),
                seed_snapshot_functions_with_body_gaps=len(seed_delta['snapshot_functions']),
                legacy_roots_retained=len(base['seeds']),new_snapshot_roots=len(seed_delta['roots']),
                historical_membership_edges=len(members),target_form_failures=v['survey']['target_form_failures'])
    blocker_counts={p.strip():sum(e.startswith(p) for e in errors) for p in prefixes}
    prior=v['prior_summary']['errors']
    scope_gaps=[n for n in seed_delta['nodes'] if n['id'].startswith('seed-v2:gap:')]
    report=dict(version=1,status='BLOCKED',exit_code=2,structure='PASS',census_qualification='NOT_QUALIFIED',
                census_gate_credit=False,counts=counts,contract_errors=blocker_counts,
                graph_change=dict(nodes=len(graph['nodes'])-len(base['nodes']),edges=len(graph['edges'])-len(base['edges']),
                                  existing_records_changed=0,original_obligations_closed=0,
                                  unresolved_edges_added=len(open_edges)-prior['unresolved reachable edge from'],
                                  unimplemented_nodes_added=len(open_nodes)-prior['unimplemented reachable node']),
                qualification_blockers=[dict(id=n['id'],reason=n['reason']) for n in scope_gaps],
                independent_census_omission_qualification='NOT_RUN',
                next_work='Resolve the 95 symbol-value obligations and apply body/parameter/registry proofs to this working graph.',
                native_build_policy='Use a new combined native build when it supplies missing witnesses more efficiently; this composition itself needs no native execution.')
    # Even a malformed future producer must not erase all qualified-input gaps
    # and turn an unqualified snapshot recipe into a successful gate record.
    require(scope_gaps and errors,'UNQUALIFIED_INPUT_PROMOTION')
    blockers=dict(version=1,status='BLOCKED',unresolved_edges=open_edges,unimplemented_nodes=open_nodes,
                  membership_edges=members,largest_fanouts=[dict(node=n,target_references=count) for n,count in
                    sorted(fanout.items(),key=lambda x:(-x[1],x[0]))[:12]],
                  fanout_scope='Diagnostic sizes only; not a classification of every edge as unsound or removable.')
    work=dict(version=1,namespace='identity:build',unwitnessed_symbols=missing,unbounded_symbol_cells=cells,
              original_body_obligations=body_rows,open_computed_calls=calls,
              unattached_assembly_functions=v['flow']['unattached_functions'],
              independent_registry_witness=dict(counts=v['registry'],original_build_credit=0,
                                                required='Construction/template and effective-method/cache witnesses, then an execution identity bridge.'),
              seed_snapshot_namespace='seed-v2:',qualification_blockers=report['qualification_blockers'])
    return report,blockers,work
