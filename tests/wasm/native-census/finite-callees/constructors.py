"""Source-qualified CONSTANTLY results for NIL/T; cell contents stay open.

The copy path is tested natively but remains unresolved: its result additionally
depends on the internal copy/store callees and must not borrow their semantics.
"""
from copy import deepcopy
from lookups import Resolver as LookupResolver
from finite import require,Unbounded


def shape(capture):
    resolver=LookupResolver(capture);g=resolver.graph;variables={}
    def visit(value,active=()):
        n=g.node(value)
        if n is None:
            return {k:v for k,v in value.items() if k!='identity'} if isinstance(value,dict) else value
        require(n['id'] not in active,'CONSTRUCTOR_IR_CYCLE');active=active+(n['id'],)
        if n['kind']=='variable':return dict(variable=variables.setdefault(n['root'],len(variables)),assigned=n['assigned'])
        if n['kind']=='acode':return [n['operator']]+[visit(v,active) for v in g.items(n['operands'])]
        if n['kind']=='cons':return [visit(v,active) for v in g.items(value)]
        raise ValueError('CONSTRUCTOR_IR_KIND')
    return visit(g.nodes[g.root]['body'])


def symbols(captures):
    result={}
    for c in captures:
        for n in c['ir']['objects']:
            if n['kind']!='symbol':continue
            key=(n['package'],n['name'])
            require(key not in result or result[key]==n,'CONSTRUCTOR_SYMBOL_IDENTITY')
            result[key]=n
    return result


def model(original,native,convert,operators):
    require(original['kind']=='before-pass2' and original['payload']['function']['name']=='COMMON-LISP::CONSTANTLY',
            'CONSTRUCTOR_DEFINITION')
    source=[r for r in native['captures'] if r['case']=='constructor-source']
    require(len(source)==1 and native['factory_checks']==12 and native['restored'] is True,'CONSTRUCTOR_NATIVE_QUALIFICATION')
    native_ops={r['id']:r['name'] for r in native['snapshot']['operators']}
    expected=shape(convert(source[0],native_ops));actual=shape(convert(original['payload'],operators))
    require(actual==expected,'CONSTRUCTOR_SOURCE_IR')
    # Exact tested U1 return structure. Do not turn arbitrary function factories
    # or same-named local functions into this three-provider contract.
    require(actual[0]=='CCL::LAMBDA-LIST' and len(actual[1])==1 and actual[2:4]==[None,None],
            'CONSTRUCTOR_SIGNATURE')
    body=actual[6]
    require(body[0]=='COMMON-LISP::IF' and body[2]==['CCL::%FUNCTION',{'symbol':'CCL::FALSE'}]
        and body[3][0]=='COMMON-LISP::IF' and body[3][2]==['CCL::%FUNCTION',{'symbol':'CCL::TRUE'}],
        'CONSTRUCTOR_RETURN_PATHS')
    syms=symbols([original['payload']])
    nodes={n['id']:n for n in original['payload']['ir']['objects']}
    root=nodes[original['payload']['ir']['root']['ref']]
    require(root['parent'] is None and root['name']=={'ref':syms['COMMON-LISP','CONSTANTLY']['id']},
            'CONSTRUCTOR_DEFINITION_SYMBOL')
    return dict(constructor=syms['COMMON-LISP','CONSTANTLY'],
        providers={name:syms['CCL',name] for name in ('FALSE','TRUE','CONSTANT-REF')},
        event=original['sequence'],function=original['payload']['function']['function_id'],
        source_ir=actual,copy_contents_qualified=False)


def native_model(raw):
    syms=symbols(raw['captures'])
    return dict(constructor=syms['COMMON-LISP','CONSTANTLY'],
        providers={name:syms['CCL',name] for name in ('FALSE','TRUE','CONSTANT-REF')},
        event='native-probe',function=None,copy_contents_qualified=False)


class Resolver(LookupResolver):
    def __init__(self,capture,constructor):
        super().__init__(capture);self.constructor=constructor
        self.auxiliary_symbols={s['id']:s for s in constructor['providers'].values()}

    def resolve(self,value,owner,site,stack=()):
        g=self.graph;n=g.node(value)
        if n and n.get('operator')=='CCL::CALL':
            args=g.items(n['operands'])
            if len(args)==3 and args[2] is None:
                op=g.node(args[0]);forms=g.items(op['operands']) if op and op.get('operator')=='CCL::IMMEDIATE' else []
                if forms==[dict(symbol='COMMON-LISP::CONSTANTLY',identity=self.constructor['constructor']['id'])]:
                    if n['id'] in stack or len(stack)>=128:raise Unbounded('constructor-expression-cycle')
                    parts=g.items(args[1]);require(len(parts)==2,'CONSTRUCTOR_ARGUMENT_PARTS')
                    actual=g.items(parts[0])+list(reversed(g.items(parts[1])))
                    if len(actual)!=1:raise Unbounded('constructor-arity')
                    arg=g.node(actual[0]);known=arg.get('operator') if arg else None
                    if known=='NIL':providers=['FALSE']
                    elif known=='COMMON-LISP::T':providers=['TRUE']
                    else:raise Unbounded('constructor-copy-path-not-qualified')
                    return ({('symbol',self.constructor['providers'][name]['id'],
                        'copied-function-cell-body' if name=='CONSTANT-REF' else 'captured-function-cell-value') for name in providers},
                        [dict(node=n['id'],operator='COMMON-LISP::CONSTANTLY',
                              source_event=self.constructor['event'],source_function=self.constructor['function'],
                              provider_names=providers,copy_identity=False,data_contents_qualified=False)])
        return super().resolve(value,owner,site,stack)


def controls(original,native,convert,operators):
    model(original,native,convert,operators);result=[]
    def reject(name,changed):
        try:model(changed,native,convert,operators)
        except ValueError:result.append(dict(name=name,status='REJECTED'))
        else:raise ValueError('CONSTRUCTOR_SOURCE_CONTROL_ESCAPED '+name)
    for name,old,new in [('replace-false-provider','FALSE','TRUE'),('replace-copy-provider','CONSTANT-REF','FALSE'),
                          ('replace-copy-operation','%COPY-FUNCTION','IDENTITY'),
                          ('replace-data-store','%SET-NTH-IMMEDIATE','SET-CODE')]:
        changed=deepcopy(original)
        for n in changed['payload']['ir']['objects']:
            if n['kind']=='symbol' and n['name']==old and n['package']=='CCL':n['name']=new
        reject(name,changed)
    return result
