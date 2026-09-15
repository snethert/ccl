"""Join a plain DEFSTRUCT's keyword defaults to its actual allocation slots.

The declaration, generated constructor and compiler IR must be from the same
execution. This is a constructor-flow rule, not a closed-world registry rule:
supplied keywords and later stores remain dependencies of every field.
"""
from copy import deepcopy
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'finite-callees'))
from run import read,save,convert,require,load_module,ROOT
from finite import Graph
Raw=load_module('structure_raw',HERE.parent/'rich-observation/analyze.py').Graph


def named(n,package,name):
    return n.get('kind')=='symbol' and n.get('package')==package and n.get('name')==name


def literal(g,ref,raw=False):
    n=g.node(ref)
    if raw:
        if n=={'atom':'nil'}:return None
        if 'integer' in n:return n['integer']
        if named(n,'COMMON-LISP','T'):return True
        xs=g.items(ref)
        require(len(xs)==2 and named(g.node(xs[0]),'COMMON-LISP','QUOTE'),'STRUCT_SOURCE_LITERAL')
        n=g.node(xs[1]);require(n.get('kind')=='symbol','STRUCT_QUOTED_SYMBOL')
        return dict(identity=n['id'],symbol=n['package']+'::'+n['name'])
    require(n and n['kind']=='acode','STRUCT_IR_LITERAL')
    op=n['operator'];args=g.items(n['operands'])
    if op in ('NIL','COMMON-LISP::T'):
        require(not args,'STRUCT_BOOLEAN_ARGS');return op=='COMMON-LISP::T' or None
    require(op in ('COMMON-LISP::FIXNUM','CCL::IMMEDIATE') and len(args)==1,'STRUCT_IR_LITERAL')
    require(type(args[0]) is int or isinstance(args[0],dict) and set(args[0])=={'identity','symbol'},'STRUCT_LITERAL_VALUE')
    return args[0]


