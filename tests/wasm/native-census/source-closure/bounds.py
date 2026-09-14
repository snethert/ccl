"""Conservative lexical callback bounds over flat acode graphs.

The criterion is the reviewed lexical-callbacks proof: one immutable local
binding, a use confined to its body, and no unclassified use anywhere in the
lexical family. Flat edge reachability replaces recursively constructed paths.
"""
from collections import defaultdict
from analysis import Graph, functions, LITERALS, require


class Unbounded(Exception): pass


def analyze(capture):
    graph=Graph(capture['flow']);graph.check(capture['function'])
    obs=list(functions(capture['function']));by_function={f['function_id']:f for f in obs}
    parents={c['function_id']:f['function_id'] for f in obs for c in f['inner_functions']}
    bindings=defaultdict(list);uses=defaultdict(list);roles={};variables={};bodies={}

    def list_cells(value):
        result=[];seen=set()
        while value is not None:
            n=graph.node(value)
            require(n and n['kind']=='cons' and n['id'] not in seen,'BOUND_LIST')
            seen.add(n['id']);result.append(n);value=n['cdr']
        return result

    def reachable(start,blocked=None):
        seen=set();pending=[start]
        while pending:
            n=graph.node(pending.pop())
            if not n or n['id'] in seen:continue
            seen.add(n['id'])
            keys=('car','cdr') if n['kind']=='cons' else (
                ('operands',) if n['kind']=='acode' and n['operator'] not in LITERALS else ())
            for k in keys:
                if (n['id'],k)!=blocked:pending.append(n[k])
        return seen

    for f in obs:
        owner=f['function_id'];root=graph.nodes[owner]['body'];body=reachable(root);bodies[owner]=body
        for ident in body:
            n=graph.nodes[ident]
            if n['kind']=='cons':
                for key in ('car','cdr'):
                    value=graph.node(n[key])
                    if value and value['kind']=='variable':
                        var=value['root'];variables.setdefault(var,[]).append(value)
                        uses[var].append((owner,ident,key))
            if n['kind']!='acode' or n['operator'] in LITERALS:continue
            args=list_cells(n['operands']);op=n['operator']
            if op in ('COMMON-LISP::LET','COMMON-LISP::LET*','COMMON-LISP::FLET'):
                require(len(args)==4,'BOUND_BINDING_SHAPE')
                vs=list_cells(args[0]['car']);initializers=list_cells(args[1]['car'])
                require(len(vs)==len(initializers),'BOUND_BINDING_ARITY')
                for v,init in zip(vs,initializers):
                    var=graph.node(v['car'])
                    if not var or var['kind']!='variable':continue
                    roles[(owner,v['id'],'car')]='binding'
                    bindings[var['root']].append(dict(owner=owner,node=ident,operator=op,
                         value=init['car'],body=args[2]['car'],body_edge=(args[2]['id'],'car')))
            if op in ('CCL::LEXICAL-REFERENCE','CCL::INHERITED-ARG','CCL::SETQ-LEXICAL'):
                require(len(args)==(2 if op=='CCL::SETQ-LEXICAL' else 1),'BOUND_VARIABLE_SHAPE')
                roles[(owner,args[0]['id'],'car')]='write' if op=='CCL::SETQ-LEXICAL' else 'read'

    region_cache={}
    def resolve(value,owner,site,seen=()):
        n=graph.node(value)
        if not n or n['kind']!='acode':raise Unbounded('non-function-initializer')
        op=n['operator'];args=graph.items(n['operands'])
        if op in ('CCL::TYPED-FORM','CCL::TYPE-ASSERTED-FORM'):
            if len(args) not in (2,3):raise Unbounded('unsupported-type-wrapper')
            return resolve(args[1],owner,site,seen)
        if op in ('CCL::SIMPLE-FUNCTION','CCL::CLOSED-FUNCTION'):
            target=graph.node(args[0]) if len(args)==1 else None
            if not target or target['kind']!='function':raise Unbounded('function-shape')
            if target['id'] not in by_function or parents.get(target['id'])!=owner:raise Unbounded('function-outside-owner')
            return target['id'],[]
        if op not in ('CCL::LEXICAL-REFERENCE','CCL::INHERITED-ARG'):raise Unbounded('non-lexical-initializer')
        variable=graph.node(args[0]) if len(args)==1 else None
        if not variable or variable['kind']!='variable':raise Unbounded('variable-shape')
        var=variable['root']
        if var in seen:raise Unbounded('binding-cycle')
        defs=bindings[var]
        if len(defs)!=1:raise Unbounded('nonunique-or-absent-binding')
        b=defs[0]
        if b['owner']!=owner:raise Unbounded('outside-binding-owner')
        key=(owner,b['node'])
        if key not in region_cache:
            region_cache[key]=(reachable(b['body']),reachable(graph.nodes[owner]['body'],b['body_edge']))
        within,outside=region_cache[key]
        if site not in within or site in outside:raise Unbounded('outside-binding-body')
        rs=[roles.get(pos,'unknown') for pos in uses[var]]
        if any(v['assigned'] for v in variables[var]) or 'write' in rs:raise Unbounded('assigned-variable')
        if 'unknown' in rs:raise Unbounded('unclassified-variable-use')
        if b['operator']=='COMMON-LISP::FLET':
            target=graph.node(b['value'])
            if not target or target['kind']!='function':raise Unbounded('flet-initializer')
            target=target['id'];chain=[]
            if target not in by_function or parents.get(target)!=owner:raise Unbounded('function-outside-owner')
        else:
            value_node=graph.node(b['value'])
            target,chain=resolve(b['value'],owner,value_node['id'] if value_node else -1,seen+(var,))
        return target,[dict(variable_id=var,binding_node=b['node'],operator=b['operator'])]+chain

    results=[]
    for f in obs:
        owner=f['function_id']
        for c in f['calls']:
            if c['dependency']['category']!='function-variable':continue
            row=dict(function_id=owner,call_site=c['site_id'],variable_id=c['dependency']['variable_id'])
            n=graph.nodes[c['site_id']];value=graph.items(n['operands'])[0]
            try:
                target,chain=resolve(value,owner,c['site_id'])
                row.update(disposition='BOUNDED_LEXICAL_PROTOTYPE',targets=[target],bindings=chain)
            except Unbounded as e:row.update(disposition='UNRESOLVED',targets=[],reason=str(e))
            results.append(row)
    return results
