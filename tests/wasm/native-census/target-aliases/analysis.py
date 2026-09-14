"""Independent alias/type semantics and real-front-end/optimizer witnesses."""
from collections import Counter
from copy import deepcopy
import importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('predicate_analysis',HERE.parent/'target-predicates/analysis.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
read,require,s,l,form,elements,context=prior.read,prior.require,prior.s,prior.l,prior.form,prior.elements,prior.context
CONTROLS={'prior':'ALIAS_FOLD','translate-first':'ALIAS_FOLD','shallow':'ALIAS_FOLD',
          'member-data':'LITERAL_DATA','optimizer-leak':'OPTIMIZER_SEMANTICS'}
SPANS=prior.SPANS+[('level-1/l1-typesys.lisp',5393,5558),('level-1/l1-typesys.lisp',4987,5391),('level-1/l1-typesys.lisp',5705,6105)]
def a(n):return s('CCL-TARGET-ALIASES::'+n)
def ll(*xs):return form(*xs)
def q(x):return ll(s('QUOTE'),x)
SMALL,LARGE=a('TARGET-SMALL'),a('TARGET-LARGE')
# A separate interpretation of the literal fixture definitions, not captured output.
BODIES={'TARGET-SMALL':s('FIXNUM'),'TARGET-LARGE':s('BIGNUM'),'SMALL-CHAIN':SMALL,
 'MAYBE-SMALL':ll(s('OR'),s('SYMBOL'),SMALL),'OUTSIDE-SMALL':ll(s('AND'),s('INTEGER'),ll(s('NOT'),SMALL)),
 'LITERAL-SMALL':ll(s('MEMBER'),SMALL),'EXPLICIT-WIDE':l(['SIGNED-BYTE',31]),'CYCLIC':a('CYCLIC')}
NAMES=['TARGET-SMALL','TARGET-LARGE','SMALL-CHAIN','MAYBE-SMALL','OUTSIDE-SMALL','CHOOSE-NUMBER','LITERAL-SMALL','EXPLICIT-WIDE','CYCLIC','GROWING']
CASES=[('small-max',536870911,SMALL),('small-boxed',536870912,SMALL),('small-min',-536870912,SMALL),
 ('small-negative-boxed',-536870913,SMALL),('large-boxed',536870912,LARGE),('large-immediate',536870911,LARGE),
 ('chain-boxed',536870912,a('SMALL-CHAIN')),('nested-or-boxed',536870912,a('MAYBE-SMALL')),
 ('nested-or-symbol',s('KEYWORD::FOO'),a('MAYBE-SMALL')),('nested-not-boxed',536870912,a('OUTSIDE-SMALL')),
 ('parameter-small',536870912,ll(a('CHOOSE-NUMBER'))),('parameter-large',536870912,ll(a('CHOOSE-NUMBER'),s('T'))),
 ('member-literal',SMALL,a('LITERAL-SMALL')),('explicit-wide',536870912,a('EXPLICIT-WIDE')),
 ('outer-or',536870912,ll(s('OR'),s('SYMBOL'),SMALL)),('outer-not',536870912,ll(s('NOT'),SMALL))]
OPT=[('recursive-or',ll(s('OR'),s('SYMBOL'),SMALL)),('expanded-or',a('MAYBE-SMALL')),
 ('recursive-and',ll(s('AND'),s('INTEGER'),ll(s('NOT'),SMALL))),('chain',a('SMALL-CHAIN')),
 ('parameter',ll(a('CHOOSE-NUMBER'),s('T')))]
VALUES=[-536870913,-536870912,536870911,536870912,s('KEYWORD::FOO')]
def normalize(x):
    """Return target type, successful alias edges (postorder), and leaf translations."""
    xs=elements(x) if isinstance(x,dict) and 'cons' in x else [x]
    name=next((n for n in NAMES if xs[0]==a(n)),None)
    if name:
        require(name not in ('CYCLIC','GROWING'),'ORACLE_RECURSION')
        expanded=(LARGE if len(xs)>1 and xs[1] is not None else SMALL) if name=='CHOOSE-NUMBER' else BODIES[name]
        answer,edges,leaves=normalize(expanded)
        return answer,edges+[dict(input=x,expanded=expanded,result=answer)],leaves
    if xs[0] in [s(n) for n in ('OR','AND','NOT')] and len(xs)>1:
        parts=[normalize(t) for t in xs[1:]]
        return ll(xs[0],*(p[0] for p in parts)),sum((p[1] for p in parts),[]),sum((p[2] for p in parts),[])
    return prior.translated(x),[],prior.translation_steps(x)
def membership(value,typ):
    if typ is None:return False
    if typ==s('T'):return True
    return prior.member(value,typ)
def expr(x,env):
    """Evaluate only the optimizer's explicit, bounded expression language."""
    if x is None:return None
    if not isinstance(x,dict):return x
    if 'symbol' in x:
        if x==s('T'):return True
        require(x['symbol'] in env,'EXPRESSION_VARIABLE');return env[x['symbol']]
    xs=elements(x);op=xs[0];args=xs[1:]
    if op==s('QUOTE'):return args[0]
    if op==s('LET'):
        bindings=elements(args[0]);local=dict(env)
        for binding in bindings:
            name,value=elements(binding);local[name['symbol']]=expr(value,env)
        require(len(args)==2,'EXPRESSION_LET');return expr(args[1],local)
    if op==s('OR'):return any(expr(y,env) for y in args)
    if op==s('AND'):return all(expr(y,env) for y in args)
    if op==s('NOT'):return not expr(args[0],env)
    if op==s('SYMBOLP'):return isinstance(expr(args[0],env),dict) and 'symbol' in expr(args[0],env)
    if op==s('CCL::FIXNUMP'):
        v=expr(args[0],env);return type(v) is int and -(2**60)<=v<2**60
    if op==s('CCL::BIGNUMP'):
        v=expr(args[0],env);return type(v) is int and not -(2**60)<=v<2**60
    if op in (s('TYPEP'),s('CCL::BUILTIN-TYPEP')):return membership(expr(args[0],env),expr(args[1],env))
    if op in (s('LOAD-TIME-VALUE'),s('CCL::FIND-BUILTIN-CELL')):return expr(args[0],env)
    raise ValueError('EXPRESSION_OPERATOR '+str(op))
def definitions(c):
    require(len(c['definitions'])==10,'DEFINITION_BOUND')
    for d,name in zip(c['definitions'],NAMES):
        context(d['reader']);require(d['compiled'] is True,'ALIAS_COMPILED')
        args=None;body=q(BODIES.get(name))
        if name=='CHOOSE-NUMBER':
            args=ll(s('&OPTIONAL'),ll(a('LARGE'),None));body=ll(s('IF'),a('LARGE'),q(LARGE),q(SMALL))
        if name=='GROWING':
            args=ll(s('&OPTIONAL'),ll(a('N'),0));body=ll(s('LIST*'),q(a('GROWING')),ll(s('LIST'),ll(s('1+'),a('N'))))
        require(d['form']==ll(s('DEFTYPE'),a(name),args,body),'DEFINITION_BODY')
        require(elements(d['lambda'])[0]==s('LAMBDA'),'ALIAS_LAMBDA')
def traversal_equivalence(first,second):
    """An injective renaming of the observer's identity namespace only."""
    keys={'site_id','function_id','id','parent_id','owner_id','variable_id','initializer_id'}
    forward={};reverse={}
    def walk(a,b,key=None):
        if key in keys and type(a) is int and type(b) is int:
            require(forward.setdefault(a,b)==b and reverse.setdefault(b,a)==a,'IDENTITY_BIJECTION');return
        require(type(a)==type(b),'TRAVERSAL_SHAPE')
        if isinstance(a,dict):
            require(a.keys()==b.keys(),'TRAVERSAL_KEYS')
            for k in a:walk(a[k],b[k],k)
        elif isinstance(a,list):
            require(len(a)==len(b),'TRAVERSAL_LENGTH')
            for x,y in zip(a,b):walk(x,y)
        else:require(a==b,'TRAVERSAL_CONTENT')
    walk(first,second);return len(forward)
def check(c,t):
    require(c['version']==1 and c['macro_environment_qualified'] is False and c['graph_edges_replaced']==0,'SCOPE')
    require(c['restored'] is True,'RESTORATION');definitions(c)
    require([(r['path'],r['start'],r['end']) for r in c['sources']]==SPANS,'SOURCE_BOUND')
    for r in c['sources']:
        context(r['reader']);text=(ROOT/r['path']).read_text()
        require(not r['host_reader'] and r['text']==text[r['start']:r['end']] and prior.previous.previous.previous.form_end(text,r['start'])==r['end'],'SOURCE_TEXT')
    require([p['name'] for p in c['probes']]==[n for n,_,_ in CASES],'PROBE_BOUND')
    expected_alias=[];true_count=0
    for p,(name,value,typ) in zip(c['probes'],CASES):
        target,edges,_=normalize(typ);answer=membership(value,target);true_count+=answer
        require(p['value']==value and p['type']==typ and p['form']==ll(s('LAMBDA'),None,ll(s('TYPEP'),q(value),q(typ))),'PROBE_INPUT')
        op='COMMON-LISP::T' if answer else 'NIL'
        require(p['operators']==['CCL::LAMBDA-LIST',op],'LITERAL_DATA' if name=='member-literal' else 'ALIAS_FOLD')
        require(p['ir']['operator']=='CCL::LAMBDA-LIST' and elements(p['ir']['operands'])[-2]==dict(operator=op,operands=None) and not p['function']['calls'],'ACTUAL_IR')
        require(len(p['events'])==1,'PROBE_EVENTS');e=p['events'][0];context(e['context'])
        require(e['operator']=='COMMON-LISP::TYPEP' and e['input']==ll(s('TYPEP'),q(value),q(typ)) and e['sequence']==0,'EVENT_INPUT')
        require(e['selected_id']==c['selected_id'],'PRIVATE_ROUTING')
        require(e['output']==(s('T') if answer else None) and e['status']=='RETURNED' and e['returned_input'] is False,'EVENT_OUTPUT')
        for _ in range(2):expected_alias += [dict(phase=name,event=0,**edge) for edge in edges]
    require([p['name'] for p in c['optimizer_probes']]==[n for n,_ in OPT],'OPTIMIZER_BOUND')
    for p,(name,typ) in zip(c['optimizer_probes'],OPT):
        target,edges,_=normalize(typ);wanted=[membership(v,target) for v in VALUES]
        require(p['type']==typ and p['input']==ll(s('TYPEP'),s('CCL::X'),q(typ)) and p['values']==VALUES,'OPTIMIZER_INPUT')
        require(p['answers']==wanted,'OPTIMIZER_SEMANTICS')
        require([bool(expr(p['expanded'],{'CCL::X':v})) for v in VALUES]==wanted,'EXPANSION_SEMANTICS')
        expected_alias += [dict(phase=name,event=-1,**edge) for edge in edges]
    require(c['refusals']==[dict(type=a('CYCLIC'),reason='ALIAS-CYCLE'),dict(type=a('GROWING'),reason='ALIAS-EXPANSION-LIMIT')],'EXPANSION_REFUSALS')
    require(c['alias_trace']==expected_alias,'ALIAS_EDGES')
    # Trace rows are checked for source context, exact parent population, target
    # input translation, membership, canonical semantics and optimizer result.
    events=sorted(c['events'],key=lambda e:e['sequence'])
    require(len(events)==293 and [e['sequence'] for e in events]==list(range(293)),'EVENT_BOUND')
    require([e['operator'] for e in events]==[m['operator'] for r in t['rows'] for m in r['macro_expansions']],'FILE_EVENT_JOIN')
    typed={e['sequence']:e for e in events if e['operator']=='COMMON-LISP::TYPEP'}
    require(list(typed)==[13,16,26,30,32,58,59,69,73,75],'FILE_TYPEP_BOUND')
    counters={};translations=[];file_counts=Counter()
    for r in c['trace']:
        context(r['context']);phase=r['phase'];helper=r['helper'];counters.setdefault(phase,Counter())[helper]+=1
        if phase=='dumplisp':
            require(r['event'] in typed,'FILE_TRACE_PARENT');event=typed[r['event']];context(event['context'])
            require(event['selected_id']==c['selected_id'],'FILE_ROUTING')
            _,thing,quoted=elements(event['input']);typ=elements(quoted)[1]
            file_counts[(r['event'],helper)]+=1
            if helper=='SPECIFIER-TYPE-IF-KNOWN':require(r['type']==typ and r['canonical']==typ,'FILE_CANONICAL')
            if helper=='TYPEP':require(r['thing']==typ and r['type']==s('SYMBOL'),'FILE_MEMBERSHIP')
            if helper=='OPTIMIZE-TYPEP':require(r['thing']==thing and r['type']==typ and r['answer']==event['output'],'FILE_OPTIMIZER_JOIN')
            if helper=='OPTIMIZE-CTYPEP':require(r['type']==typ,'FILE_CTYPE')
        else:require(r['event']==(-1 if phase in dict(OPT) else 0),'TRACE_PARENT')
        if helper=='TARGET-TYPE':
            require(r['answer']==prior.translated(r['input']),'LEAF_TRANSLATION');translations.append((r['input'],r['answer']))
        elif helper in ('TYPEP','SPECIFIER-TYPE-IF-KNOWN'):
            target,_,leaves=normalize(r['type']);require(r['target_type']==target,'NORMALIZATION_ORDER')
            require(translations==leaves,'TRANSLATION_BOUND');translations=[]
            if helper=='TYPEP':require(r['answer']==membership(r['thing'],target),'MEMBERSHIP')
            else:
                require(r['known'] is True,'KNOWN_TYPE')
                if phase!='dumplisp':
                    require([membership(v,r['canonical']) for v in VALUES]==[membership(v,target) for v in VALUES],'CANONICAL_SEMANTICS')
        elif helper=='OPTIMIZE-CTYPEP':require(r['cross_target'] is True and r['answer'] is None,'CTYPE_GUARD')
        elif helper=='OPTIMIZE-TYPEP':
            if phase!='dumplisp':
                key=r['thing']['symbol'];target,_,_=normalize(r['type'])
                require([bool(expr(r['answer'],{key:v})) for v in VALUES]==[membership(v,target) for v in VALUES],'RECURSIVE_OPTIMIZER')
        else:raise ValueError('TRACE_HELPER')
    require(not translations,'TRANSLATION_BOUND')
    expected={}
    for name,_,typ in CASES:
        expected[name]=Counter({'TARGET-TYPE':2*len(normalize(typ)[2]),'SPECIFIER-TYPE-IF-KNOWN':1,'TYPEP':1})
    for name,leaf,steps,guards in [('recursive-or',7,3,2),('expanded-or',7,3,2),('recursive-and',7,3,3),('chain',2,1,1),('parameter',6,3,3)]:
        expected[name]=Counter({'TARGET-TYPE':leaf,'SPECIFIER-TYPE-IF-KNOWN':steps,'TYPEP':steps,'OPTIMIZE-TYPEP':steps,'OPTIMIZE-CTYPEP':guards})
    expected['dumplisp']=Counter({'TARGET-TYPE':20,'SPECIFIER-TYPE-IF-KNOWN':10,'TYPEP':10,'OPTIMIZE-TYPEP':10,'OPTIMIZE-CTYPEP':8})
    require(counters==expected,'TRACE_BOUND')
    expected_file=Counter()
    for n in typed:
        for helper,count in [('TARGET-TYPE',2),('SPECIFIER-TYPE-IF-KNOWN',1),('TYPEP',1),('OPTIMIZE-TYPEP',1),('OPTIMIZE-CTYPEP',0 if n in (13,16) else 1)]:
            if count:expected_file[(n,helper)]=count
    require(file_counts==expected_file,'FILE_TRACE_BOUND')
    counts=prior.previous.previous.previous.prior.previous.check_capture(t,(ROOT/'lib/dumplisp.lisp').read_bytes(),read(HERE.parent/'target-descriptions/descriptions.json'))
    return dict(alias_definitions=10,constant_probes=16,true_probes=true_count,false_probes=16-true_count,optimizer_probes=5,optimizer_evaluations=25,expansion_refusals=2,alias_edges=len(expected_alias),trace_records=len(c['trace']),**counts)
def controls(c,t):
    cases=[('scope','SCOPE',lambda x:x.update(macro_environment_qualified=True)),('restore','RESTORATION',lambda x:x.update(restored=False)),
     ('definition','DEFINITION_BODY',lambda x:x['definitions'][0].update(form=None)),('omit-definition','DEFINITION_BOUND',lambda x:x['definitions'].pop()),
     ('source','SOURCE_TEXT',lambda x:x['sources'][-1].update(text='changed')),('extra-probe','PROBE_BOUND',lambda x:x['probes'].append(x['probes'][0])),
     ('boxed','ALIAS_FOLD',lambda x:x['probes'][1].update(operators=['CCL::LAMBDA-LIST','COMMON-LISP::T'])),
     ('actual-ir','ACTUAL_IR',lambda x:x['probes'][1]['ir'].update(operator='NIL')),('routing','PRIVATE_ROUTING',lambda x:x['probes'][0]['events'][0].update(selected_id=-1)),
     ('optimizer','OPTIMIZER_SEMANTICS',lambda x:x['optimizer_probes'][2].update(answers=[False]*5)),
     ('expansion','EXPANSION_SEMANTICS',lambda x:x['optimizer_probes'][0].update(expanded=s('T'))),
     ('omit-alias-edge','ALIAS_EDGES',lambda x:x['alias_trace'].pop()),('insert-alias-edge','ALIAS_EDGES',lambda x:x['alias_trace'].append(x['alias_trace'][0])),
     ('late-expansion','NORMALIZATION_ORDER',lambda x:next(r for r in x['trace'] if r['phase']=='small-boxed' and r['helper']=='SPECIFIER-TYPE-IF-KNOWN').update(target_type=s('FIXNUM'))),
     ('ctype','CTYPE_GUARD',lambda x:next(r for r in x['trace'] if r['helper']=='OPTIMIZE-CTYPEP').update(answer=s('T'))),
     ('cycle','EXPANSION_REFUSALS',lambda x:x['refusals'][0].update(reason='ALIAS-EXPANSION-LIMIT')),
     ('file-parent','FILE_TRACE_PARENT',lambda x:next(r for r in x['trace'] if r['phase']=='dumplisp').update(event=-1)),
     ('file-canonical','FILE_CANONICAL',lambda x:next(r for r in x['trace'] if r['phase']=='dumplisp' and r['helper']=='SPECIFIER-TYPE-IF-KNOWN').update(canonical=s('FIXNUM'))),
     ('file-routing','FILE_ROUTING',lambda x:next(e for e in x['events'] if e['sequence']==13).update(selected_id=-1)),
     ('trace-extra','TRACE_BOUND',lambda x:x['trace'].append(next(r for r in x['trace'] if r['helper']=='OPTIMIZE-CTYPEP')))]
    out=[]
    for name,reason,mutate in cases:
        x=deepcopy(c);mutate(x)
        try:check(x,t)
        except ValueError as e:require(str(e)==reason,'WRONG_CONTROL '+name+': '+str(e))
        else:raise ValueError('CONTROL_ESCAPED '+name)
        out.append(dict(name=name,status='REJECTED',reason=reason))
    return out
