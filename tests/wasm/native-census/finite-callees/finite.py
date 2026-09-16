"""Finite callee expressions over real CCL IR, with immutable lexical scope checks.

Candidates name lexical prototypes or exact symbol cells. Symbol-cell contents
remain separate runtime obligations; a finite designator set is not a bound on
the changing code objects in those cells.
"""
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'source-closure'))
from analysis import Graph,functions,LITERALS,require


class Unbounded(Exception): pass


class Resolver:
    def __init__(self,capture):
        self.graph=Graph(capture['flow']);self.graph.check(capture['function'])
        self.family={f['function_id']:f for f in functions(capture['function'])}
        self.parents={c['function_id']:f['function_id'] for f in self.family.values() for c in f['inner_functions']}
        self.bindings=defaultdict(list);self.uses=defaultdict(list);self.roles={};self.variables=defaultdict(list)
        self.regions={}
        for owner in self.family:
            for ident in self.reachable(self.graph.nodes[owner]['body']):
                n=self.graph.nodes[ident]
                if n['kind']=='cons':
                    for field in ('car','cdr'):
                        v=self.graph.node(n[field])
                        if v and v['kind']=='variable':
                            self.uses[v['root']].append((owner,ident,field));self.variables[v['root']].append(v)
                if n['kind']!='acode' or n['operator'] in LITERALS:continue
                args=self.cells(n['operands']);op=n['operator']
                if op in ('COMMON-LISP::LET','COMMON-LISP::LET*','COMMON-LISP::FLET','COMMON-LISP::LABELS'):
                    require(len(args)==4,'FINITE_BINDING_SHAPE')
                    vs=self.cells(args[0]['car']);values=self.cells(args[1]['car'])
                    require(len(vs)==len(values),'FINITE_BINDING_ARITY')
                    for ordinal,(var_cell,value) in enumerate(zip(vs,values)):
                        var=self.graph.node(var_cell['car'])
                        if not var or var['kind']!='variable':continue
                        self.roles[(owner,var_cell['id'],'car')]='binding'
                        later=values[ordinal+1:] if op=='COMMON-LISP::LET*' else []
                        self.bindings[var['root']].append(dict(owner=owner,node=ident,operator=op,value=value['car'],
                            scope_roots=[args[2]['car']]+[v['car'] for v in later],
                            scope_edges={(args[2]['id'],'car')}|{(v['id'],'car') for v in later}))
                if op=='CCL::LAMBDA-BIND':
                    require(len(args)==7,'FINITE_LAMBDA_BIND_SHAPE')
                    values=self.cells(args[0]['car']);vs=self.cells(args[1]['car'])
                    aux=self.cells(args[4]['car']);require(len(aux)==2,'FINITE_AUX_SHAPE')
                    avs=self.cells(aux[0]['car']);avals=self.cells(aux[1]['car'])
                    require(len(values)>=len(vs) and len(avs)==len(avals),'FINITE_LAMBDA_BIND_ARITY')
                    for group,vals in ((vs,values),(avs,avals)):
                        for ordinal,(var_cell,value) in enumerate(zip(group,vals)):
                            var=self.graph.node(var_cell['car'])
                            if not var or var['kind']!='variable':continue
                            self.roles[(owner,var_cell['id'],'car')]='binding'
                            later=avals if group is vs else avals[ordinal+1:]
                            self.bindings[var['root']].append(dict(owner=owner,node=ident,operator=op,value=value['car'],
                                scope_roots=[args[5]['car']]+[v['car'] for v in later],
                                scope_edges={(args[5]['id'],'car')}|{(v['id'],'car') for v in later}))
                if op in ('CCL::LEXICAL-REFERENCE','CCL::INHERITED-ARG','CCL::SETQ-LEXICAL'):
                    require(len(args)==(2 if op=='CCL::SETQ-LEXICAL' else 1),'FINITE_VARIABLE_SHAPE')
                    self.roles[(owner,args[0]['id'],'car')]='write' if op=='CCL::SETQ-LEXICAL' else 'read'

    def cells(self,value):
        result=[];seen=set()
        while value is not None:
            n=self.graph.node(value)
            require(n and n['kind']=='cons' and n['id'] not in seen,'FINITE_LIST')
            seen.add(n['id']);result.append(n);value=n['cdr']
        return result

    def reachable(self,start,blocked=()):
        seen=set();pending=[start]
        while pending:
            n=self.graph.node(pending.pop())
            if not n or n['id'] in seen:continue
            seen.add(n['id'])
            keys=('car','cdr') if n['kind']=='cons' else (
                ('operands',) if n['kind']=='acode' and n['operator'] not in LITERALS else ())
            for key in keys:
                if (n['id'],key) not in blocked:pending.append(n[key])
        return seen

    def resolve(self,value,owner,site,stack=()):
        g=self.graph;n=g.node(value)
        if not n or n['kind']!='acode':raise Unbounded('non-function-value')
        if len(stack)>=128:raise Unbounded('expression-depth-limit')
        if n['id'] in stack:raise Unbounded('expression-cycle')
        stack=stack+(n['id'],);op=n['operator'];args=g.items(n['operands'])
        steps=[dict(node=n['id'],operator=op)]
        def child(x,use=None):return self.resolve(x,owner,site if use is None else use,stack)
        def forward(x,use=None):
            targets,trace=child(x,use);return targets,steps+trace
        if op in ('CCL::TYPED-FORM','CCL::TYPE-ASSERTED-FORM'):
            if len(args) not in (2,3):raise Unbounded('type-wrapper-shape')
            return forward(args[1])
        if op in ('CCL::SIMPLE-FUNCTION','CCL::CLOSED-FUNCTION'):
            target=g.node(args[0]) if len(args)==1 else None
            if not target or target['kind']!='function' or self.parents.get(target['id'])!=owner:
                raise Unbounded('function-outside-owner')
            return {('afunc',target['id'],'lexical-value')},steps
        if op in ('CCL::%FUNCTION','CCL::IMMEDIATE'):
            if len(args)!=1 or not isinstance(args[0],dict) or set(args[0])!={'symbol','identity'}:
                raise Unbounded('non-symbol-function-constant')
            # Preserve time-of-lookup semantics: #\'foo captures the cell's
            # value when evaluated; a quoted symbol is resolved at FUNCALL.
            mode='captured-function-cell-value' if op=='CCL::%FUNCTION' else 'symbol-designator'
            return {('symbol',args[0]['identity'],mode)},steps
        if op=='COMMON-LISP::IF':
            require(len(args)==3,'FINITE_IF_SHAPE')
            left,lt=child(args[1]);right,rt=child(args[2])
            return left|right,steps+lt+rt
        if op in ('COMMON-LISP::PROGN','COMMON-LISP::PROG1','COMMON-LISP::MULTIPLE-VALUE-PROG1','COMMON-LISP::VALUES'):
            require(len(args)==1,'FINITE_SEQUENCE_SHAPE');items=g.items(args[0])
            if not items:raise Unbounded('empty-value-sequence')
            return forward(items[-1] if op=='COMMON-LISP::PROGN' else items[0])
        if op in ('COMMON-LISP::LET','COMMON-LISP::LET*'):
            require(len(args)==4,'FINITE_LET_SHAPE');body=g.node(args[2])
            return forward(args[2],body['id'] if body else -1)
        if op=='CCL::LAMBDA-BIND':
            require(len(args)==7,'FINITE_LAMBDA_BIND_VALUE_SHAPE');body=g.node(args[5])
            return forward(args[5],body['id'] if body else -1)
        if op not in ('CCL::LEXICAL-REFERENCE','CCL::INHERITED-ARG'):
            raise Unbounded('unsupported-value-operator:'+op)
        variable=g.node(args[0]) if len(args)==1 else None
        if not variable or variable['kind']!='variable':raise Unbounded('variable-shape')
        var=variable['root'];definitions=self.bindings[var]
        if len(definitions)!=1:raise Unbounded('nonunique-or-absent-binding')
        b=definitions[0]
        if b['owner']!=owner:raise Unbounded('outside-binding-owner')
        key=(owner,b['node'],var)
        if key not in self.regions:
            within=set().union(*(self.reachable(root) for root in b['scope_roots']))
            self.regions[key]=(within,self.reachable(g.nodes[owner]['body'],b['scope_edges']))
        within,outside=self.regions[key]
        if site not in within or site in outside:raise Unbounded('outside-binding-body')
        roles=[self.roles.get(u,'unknown') for u in self.uses[var]]
        if any(v['assigned'] for v in self.variables[var]) or 'write' in roles:raise Unbounded('assigned-variable')
        if 'unknown' in roles:raise Unbounded('unclassified-variable-use')
        steps.append(dict(variable=var,binding=b['node'],operator=b['operator']))
        if b['operator'] in ('COMMON-LISP::FLET','COMMON-LISP::LABELS'):
            target=g.node(b['value'])
            if not target or target['kind']!='function' or self.parents.get(target['id'])!=owner:
                raise Unbounded('function-outside-owner')
            return {('afunc',target['id'],'lexical-value')},steps
        initial=g.node(b['value']);targets,trace=child(b['value'],initial['id'] if initial else -1)
        return targets,steps+trace

    def calls(self):
        results=[]
        for owner,f in self.family.items():
            for c in f['calls']:
                if c['dependency']['category'] not in ('function-variable','computed-callee'):continue
                n=self.graph.nodes[c['site_id']];value=self.graph.items(n['operands'])[0]
                row=dict(function_id=owner,site_id=c['site_id'],name=f['name'],variable_id=c['dependency'].get('variable_id'))
                try:
                    targets,steps=self.resolve(value,owner,c['site_id'])
                    require(targets,'EMPTY_FINITE_BOUND')
                    row.update(status='FINITE_EXPRESSION',targets=[dict(kind=k,id=i,mode=m) for k,i,m in sorted(targets)],steps=steps)
                except Unbounded as e:row.update(status='UNRESOLVED',targets=[],reason=str(e))
                results.append(row)
        return results
