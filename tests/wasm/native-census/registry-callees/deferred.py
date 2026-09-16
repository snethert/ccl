"""Join compiler deferred literals to their actual initializer functions.

The marker is identified by its installed compiler macro and that macro's exact
U1 source span. An uninterned symbol with the same name is insufficient. Results
and side effects of the initializer remain obligations, not observed values.
"""
from collections import Counter
from pathlib import Path
import gzip
import json
import re
import sys
from payloads import require,source_key,read,save
from source_map import span

HERE=Path(__file__).resolve().parent
HEADER=re.compile(rb'^\{"version":2,"sequence":([0-9]+),"kind":"([a-z0-9-]+)"')
MACRO_MARKER=0xc9cd0000000000>>3
EXPANDER=b"#'(lambda (call env) (declare (ignore env)) (list 'eval (list 'quote call)))"


def items(value,objects):
    result=[];seen=set()
    while value!={'atom':'nil'}:
        if not isinstance(value,dict) or set(value)!={'ref'} or value['ref'] in seen:return None
        seen.add(value['ref']);n=objects.get(value['ref'])
        if not n or n['kind']!='cons' or not n['expanded']:return None
        result.append(n['car']);value=n['cdr']
    return result


def marker(row,functions,expected_span,loader=None):
    objects={n['id']:n for n in row['payload']['objects']};args=items(row['payload']['root'],objects)
    if not args or len(args)!=2:return None
    sym=objects.get(args[0].get('ref'));wrapper=objects.get(args[1].get('ref'))
    if not sym or sym.get('kind')!='symbol' or (sym['name'],sym['package'],sym['setter_of'])!=('LOAD-TIME-EVAL',None,None):return None
    if not wrapper or wrapper.get('kind')!='simple-vector' or not wrapper['expanded'] or wrapper['length']!=2:return None
    es=wrapper['elements']
    if len(es)!=2 or es[0]!={'integer':MACRO_MARKER}:return None
    fn=objects.get(es[1].get('ref'))
    if not fn or fn['kind']!='function' or fn['id']!=fn['code']:return None
    provenance=[r for r in (loader or {}).get(fn['id'],[]) if r['event']<row['sequence']]
    candidates=[functions[i] for i in [fn['id']]+[r['writer']['code'] for r in provenance] if i in functions]
    candidates=[f for f in candidates if source_key(f['source'])=='lib/nfcomp.lisp'
                and (f['source_start'],f['source_end'])==tuple(expected_span)]
    if not candidates or source_key(fn['description']['source'])!='lib/nfcomp.lisp' or fn['description']['position']!=expected_span[0]:return None
    return dict(symbol=sym['id'],event=row['sequence'],expander=fn['id'],span=list(expected_span),
                compiler_functions=[f['id'] for f in candidates],loader_records=provenance,
                relation='INSTALLED_U1_LOAD_TIME_EVAL_MACRO')


def placeholder(ident,objects,markers):
    head=objects.get(ident)
    if not head or head['kind']!='cons' or not head['expanded'] or head['car'].get('ref') not in markers:return None
    args=items({'ref':ident},objects)
    if not args or len(args)!=2 or args[0].get('ref') not in markers:return None
    call=items(args[1],objects)
    if not call or len(call)!=2:return None
    operator=objects.get(call[0].get('ref'));function=objects.get(call[1].get('ref'))
    if not operator or operator.get('kind')!='symbol' or (operator['package'],operator['name'],operator['setter_of'])!=('COMMON-LISP','FUNCALL',None):return None
    if not function or function.get('kind')!='function' or function['id']!=function['code']:return None
    return dict(object=ident,marker=args[0]['ref'],function=function['id'],
                result_status='UNRESOLVED',effects_status='UNRESOLVED')


def consumers(objects,identifiers):
    result={i:[] for i in identifiers}
    for afunc in objects.values():
        if afunc['kind']!='afunc':continue
        pending=[afunc['body']];seen=set()
        while pending:
            ref=pending.pop()
            if not isinstance(ref,dict) or set(ref)!={'ref'} or ref['ref'] in seen:continue
            ident=ref['ref'];seen.add(ident);n=objects[ident]
            if ident in result:result[ident].append(afunc['id'])
            # Function/AFUNC references do not execute the referred body here.
            if n['kind']=='acode' and n['expanded']:pending.append(n['operands'])
            elif n['kind']=='cons' and n['expanded']:pending.extend((n['car'],n['cdr']))
            elif n['kind']=='simple-vector' and n['expanded']:pending.extend(n['elements'])
    return result


