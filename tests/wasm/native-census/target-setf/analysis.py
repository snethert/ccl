"""Bound the SETF source/registry joins and independently check expansion semantics."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
previous=module('setf_previous',HERE.parent/'source-expanders/check.py')
traversal=module('setf_traversal',HERE.parent/'target-descriptions/analysis.py')
read,require,form,elements=previous.read,previous.require,previous.form,previous.elements
CONTROLS={'cached-method':'REPLACEMENT_SEMANTICS','drop-values':'CALLABLE_SEMANTICS','drop-environment':'CALLABLE_SEMANTICS','ignore-local':'LOCAL_FUNCTION','drop-getter':'BRIDGE_VALUES'}
SPANS=[('compiler/optimizers.lisp',7408,7953),('compiler/nx0.lisp',80372,80629),('compiler/optimizers.lisp',20905,21052),('compiler/nx0.lisp',119274,119534),('compiler/nx0.lisp',117651,118833),('compiler/nx-basic.lisp',16754,17001),('compiler/nx0.lisp',27546,27807),('compiler/optimizers.lisp',75294,75408),('compiler/optimizers.lisp',71635,72010),('compiler/optimizers.lisp',66008,66505),('compiler/optimizers.lisp',61361,66006),('level-1/l1-utils.lisp',31132,31187),('lib/macros.lisp',27306,27329),('level-1/l1-clos-boot.lisp',119573,119608),('lib/macros.lisp',158632,158677),('lib/macros.lisp',22188,26311),('lib/setf.lisp',1064,1123)]
EVENTS=[9,45,47,88,255]
OPERATORS=['CCL::*%SAVED-METHOD-VAR%*','CCL::BASIC-STREAM.STATE','CCL::%SVREF','COMMON-LISP::SLOT-VALUE','CCL::INTERRUPT-LEVEL']
SETTERS=['CCL::SET-*%SAVED-METHOD-VAR%*',None,'CCL::%SVSET','CCL::SET-SLOT-VALUE','CCL::SET-INTERRUPT-LEVEL']
NAMES=['callable','replacement','symbol','absent','present-nil','local-function','nonlocal','after-nonlocal','bridge-values']
def s(x):return {'symbol':x if '::'in x else 'COMMON-LISP::'+x}
def f(x):return s('CCL-TARGET-SETF::'+x)
def c(x):return s('CCL::'+x)
PLACE=form(f('PROBE-PLACE'),form(f('EFFECT'),f('CELL')))
VALUE=form(s('VALUES'),form(f('EFFECT'),11),form(f('EFFECT'),22))
INPUT=form(s('SETF'),PLACE,VALUE)
SIMPLE=form(s('SETF'),form(f('PROBE-PLACE'),f('CELL')),7)
def returned_values(reverse=False):
 a,b=(f('SECOND-VALUE'),f('FIRST-VALUE')) if reverse else (f('FIRST-VALUE'),f('SECOND-VALUE'))
 return [form(f('TEMPORARY')),form(form(f('EFFECT'),f('CELL'))),form(f('FIRST-VALUE'),f('SECOND-VALUE')),form(f('STORE-PAIR'),f('TEMPORARY'),a,b),form(f('READ-PAIR'),f('TEMPORARY'))]
def expansion(reverse=False):
 v=returned_values(reverse)
 return form(s('LET*'),form(form(f('TEMPORARY'),form(f('EFFECT'),f('CELL')))),form(s('DECLARE'),form(s('IGNORABLE'),f('TEMPORARY'))),form(s('MULTIPLE-VALUE-BIND'),v[2],VALUE,v[3]))
def fallback(output):
 parts=elements(output)
 require(len(parts)==3 and parts[0]==s('LET'),'FALLBACK_SHAPE')
 bindings=elements(parts[1]);require(len(bindings)==1,'FALLBACK_SHAPE');binding=elements(bindings[0]);require(len(binding)==2,'FALLBACK_SHAPE');var=binding[0]
 require(isinstance(var,dict) and type(var.get('identity'))is int and var.get('symbol','').startswith('#::G'),'FALLBACK_TEMPORARY')
 require(output==form(s('LET'),form(form(var,f('CELL'))),form(s('FUNCALL'),form(s('FUNCTION'),form(s('SETF'),f('PROBE-PLACE'))),7,var)),'FALLBACK_BINDING')
def canonical_generated(x):
 ids={};labels={}
 def walk(x):
  if isinstance(x,list):return [walk(y)for y in x]
  if isinstance(x,dict):
   if 'identity'in x:
    ident=x['identity'];require(type(ident)is int and x['symbol'].startswith('#::'),'GENERATED_IDENTITY')
    require(labels.setdefault(ident,x['symbol'])==x['symbol'],'GENERATED_ALIAS')
    return dict(symbol=x['symbol'],identity=ids.setdefault(ident,len(ids)))
   return {k:walk(v)for k,v in x.items()}
  return x
 return walk(x)
def lookup(phase,table,op,value,present,kind,event=None):return dict(kind='lookup',phase=phase,event=event,operator=op,table_id=table,present=present,value_kind=kind,value=value)
def call(phase,fn,env,values,status='RETURNED'):return dict(kind='call',phase=phase,event=None,function_id=fn,input=PLACE,environment_id=env,status=status,values=values)
def check(capture,t):
 x=capture;require(x['version']==1 and x['macro_environment_qualified']is False and x['graph_edges_replaced']==0,'SCOPE');require(x['restored']is True,'RESTORATION')
 require([(r['path'],r['start'],r['end'])for r in x['sources']]==SPANS,'SOURCE_BOUND')
 for r in x['sources']:
  text=(ROOT/r['path']).read_text();require(r['text']==text[r['start']:r['end']] and previous.form_end(text,r['start'])==r['end'],'SOURCE_TEXT')
  traversal.base.context(r['reader']);require(r['host_reader']is False,'TARGET_READER')
 for r,op,setter in zip(x['sources'][11:15],[OPERATORS[i]for i in (0,2,3,4)],[SETTERS[i]for i in (0,2,3,4)]):
  expected=form(s('DEFSETF'),s(op),s(setter));require(r['form']==expected,'INVERSE_SOURCE');require(re.fullmatch(r'\(defsetf\s+[^\s()]+\s+[^\s()]+\)',r['text'],re.I),'INVERSE_TEXT')
 require(x['inverse_sources']==[r['form']for r in x['sources'][11:15]],'INVERSE_JOIN')
 require(x['sources'][-1]['form']==form(s('DEFUN'),s('CCL::%SETF-METHOD'),form(s('CCL::NAME')),form(s('GETHASH'),s('CCL::NAME'),s('CCL::%SETF-METHODS%'))),'LOOKUP_SOURCE')
 sf=elements(x['sources'][-2]['form']);require(sf[0:2]==[s('DEFMACRO'),s('SETF')],'SETF_SOURCE')
 compiled=x['compiled'];inners=compiled['inner_functions'];require(compiled['name']=='NIL' and len(inners)==1 and inners[0]['name']=='CCL::%SETF-METHOD' and not inners[0]['inner_functions'],'PRIVATE_FUNCTIONS')
 local=[a for a in compiled['calls']if a['dependency']['category']=='lexical'];require(len(local)==1 and local[0]['dependency']['targets']==[dict(kind='function',id=inners[0]['function_id'],name='CCL::%SETF-METHOD')],'PRIVATE_LOOKUP_EDGE')
 require(type(x['selected_id'])is int and compiled['function_id']!=inners[0]['function_id'],'PRIVATE_IDENTITIES')
 events=x['events'];require(len(events)==293 and [e['sequence']for e in events]==list(range(293)),'EVENT_BOUND')
 require([e['sequence']for e in events if e['operator']=='COMMON-LISP::SETF']==EVENTS,'SETF_EVENT_BOUND')
 for e in events:
  require(e['role']!='UNMATCHED' and e['selected_id']!=e['original_id'],'SOURCE_ROUTING');traversal.base.context(e['context'])
 reg=x['file_registry'];entries=[];expected_trace=[]
 for event,op,setter in zip(EVENTS,OPERATORS,SETTERS):
  value=s(setter)if setter else None;kind='symbol'if setter else 'null'
  entries.append(dict(operator=op,present=bool(setter),value_kind=kind,value=value,source_note=None));expected_trace.append(lookup('dumplisp',reg['table_id'],op,value,bool(setter),kind,event))
  e=events[event];require(e['selected_id']==x['selected_id'],'SETF_ROUTING');parts=elements(e['input']);place=elements(parts[1])
  require(place[0]==s(op) and e['status']=='RETURNED' and e['problem']is None,'FILE_INPUT')
  expected=form(s(setter),*place[1:],parts[2])if setter else form(s('SETF'),form(c('%SVREF'),c('O'),2),None)
  require(e['output']==expected,'FILE_EXPANSION')
 require(reg['entries']==entries,'FILE_REGISTRY');require(x['file_trace']==expected_trace,'FILE_TRACE')
 rows=x['probes'];require([r['name']for r in rows]==NAMES,'PROBE_BOUND')
 for p in rows:
  name=p['name']
  if name=='nonlocal':require(p==dict(name=name,escaped=True,restored=True),'NONLOCAL');continue
  if name=='bridge-values':require(p==dict(name=name,status='RETURNED',problem=None,values=returned_values()),'BRIDGE_VALUES');continue
  if name in ('callable','replacement','after-nonlocal'):
   rev=name=='replacement';a,b=(22,11)if rev else (11,22)
   expected=dict(name=name,input=INPUT,status='RETURNED',output=expansion(rev),problem=None,values=form(a,b),cell={'cons':[a,b]},effects=form(s('KEYWORD::PLACE'),11,22,s('KEYWORD::STORE')))
   require(p==expected,'REPLACEMENT_SEMANTICS'if rev else 'CALLABLE_SEMANTICS')
  else:
   require(p['status']=='RETURNED' and p['problem']is None,'LOCAL_FUNCTION'if name=='local-function'else 'PROBE_RESULT')
   if name=='symbol':require(p['output']==form(f('SYMBOL-SETTER'),f('CELL'),7),'SYMBOL_INVERSE')
   else:fallback(p['output'])
   require(p==dict(name=name,input=SIMPLE,status='RETURNED',output=p['output'],problem=None,values=None,cell={'cons':[0,0]},effects=None),'PROBE_RESULT')
 reg=x['probe_registry'];ref=x['reference_registry'];a,b,esc=(reg[k]for k in ('method_a_id','method_b_id','escaping_id'));table=reg['table_id'];env=reg['environment_id']
 traversal.base.context(reg['context']);traversal.base.context(ref['context'])
 require(len({a,b,esc,table,env,reg['original_table_id']})==6 and reg['original_table_id']==x['file_registry']['table_id'],'REGISTRY_IDENTITIES')
 tr=[]
 for name,value,present,kind in [('callable',a,True,'function'),('replacement',b,True,'function'),('symbol',f('SYMBOL-SETTER'),True,'symbol'),('absent',None,False,'null'),('present-nil',None,True,'null'),('nonlocal',esc,True,'function'),('after-nonlocal',a,True,'function')]:
  tr.append(lookup(name,table,'CCL-TARGET-SETF::PROBE-PLACE',value,present,kind))
  if kind=='function':tr.append(call(name,value,env,None if name=='nonlocal' else returned_values(name=='replacement'),'ESCAPED'if name=='nonlocal' else 'RETURNED'))
 tr.append(call('bridge-values',a,env,returned_values()));require(x['probe_trace']==tr,'PROBE_TRACE')
 require(all(reg[k]==ref[k]for k in ('method_a_id','method_b_id','escaping_id','original_table_id')) and reg['table_id']!=ref['table_id'] and env!=ref['environment_id'],'REFERENCE_REGISTRY')
 require(canonical_generated(rows)==canonical_generated(x['reference_probes']),'NATIVE_REFERENCE')
 counts=traversal.check_capture(t,(ROOT/'lib/dumplisp.lisp').read_bytes(),read(HERE.parent/'target-descriptions/descriptions.json'))
 return dict(source_forms=17,source_inverse_declarations=4,source_setf_macros=1,source_lookup_functions=1,file_setf_events=5,file_lookup_records=5,file_computed_calls=0,probe_cases=9,native_reference_cases=9,probe_lookup_records=7,probe_computed_calls=5,**counts)
def controls(c,t):
 cases=[('scope','SCOPE',lambda x:x.update(macro_environment_qualified=True)),('restore','RESTORATION',lambda x:x.update(restored=False)),('source-omit','SOURCE_BOUND',lambda x:x['sources'].pop()),('source-text','SOURCE_TEXT',lambda x:x['sources'][-1].update(text='bad')),('host-reader','TARGET_READER',lambda x:x['sources'][-1].update(host_reader=True)),('inverse-value','INVERSE_SOURCE',lambda x:x['sources'][11].update(form=None)),('inverse-join','INVERSE_JOIN',lambda x:x['inverse_sources'].pop()),('lookup-source','LOOKUP_SOURCE',lambda x:x['sources'][-1].update(form=None)),('private-function','PRIVATE_FUNCTIONS',lambda x:x['compiled']['inner_functions'].clear()),('private-edge','PRIVATE_LOOKUP_EDGE',lambda x:next(a for a in x['compiled']['calls']if a['dependency']['category']=='lexical')['dependency']['targets'][0].update(id=-1)),('event-omit','EVENT_BOUND',lambda x:x['events'].pop()),('file-route','SETF_ROUTING',lambda x:x['events'][9].update(selected_id=-1)),('wrong-setter','FILE_EXPANSION',lambda x:x['events'][9].update(output=None)),('registry-substitution','FILE_REGISTRY',lambda x:x['file_registry']['entries'][0].update(value=None)),('invent-file-call','FILE_TRACE',lambda x:x['file_trace'].append(x['file_trace'][0])),('wrong-table','FILE_TRACE',lambda x:x['file_trace'][0].update(table_id=-1)),('probe-omit','PROBE_BOUND',lambda x:x['probes'].pop()),('effect-order','CALLABLE_SEMANTICS',lambda x:x['probes'][0].update(effects=form(11,s('KEYWORD::PLACE'),22,s('KEYWORD::STORE')))),('replacement','REPLACEMENT_SEMANTICS',lambda x:x['probes'][1].update(values=form(11,22))),('lost-getter','BRIDGE_VALUES',lambda x:x['probes'][-1]['values'].pop()),('lost-throw','NONLOCAL',lambda x:x['probes'][6].update(escaped=False)),('lost-presence','PROBE_TRACE',lambda x:next(r for r in x['probe_trace']if r['phase']=='present-nil').update(present=False)),('call-env','PROBE_TRACE',lambda x:x['probe_trace'][1].update(environment_id=-1)),('surplus-probe-call','PROBE_TRACE',lambda x:x['probe_trace'].append(x['probe_trace'][-1])),('reference-result','NATIVE_REFERENCE',lambda x:x['reference_probes'][0].update(values=None))]
 out=[]
 for name,reason,mutate in cases:
  changed=deepcopy(c);mutate(changed)
  try:check(changed,t)
  except ValueError as e:require(str(e)==reason,'WRONG_CONTROL '+name+': '+str(e))
  else:raise ValueError('CONTROL_ESCAPED '+name)
  out.append(dict(name=name,status='REJECTED',reason=reason))
 return out
