"""Executable literals, debug metadata and compile-origin separation."""
from copy import deepcopy
import hashlib
from payloads import correspondences,literal_regions,literal_key,source_key,require


def run():
    def fn(ident,metadata):
        return dict(id=ident,prototype=ident,words=5,code_words=1,bits=1<<23,
            payload_hex='ab'*40,literals=[{'symbol':10},{'object':metadata},{'symbol':11}],
            name={'symbol':'PROBE','package':'PRIVATE'},source='ccl:lib;probe.lisp.newest',
            source_start=12,source_end=63)
    a=fn(1,100);b=fn(2,200)
    # The fixture's payload includes its LFUN-bits word; the matching routine
    # uses the separately bounded instruction prefix and semantic literals.
    functions={1:a,2:b};emissions={2:[dict(afunc=20,event=25)]}
    before={20:dict(source='/tmp/ccl/lib/probe.lisp',source_position=10,event=24,root=20,parent=None)}
    old={'bodies':[dict(code=1,payload_sha256=hashlib.sha256(bytes.fromhex(a['payload_hex'])).hexdigest())]}
    def assess(f=functions,e=emissions,bf=before,wr=set()):return correspondences(f,e,wr,old,bf)
    m,u=assess();require(len(m)==1 and not u and m[0]['metadata_disposition']=='UNRESOLVED','METADATA_NOT_IDENTIFIED')
    require(m[0]['metadata_literals']==[{'object':100},{'symbol':11}],'METADATA_RETAINED')
    refused=[]
    def refuse(name,mutate):
        f=deepcopy(functions);e=deepcopy(emissions);bf=deepcopy(before);wr=set()
        mutate(f,e,bf,wr)
        match,remaining=assess(f,e,bf,wr)
        require(not match and remaining==[1],'BODY_CONTROL_ESCAPED '+name);refused.append(name)
    refuse('different-executable-symbol',lambda f,e,b,w:f[2]['literals'][0].update(symbol=12))
    refuse('different-code',lambda f,e,b,w:f[2].update(payload_hex='cd'+f[2]['payload_hex'][2:]))
    refuse('different-source-span',lambda f,e,b,w:f[2].update(source_end=64))
    refuse('absent-source-span',lambda f,e,b,w:f[2].update(source_start=None))
    refuse('wrong-source-unit',lambda f,e,b,w:b[20].update(source='/tmp/ccl/lib/other.lisp'))
    refuse('absent-compiler-body',lambda f,e,b,w:b.clear())
    refuse('emission-before-compiler-body',lambda f,e,b,w:e[2][0].update(event=23))
    refuse('observer-wrapper',lambda f,e,b,w:w.add(2))
    refuse('different-lfun-bits',lambda f,e,b,w:f[2].update(bits=f[2]['bits']+1))
    refuse('closure-instance',lambda f,e,b,w:f[2].update(prototype=1))
    refuse('boxed-integer-by-value',lambda f,e,b,w:[x['literals'].__setitem__(0,{'integer':1<<62}) for x in f.values()])
    refuse('string-by-value',lambda f,e,b,w:[x['literals'].__setitem__(0,{'string':'same'}) for x in f.values()])
    for bit,expected in [(0,2),(1<<23,1),(1<<29,3),((1<<29)|(1<<23),2)]:
        x=deepcopy(a);x['bits']=bit
        require(len(literal_regions(x)[0])==expected,'METADATA_BIT_PARTITION')
    require(literal_regions(dict(bits=-(1<<29),literals=[]))==([],[]),'UNNAMED_EMPTY_LITERAL_RANGE')
    for value in (-(1<<60),(1<<60)-1):require(literal_key({'integer':value}) is not None,'NATIVE_FIXNUM_EDGE')
    for value in (-(1<<60)-1,1<<60):require(literal_key({'integer':value}) is None,'NATIVE_BOXED_EDGE')
    f=deepcopy(functions);f[2].update(source=None,source_start=None,source_end=None)
    late={2:dict(event=40,description=dict(source='ccl:lib;probe.lisp.newest',position=12))}
    m,u=correspondences(f,emissions,set(),old,before,late)
    require(len(m)==1 and not u and m[0]['late_source_notes']=={'2':late[2]},'LATE_NOTE_JOIN')
    for key,value in [('position',13),('source','ccl:lib;other.lisp')]:
        changed=deepcopy(late);changed[2]['description'][key]=value
        require(correspondences(f,emissions,set(),old,before,changed)==([],[1]),'LATE_NOTE_SUBSTITUTION')
        refused.append('late-note-'+key)
    changed=deepcopy(late);changed[2]['event']=23
    require(correspondences(f,emissions,set(),old,before,changed)==([],[1]),'LATE_NOTE_ORDER')
    refused.append('late-note-before-emission')
    include=deepcopy(before);include[20].update(source='/tmp/ccl/compiler/nx.lisp',reader_source='ccl:lib;probe.lisp')
    m,u=correspondences(functions,emissions,set(),old,include)
    require(len(m)==1 and not u and 'reader_source' in m[0]['compiler_records'][0]['before'],'INCLUDED_SOURCE')
    include[20]['reader_source']='ccl:lib;wrong.lisp'
    require(correspondences(functions,emissions,set(),old,include)==([],[1]),'WRONG_INCLUDED_SOURCE')
    require(source_key('ccl:l1;l1-clos.lisp.newest')==source_key('/tmp/ccl/level-1/l1-clos.lisp')
            and source_key('/tmp/ccl/l1/l1-clos.lisp')!=source_key('/tmp/ccl/level-1/l1-clos.lisp'),
            'LOGICAL_ALIAS_NOT_PHYSICAL_ALIAS')
    # Named definitions remain usable when neither LFUN ever receives a
    # source note. Their exact cell/definition witness replaces that route;
    # it must not manufacture a late note or fall back to matching names.
    f=deepcopy(functions)
    for item in f.values():item.update(source=None,source_start=None,source_end=None)
    symbol=dict(id=50,kind='symbol',package='PRIVATE',name='PROBE',setter_of=None)
    witness=dict(initial=dict(value=dict(code=1),symbol=symbol,sequence=10),
        definition=dict(symbol=symbol,afunc=20,event=24),materialization=dict(function=2,afunc=20,event=25))
    m,u=correspondences(f,emissions,set(),old,before,definition_witnesses={(1,2,20):witness})
    require(len(m)==1 and not u and 'late_source_notes' not in m[0]
            and m[0]['metadata_disposition']=='UNRESOLVED','SOURCELESS_DEFINITION_BODY')
    require(correspondences(f,emissions,set(),old,before)==([],[1]),'SOURCELESS_NAME_ONLY_JOIN')
    refused.append('source-less-body-without-cell-witness')
    # Body-dependency reuse may expose calls while leaving noncallable
    # constants unqualified. It must never erase the data obligation or relax
    # a symbol/function callee identity in the same instruction stream.
    for left,right in [({'object':500,'type':'vector'},{'object':600,'type':'vector'}),
                       ({'string':'literal'},{'string':'literal'}),
                       ({'integer':1<<62},{'integer':1<<62})]:
        f=deepcopy(functions);f[1]['literals'][0]=left;f[2]['literals'][0]=right
        m,u=correspondences(f,emissions,set(),old,before,data_dependencies=True)
        require(len(m)==1 and not u and m[0]['data_dependencies']==[dict(index=0,
            bootstrap_literal=left,compiled_literals={'2':right},disposition='UNRESOLVED',callable=False)],
            'NONCALLABLE_DATA_NOT_IDENTIFIED')
    for left,right in [({'symbol':10},{'symbol':12}),({'function':10},{'function':12}),
                       ({'object':500,'type':'vector'},{'function':12}),
                       ({'string':'old'},{'string':'new'})]:
        f=deepcopy(functions);f[1]['literals'][0]=left;f[2]['literals'][0]=right
        require(correspondences(f,emissions,set(),old,before,data_dependencies=True)==([],[1]),
                'DATA_MATCH_CALLEE_OR_VALUE_SUBSTITUTION')
    return dict(status='PASS',negative_cases=refused,metadata_layouts=4,native_integer_boundaries=4,late_note_join=True)


if __name__=='__main__':print(run())
