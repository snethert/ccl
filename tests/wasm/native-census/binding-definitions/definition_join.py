"""Compiler/declaration references for unwitnessed cells, never callable bounds."""
from collections import Counter
import gzip
import hashlib
import json
import re

HEADER=re.compile(rb'^\{"version":2,"sequence":([0-9]+),"kind":"([a-z0-9-]+)"')
SCOPE='Same-build compiled-name and class-declaration references; no installation, unbound-state, exhaustive callable-value or target implementation claim.'

def require(ok,reason):
    if not ok:raise ValueError(reason)

class Graph:
    def __init__(self,payload):
        self.root=payload['root'];self.nodes={n['id']:n for n in payload['objects']}
        require(len(self.nodes)==len(payload['objects']),'OBJECT_IDS')
    def node(self,x):return self.nodes[x['ref']] if 'ref' in x else x
    def items(self,x):
        result=[];seen=set()
        while x!={'atom':'nil'}:
            n=self.node(x)
            require(n.get('kind')=='cons' and n['expanded'] and n['id'] not in seen,'PROPER_LIST')
            seen.add(n['id']);result.append(n['car']);x=n['cdr']
        return result

def missing_cells(histories):
    rows={h['symbol_id']:h for h in histories if h['call_count'] and not h['observations']}
    require(len(rows)==95 and sum(h['call_count'] for h in rows.values())==345,'ORIGINAL_POPULATION')
    return rows

def compiled(row,missing,functions):
    if row['kind'] not in ('before-pass2','frontend'):return []
    g=Graph(row['payload']['ir']);result=[]
    for n in g.nodes.values():
        if n['kind']!='afunc' or n['name'].get('ref') not in missing:continue
        f=functions.get(n['id'])
        # FRONTEND and BEFORE-PASS2 can describe the same object. Use the
        # reviewed function record's actual IR witness, not both observations.
        if not f or f['event']!=row['sequence']:continue
        symbol=g.node(n['name']);h=missing[symbol['id']]
        require(symbol in h['descriptors'],'COMPILER_SYMBOL_IDENTITY')
        require(f['process']==row['process'] and f['source']==row['source'] and
                f['source_position']==row['source_position'] and f['parent_id']==n['parent'], 'COMPILER_CONTEXT')
        require(f['emitted'] and all(c['event']>row['sequence'] for c in f['emitted']),'COMPILER_COMPLETION')
        result.append(dict(symbol=symbol,function_id=n['id'],event=row['sequence'],process=row['process'],
                           source=row['source'],source_position=row['source_position'],emitted=f['emitted']))
    return result

def declarations(row,missing):
    if row['kind']!='expander-enter':return []
    g=Graph(row['payload']);args=g.items(g.root)
    require(len(args)==4,'EXPANDER_ARGUMENTS')
    form=g.node(args[2])
    if form.get('kind')!='cons':return []
    xs=g.items(args[2]);head=g.node(xs[0])
    if head.get('package')!='COMMON-LISP' or head.get('name') not in ('DEFCLASS','DEFINE-CONDITION'):return []
    require(len(xs)>=4,'CLASS_FORM');found=[]
    for slot in g.items(xs[3]):
        if g.node(slot).get('kind')!='cons':continue
        fields=g.items(slot);require(len(fields)%2==1,'SLOT_OPTIONS')
        for key,value in zip(fields[1::2],fields[2::2]):
            k=g.node(key)
            if k.get('package')=='KEYWORD' and k.get('name') in ('READER','ACCESSOR','WRITER') and value.get('ref') in missing:
                symbol=g.node(value)
                require(symbol in missing[symbol['id']]['descriptors'],'DECLARATION_SYMBOL_IDENTITY')
                found.append(dict(symbol=symbol,role=k['name'],slot=g.node(fields[0])))
    if not found:return []
    return [dict(event=row['sequence'],process=row['process'],class_name=g.node(xs[1]),operator=head['name'],
                 source=row['source'],source_position=row['source_position'],entries=found)]

def collect(path,histories,function_rows,witness_path):
    missing=missing_cells(histories);fs={f['function_id']:f for f in function_rows}
    counts=Counter();last=0;complete=False;cs=[];ds=[];pending={};witnesses=[]
    with gzip.open(path,'rb') as stream:
        for line in stream:
            m=HEADER.match(line);require(m is not None,'EVENT_HEADER')
            seq=int(m[1]);kind=m[2].decode()
            require(seq==last+1 and not complete,'EVENT_SEQUENCE');last=seq;counts[kind]+=1
            if kind in ('before-pass2','frontend'):
                row=json.loads(line);new=compiled(row,missing,fs)
                if new:cs.extend(new);witnesses.append(line)
            elif kind=='expander-enter':
                # Byte filters only avoid parsing irrelevant events. Matching
                # heads, slot roles and symbol IDs are checked structurally.
                if not any(t in line for t in (b'"name":"DEFCLASS"',b'"name":"DEFINE-CONDITION"')):continue
                row=json.loads(line);new=declarations(row,missing)
                if new:pending[seq]=(new[0],line)
            elif kind in ('expander-return','expander-abort'):
                if not pending:continue
                row=json.loads(line)
                if row['parent'] not in pending:continue
                require(kind=='expander-return','DECLARATION_EXPANSION_ABORT')
                d,original=pending.pop(row['parent']);before=json.loads(original)
                require(row['process']==d['process'],'DECLARATION_PROCESS')
                g=Graph(row['payload']);a=g.items(g.root);b=Graph(before['payload'])
                require(len(a)==5 and a[:4]==b.items(b.root),'DECLARATION_RETURN_ARGUMENTS')
                d['return_event']=seq;ds.append(d);witnesses.extend((original,line))
            elif kind=='complete':
                row=json.loads(line);actual=dict(counts);del actual['complete']
                require(actual=={r['kind']:r['count'] for r in row['payload']['counts']} and
                        row['payload']['events_before_complete']==seq-1,'COMPLETION_COUNTS');complete=True
    require(complete and not pending,'INCOMPLETE_STREAM')
    witnesses.sort(key=lambda line:int(HEADER.match(line)[1]))
    raw=b''.join(witnesses)
    witness_path.write_bytes(gzip.compress(raw,mtime=0))
    return dict(version=1,scope=SCOPE,events=last,compiled=sorted(cs,key=lambda r:(r['symbol']['id'],r['event'])),
                declarations=sorted(ds,key=lambda r:r['event']),selected_event_sha256=hashlib.sha256(raw).hexdigest(),
                selected_events=len(witnesses))

