"""Validate correlated capture records and find strict native body correspondences.

Code correspondences are not function identity or caller-environment bounds.
Any reuse of IR must leave the matched body's incoming/captured values unknown.
"""
from collections import Counter,defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'closure'))
from support import read,save


def require(ok,reason):
    if not ok:raise ValueError(reason)


def rows(path):
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt') as src:
        for line in src:yield json.loads(line)


def capture(path,extra_kinds=()):
    functions={};emissions=defaultdict(list);counts=Counter();active=[];checkpoints=[];wrappers=set();complete=None
    seen=0;last_build=0
    for row in rows(path):
        seen+=1;require(row['sequence']==seen and complete is None,'SIDE_SEQUENCE')
        require(type(row['build_event']) is int and row['build_event']>=last_build,'SIDE_BUILD_ORDER')
        last_build=row['build_event'];kind=row['kind'];counts[kind]+=1
        if kind=='function':
            ident=row['id'];require(ident not in functions,'DUPLICATE_NATIVE_FUNCTION')
            require(type(ident) is int and ident>0 and type(row['prototype']) is int and row['prototype']>0,'NATIVE_ID')
            words=row['words'];code=row['code_words'];payload=row['payload_hex']
            # An unnamed function with no info or constants has only its code
            # prefix and the final bits word. Such functions legitimately have
            # an empty %MAP-LFIMMS range.
            require(type(words) is int and type(code) is int and 1<=code<=words-1,'NATIVE_WORDS')
            require(len(payload)==16*words and bytes.fromhex(payload).hex()==payload,'NATIVE_PAYLOAD')
            binary=bytes.fromhex(payload)
            require(int.from_bytes(binary[:4],'little')==code,'NATIVE_CODE_HEADER')
            bits=int.from_bytes(binary[-8:],'little',signed=True)
            require(bits & 7==0 and bits>>3==row['bits'],'NATIVE_BITS_WORD')
            # %MAP-LFIMMS includes the name/info word at WORDS-2. It omits
            # only the final LFUN-bits word, unlike the execution-literal range.
            require(len(row['literals'])==words-code-1,'NATIVE_LITERAL_COUNT')
            for index,literal in enumerate(row['literals'],code):
                if isinstance(literal,dict) and 'integer' in literal and -(1<<60)<=literal['integer']<(1<<60):
                    word=int.from_bytes(binary[index*8:(index+1)*8],'little',signed=True)
                    require(word==literal['integer']<<3,'NATIVE_IMMEDIATE_WORD')
            functions[ident]=row
        elif kind=='compiler-materialization':
            ids=[f['afunc'] for f in row['functions']]
            require(len(ids)==len(set(ids)) and bool(ids),'MATERIALIZED_FAMILY')
            for f in row['functions']:
                if f['function'] is not None:emissions[f['function']].append(dict(afunc=f['afunc'],event=row['build_event']))
        elif kind=='observer-wrapper':wrappers.add(row['wrapper'])
        elif kind=='mutation-enter':
            require(row['parent']==(active[-1] if active else None),'MUTATION_PARENT');active.append(row['sequence'])
        elif kind=='mutation-leave':
            require(active and active.pop()==row['entry'] and row['completed'] is True,'MUTATION_COMPLETION')
        elif kind=='registry-checkpoint':checkpoints.append(row)
        elif kind=='complete':complete=row
        else:require(kind in ('backend-checkpoint','capture-policy') or kind in extra_kinds,'UNKNOWN_SIDE_EVENT')
    require(complete and complete['completed'] is True and complete['hooks_restored'] is True and not active,'SIDE_COMPLETION')
    require(complete['native_functions']==len(functions) and set(emissions)<=set(functions),'NATIVE_POPULATION')
    require([r['stage'] for r in checkpoints]==['before','after'],'REGISTRY_CHECKPOINTS')
    for fn in functions.values():
        require(fn['prototype'] in functions,'PROTOTYPE_REFERENCE')
        for literal in fn['literals']:
            if isinstance(literal,dict) and 'function' in literal:require(literal['function'] in functions,'FUNCTION_LITERAL_REFERENCE')
    return functions,emissions,checkpoints,wrappers,dict(counts)


def literal_key(value):
    if value is None:return ('nil',)
    require(isinstance(value,dict),'LITERAL_SHAPE')
    for kind in ('function','symbol','object','character'):
        if kind in value:return (kind,value[kind])
    if 'integer' in value:
        # Only native fixnums have identity fixed by their recorded value.
        # A boxed integer/string serialized by value has no identity witness.
        if -(1<<60)<=value['integer']<(1<<60):return ('fixnum',value['integer'])
        return None
    if 'string' in value:return None
    raise ValueError('UNCLASSIFIED_LITERAL')


