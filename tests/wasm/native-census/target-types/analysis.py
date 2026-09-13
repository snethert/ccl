"""Bounded independent oracle for declared numeric types and EQL lowering."""
from collections import Counter
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location('helper_analysis', HERE.parent/'target-helpers/analysis.py')
previous = importlib.util.module_from_spec(spec); spec.loader.exec_module(previous)
require, sym, form, elements, context = previous.require, previous.sym, previous.form, previous.elements, previous.context
CONTROLS = {'prior':'BOXED_TYPE_LOWERING', 'shallow':'BOXED_TYPE_LOWERING',
            'host-range':'BOXED_TYPE_LOWERING', 'trust':'DECLARATION_POLICY'}
SPANS = [('compiler/optimizers.lisp',7408,7953), ('compiler/nx0.lisp',80372,80629),
         ('compiler/optimizers.lisp',20905,21052), ('compiler/nx0.lisp',119274,119534),
         ('compiler/nx0.lisp',117651,118833), ('compiler/nx-basic.lisp',16754,17001),
         ('compiler/nx0.lisp',27546,27807), ('compiler/optimizers.lisp',75294,75408),
         ('compiler/optimizers.lisp',71635,72010)]


def read(p): return json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())
def lisp(x):
    if isinstance(x,list): return form(*(lisp(v) for v in x))
    if isinstance(x,str): return sym(('KEYWORD::'+x[1:]) if x.startswith(':') else 'COMMON-LISP::'+x)
    return x


CASES = [('symbol','SYMBOL',True), ('character','CHARACTER',True), ('fixnum','FIXNUM',True),
    ('signed-30',['SIGNED-BYTE',30],True), ('signed-31',['SIGNED-BYTE',31],False),
    ('positive-boxed',['INTEGER',536870912,536870912],False),
    ('negative-boxed',['INTEGER',-536870913,-536870913],False),
    ('single-float','SINGLE-FLOAT',False), ('double-float','DOUBLE-FLOAT',False),
    ('mixed-boxed',['OR','SYMBOL',['INTEGER',536870912,536870912]],False),
    ('mixed-immediate',['OR','SYMBOL',['INTEGER',0,5]],True), ('unknown','T',False),
    ('symbol-members',['MEMBER',':FOO',':BAR'],True), ('literal-fixnum',['MEMBER','FIXNUM'],True),
    ('untrusted-symbol','SYMBOL',False)]
QUERY = lisp(['OR','FIXNUM','SYMBOL','CHARACTER',['AND',['NOT','NUMBER'],['NOT','CCL_MACPTR']]])
# MACPTR belongs to CCL, not COMMON-LISP.
QUERY = json.loads(json.dumps(QUERY).replace('COMMON-LISP::CCL_MACPTR','CCL::MACPTR'))


def target_type(x):
    if x == lisp('FIXNUM'): return lisp(['SIGNED-BYTE',30])
    if isinstance(x,dict) and 'cons' in x:
        xs = elements(x)
        if xs and xs[0] in [lisp(n) for n in ('OR','AND','NOT')]:
            return form(xs[0], *(target_type(a) for a in xs[1:]))
    return x