def replay(witness_path,histories,function_rows,expected):
    require(set(expected)=={'version','scope','events','compiled','declarations','selected_event_sha256','selected_events'}
            and expected['version']==1 and expected['scope']==SCOPE and expected['events']==4006405,'FACT_SCOPE')
    missing=missing_cells(histories);fs={f['function_id']:f for f in function_rows}
    raw=gzip.decompress(witness_path.read_bytes());rows=[json.loads(x) for x in raw.splitlines()]
    require(hashlib.sha256(raw).hexdigest()==expected['selected_event_sha256'] and len(rows)==expected['selected_events'],'SELECTED_BYTES')
    cs=[];ds=[];byseq={r['sequence']:r for r in rows}
    require(len(byseq)==len(rows) and list(byseq)==sorted(byseq),'SELECTED_ORDER')
    for r in rows:
        cs.extend(compiled(r,missing,fs))
        for d in declarations(r,missing):
            returns=[x for x in rows if x['kind']=='expander-return' and x['parent']==r['sequence']]
            require(len(returns)==1 and returns[0]['process']==r['process'],'SELECTED_RETURN')
            a=Graph(returns[0]['payload']);b=Graph(r['payload'])
            require(a.items(a.root)[:4]==b.items(b.root) and len(a.items(a.root))==5,'DECLARATION_RETURN_ARGUMENTS')
            d['return_event']=returns[0]['sequence'];ds.append(d)
    require(sorted(cs,key=lambda r:(r['symbol']['id'],r['event']))==expected['compiled'] and
            sorted(ds,key=lambda r:r['event'])==expected['declarations'],'SELECTED_FACTS')

def patch(facts):
    nodes=[];edges=[]
    def edge(owner,target,ev):
        return {'from':owner,'targets':[target],'phase':'compile','origin':'observed','resolution':'complete','evidence':ev}
    for r in facts['compiled']:
        edges.append(edge('identity:build:binding-cell:'+str(r['symbol']['id']),
                          'identity:build:afunc:'+str(r['function_id']),
                          'binding-definitions/compiled/'+str(r['event'])+'/'+str(r['symbol']['id'])))
    for r in facts['declarations']:
        ident='identity:build:binding-declaration:'+str(r['event'])
        nodes.append(dict(id=ident,kind='store',required=True,disposition='unresolved',implementation=None,
                          reason='Observed class/condition accessor declaration; construction, installed methods, dispatch and target lowering remain unqualified.',
                          evidence='binding-definitions/declaration/'+str(r['event']),tests=['S0-LL15-b','S0-LL15-c']))
        for entry in r['entries']:
            edges.append(edge('identity:build:binding-cell:'+str(entry['symbol']['id']),ident,
                              'binding-definitions/accessor/'+str(r['event'])+'/'+str(entry['symbol']['id'])))
    return dict(version=1,scope=SCOPE,census_gate_credit=False,original_runtime_obligations_closed=0,nodes=nodes,edges=edges)

def apply(base,delta):
    require(not {n['id'] for n in base['nodes']} & {n['id'] for n in delta['nodes']},'NODE_COLLISION')
    return dict(base,nodes=base['nodes']+delta['nodes'],edges=base['edges']+delta['edges'],profile=base['profile']+'; '+SCOPE)

def check(base,graph,delta,facts):
    require(delta==patch(facts),'EXACT_DECLARATION_PATCH')
    require(graph==apply(base,delta),'EXACT_GRAPH_PRESERVATION')
    ids={n['id'] for n in graph['nodes']}
    require(all(e['from'] in ids and set(e['targets'])<=ids for e in delta['edges']),'DECLARATION_ENDPOINTS')
    # A compile-phase metadata edge must never substitute for the distinct
    # unresolved runtime value edge, even when it reaches a materialized body.
    old=[e for e in base['edges'] if e['evidence'].startswith('binding-versions/open/')]
    current=[e for e in graph['edges'] if e['evidence'].startswith('binding-versions/open/')]
    require(old==current and all(e['resolution']=='unresolved' for e in current),'RUNTIME_BOUNDS_PRESERVED')
