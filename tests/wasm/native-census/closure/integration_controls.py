"""Integration regressions on the genuine blocked graph; no LL15-c credit."""
from copy import deepcopy
import seeds
from support import require


def run(base,graph,delta,v,pins,tools,report):
    rows=[]
    def reject(name,thunk,reason):
        try:thunk()
        except ValueError as e:
            require(str(e)==reason,'CONTROL_REASON '+name+' '+str(e))
            rows.append(dict(name=name,status='REJECTED',reason=reason));return
        raise ValueError('CONTROL_ESCAPED '+name)
    # Copy-on-write mutations keep the million-edge baseline shared and intact.
    def graph_change(name,change,reason):
        g=dict(graph,nodes=list(graph['nodes']),edges=list(graph['edges']),seeds=list(graph['seeds']))
        change(g);reject(name,lambda:seeds.check(base,g,delta,delta),reason)
    graph_change('remove-reviewed-root',lambda g:g['seeds'].pop(),'EXACT_ROOTS')
    graph_change('erase-historical-root',lambda g:g['seeds'].pop(0),'EXACT_ROOTS')
    graph_change('extra-root',lambda g:g['seeds'].append(g['seeds'][0]),'EXACT_ROOTS')
    graph_change('omit-required-node',lambda g:g['nodes'].pop(0),'EXACT_NODE_RECORDS')
    graph_change('surplus-node',lambda g:g['nodes'].append(g['nodes'][0]),'EXACT_NODE_RECORDS')
    def promote(g):
        i=next(i for i,n in enumerate(g['nodes']) if n['disposition']=='unresolved')
        g['nodes'][i]=dict(g['nodes'][i],disposition='implemented',implementation='fabricated')
    graph_change('promote-unimplemented-node',promote,'EXACT_NODE_RECORDS')
    graph_change('omit-old-edge',lambda g:g['edges'].pop(0),'EXACT_EDGE_RECORDS')
    graph_change('insert-cross-run-edge',lambda g:g['edges'].append(dict(g['edges'][0],targets=[delta['roots'][0]])),'EXACT_EDGE_RECORDS')
    def conceal(g):
        i=next(i for i,e in enumerate(g['edges']) if e['resolution']=='unresolved')
        g['edges'][i]=dict(g['edges'][i],resolution='complete',targets=[base['seeds'][0]])
    graph_change('conceal-unknown-call',conceal,'EXACT_EDGE_RECORDS')
    def retarget(g):
        i=len(base['edges']);g['edges'][i]=dict(g['edges'][i],targets=[base['seeds'][0]])
    graph_change('seed-id-reused-in-old-namespace',retarget,'EXACT_EDGE_RECORDS')
    graph_change('alter-initializer-order',lambda g:g.update(initializers=[dict(g['initializers'][0],rank=-1)]+g['initializers'][1:]),'GRAPH_METADATA initializers')
    graph_change('erase-trace-reconciliation',lambda g:g.update(observed_modules=[]),'GRAPH_METADATA observed_modules')
    graph_change('false-seed-review',lambda g:g.update(seed_review='COMPLETE'),'GRAPH_METADATA seed_review')
    for field in ('entry_bindings','root_functions','snapshot_functions'):
        d=deepcopy(delta);d[field].pop()
        reject('omit-'+field,lambda:seeds.check(base,graph,d,delta),'EXACT_SEED_RECORDS')
    value=dict(v,seed_candidates=deepcopy(v['seed_candidates']))
    value['seed_candidates']['root_functions'].pop()
    reject('damaged-root-witness',lambda:seeds.make(value,pins,tools),'ROOT_UNION')
    value=dict(v,seeds=deepcopy(v['seeds']));value['seeds']['review_disposition']='PROPOSED'
    reject('unreviewed-seed-manifest',lambda:seeds.make(value,pins,tools),'SEED_REVIEW')
    value=dict(v,seed_image=deepcopy(v['seed_image']))
    b=value['seed_image']['kernel_entries']['builtins'];b[0],b[1]=b[1],b[0]
    reject('swapped-builtin-slots',lambda:seeds.make(value,pins,tools),'kernel vector slot coverage: builtins')
    value=dict(v,seed_image=deepcopy(v['seed_image']))
    value['seed_image']['kernel_entries']['callbacks'][1]['symbol_value_matches']=False
    reject('callback-without-trampoline',lambda:seeds.make(value,pins,tools),'kernel callback lacks a matching trampoline: CCL::XCMAIN')
    # BLOCKED is the actual command outcome, not a PASS for LL15. Regression
    # rejections have distinct local causes despite the genuine baseline gaps.
    require(report['status']=='BLOCKED' and report['exit_code']==2 and report['census_gate_credit'] is False,'BLOCKED_EXIT_POLICY')
    return dict(status='PASS',scope='Integration regressions only; no instrumentation completeness or LL15-c qualification.',
                controls_rejected=len(rows),controls=rows)