def check(c, traversal):
    require(c['version']==1 and c['macro_environment_qualified'] is False and c['graph_edges_replaced']==0, 'SCOPE')
    require(c['restored'] is True,'RESTORATION')
    require([(s['path'],s['start'],s['end']) for s in c['sources']]==SPANS,'SOURCE_BOUND')
    for s in c['sources']:
        text=(ROOT/s['path']).read_text(); context(s['reader'])
        require(not s['host_reader'] and s['text']==text[s['start']:s['end']] and
                previous.previous.form_end(text,s['start'])==s['end'],'SOURCE_TEXT')
    require([p['name'] for p in c['probes']]==[n for n,_,_ in CASES],'PROBE_BOUND')
    by_phase={}
    for row in c['trace']: by_phase.setdefault(row['phase'],[]).append(row)
    for p,(name,typ,eq) in zip(c['probes'],CASES):
        safety=3 if name=='untrusted-symbol' else 0
        require(p['type']==lisp(typ) and p['safety']==safety,'PROBE_DECLARATION')
        wanted=form(lisp('LAMBDA'),form(sym('CCL::X'),sym('CCL::Y')),
            form(lisp('DECLARE'),form(lisp('TYPE'),lisp(typ),sym('CCL::X')),
                 form(lisp('OPTIMIZE'),form(lisp('SAFETY'),safety),form(lisp('SPEED'),3))),
            form(lisp('EQL'),sym('CCL::X'),sym('CCL::Y')))
        require(p['form']==wanted,'PROBE_DECLARATION')
        reason='DECLARATION_POLICY' if safety==3 else 'BOXED_TYPE_LOWERING'
        require(('COMMON-LISP::EQ' in p['operators']) is eq,reason)
        calls=p['function']['calls']
        if eq: require(not calls,'EQL_CALL_TARGET')
        else:
            expected=dict(category='global-binding',targets=[dict(kind='global-binding',name='COMMON-LISP::EQL')]) if safety==3 else dict(category='builtin',builtin_index=10,targets=[dict(kind='global-binding',name='COMMON-LISP::EQL')])
            require(len(calls)==1 and calls[0]['dependency']==expected,'EQL_CALL_TARGET')
        events=[e for e in p['events'] if e['operator']=='COMMON-LISP::EQL']
        require(len(events)==1 and events[0]['input']==form(lisp('EQL'),sym('CCL::X'),sym('CCL::Y')) and
                events[0]['output']==form(lisp('EQ' if eq else 'EQL'),sym('CCL::X'),sym('CCL::Y')) and
                events[0]['returned_input'] is (not eq),'PROBE_EXPANSION')
    compiled=c['compiled']; require([r['mode'] for r in compiled]==['prior','normal','shallow','host-range','trust'] and
        len({r['id'] for r in compiled})==5 and all(r['function'] for r in compiled),'COMPILED_BOUND')
    require(c['selected_id']==compiled[1]['id'],'PRIVATE_ROUTING')
    events=sorted(c['events'],key=lambda r:r['sequence'])
    require(len(events)==293 and [e['sequence'] for e in events]==list(range(293)),'EVENT_BOUND')
    original=[m for r in traversal['rows'] for m in r['macro_expansions']]
    require([e['operator'] for e in events]==[e['operator'] for e in original],'EVENT_JOIN')
    for e in events:
        context(e['context'])
        if e['operator']=='COMMON-LISP::EQL': require(e['selected_id']==c['selected_id'],'EVENT_ROUTING')
    type_counts=[1,2,3,3,6,6,6,6,6,6,3,6,1,1,6]
    target_counts=[2,4,14,14,28,28,28,28,28,34,20,28,2,2,22]
    wanted={('dumplisp','NX-TARGET-TYPE'):244,('dumplisp','NX-FORM-TYPE'):60,('dumplisp','NX-FORM-TYPEP'):60}
    for (name,_,_),n,t in zip(CASES,type_counts,target_counts):
        wanted.update({(name,'NX-FORM-TYPE'):n,(name,'NX-FORM-TYPEP'):n,(name,'NX-TARGET-TYPE'):t})
    require(Counter((r['phase'],r['helper']) for r in c['trace'])==wanted,'TRACE_BOUND')
    phase_events={'dumplisp':events,**{p['name']:p['events'] for p in c['probes']}}
    for r in c['trace']:
        context(r['context'])
        matches=[e for e in phase_events[r['phase']] if e['sequence']==r['event'] and e['operator']=='COMMON-LISP::EQL']
        require(len(matches)==1,'TRACE_PARENT')
        if r['helper']=='NX-TARGET-TYPE': require(r['answer']==target_type(r['input']),'TYPE_TRANSLATION')
        else:
            require(r['form'] in elements(matches[0]['input'])[1:],'TRACE_FORM')
            if r['helper']=='NX-FORM-TYPEP':
                require(r['requested'] in [lisp('SYMBOL'),lisp('CHARACTER'),QUERY] and
                        r['query']==target_type(r['requested']),'TYPE_QUERY')
                require(len(r['answers'])==2 and all(type(v) is bool for v in r['answers']),'SUBTYPE_VALUES')
    for (name,typ,eq),n in zip(CASES,type_counts):
        rows=by_phase[name]; facts=[r for r in rows if r['helper']=='NX-FORM-TYPE']
        expected_type=lisp('T') if name=='untrusted-symbol' else target_type(lisp(typ))
        if name=='mixed-immediate': expected_type=lisp(['OR','SYMBOL',['MOD',6]])
        require(all(r['answer']==(expected_type if r['form']==sym('CCL::X') else lisp('T')) for r in facts),'DECLARED_FACT')
        decisions=[r['answers'] for r in rows if r['helper']=='NX-FORM-TYPEP']
        expect=[[False,True]]*(n-1)+[[True,True]] if eq else [[False,True]]*5+[[False,False]]
        if name in ('unknown','untrusted-symbol'): expect[2]=[False,False]
        require(decisions==expect,'SUBTYPE_DECISIONS')
    counts=previous.previous.prior.previous.check_capture(traversal,(ROOT/'lib/dumplisp.lisp').read_bytes(),
              read(HERE.parent/'target-descriptions/descriptions.json'))
    return dict(source_forms=9,declared_type_probes=15,safe_eq_probes=sum(eq for _,_,eq in CASES),
                retained_eql_probes=sum(not eq for _,_,eq in CASES),
                file_type_queries=60,file_type_facts=60,file_translation_steps=244,trace_records=770,
                full_macro_environment_qualified=False,**counts)