def derive(enter,leave,ir,operators):
    require(enter['kind']=='expander-enter' and leave['kind']=='expander-return' and
            leave['parent']==enter['sequence'] and ir['kind']=='before-pass2' and
            enter['sequence']<leave['sequence']<ir['sequence'],'STRUCT_EVENT_CHAIN')
    require(all(enter[k]==leave[k]==ir[k] for k in ('process','source','source_position')),'STRUCT_CONTEXT')
    a=Raw(enter['payload']);b=Raw(leave['payload']);args=a.items();ret=b.items()
    require(len(args)==4 and len(ret)==5 and args==ret[:4],'STRUCT_EXPANSION_ARGUMENTS')
    form=a.items(args[2]);require(named(a.node(form[0]),'COMMON-LISP','DEFSTRUCT'),'STRUCT_FORM')
    typ=a.node(form[1]);require(typ.get('kind')=='symbol','STRUCT_PLAIN_NAME')
    slots=[]
    for ref in form[2:]:
        n=a.node(ref)
        if n.get('kind')=='symbol':slot=n;default=None
        else:
            xs=a.items(ref);slot=a.node(xs[0]);require(len(xs)>=2,'STRUCT_SLOT_FORM')
            default=literal(a,xs[1],raw=True)
        require(slot.get('kind')=='symbol','STRUCT_SLOT_NAME');slots.append((slot,default))
    outs=b.items(ret[-1]);require(len(outs)==1,'STRUCT_EXPANSION_VALUES')
    expanded=b.items(outs[0]);require(named(b.node(expanded[0]),'COMMON-LISP','PROGN'),'STRUCT_EXPANSION_TOP')
    rawir=Raw(ir['payload']['ir']);root=rawir.node(rawir.root)
    ctor_symbol=rawir.node(root['name']);matches=[]
    for v in expanded[1:]:
        xs=b.items(v)
        if named(b.node(xs[0]),'COMMON-LISP','DEFUN') and b.node(xs[1])==ctor_symbol:matches.append(xs)
    require(len(matches)==1 and len(matches[0])==4,'STRUCT_CONSTRUCTOR_DEFINITION')
    generated=matches[0];params=b.items(generated[2]);body=b.items(generated[3])
    require(named(b.node(params[0]),'COMMON-LISP','&KEY') and len(params)==len(slots)+1,'STRUCT_KEY_PARAMETERS')
    require(named(b.node(body[0]),'CCL','GVECTOR') and named(b.node(body[1]),'KEYWORD','STRUCT') and
            len(body)==len(slots)+3,'STRUCT_ALLOCATION_SOURCE')
    cell=b.items(body[2]);require(len(cell)==2 and named(b.node(cell[0]),'COMMON-LISP','QUOTE'),'STRUCT_CELL_QUOTE')
    # CCL prints a class-cell as an opaque object inside a singleton list.
    cell_items=b.items(cell[1]);require(len(cell_items)==1,'STRUCT_CLASS_CELL')
    classcell=b.node(cell_items[0]);require(classcell.get('type')=='CCL::CLASS-CELL','STRUCT_CLASS_CELL')
    capture=convert(ir['payload'],operators);g=Graph(capture['flow']);g.check(capture['function'])
    owner=capture['function']['function_id'];lam=g.node(g.nodes[owner]['body'])
    require(lam['operator']=='CCL::LAMBDA-LIST','STRUCT_CONSTRUCTOR_LAMBDA')
    la=g.items(lam['operands']);require(len(la)==7 and all(x is None for x in la[:3]),'STRUCT_CONSTRUCTOR_SIGNATURE')
    keys=g.items(la[3]);require(len(keys)==5 and keys[0] is None,'STRUCT_KEY_SHAPE')
    variables=g.items(keys[1]);defaults=g.items(keys[3]);kw=rawir.node(keys[4])
    require(kw.get('kind')=='simple-vector' and kw['expanded'] and
            kw['length']==len(kw['elements'])==len(slots)==len(variables)==len(defaults),'STRUCT_KEY_VECTOR')
    allocation=g.node(la[5]);require(allocation['operator']=='CCL::%GVECTOR','STRUCT_ALLOCATION_IR')
    ar=g.items(allocation['operands']);require(len(ar)==1,'STRUCT_ALLOCATION_ARGS')
    parts=g.items(ar[0]);require(len(parts)==2,'STRUCT_ALLOCATION_ARGPARTS')
    vals=g.items(parts[0])+list(reversed(g.items(parts[1])))
    require(len(vals)==len(slots)+2,'STRUCT_ALLOCATION_LENGTH')
    cv=g.node(vals[1]);require(cv['operator']=='CCL::IMMEDIATE','STRUCT_CELL_IR')
    cvargs=g.items(cv['operands']);require(len(cvargs)==1 and cvargs[0]==cell[1],'STRUCT_CELL_IDENTITY')
    ircells=rawir.items(cvargs[0]);require(len(ircells)==1 and rawir.node(ircells[0])==classcell,'STRUCT_CELL_CONTENTS')
    result=[]
    for ix,((slot,default),p,v,d,k,value,source_value) in enumerate(zip(slots,params[1:],variables,defaults,kw['elements'],vals[2:],body[3:]),1):
        pp=b.items(p);require(len(pp)==2,'STRUCT_GENERATED_PARAMETER')
        pair=b.items(pp[0]);require(len(pair)==2,'STRUCT_GENERATED_KEY')
        keyword=b.node(pair[0]);sourcevar=b.node(pair[1]);var=g.node(v)
        require(keyword==rawir.node(k) and keyword.get('package')=='KEYWORD' and keyword['name']==slot['name'],
                'STRUCT_KEY_SLOT_IDENTITY')
        require(var and var['kind']=='variable' and rawir.node({'ref':var['id']})['name']==pair[1],
                'STRUCT_VARIABLE_IDENTITY')
        # TYPECHECK wrappers may guard a stored argument; identify the actual
        # constructor variable inside, without treating a guard as a callee.
        sv=b.node(source_value)
        if sv.get('kind')=='cons':
            sx=b.items(source_value);require(len(sx)==3 and named(b.node(sx[0]),'CCL','TYPECHECK'),'STRUCT_SOURCE_STORE')
            sv=b.node(sx[1])
        require(sv==sourcevar,'STRUCT_SOURCE_VALUE')
        stored=g.node(value)
        seen=set()
        while stored and stored.get('operator') in ('CCL::TYPED-FORM','CCL::TYPE-ASSERTED-FORM'):
            require(stored['id'] not in seen,'STRUCT_VALUE_CYCLE');seen.add(stored['id'])
            stored=g.node(g.items(stored['operands'])[1])
        # A guard can invoke a restart which supplies a replacement value.
        # Only a direct lexical reference proves argument-to-slot identity;
        # guard expansions stay open even when their defaults are known.
        direct=stored and stored['operator']=='CCL::LEXICAL-REFERENCE'
        if direct:
            require(g.node(g.items(stored['operands'])[0])['root']==var['root'],'STRUCT_STORED_VARIABLE')
        else:
            require(sv==sourcevar and b.node(source_value).get('kind')=='cons','STRUCT_UNEXPECTED_STORE')
        require(literal(b,pp[1],raw=True)==default==literal(g,d),'STRUCT_DEFAULT_VALUE')
        result.append(dict(index=ix,slot=slot,keyword=keyword,variable=var['root'],default=default,
                           default_ir=d,stored_ir=value,flow='DIRECT_ARGUMENT' if direct else 'GUARDED_VALUE_OPEN'))
    return dict(type_symbol=typ,constructor_symbol=ctor_symbol,function=owner,
                declaration_event=enter['sequence'],expansion_event=leave['sequence'],ir_event=ir['sequence'],
                native_subtag=literal(g,vals[0]),class_cell=classcell,fields=result,
                supplied_arguments='OPEN',later_stores='OPEN',target_layout='UNQUALIFIED')