def source_key(source):
    if not isinstance(source,str):return None
    logical=source.lower().startswith('ccl:')
    if logical:source=source[4:].replace(';','/')
    elif '/ccl/' in source:source=source.split('/ccl/',1)[1]
    else:return None
    source=source.casefold()
    # SETUP-INITIAL-TRANSLATIONS in U1 l1-pathnames.lisp maps CCL:l1;
    # onto CCL:level-1;. It is a logical alias, not a physical-path alias.
    if logical and source.startswith('l1/'):source='level-1/'+source[3:]
    return source.removesuffix('.newest')


def literal_regions(fn):
    """U1's constant/name/info split, also used by EDIT-CALLERS.

    The final LFUN word is already outside %MAP-LFIMMS. Name and info
    words are described by bits 29 and 23 (library/lispequ.lisp). Keep
    metadata as separate dependencies; it is never silently identified.
    """
    name_count=0 if fn['bits'] & (1<<29) else 1
    info_count=1 if fn['bits'] & (1<<23) else 0
    end=len(fn['literals'])-name_count-info_count
    require(end>=0,'METADATA_LITERAL_BOUNDARY')
    return fn['literals'][:end],fn['literals'][end:]


def body_key(fn):
    if fn['id']!=fn['prototype']:return None
    literals=[literal_key(v) for v in literal_regions(fn)[0]]
    if any(v is None for v in literals):return None
    return (fn['bits'],fn['code_words'],fn['payload_hex'][:16*fn['code_words']],tuple(literals),
            json.dumps(fn['name'],sort_keys=True))


def dependency_body_key(fn,candidate_function_literals=False):
    """Match call-bearing code while preserving noncallable data as obligations.

    Symbols and functions can be direct callees and must retain exact identity.
    Noncallable aggregate contents are not identified: every substituted object
    becomes an unresolved data dependency. No computed target or argument-flow
    proof is transferred from the newly compiled function.
    """
    if fn['id']!=fn['prototype']:return None
    keys=[]
    for v in literal_regions(fn)[0]:
        if v is None:keys.append(('nil',))
        elif candidate_function_literals and 'function' in v:keys.append(('function-pair-required',))
        elif 'object' in v:keys.append(('data-object',json.dumps(v['type'],sort_keys=True)))
        elif 'string' in v:keys.append(('string-value',v['string']))
        elif 'integer' in v:keys.append(('integer-value',v['integer']))
        else:keys.append(literal_key(v))
    # The name is in the already-separated metadata region. Reflective
    # consumers still have the metadata-materialization obligation.
    return (fn['bits'],fn['code_words'],fn['payload_hex'][:16*fn['code_words']],tuple(keys))


def before_functions(build,emissions=None,late_notes=None):
    result={};materialized={}
    for row in rows(build):
        if late_notes is not None and row['kind']=='resident-function' and row['payload']['stage']=='after':
            graph=row['payload']['function'];objects={n['id']:n for n in graph['objects']}
            native=objects[graph['root']['ref']]
            require(native['kind']=='function','FINAL_FUNCTION_DESCRIPTOR')
            if native['id']==native['code']:
                ident=native['id'];desc=native['description']
                require(ident not in late_notes or late_notes[ident]['description']==desc,'FINAL_DESCRIPTOR_CONFLICT')
                late_notes[ident]=dict(event=row['sequence'],description=desc)
        if emissions is not None and row['kind']=='function-materialized':
            objects={n['id']:n for n in row['payload']['objects']}
            for n in objects.values():
                if n['kind']!='afunc':continue
                target=n['function']
                if target=={'atom':'nil'}:continue
                require(set(target)=={'ref'} and target['ref'] in objects
                        and objects[target['ref']]['kind']=='function','MAIN_MATERIALIZED_REFERENCE')
                key=(row['sequence'],n['id']);require(key not in materialized,'DUPLICATE_MAIN_MATERIALIZATION')
                materialized[key]=target['ref']
        if row['kind']!='before-pass2':continue
        pending=[row['payload']['function']]
        while pending:
            fn=pending.pop();ident=fn['function_id']
            require(ident not in result,'REPEATED_BEFORE_PASS2')
            result[ident]=dict(event=row['sequence'],root=row['payload']['function']['function_id'],
                               parent=fn['parent_id'],source=row['source'],source_position=row['source_position'])
            # %INCLUDE retains the outer compilation unit while FCOMP's
            # read loop records the included input in LOADING_SOURCE.
            if source_key(row.get('loading_source'))!=source_key(row['source']):
                result[ident]['reader_source']=row.get('loading_source')
            pending.extend(fn['inner_functions'])
    if emissions is not None:
        got={(e['event'],e['afunc']):fid for fid,es in emissions.items() for e in es}
        require(len(got)==sum(map(len,emissions.values())) and got==materialized,'MAIN_SIDE_MATERIALIZATION_JOIN')
    return result


