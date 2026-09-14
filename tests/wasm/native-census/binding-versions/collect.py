"""Read checkpoints, actual store hooks and exact FASL versions, without IR replay."""
from collections import Counter
import gzip
import json
import re
import sys
from common import HERE, require, canonical

sys.path.insert(0, str(HERE.parent/'rich-observation'))
from analyze import Graph, reader_context, reader_value

HEADER = re.compile(rb'^\{"version":2,"sequence":([0-9]+),"kind":"([a-z0-9-]+)"')
SELECTED = {'inventory-enter', 'inventory-return', 'resident-binding', 'resident-function',
            'binding-removing', 'binding-installed', 'fasl-function-write',
            'fasl-function-enter', 'fasl-function-return', 'complete'}
MACRO_MARKER = 0xc9cd0000000000 >> 3  # pinned native xloader word, read as a fixnum


def value(graph, ref):
    n = graph.node(ref)
    if n.get('kind') == 'function':
        return dict(role='function', object=n['id'], code=n['code'], description=n['description'])
    if n.get('kind') == 'simple-vector' and n['expanded'] and n['length'] == len(n['elements']):
        elements = n['elements']
        if len(elements) == 2 and elements[0] == {'integer': MACRO_MARKER}:
            payload = graph.node(elements[1])
            if payload.get('kind') == 'function':
                return dict(role='macro-wrapper', object=n['id'], marker=MACRO_MARKER,
                            payload=value(graph, elements[1]))
            if payload.get('kind') == 'symbol':
                return dict(role='special-wrapper', object=n['id'], marker=MACRO_MARKER, payload=payload)
    # Do not guess from vector shape or treat a macro's expander as a runtime callee.
    return dict(role='unclassified', raw=graph.slice(ref))


def binding(row):
    resident = row['kind'] == 'resident-binding'
    graph = Graph(row['payload']['binding'] if resident else row['payload'])
    refs = graph.items(); removing = row['kind'] == 'binding-removing'
    require(len(refs) == (3 if removing else 2), 'BINDING_ARGUMENTS')
    symbol = graph.node(refs[0])
    require(symbol=={'atom':'nil'} or
            set(symbol) == {'id','kind','name','package','setter_of'} and symbol['kind']=='symbol',
            'BINDING_SYMBOL')
    out = {k:row[k] for k in ('sequence','kind','process','parent','source','source_position','loading_source')}
    out.update(symbol=symbol, value=value(graph, refs[1]))
    if resident: out['stage'] = row['payload']['stage']
    if removing:
        # The old value is witnessed. The new sentinel is removal INTENT: the
        # hook runs before the store and cannot witness that store's completion.
        out['removal_intent'] = graph.slice(refs[2])
        if refs[1]==refs[2]:out['value']=dict(role='unbound',raw=graph.slice(refs[1]))
    return out


def collect(path):
    counts=Counter(); last=0; complete=False; stage=None; stages=[]
    bindings=[]; inventories=[]; residents=[]; writes={}; reads=[]; entries={}; samples={}
    with gzip.open(path,'rb') as stream:
        for line in stream:
            m=HEADER.match(line); require(m is not None,'EVENT_HEADER')
            seq=int(m[1]); kind=m[2].decode()
            require(seq==last+1 and not complete,'EVENT_SEQUENCE')
            last=seq; counts[kind]+=1
            if kind not in SELECTED: continue
            r=json.loads(line); require(r['sequence']==seq and r['kind']==kind,'EVENT_HEADER_JOIN')
            if kind=='inventory-enter':
                require(stage is None and r['payload']['stage'] in ('before','after'),'INVENTORY_ENTER')
                stage=r['payload']['stage']; stages.append(stage); inventories.append(r)
            elif kind=='inventory-return':
                require(stage==r['payload']['stage'],'INVENTORY_RETURN'); stage=None; inventories.append(r)
            elif kind=='resident-function':
                require(stage==r['payload']['stage'],'RESIDENT_FUNCTION_STAGE')
                g=Graph(r['payload']['function']); fn=g.node(g.root)
                require(fn['kind']=='function','RESIDENT_FUNCTION_KIND')
                residents.append(dict(event=seq,stage=stage,code=fn['code'],object=fn['id']))
            elif kind in ('resident-binding','binding-installed','binding-removing'):
                if kind=='resident-binding': require(stage==r['payload']['stage'],'RESIDENT_BINDING_STAGE')
                else: require(stage is None,'STORE_DURING_INVENTORY')
                b=binding(r); bindings.append(b)
                samples.setdefault(kind+':'+b.get('stage','')+':'+b['value']['role'],r)
            elif kind=='fasl-function-write':
                g=Graph(r['payload']); refs=g.items(); require(len(refs)==4,'WRITE_ARGUMENTS')
                file,pos,opcode=g.args()[:3]
                require(isinstance(file,str) and type(pos) is int and type(opcode) is int,'WRITE_LOCATION')
                writes[(file,pos+1)]=dict(event=seq,file=file,position_after_opcode=pos+1,
                                        opcode=opcode,code=g.function(refs[3]))
            elif kind=='fasl-function-enter':
                require(seq not in entries,'READER_DUPLICATE'); entries[seq]=r
            elif kind=='fasl-function-return':
                require(r['parent'] in entries,'READER_PAIR')
                begin=entries.pop(r['parent']); g=Graph(r['payload'])
                context=reader_context(begin['payload'],r['payload']); result=reader_value(g,context)
                args=Graph(begin['payload']).args(); end=g.args()
                require(begin['process']==r['process'] and args[:2]==end[:2]
                        and type(end[2]) is int and end[2]>args[2],'READER_LOCATION')
                written=writes.get((args[0],args[2]))
                if written: require(written['event']<begin['sequence'] and written['opcode']==args[1], 'READER_WRITE_VERSION')
                reads.append(dict(event=seq,enter=begin['sequence'],process=r['process'],file=args[0],
                    position_after_opcode=args[2],position_after_function=end[2],
                    opcode=args[1],**context,**result,written=written))
            else:
                expected={n['kind']:n['count'] for n in r['payload']['counts']}
                actual=dict(counts); del actual['complete']
                require(expected==actual and r['payload']['events_before_complete']==seq-1,'COMPLETION_COUNTS')
                complete=True
    require(complete and not entries and stage is None and stages==['before','after'],'INCOMPLETE_STREAM')
    return dict(version=1,events=last,counts=dict(counts),inventories=inventories,
                bindings=bindings,residents=residents,reads=reads),samples
