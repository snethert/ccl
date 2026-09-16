"""Captured immutable bindings and exhaustive argument flow for local functions."""
from collections import defaultdict
from finite import Resolver as FiniteResolver,Unbounded,require


class Resolver(FiniteResolver):
    def __init__(self,capture):
        super().__init__(capture)
        self.parameters=defaultdict(list);self.signatures={}
        self.creations=defaultdict(list);self.incoming=defaultdict(list)
        self.declarations=defaultdict(list);self.escapes=defaultdict(list)
        self.active_parameters=set()
        g=self.graph
        for owner in self.family:
            root=g.node(g.nodes[owner]['body'])
            if not root or root.get('operator')!='CCL::LAMBDA-LIST':continue
            cells=self.cells(root['operands']);args=[c['car'] for c in cells]
            require(len(args) in (7,8),'PARAMETER_LAMBDA_SHAPE')
            variables=self.cells(args[0]);ids=[]
            for ordinal,cell in enumerate(variables):
                var=g.node(cell['car'])
                if not var or var['kind']!='variable':break
                self.parameters[var['root']].append((owner,ordinal))
                self.roles[(owner,cell['id'],'car')]='parameter'
                ids.append(var['root'])
            else:
                # Optional/rest/keyword protocols need their own argument
                # binder; this pass does not guess defaults or supplied-p.
                if all(a is None for a in args[1:4]) and len(ids)==len(set(ids)):
                    self.signatures[owner]=ids
        for owner in self.family:self.scan_function_uses(owner)

    def scan_function_uses(self,owner):
        """Visit value and operand contexts separately; shared lists cannot hide an escape."""
        g=self.graph;seen=set();pending=[(g.nodes[owner]['body'],'value',None)]
        while pending:
            value,role,site=pending.pop();n=g.node(value)
            if not n:continue
            if n['kind']=='function':
                if role=='declaration':
                    self.declarations[n['id']].append(dict(owner=owner,site=site))
                    self.creations[n['id']].append(dict(owner=owner,site=site,kind='declaration'))
                elif role!='direct-call':self.escapes[n['id']].append(dict(owner=owner,site=site,kind=role))
                continue
            key=(n['id'],role,site if role in ('declaration','direct-call') else None)
            if key in seen:continue
            seen.add(key)
            if n['kind']=='cons':
                pending.extend(((n['car'],role,site),(n['cdr'],role,site)));continue
            if n['kind']!='acode':continue
            args=g.items(n['operands']);op=n['operator']
            if op in ('COMMON-LISP::FLET','COMMON-LISP::LABELS'):
                require(len(args)==4,'LOCAL_DECLARATION_SHAPE')
                variables=self.cells(args[0]);functions=g.items(args[1])
                require(len(variables)==len(functions),'LOCAL_DECLARATION_ARITY')
                for cell,fn in zip(variables,functions):
                    variable=g.node(cell['car']);target=g.node(fn)
                    require(variable and variable['kind']=='variable' and target and target['kind']=='function',
                            'LOCAL_DECLARATION_BINDING')
                    binding=(owner,cell['id'],'car')
                    # #'LOCAL is represented by a read of its FLET/LABELS
                    # binding variable, not necessarily SIMPLE-FUNCTION.
                    # Any such value use can expose an additional caller.
                    for use in self.uses[variable['root']]:
                        if use!=binding:
                            self.escapes[target['id']].append(dict(owner=use[0],site=use[1],kind='function-binding-value'))
                pending.extend(((args[1],'declaration',n['id']),
                                (args[0],'value',n['id']),(args[2],'value',n['id']),(args[3],'value',n['id'])))
            elif op in ('CCL::LEXICAL-FUNCTION-CALL','CCL::SELF-CALL'):
                if op=='CCL::SELF-CALL':
                    require(len(args) in (1,2),'SELF_ARGUMENT_SHAPE')
                    target=owner;arglist=args[0];spread=args[1] if len(args)==2 else None
                else:
                    require(len(args) in (2,3),'LOCAL_ARGUMENT_SHAPE')
                    target=g.node(args[0]);require(target and target['kind']=='function','LOCAL_CALLEE_SHAPE')
                    target=target['id'];arglist=args[1];spread=args[2] if len(args)==3 else None
                    pending.append((args[0],'direct-call',n['id']))
                self.incoming[target].append(dict(owner=owner,site=n['id'],arglist=arglist,spread=spread))
                pending.append((arglist,'value',n['id']))
            elif op in ('CCL::SIMPLE-FUNCTION','CCL::CLOSED-FUNCTION'):
                require(len(args)==1,'LOCAL_VALUE_SHAPE');target=g.node(args[0])
                require(target and target['kind']=='function','LOCAL_VALUE_TARGET')
                self.creations[target['id']].append(dict(owner=owner,site=n['id'],kind=op))
                # Even if a test never exercises the escaping value, all of
                # its possible callers remain unknown to this local analysis.
                self.escapes[target['id']].append(dict(owner=owner,site=n['id'],kind=op))
            else:
                # Include literals here: embedding an AFUNC as data cannot
                # count as proof that its callable representation stays local.
                pending.append((n['operands'],'value',n['id']))

    def immutable(self,var):
        roles=[self.roles.get(u,'unknown') for u in self.uses[var]]
        if any(v['assigned'] for v in self.variables[var]) or 'write' in roles:raise Unbounded('assigned-variable')
        if 'unknown' in roles:raise Unbounded('unclassified-variable-use')

    def capture_scope(self,owner,binding_owner,var):
        """Find the actual first closure creation under the owning binding."""
        child=owner;seen=set()
        while self.parents.get(child)!=binding_owner:
            if child in seen or child not in self.parents:raise Unbounded('binding-not-ancestor')
            seen.add(child);child=self.parents[child]
        sites=[s for s in self.creations[child] if s['owner']==binding_owner]
        if not sites:raise Unbounded('missing-closure-creation')
        if len(self.bindings[var])==1:
            b=self.bindings[var][0]
            within=set().union(*(self.reachable(root) for root in b['scope_roots']))
            outside=self.reachable(self.graph.nodes[binding_owner]['body'],b['scope_edges'])
            # LABELS binds its function names within their definitions too.
            # FLET does not; its declaration site must pass the normal test.
            def recursive_declaration(s):
                return b['operator']=='COMMON-LISP::LABELS' and s['kind']=='declaration' and s['site']==b['node']
            if any(not recursive_declaration(s) and (s['site'] not in within or s['site'] in outside) for s in sites):
                raise Unbounded('closure-created-outside-binding')
        # A required argument is bound throughout its lambda body. Its lambda
        # signature and unique binding are checked by parameter().
        return [dict(capture_owner=owner,binding_owner=binding_owner,first_child=child,creation_sites=sites)]

    def captured(self,var,owner,stack):
        defs=self.bindings[var]
        if len(defs)!=1:raise Unbounded('nonunique-or-absent-binding')
        b=defs[0];self.immutable(var);steps=self.capture_scope(owner,b['owner'],var)
        if b['operator'] in ('COMMON-LISP::FLET','COMMON-LISP::LABELS'):
            target=self.graph.node(b['value'])
            if not target or target['kind']!='function' or self.parents.get(target['id'])!=b['owner']:
                raise Unbounded('function-outside-owner')
            return {('afunc',target['id'],'lexical-value')},steps
        initial=self.graph.node(b['value'])
        targets,trace=self.resolve(b['value'],b['owner'],initial['id'] if initial else -1,stack)
        return targets,steps+trace

    def parameter(self,var,owner):
        entries=self.parameters[var]
        if len(entries)!=1 or self.bindings[var]:raise Unbounded('nonunique-parameter-binding')
        bound_owner,ordinal=entries[0];steps=[]
        self.immutable(var)
        if owner!=bound_owner:steps+=self.capture_scope(owner,bound_owner,var)
        if bound_owner not in self.parents:raise Unbounded('external-parameter')
        if not self.declarations[bound_owner]:raise Unbounded('parameter-without-local-declaration')
        if self.escapes[bound_owner]:raise Unbounded('escaping-local-function')
        if bound_owner not in self.signatures:raise Unbounded('unsupported-parameter-signature')
        if not self.incoming[bound_owner]:raise Unbounded('local-function-without-callers')
        key=(bound_owner,var)
        if key in self.active_parameters:
            # A cycle contributes no new values. Every nonrecursive incoming
            # path is still visited; an unknown one rejects the whole bound.
            return set(),steps+[dict(parameter_cycle=list(key))]
        self.active_parameters.add(key);targets=set()
        try:
            for call in self.incoming[bound_owner]:
                if call['spread'] is not None:raise Unbounded('spread-local-call')
                parts=self.graph.items(call['arglist'])
                require(len(parts)==2,'LOCAL_ARGUMENT_PARTS')
                # NX1-ARGLIST retains stack arguments in source order and
                # pushes register arguments in reverse order, before pass 2.
                args=self.graph.items(parts[0])+list(reversed(self.graph.items(parts[1])))
                if len(args)!=len(self.signatures[bound_owner]):raise Unbounded('local-call-arity')
                value,trace=self.resolve(args[ordinal],call['owner'],call['site'])
                targets.update(value);steps.append(dict(parameter=var,function=bound_owner,ordinal=ordinal,
                    caller=call['owner'],call_site=call['site'],argument=args[ordinal]))
                steps.extend(trace)
        finally:self.active_parameters.remove(key)
        return targets,steps

    def resolve(self,value,owner,site,stack=()):
        root=not stack and not self.active_parameters
        n=self.graph.node(value)
        if n and n.get('operator') in ('CCL::LEXICAL-REFERENCE','CCL::INHERITED-ARG'):
            args=self.graph.items(n['operands']);var=self.graph.node(args[0]) if len(args)==1 else None
            if var and var['kind']=='variable':
                ident=var['root'];defs=self.bindings[ident]
                if not defs and self.parameters[ident]:
                    result=self.parameter(ident,owner)
                    if root and not result[0]:raise Unbounded('parameter-cycle-without-value')
                    return result
                if len(defs)==1 and defs[0]['owner']!=owner:
                    result=self.captured(ident,owner,stack)
                    if root and not result[0]:raise Unbounded('parameter-cycle-without-value')
                    return result
        result=super().resolve(value,owner,site,stack)
        if root and not result[0]:raise Unbounded('parameter-cycle-without-value')
        return result