def controls(c,t):
    cases=[('scope','SCOPE',lambda x:x.update(macro_environment_qualified=True)),
      ('omit-source','SOURCE_BOUND',lambda x:x['sources'].pop()),
      ('rewrite-source','SOURCE_TEXT',lambda x:x['sources'][0].update(text='wrong')),
      ('omit-probe','PROBE_BOUND',lambda x:x['probes'].pop()),
      ('alter-declaration','PROBE_DECLARATION',lambda x:x['probes'][4].update(type=lisp('FIXNUM'))),
      ('boxed-eq','BOXED_TYPE_LOWERING',lambda x:x['probes'][4]['operators'].append('COMMON-LISP::EQ')),
      ('wrong-eql-target','EQL_CALL_TARGET',lambda x:x['probes'][4]['function']['calls'][0]['dependency'].update(builtin_index=9)),
      ('trust-policy','DECLARATION_POLICY',lambda x:x['probes'][-1]['operators'].append('COMMON-LISP::EQ')),
      ('omit-trace','TRACE_BOUND',lambda x:x['trace'].pop()),
      ('insert-trace','TRACE_BOUND',lambda x:x['trace'].append(deepcopy(x['trace'][0]))),
      ('wrong-parent','TRACE_PARENT',lambda x:x['trace'][0].update(event=-1)),
      ('wrong-translation','TYPE_TRANSLATION',lambda x:x['trace'][0].update(answer=lisp('NIL'))),
      ('member-literal','TYPE_TRANSLATION',lambda x:next(r for r in x['trace'] if r['helper']=='NX-TARGET-TYPE' and r['input']==lisp(['MEMBER','FIXNUM'])).update(answer=lisp(['MEMBER',['SIGNED-BYTE',30]]))),
      ('lost-certainty','SUBTYPE_VALUES',lambda x:next(r for r in x['trace'] if r['helper']=='NX-FORM-TYPEP')['answers'].pop()),
      ('wrong-expansion','PROBE_EXPANSION',lambda x:next(e for e in x['probes'][0]['events'] if e['operator']=='COMMON-LISP::EQL').update(output=lisp('NIL'))),
      ('wrong-entry','PRIVATE_ROUTING',lambda x:x.update(selected_id=x['compiled'][0]['id'])),
      ('restoration','RESTORATION',lambda x:x.update(restored=False))]
    out=[]
    for name,reason,mutate in cases:
        x=deepcopy(c); mutate(x)
        try:check(x,t)
        except ValueError as e:require(str(e)==reason,'WRONG_CONTROL_REASON '+name+': '+str(e))
        else:raise ValueError('CONTROL_ESCAPED '+name)
        out.append(dict(name=name,status='REJECTED',reason=reason))
    return out
