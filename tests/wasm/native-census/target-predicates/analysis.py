"""Independent D1 membership and bounded TYPEP trace oracle."""
from collections import Counter
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('type_analysis',HERE.parent/'target-types/analysis.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
require,sym,form,elements,context=previous.require,previous.sym,previous.form,previous.elements,previous.context
SPANS=previous.SPANS+[('compiler/optimizers.lisp',66008,66505),('compiler/optimizers.lisp',61361,66006)]
CONTROLS={'inherited':'FIXNUM_FOLD','fixnum-only':'BIGNUM_FOLD','shallow':'COMPOUND_FOLD',
          'member-data':'MEMBER_DATA','host-ctype':'CTYPE_GUARD'}

def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def s(name):return sym(name if '::' in name else 'COMMON-LISP::'+name)
def l(x):
    if isinstance(x,list):return form(*(l(v) for v in x))
    return s(x) if isinstance(x,str) else x

def float_one(kind):return dict(float='COMMON-LISP::'+kind,significand=8388608 if kind=='SINGLE-FLOAT' else 4503599627370496,exponent=-23 if kind=='SINGLE-FLOAT' else -52,sign=1)

# Oracle inputs are explicit, separately from the native driver's Lisp corpus.
CASES=[('fixnum-zero',0,'FIXNUM'),('fixnum-max',536870911,'FIXNUM'),('fixnum-min',-536870912,'FIXNUM'),
 ('fixnum-positive-boxed',536870912,'FIXNUM'),('fixnum-negative-boxed',-536870913,'FIXNUM'),
 ('fixnum-single-float',float_one('SINGLE-FLOAT'),'FIXNUM'),
 ('bignum-positive',536870912,'BIGNUM'),('bignum-negative',-536870913,'BIGNUM'),
 ('bignum-immediate',536870911,'BIGNUM'),('bignum-large',1152921504606846976,'BIGNUM'),
 ('bignum-float',float_one('DOUBLE-FLOAT'),'BIGNUM'),
 ('or-boxed',536870912,['OR','SYMBOL','FIXNUM']),('or-symbol','KEYWORD::FOO',['OR','SYMBOL','FIXNUM']),
 ('not-fixnum',536870912,['NOT','FIXNUM']),('and-immediate',5,['AND','INTEGER','FIXNUM']),
 ('and-boxed',536870912,['AND','INTEGER',['NOT','FIXNUM']]),('bignum-complement',536870912,['NOT','BIGNUM']),
 ('member-fixnum-literal','FIXNUM',['MEMBER','FIXNUM']),('member-bignum-literal','BIGNUM',['MEMBER','BIGNUM']),
 ('member-integer-literal',536870912,['MEMBER',536870912]),
 ('explicit-signed-31',536870912,['SIGNED-BYTE',31]),('explicit-bound',536870912,['INTEGER',536870912,536870912])]
FIX=l(['SIGNED-BYTE',30])
BIG=l(['OR',['INTEGER','*',-536870913],['INTEGER',536870912]])
CANONICAL=([FIX]*6+[BIG]*5+[l(['OR','SYMBOL',['SIGNED-BYTE',30]])]*2+
 [l(['OR',['NOT','INTEGER'],['INTEGER','*',-536870913],['INTEGER',536870912]]),FIX,BIG,
  l(['OR',['NOT','INTEGER'],['SIGNED-BYTE',30]]),l(['MEMBER','FIXNUM']),l(['MEMBER','BIGNUM']),
  l(['INTEGER',536870912,536870912]),l(['SIGNED-BYTE',31]),l(['INTEGER',536870912,536870912])])

def member(value,typ):
    if typ==s('FIXNUM'):return type(value) is int and -(2**29)<=value<2**29
    if typ==s('BIGNUM'):return type(value) is int and not -(2**29)<=value<2**29
    if typ==s('INTEGER'):return type(value) is int
    if typ==s('SYMBOL'):return isinstance(value,dict) and 'symbol' in value
    xs=elements(typ);op,args=xs[0],xs[1:]
    if op==s('OR'):return any(member(value,a) for a in args)
    if op==s('AND'):return all(member(value,a) for a in args)
    if op==s('NOT'):return not member(value,args[0])
    if op==s('MEMBER'):return value in args
    if op==s('SIGNED-BYTE'):return type(value) is int and -(2**(args[0]-1))<=value<2**(args[0]-1)
    if op==s('INTEGER'):
        low,high=(args+[s('*')])[:2]
        return type(value) is int and (low==s('*') or value>=low) and (high==s('*') or value<=high)
    raise ValueError('UNSUPPORTED_ORACLE_TYPE')

def translated(x):
    if x==s('FIXNUM'):return FIX
    if x==s('BIGNUM'):return l(['AND','INTEGER',['NOT',['SIGNED-BYTE',30]]])
    if isinstance(x,dict) and 'cons' in x:
        xs=elements(x)
        if xs[0] in (s('OR'),s('AND'),s('NOT')):return form(xs[0],*(translated(a) for a in xs[1:]))
    return x

def translation_steps(x):
    steps=[]
    if isinstance(x,dict) and 'cons' in x:
        xs=elements(x)
        if xs[0] in (s('OR'),s('AND'),s('NOT')):
            for a in xs[1:]:steps+=translation_steps(a)
    return steps+[(x,translated(x))]

def check(c,traversal):
    require(c['version']==1 and c['macro_environment_qualified'] is False and c['graph_edges_replaced']==0,'SCOPE')
    require(c['restored'] is True,'RESTORATION')
    require([(r['path'],r['start'],r['end']) for r in c['sources']]==SPANS,'SOURCE_BOUND')
    for r in c['sources']:
        text=(ROOT/r['path']).read_text();context(r['reader'])
        require(not r['host_reader'] and r['text']==text[r['start']:r['end']] and
                previous.previous.previous.form_end(text,r['start'])==r['end'],'SOURCE_TEXT')
    guard_types=[l(['SIGNED-BYTE',30]),l(['SIMPLE-ARRAY',['UNSIGNED-BYTE',8],['*']])]
    require(c['guards']==[dict(type=t,answer=None) for t in guard_types],'CTYPE_GUARD')
    require([p['name'] for p in c['probes']]==[n for n,_,_ in CASES],'PROBE_BOUND')
    require(c['compiled'] and type(c['selected_id']) is int and type(c['native_ctype_helper_id']) is int,'COMPILED_BINDING')
    literal_by_id={r['id']:r for r in c['literals']}
    require(len(literal_by_id)==len(c['literals'])==5 and
        Counter((r['type'],r['name'],r['disposition']) for r in c['literals'])==Counter([
        ('CCL::LEXICAL-ENVIRONMENT',None,'UNQUALIFIED_NATIVE_LITERAL'),
        ('CCL::CLASS-CELL','CCL::IOBLOCK','UNQUALIFIED_NATIVE_LITERAL'),
        ('CCL::CLASS-WRAPPER','COMMON-LISP::RESTART','UNQUALIFIED_NATIVE_LITERAL'),
        ('COMMON-LISP::SINGLE-FLOAT',None,'UNQUALIFIED_NATIVE_LITERAL'),
        ('COMMON-LISP::DOUBLE-FLOAT',None,'UNQUALIFIED_NATIVE_LITERAL')]),'NATIVE_LITERAL_SCOPE')
    expected_true=0
    for p,(name,value,typ) in zip(c['probes'],CASES):
        value,typ=l(value),l(typ)
        require(p['value']==value and p['type']==typ and p['form']==form(s('LAMBDA'),None,
                form(s('TYPEP'),form(s('QUOTE'),value),form(s('QUOTE'),typ))),'PROBE_INPUT')
        expected=member(value,typ);expected_true+=expected
        reason=('FIXNUM_FOLD' if name.startswith('fixnum-') else 'BIGNUM_FOLD' if name.startswith('bignum-')
                else 'MEMBER_DATA' if name.startswith('member-') else 'COMPOUND_FOLD')
        op='COMMON-LISP::T' if expected else 'NIL'
        require(p['operators']==['CCL::LAMBDA-LIST',op],reason)
        require(p['ir']['operator']=='CCL::LAMBDA-LIST' and
                elements(p['ir']['operands'])[-2]==dict(operator=op,operands=None) and not p['function']['calls'],'ACTUAL_IR')
        require(len(p['events'])==1,'PROBE_EVENT_BOUND')
        event=p['events'][0];ev_value=elements(elements(event['input'])[1])[1]
        if isinstance(value,dict) and 'float' in value:
            require(set(ev_value)=={'object_ref'} and literal_by_id[ev_value['object_ref']]['type']==value['float'],'FLOAT_EVENT_LITERAL')
        else:require(ev_value==value,'PROBE_EVENT_INPUT')
        require(event['sequence']==0 and event['operator']=='COMMON-LISP::TYPEP' and
                event['input']==form(s('TYPEP'),form(s('QUOTE'),ev_value),form(s('QUOTE'),typ)),'PROBE_EVENT_INPUT')
        require(event['output']==(s('T') if expected else None) and event['returned_input'] is False and event['status']=='RETURNED','PROBE_EXPANSION')
        require(event['selected_id']==c['selected_id'],'PRIVATE_ROUTING');context(event['context'])
    expected_pass=[form(s('TYPEP'),s('CCL::X'),s('TYPE')),form(s('TYPEP'),s('CCL::X'),form(s('QUOTE'),s('FIXNUM')),s('CCL::ENV'))]
    require(c['passthrough']==[dict(input=x,output=x,same=True) for x in expected_pass],'PASSTHROUGH')
    events=sorted(c['events'],key=lambda e:e['sequence'])
    require(len(events)==293 and [e['sequence'] for e in events]==list(range(293)),'EVENT_BOUND')
    original=[m for r in traversal['rows'] for m in r['macro_expansions']]
    require([e['operator'] for e in events]==[e['operator'] for e in original],'EVENT_JOIN')
    typed=[e for e in events if e['operator']=='COMMON-LISP::TYPEP']
    require([e['sequence'] for e in typed]==[13,16,26,30,32,58,59,69,73,75],'FILE_TYPEP_BOUND')
    # Bound every trace row to an independently reconstructed record, in order.
    wanted=[]
    def add(helper,phase,event,**fields):wanted.append(dict(helper=helper,phase=phase,event=event,**fields))
    def add_translation(x,phase,event):
        for a,b in translation_steps(x):add('TARGET-TYPE',phase,event,input=a,answer=b)
    for event in typed:
        context(event['context']);require(event['selected_id']==c['selected_id'],'PRIVATE_ROUTING')
        _,thing,quoted=elements(event['input']);typ=elements(quoted)[1];n=event['sequence']
        if n in (13,16):
            require(typ==s('CCL::BASIC-STREAM') and thing==s('CCL::O'),'FILE_TYPE_INPUT')
            answer=form(s('CCL::BASIC-STREAM-P'),thing)
        elif n in (58,59):
            require(typ==s('CCL::BUFFERED-STREAM-MIXIN') and thing==s('CCL::O'),'FILE_TYPE_INPUT')
            answer=form(s('CCL::STD-INSTANCE-CLASS-CELL-TYPEP'),thing,
                form(s('LOAD-TIME-VALUE'),form(s('CCL::FIND-CLASS-CELL'),form(s('QUOTE'),typ),s('T'))))
        else:
            require(typ==s('CCL::IOBLOCK') and thing==s('CCL::S'),'FILE_TYPE_INPUT')
            cell=next(r['id'] for r in c['literals'] if r['name']=='CCL::IOBLOCK')
            answer=form(s('CCL::STRUCTURE-TYPEP'),thing,form(s('QUOTE'),dict(object_ref=cell)))
        require(event['output']==answer,'FILE_TYPE_OUTPUT')
        add_translation(typ,'dumplisp',n)
        add('SPECIFIER-TYPE-IF-KNOWN','dumplisp',n,type=typ,target_type=typ,known=True,canonical=typ)
        add_translation(s('SYMBOL'),'dumplisp',n)
        add('TYPEP','dumplisp',n,thing=typ,type=s('SYMBOL'),target_type=s('SYMBOL'),answer=True)
        if n not in (13,16):add('OPTIMIZE-CTYPEP','dumplisp',n,cross_target=True,type=typ,answer=None)
        add('OPTIMIZE-TYPEP','dumplisp',n,thing=thing,type=typ,answer=answer)
    for typ in guard_types:add('OPTIMIZE-CTYPEP','ctype-guard',None,cross_target=True,type=typ,answer=None)
    for (name,value,typ),canonical in zip(CASES,CANONICAL):
        value,typ=l(value),l(typ)
        add_translation(typ,name,0)
        add('SPECIFIER-TYPE-IF-KNOWN',name,0,type=typ,target_type=translated(typ),known=True,canonical=canonical)
        add_translation(typ,name,0)
        add('TYPEP',name,0,thing=value,type=typ,target_type=translated(typ),answer=member(value,typ))
    actual=[]
    for r in c['trace']:
        context(r['context']);actual.append({k:v for k,v in r.items() if k!='context'})
    require(len(actual)==len(wanted),'TRACE_BOUND')
    for a,b in zip(actual,wanted):
        require((a['helper'],a['phase'],a['event'])==(b['helper'],b['phase'],b['event']),'TRACE_PARENT')
        require(a==b,'TRACE_CONTENT')
    counts=previous.previous.previous.prior.previous.check_capture(traversal,(ROOT/'lib/dumplisp.lisp').read_bytes(),
        read(HERE.parent/'target-descriptions/descriptions.json'))
    return dict(source_forms=11,constant_probes=len(CASES),true_probes=expected_true,false_probes=len(CASES)-expected_true,
        ctype_guard_probes=2,passthrough_probes=2,file_typep_events=len(typed),trace_records=len(wanted),
        full_macro_environment_qualified=False,**counts)


def controls(c,t):
    cases=[('scope','SCOPE',lambda x:x.update(macro_environment_qualified=True)),
      ('omit-source','SOURCE_BOUND',lambda x:x['sources'].pop()),
      ('source-body','SOURCE_TEXT',lambda x:x['sources'][-1].update(text='wrong')),
      ('omit-probe','PROBE_BOUND',lambda x:x['probes'].pop()),
      ('insert-probe','PROBE_BOUND',lambda x:x['probes'].append(deepcopy(x['probes'][0]))),
      ('value','PROBE_INPUT',lambda x:x['probes'][0].update(value=1)),
      ('fold-boxed','FIXNUM_FOLD',lambda x:x['probes'][3].update(operators=['CCL::LAMBDA-LIST','COMMON-LISP::T'])),
      ('ir','ACTUAL_IR',lambda x:x['probes'][3]['ir'].update(operator='COMMON-LISP::T')),
      ('expansion','PROBE_EXPANSION',lambda x:x['probes'][0]['events'][0].update(output=None)),
      ('routing','PRIVATE_ROUTING',lambda x:x['probes'][0]['events'][0].update(selected_id=-1)),
      ('ctype-guard','CTYPE_GUARD',lambda x:x['guards'][0].update(answer=s('T'))),
      ('passthrough-identity','PASSTHROUGH',lambda x:x['passthrough'][0].update(same=False)),
      ('native-class-scope','NATIVE_LITERAL_SCOPE',lambda x:x['literals'][1].update(disposition='QUALIFIED')),
      ('erase-class-dependency','FILE_TYPE_OUTPUT',lambda x:next(e for e in x['events'] if e['sequence']==58).update(output=s('T'))),
      ('omit-trace','TRACE_BOUND',lambda x:x['trace'].pop()),
      ('insert-trace','TRACE_BOUND',lambda x:x['trace'].append(deepcopy(x['trace'][0]))),
      ('parent','TRACE_PARENT',lambda x:x['trace'][0].update(event=-1)),
      ('translation','TRACE_CONTENT',lambda x:x['trace'][0].update(answer=s('FIXNUM'))),
      ('canonical-bounds','TRACE_CONTENT',lambda x:next(r for r in x['trace'] if r['phase']=='bignum-positive' and r['helper']=='SPECIFIER-TYPE-IF-KNOWN').update(canonical=s('BIGNUM'))),
      ('literal-data','TRACE_CONTENT',lambda x:next(r for r in x['trace'] if r['phase']=='member-fixnum-literal').update(answer=l(['MEMBER',['SIGNED-BYTE',30]]))),
      ('membership-answer','TRACE_CONTENT',lambda x:next(r for r in x['trace'] if r['phase']=='fixnum-positive-boxed' and r['helper']=='TYPEP').update(answer=True)),
      ('restoration','RESTORATION',lambda x:x.update(restored=False))]
    out=[]
    for name,reason,mutate in cases:
        changed=deepcopy(c);mutate(changed)
        try:check(changed,t)
        except ValueError as e:require(str(e)==reason,'WRONG_CONTROL_REASON '+name+': '+str(e))
        else:raise ValueError('CONTROL_ESCAPED '+name)
        out.append(dict(name=name,status='REJECTED',reason=reason))
    return out