def project(base,model,fields):
    edges=[];nodes=[];ids={n['id'] for n in base['nodes']};typeid=model['type_symbol']['id']
    for f in model['fields']:
        key=str(typeid)+':'+str(f['index'])
        if key not in fields:continue
        require(f['flow']=='DIRECT_ARGUMENT','STRUCT_CALLBACK_GUARD_NOT_QUALIFIED')
        require(fields[key]['type_symbol']==dict(identity=typeid,symbol=model['type_symbol']['package']+'::'+model['type_symbol']['name']),
                'STRUCT_FIELD_TYPE_IDENTITY')
        owner='field-values:'+key;constructor='identity:build:afunc:'+str(model['function'])
        require(owner in ids and constructor in ids,'STRUCT_GRAPH_ENDPOINT')
        edges.append(dict(zip(('from','targets','phase','origin','resolution','evidence'),
            (owner,[constructor],'run','conservative','complete','structure-values/constructor/'+key))))
        default=f['default']
        if isinstance(default,dict):
            target='identity:build:binding-cell:'+str(default['identity'])
            if target not in ids:
                ids.add(target);nodes.append(dict(id=target,kind='function',required=True,disposition='unresolved',implementation=None,
                    reason='Constructor-default symbol designator '+default['symbol']+'; callable values remain unbounded.',
                    evidence='structure-values/symbol/'+str(default['identity']),tests=['S0-LL15-b','S0-LL15-c']))
                edges.append(dict(zip(('from','targets','phase','origin','resolution','evidence'),
                    (target,[],'run','conservative','unresolved','structure-values/value/'+str(default['identity'])))))
            edges.append(dict(zip(('from','targets','phase','origin','resolution','evidence'),
                (owner,[target],'run','conservative','complete','structure-values/default/'+key))))
    return dict(nodes=nodes,edges=edges)


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    ops={int(k):v for k,v in next(iter(read(a.evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))['operators'].items()}
    rs=read(a.expansions);ir=read(a.ir);enter=rs[0];leave=rs[1]
    model=derive(enter,leave,ir,ops);controls=[]
    # Corrupt the raw capture inputs: wrong context, callback variable,
    # default and keyword position must fail at the actual source/IR join.
    def raw_node(row,ident):
        return next(n for n in row['payload']['ir']['objects'] if n['id']==ident)
    def change_default(row):
        g=Raw(row['payload']['ir'])
        a=g.node(g.node(model['fields'][8]['default_ir'])['operands'])
        b=g.node(g.node(model['fields'][9]['default_ir'])['operands'])
        a['car'],b['car']=b['car'],a['car']
    def change_variable(row):
        n=raw_node(row,model['fields'][8]['stored_ir']['ref'])
        raw_node(row,n['operands']['ref'])['car']={'ref':model['fields'][9]['variable']}
    def exchange_keywords(row):
        c=convert(row['payload'],ops);g=Graph(c['flow']);lam=g.node(g.nodes[model['function']]['body'])
        keys=g.items(g.items(lam['operands'])[3]);v=raw_node(row,keys[4]['ref'])
        v['elements'][8],v['elements'][9]=v['elements'][9],v['elements'][8]
    for name,mutate,reason in [
        ('cross-execution',lambda r:r.update(process=r['process']+1),'STRUCT_CONTEXT'),
        ('default-substitution',change_default,'STRUCT_DEFAULT_VALUE'),
        ('stored-variable-substitution',change_variable,'STRUCT_STORED_VARIABLE'),
        ('keyword-position-swap',exchange_keywords,'STRUCT_KEY_SLOT_IDENTITY')]:
        damaged=deepcopy(ir);mutate(damaged)
        try:derive(enter,leave,damaged,ops)
        except ValueError as e:
            require(str(e)==reason,'STRUCT_CONTROL_REASON '+name+': '+str(e))
        else:raise ValueError('STRUCT_CONTROL_ESCAPED '+name)
        controls.append(dict(name=name,status='REJECTED',reason=reason))
    base=read(a.base);fields=read(a.fields)['fields'];delta=project(base,model,fields)
    graph=dict(base,nodes=base['nodes']+delta['nodes'],edges=base['edges']+delta['edges'])
    errors=load_module('structure_contract',ROOT/'doc/WASM/tools/check-census.py').validate(graph)
    require(all(e.startswith(('unresolved reachable edge from ','unimplemented reachable node ')) for e in errors),'STRUCT_GRAPH_STRUCTURE')
    for name,value in [('constructor.json',model),('delta.json.gz',delta),('census.json.gz',graph),('controls.json',controls)]:save(a.output/name,value)
    summary=dict(status='PASS',constructor_fields=len(model['fields']),
        joined_callback_fields=sum(e['evidence'].startswith('structure-values/constructor/') for e in delta['edges']),
        new_callee_bounds=0,controls=len(controls),census_status='BLOCKED')
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('expansions','ir','base','fields','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():
            (a.output/'failure.txt').write_text(traceback.format_exc())
            (a.output/'executed-source.py').write_bytes(Path(__file__).read_bytes())
        raise
