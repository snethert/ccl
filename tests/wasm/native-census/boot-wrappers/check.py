"""Independent record bounds derived from the literal-slot witness."""
from collections import Counter
import hashlib
from join import canonical, key, require, SCOPE, DISPATCH_WORD


def expected(base,data,binding):
    prior={n['id']:n for n in base['nodes']};added={};changes={};edges=[]
    def n(i,kind,impl,evidence,reason):
        r={'id':i,'kind':kind,'disposition':'implemented','required':True,'implementation':impl,
           'evidence':evidence,'reason':reason,'tests':['S0-LL15-b','S0-LL15-c']}
        if i in prior:require(prior[i]==r,'CHECKER_EXISTING_RECORD')
        else:added[i]=r
    def e(source,target,phase,label):
        edges.append({'from':source,'targets':[target],'phase':phase,'origin':'observed','resolution':'complete','evidence':'boot/wrappers/'+label})
    trap='boot:wrapper-dispatch';table='boot:wrapper-handler-table:'+str(data['handler_table'])
    n(trap,'trap','Recorded native macro/special application trap','boot/wrappers/dispatch',str(DISPATCH_WORD))
    n(table,'store','Observed *nx1-alphatizers* table identity','boot/wrappers/handler-table',str(data['handler_table']))
    descriptions={r['id']:r for r in data['objects']}
    for witness in data['oracle']:
        i=key(witness['wrapper']);macro=witness['slot1_kind']=='function';kind='macro-wrapper' if macro else 'special-wrapper'
        contents={'id':witness['wrapper'],'kind':kind,'dispatch_value':witness['slot0'],'payload':witness['slot1'],'handler':witness['handler']}
        before=prior[i]
        changes[i]={'before':before,'after':{**before,'disposition':'implemented','implementation':'Recorded native '+kind+' identity',
                    'evidence':'boot/wrappers/value/'+str(witness['wrapper']),'reason':canonical(contents)}}
        e(i,trap,'run','dispatch/'+str(witness['wrapper']))
        if macro:e(i,key(witness['slot1']),'macroexpand','expander/'+str(witness['wrapper']))
        else:
            marker='boot:special-operator:'+str(witness['slot1'])
            r=descriptions[witness['slot1']]
            n(marker,'operator','Recorded native special-operator marker','boot/wrappers/symbol/'+str(r['id']),canonical(r))
            e(i,marker,'compile','marker/'+str(witness['wrapper']))
            e(marker,key(witness['handler']),'compile','handler/'+str(witness['wrapper']))
            e(marker,table,'compile','handler-table/'+str(witness['wrapper']))
        function=descriptions[witness['slot1'] if macro else witness['handler']]
        n(key(function['id']),'function','Recorded native function identity','boot/objects/'+str(function['id']),canonical(function))
    gap=prior['boot:gap:closure']
    changes[gap['id']]={'before':gap,'after':{**gap,'reason':'Full target traversal, callable bodies and Wasm dispositions remain unqualified.'}}
    return {'version':1,'scope':SCOPE,'input_binding':binding,'nodes':added,'replacements':changes,
            'edges':Counter(canonical(r) for r in edges)}


def check(patch,oracle):
    require(set(patch)==set(oracle),'PATCH_FIELDS')
    for k in ('version','scope','input_binding'):require(patch[k]==oracle[k],'PATCH_'+k.upper())
    nodes={r['id']:r for r in patch['nodes']}
    require(len(nodes)==len(patch['nodes']) and nodes==oracle['nodes'],'ADDED_NODE_RECORDS')
    changes={r['before']['id']:r for r in patch['replacements']}
    require(len(changes)==len(patch['replacements']) and changes==oracle['replacements'],'REPLACEMENT_RECORDS')
    require(Counter(canonical(r) for r in patch['edges'])==oracle['edges'],'EDGE_RECORDS')


def check_graph(base,graph,patch):
    require(set(base)==set(graph),'GRAPH_FIELDS')
    changes={r['before']['id']:r for r in patch['replacements']}
    require(set(changes)<={r['id'] for r in base['nodes']},'MISSING_REPLACEMENT_BASE')
    wanted=[changes[n['id']]['after'] if n['id'] in changes else n for n in base['nodes']]+patch['nodes']
    require(graph['nodes']==wanted,'GRAPH_NODES')
    require(len({n['id'] for n in graph['nodes']})==len(graph['nodes']),'GRAPH_NODE_COLLISION')
    require(graph['edges']==base['edges']+patch['edges'],'GRAPH_EDGES')
    require(graph['profile']==base['profile']+'; decoded native macro/special wrappers','GRAPH_PROFILE')
    sha=hashlib.sha256(canonical({'base':base['inputs_sha256'],'wrapper_binding':patch['input_binding']}).encode()).hexdigest()
    require(graph['inputs_sha256']==sha,'GRAPH_INPUT_BINDING')
    for k in set(base)-{'nodes','edges','profile','inputs_sha256'}:
        require(graph[k]==base[k],'GRAPH_'+k.upper())