def correspondences(functions,emissions,wrappers,old_bodies,before,late_notes=None,source_maps=None,
                    data_dependencies=False,candidate_function_literals=False,deferred=None,definition_witnesses=None):
    requested={b['code']:b for b in old_bodies['bodies']};groups=defaultdict(list)
    require(not candidate_function_literals or data_dependencies,'FUNCTION_CANDIDATE_MODE')
    key_for=(lambda fn:dependency_body_key(fn,candidate_function_literals)) if data_dependencies else body_key
    require(deferred is None or data_dependencies,'DEFERRED_REQUIRES_DATA_OBLIGATIONS')
    def group_key(key):return key[:3]+(len(key[3]),) if deferred is not None and key is not None else key
    for ident in emissions:
        fn=functions[ident];key=key_for(fn)
        if key is not None and ident not in wrappers and any(e['afunc'] in before for e in emissions[ident]):groups[group_key(key)].append(ident)
    matches=[];missing=[]
    for ident,old in sorted(requested.items()):
        require(ident in functions,'MISSING_ANCHORED_BODY')
        fn=functions[ident]
        require(hashlib.sha256(bytes.fromhex(fn['payload_hex'])).hexdigest()==old['payload_sha256'],'BOOTSTRAP_PAYLOAD_CHANGED')
        key=key_for(fn);candidates=sorted(groups.get(group_key(key),[])) if key is not None else []
        def deferred_constant(e,f,index):
            value=literal_regions(functions[f])[0][index]
            if deferred is None or not isinstance(value,dict) or value.get('type')!={'package':'COMMON-LISP','symbol':'CONS'}:return None
            b=before.get(e['afunc']);r=deferred.get((b['event'],value.get('object'))) if b else None
            return r if r and e['afunc'] in r['owners'] else None
        def compatible(e,f):
            other=key_for(functions[f])
            if deferred is None:return True
            for index,(a,b) in enumerate(zip(key[3],other[3])):
                if a==b:continue
                old_literal=literal_regions(fn)[0][index]
                if not (isinstance(old_literal,dict) and 'object' in old_literal and deferred_constant(e,f,index)):return False
            return True
        # A descriptor drained after materialization carries the source note
        # attached to that exact LFUN. The compiler's stream position may
        # precede the note by reader whitespace; it is not the note offset.
        # Require both the compiler source and the actual LFUN's full span.
        source=source_key(fn['source']);position=fn['source_start'];end=fn['source_end'];source_witness=None
        if source_maps is not None and source is not None and position is not None and end is not None:
            from source_map import span
            mapped,source_witness=span(source_maps,source,position,end)
            if mapped is None:missing.append(ident);continue
            position,end=mapped
        def same_form(e,f):
            b=before.get(e['afunc'])
            compiled=functions[f]
            if not compatible(e,f):return False
            witness=(definition_witnesses or {}).get((ident,f,e['afunc']))
            if witness is not None:
                # This alternative is an actual named compiler definition of
                # the exact resident symbol cell, qualified separately from
                # source notes. It witnesses executable-body dependencies,
                # not the old function's compilation history or installation.
                require(fn['source'] is None and b and b['parent'] is None and b['root']==e['afunc']
                        and witness['initial']['value']['code']==ident
                        and witness['definition']['afunc']==e['afunc']
                        and witness['definition']['event']==b['event']
                        and witness['materialization']==dict(function=f,**e)
                        and witness['initial']['symbol']==witness['definition']['symbol']
                        and witness['initial']['sequence']<b['event']<e['event'],
                        'DEFINITION_BODY_WITNESS')
                return True
            if not (b and b['event']<e['event'] and source is not None and position is not None and end is not None
                    and (source_key(b['source'])==source or source_key(b.get('reader_source'))==source)):return False
            if compiled['source'] is not None:
                return (source_key(compiled['source'])==source and compiled['source_start']==position
                        and compiled['source_end']==end)
            # Some functions are drained before their AFUNC source note is
            # attached. The final inventory reads the actual same prototype
            # again. Use that recorded note, never the function's name or a
            # guessed offset from the compiler stream's preceding whitespace.
            late=(late_notes or {}).get(f)
            return (late and e['event']<late['event'] and source_key(late['description']['source'])==source
                    and late['description']['position']==position)
        candidates=[f for f in candidates if any(same_form(e,f) for e in emissions[f])]
        if not candidates:missing.append(ident);continue
        def compiler_record(e,f):
            b=dict(before[e['afunc']])
            if source_key(b['source'])==source:b.pop('reader_source',None)
            witness=(definition_witnesses or {}).get((ident,f,e['afunc']))
            return dict(function=f,**e,before=b,**({'definition_witness':witness} if witness else {}))
        data=[];function_data=[]
        if data_dependencies:
            for index,value in enumerate(literal_regions(fn)[0]):
                actual=literal_key(value)
                counterparts={str(f):literal_regions(functions[f])[0][index] for f in candidates}
                if actual is None or any(literal_key(v)!=actual for v in counterparts.values()):
                    if isinstance(value,dict) and 'function' in value and candidate_function_literals:
                        function_data.append(dict(index=index,bootstrap_literal=value,compiled_literals=counterparts,
                                                  disposition='POTENTIAL'))
                        continue
                    require(isinstance(value,dict) and not ({'function','symbol'} & set(value)),
                            'CALLABLE_LITERAL_SUBSTITUTION')
                    data.append(dict(index=index,bootstrap_literal=value,compiled_literals=counterparts,
                        disposition='UNRESOLVED',callable=False))
                    initializers={str(f):[r for e in emissions[f] if same_form(e,f)
                        and (r:=deferred_constant(e,f,index)) is not None] for f in candidates}
                    initializers={f:rs for f,rs in initializers.items() if rs}
                    if initializers:data[-1]['deferred_initializers']=initializers
        matches.append(dict(bootstrap_code=ident,code_words=fn['code_words'],literal_count=len(literal_regions(fn)[0]),
            metadata_literals=literal_regions(fn)[1],metadata_disposition='UNRESOLVED',
            **({'candidate_only':True,'function_dependencies':function_data} if candidate_function_literals else {}),
            **({'data_dependencies':data} if data else {}),
            **({'source_coordinate_witness':source_witness} if source_witness and
               source_witness['original_span']!=source_witness['observed_span'] else {}),
            **({'late_source_notes':{str(f):late_notes[f] for f in candidates
                                    if functions[f]['source'] is None and f in (late_notes or {})}}
               if any(functions[f]['source'] is None and f in (late_notes or {}) for f in candidates) else {}),
            compiled_functions=candidates,
            compiler_records=[compiler_record(e,f) for f in candidates for e in emissions[f] if same_form(e,f)],
            scope=('Exact native code, LFUN bits and callable literals at the same source form; noncallable data substitutions remain unresolved and no computed targets or caller environments are transferred.'
                   if data else 'Exact native code, LFUN bits and execution-literal identities at the same source form; metadata remains separate and caller environments are not transferred.')))
    return matches,missing


def prefix_check(build,prior):
    with gzip.open(prior,'rb') as old:
        opener=gzip.open if build.suffix=='.gz' else open
        with opener(build,'rb') as current:
            for _ in range(14720):
                a=old.readline();b=current.readline();require(a and a==b,'READONLY_PREFIX_CHANGED')


def run(output,store):
    prefix_check(output/'build.jsonl.gz',store/'2026-09-14-resident-bodies-r1/first-prefix.jsonl.gz')
    functions,emissions,checkpoints,wrappers,counts=capture(output/'registries.jsonl.gz')
    before=before_functions(output/'build.jsonl.gz',emissions)
    matches,missing=correspondences(functions,emissions,wrappers,read(store/'2026-09-14-resident-bodies-r1/bodies.json.gz'),before)
    save(output/'body-correspondences.json',dict(matches=matches,remaining_codes=missing))
    summary=dict(side_counts=counts,materialized_functions=len(emissions),
                 registry_populations=[len(r['entries']) for r in checkpoints],
                 anchored_bodies=4373,strict_body_correspondences=len(matches),remaining=len(missing))
    save(output/'payload-summary.json',summary);print(summary)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence');a=p.parse_args();run(a.output,a.evidence)