def collect(build,functions,emissions,before,source,coordinates,loader=None,initial_markers=()):
    text=(source/'lib/nfcomp.lisp').read_bytes();start=text.index(EXPANDER)
    prefix=b'(%macro-have cfasl-load-time-eval-sym\n    '
    require(text.count(EXPANDER)==1 and text[start-len(prefix):start]==prefix,
            'DEFERRED_MARKER_SOURCE')
    expected,witness=span(coordinates,'lib/nfcomp.lisp',start,start+len(EXPANDER))
    require(expected is not None,'DEFERRED_MARKER_PATCH_INTERSECTION')
    markers={m['symbol']:m for m in initial_markers};result={};unjoined=[];counts=Counter()
    require(len(markers)==len(initial_markers),'DEFERRED_INITIAL_MARKER_DUPLICATE')
    opener=gzip.open if build.suffix=='.gz' else open
    with opener(build,'rb') as stream:
        for line in stream:
            h=HEADER.match(line);require(h is not None,'DEFERRED_STREAM_HEADER')
            kind=h[2].decode()
            if kind not in ('before-pass2','binding-installed'):continue
            row=json.loads(line)
            if kind=='binding-installed':
                m=marker(row,functions,expected,loader)
                if m:
                    require(m['symbol'] not in markers,'DEFERRED_MARKER_REPEATED');markers[m['symbol']]=m
                continue
            objects={n['id']:n for n in row['payload']['ir']['objects']}
            found={}
            for ident,n in objects.items():
                if n['kind']!='cons':continue
                p=placeholder(ident,objects,markers)
                if p is None:continue
                require(markers[p['marker']]['event']<row['sequence'],'DEFERRED_MARKER_ORDER')
                compiler=[dict(function=p['function'],**e,before=before[e['afunc']])
                          for e in emissions.get(p['function'],[]) if e['afunc'] in before
                          and before[e['afunc']]['event']<e['event']<row['sequence']]
                if not compiler:
                    unjoined.append(dict(event=row['sequence'],**p));continue
                p.update(event=row['sequence'],compiler_records=compiler);found[ident]=p
            owners=consumers(objects,found)
            for ident,p in found.items():
                p['owners']=sorted(set(owners[ident]));require(p['owners'],'DEFERRED_LITERAL_WITHOUT_CONSUMER')
                key=(row['sequence'],ident);require(key not in result,'DEFERRED_LITERAL_DUPLICATE');result[key]=p
    return dict(markers=list(markers.values()),source_witness=witness,placeholders=list(result.values()),
                unjoined=unjoined,results_qualified=False,effects_qualified=False)


def index(facts):
    result={(r['event'],r['object']):r for r in facts['placeholders']}
    require(len(result)==len(facts['placeholders']),'DEFERRED_INDEX_DUPLICATE');return result


def check_links(graph,records,namespace='correlated-build:'):
    nodes={n['id']:n for n in graph['nodes']};prefix=namespace+'deferred:';evidence=namespace.rstrip(':')+'/'
    expected_nodes=set();expected_edges=[]
    def edge(owner,targets,evidence):
        expected_edges.append({'from':owner,'targets':sorted(set(targets)),'phase':'load',
            'origin':'conservative','resolution':'complete','evidence':evidence})
    for r in records:
        owners=[namespace+f'afunc:{i}' for i in r['owners'] if namespace+f'afunc:{i}' in nodes]
        if not owners:continue
        ident=prefix+f'{r["event"]}:{r["object"]}';expected_nodes.add(ident)
        for owner in owners:
            edge(owner,[ident],evidence+f'deferred-use/{owner.rsplit(":",1)[1]}/{r["object"]}')
        edge(ident,[namespace+f'afunc:{e["afunc"]}' for e in r['compiler_records']],
             evidence+f'deferred-body/{r["event"]}/{r["object"]}')
    require({i for i in nodes if i.startswith(prefix)}==expected_nodes,'DEFERRED_GRAPH_NODE_BOUND')
    for ident in expected_nodes:
        n=nodes[ident]
        require(n['kind']=='function' and n['required'] is True and n['disposition']=='unresolved'
                and n['implementation'] is None,'DEFERRED_GRAPH_RESULT_OPEN')
    actual=[e for e in graph['edges'] if e['from'].startswith(prefix) or any(t.startswith(prefix) for t in e['targets'])]
    bag=lambda rs:Counter(json.dumps(r,sort_keys=True) for r in rs)
    require(bag(actual)==bag(expected_edges),'DEFERRED_GRAPH_EDGE_BOUND')
