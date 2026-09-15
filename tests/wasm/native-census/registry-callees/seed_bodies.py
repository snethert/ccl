"""Traverse approved startup roots using bodies observed in the same process.

Every seed recipe lookup is re-evaluated in the new image snapshot. Numeric
identities from earlier sessions are never reused as correspondence evidence.
"""
from collections import Counter,defaultdict,deque
from copy import deepcopy
from pathlib import Path
import hashlib,json,sys
from payloads import (read,save,require,rows,capture,literal_regions,literal_key,dependency_body_key,
                      before_functions,correspondences,source_key)
from nested_bodies import pairs,qualify
from initial_marker_join import read_marker
from deferred import collect,index as deferred_index
from lap_join import KINDS as LAP_KINDS,replay as replay_lap,transfers
from bodies import selected_rows

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'startup-closure'))
import candidates


def select(image,spec,mapping,functions):
    require(spec['version']==2 and spec['review_disposition']=='REVIEWED_APPROVED','SEED_APPROVED_RECIPE')
    kernel=candidates.kernel_inputs(image,spec)
    native={r['id']:r for r in image['functions']}
    require(len(native)==len(image['functions']),'SEED_INSPECTOR_IDS')
    ids={r['inspection_id']:r['function'] for r in mapping['entries']}
    require(len(ids)==len(mapping['entries']) and len(set(ids.values()))==len(ids)
            and set(ids)==set(native) and set(ids.values())<=set(functions),'SEED_OBJECT_MAPPING')
    for i,r in native.items():
        f=functions[ids[i]]
        require(f['prototype'] in functions,'SEED_PROTOTYPE')
        observed={x['function'] for x in f['literals'] if isinstance(x,dict) and 'function' in x}
        # The inspector explicitly maps closure instances to their code
        # prototypes. Preserve the instance/environment dependency separately.
        require({functions[j]['prototype'] for j in observed}=={ids[j] for j in r['literal_functions']},
                'SEED_LITERAL_IDENTITY')
    roots=set();bindings=[]
    for s in spec['entrypoints']:
        pool=kernel['callbacks'] if s['binding_kind']=='callback' else [r for r in image['bindings'] if r['namespace']=='function']
        found=[r for r in pool if r['name']==s['name']]
        require(len(found)==1 and found[0]['function'] in ids,'SEED_ENTRY_BINDING '+s['name'])
        i=found[0]['function'];roots.add(i);bindings.append(dict(s,inspection_function=i,function=ids[i]))
    roots.update(r['function'] for r in kernel['callbacks']+kernel['builtins']+kernel['toplevel_methods'] if r['function'] is not None)
    roots.update(r['function'] for g in image['startup_groups'] for r in g['functions'])
    pending=deque(roots);seen=set()
    while pending:
        i=pending.popleft()
        if i in seen:continue
        require(i in native,'SEED_LITERAL_MISSING');seen.add(i);pending.extend(native[i]['literal_functions'])
    require(all(functions[ids[i]]['prototype']==ids[i] for i in seen),'SEED_SELECTED_CLOSURE_ENVIRONMENT')
    instances=[dict(owner=ids[i],instance=x['function'],prototype=functions[x['function']]['prototype'])
               for i in sorted(seen) for x in functions[ids[i]]['literals']
               if isinstance(x,dict) and 'function' in x and x['function']!=functions[x['function']]['prototype']]
    return dict(roots=sorted(roots),population=sorted(seen),mapping=ids,entry_bindings=bindings,literal_instances=instances,
                requested=sorted(ids[i] for i in seen),kernel=kernel,startup_groups=image['startup_groups'])


def final_reads(functions,events,initial,selected):
    result=dict(functions);seen=set();changes=[]
    for row in events:
        if row['kind']!='final-function':continue
        i=row['id'];require(i in functions and i not in seen,'SEED_FINAL_ID');seen.add(i);old=functions[i]
        raw=bytes.fromhex(row['payload_hex']);require(len(raw)==8*row['words'],'SEED_FINAL_PAYLOAD')
        require(row['code_words']==int.from_bytes(raw[:4],'little') and
                int.from_bytes(raw[-8:],'little',signed=True)==row['bits']<<3 and
                len(row['literals'])==row['words']-row['code_words']-1,'SEED_FINAL_LAYOUT')
        same_execution=(row['prototype']==old['prototype'] and row['code_words']==old['code_words'] and
                row['payload_hex'][:16*row['code_words']]==old['payload_hex'][:16*old['code_words']] and
                (row['bits'] & ~(1<<23))==(old['bits'] & ~(1<<23)) and
                literal_regions(row)[0]==literal_regions(old)[0])
        # Compiling definitions can legitimately update unrelated generic
        # functions. Keep their original checkpoint; never transplant that
        # changed state into the startup snapshot or a compiled-body match.
        if i not in initial or i in selected:require(same_execution,'SEED_FINAL_EXECUTION_CHANGED')
        if i in selected:
            require(all(row[k]==old[k] for k in ('bits','words','source','source_start','source_end','literals')),
                    'SEED_INITIAL_OBJECT_CHANGED')
        for ix,lit in enumerate(row['literals'],row['code_words']):
            if isinstance(lit,dict) and 'integer' in lit and -(1<<60)<=lit['integer']<(1<<60):
                require(int.from_bytes(raw[ix*8:(ix+1)*8],'little',signed=True)==lit['integer']<<3,
                        'SEED_FINAL_IMMEDIATE')
        fields=('bits','words','source','source_start','source_end','literals','payload_hex')
        if any(row[k]!=old[k] for k in fields):
            changes.append(dict(function=i,initial_read=old['sequence'],final_read=row['sequence'],
                                changed=[k for k in fields if row[k]!=old[k]],
                                initial_object=i in initial,
                                execution_changed=not same_execution,
                                literal_words_changed=[ix for ix in range(row['code_words'],min(row['words'],old['words'])-1)
                                  if row['payload_hex'][16*ix:16*(ix+1)]!=old['payload_hex'][16*ix:16*(ix+1)]]))
        if i not in initial and old['sequence']<row['sequence']:result[i]=dict(row,kind='function')
    start=min(r['sequence'] for r in events if r['kind']=='final-function')
    require({i for i,r in functions.items() if r['sequence']<start}<=seen,'SEED_FINAL_COVERAGE')
    return result,changes


def callback_bodies(runtime,functions,emissions,before,build,requested,existing):
    """An exact callback-name identity plus the actual compiled entry body.

    Only the source-info flag may differ. It changes metadata, which stays
    unresolved; every runtime flag, instruction and callable literal is checked.
    """
    found=[]
    for callback in runtime['callbacks']:
        old=callback['function']
        if old not in requested or old in existing:continue
        graph=callback['symbol'];objects={n['id']:n for n in graph['objects']};symbol=objects.get(graph['root'].get('ref'))
        require(symbol and symbol['kind']=='symbol','SEED_CALLBACK_SYMBOL')
        a=functions[old];key=dependency_body_key(a,True)
        if key is None:continue
        possible=[]
        for i,records in emissions.items():
            b=functions[i];other=dependency_body_key(b,True)
            if other is None or (key[0] & ~(1<<23))!=(other[0] & ~(1<<23)) or key[1:]!=other[1:]:continue
            for e in records:
                info=before[e['afunc']]
                if info['parent'] is None:possible.append((i,e,info))
        events={r['sequence']:r for r in selected_rows(build,{b['event'] for _,_,b in possible})}
        records=[];witnesses=[]
        for i,e,info in possible:
            row=events[info['event']];raw={n['id']:n for n in row['payload']['ir']['objects']};af=raw[row['payload']['ir']['root']['ref']]
            name=raw.get(af['name'].get('ref'))
            if name!=symbol:continue
            require(af['id']==e['afunc'] and af['parent'] is None and
                    runtime['build_event']<info['event']<e['event'],'SEED_CALLBACK_ORDER')
            records.append(dict(function=i,**e,before=info))
            witnesses.append(dict(slot=callback['slot'],native_function=old,symbol=symbol,
                compiled_function=i,afunc=e['afunc'],before=info,materialization=e['event'],
                native_bits=a['bits'],compiled_bits=functions[i]['bits'],
                separated_info_flag=1<<23,entry_record=runtime['sequence']))
        if not records:continue
        ids=sorted({r['function'] for r in records});deps=[]
        for ix,x in enumerate(literal_regions(a)[0]):
            if isinstance(x,dict) and 'function' in x:
                deps.append(dict(index=ix,bootstrap_literal=x,
                    compiled_literals={str(i):literal_regions(functions[i])[0][ix] for i in ids},disposition='POTENTIAL'))
            else:
                require(literal_key(x) is not None and all(literal_key(x)==literal_key(literal_regions(functions[i])[0][ix]) for i in ids),
                        'SEED_CALLBACK_NONCALLABLE_SUBSTITUTION')
        found.append(dict(bootstrap_code=old,code_words=a['code_words'],literal_count=len(literal_regions(a)[0]),
            metadata_literals=literal_regions(a)[1],metadata_disposition='UNRESOLVED',candidate_only=True,
            function_dependencies=deps,compiled_functions=ids,compiler_records=records,callback_witnesses=witnesses,
            scope='Same-execution callback entry body; source-info metadata and captured environments remain separate.'))
    return found


def special_bodies(selection,functions,assembly,checkpoints,runtime,remaining):
    result=[];initial=checkpoints[0]
    for i in sorted(remaining):
        f=functions[i];states=[r for r in initial['entries'] if r['gf']==i]
        if states:
            from registry import state_check
            require(len(states)==1,'SEED_GF_STATE');state=states[0];state_check(state,functions)
            ps=[r['prototype'] for r in runtime['dcode_prototypes'] if r['dcode']==state['dcode']]
            require(len(ps)<=1,'SEED_GF_PROTOTYPE_REGISTRY')
            prototype=ps[0] if ps else runtime['default_gf_prototype'];p=functions[prototype]
            require(f['code_words']==p['code_words'] and
                    f['payload_hex'][:16*f['code_words']]==p['payload_hex'][:16*p['code_words']],
                    'SEED_GF_CODE_TEMPLATE')
            lits=literal_regions(f)[0]
            require(len(lits)==4 and lits[0].get('object')==state['wrapper'] and
                    lits[2].get('object')==state['dispatch_table'] and lits[3]==dict(function=state['dcode']),
                    'SEED_GF_LITERAL_SLOTS')
            require(state['dcode'] in selection['requested'] and
                    {m['function'] for m in state['methods']}<=set(selection['requested']),
                    'SEED_GF_METHOD_COVERAGE')
            kind='GENERIC_FUNCTION_TEMPLATE';extra=dict(registry=state,prototype=prototype,
                registry_bound='UNRESOLVED_FUTURE_MUTATIONS',captured_data='UNRESOLVED')
        else:prototype=i;p=f;kind='ASSEMBLED_ENTRY';extra={}
        # Native assembly names live in the actual name-slot word; spelling
        # alone cannot identify a definition from another execution.
        name=p['literals'][-1]
        require('symbol' in name,'SEED_ASSEMBLY_NAME_SLOT')
        matches=[d for d in assembly if d['name'] and d['name']['id']==name['symbol'] and
                 dependency_body_key(functions[d['function']])==dependency_body_key(p)]
        require(len(matches)==1,'SEED_ASSEMBLY_BODY '+str(i))
        definition=matches[0]
        result.append(dict(function=i,kind=kind,assembly=definition,transfers=transfers(definition),
                           target_replacement='UNRESOLVED',**extra))
    return result


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    require(read(a.native/'summary.json')['status']=='PASS','SEED_NATIVE_RUN')
    root=a.native/'observed';events=list(rows(root/'registries.jsonl.gz'))
    fs,em,checkpoints,wr,_=capture(root/'registries.jsonl.gz',LAP_KINDS|{'inspection-map','seed-runtime-inputs','deferred-marker-read','final-function'})
    maps=[r for r in events if r['kind']=='inspection-map'];require(len(maps)==1,'SEED_MAPPING_COUNT')
    spec=read(HERE.parent/'startup-closure/seeds.json');image=read(root/'image.json')
    selection=select(image,spec,maps[0],fs);save(a.output/'selection.json',selection)
    initial={r['function'] for r in maps[0]['entries']};fs,changes=final_reads(fs,events,initial,set(selection['requested']))
    before=before_functions(root/'build.jsonl.gz',em)
    markers=[read_marker(r,fs,a.source) for r in events if r['kind']=='deferred-marker-read']
    require(len(markers)==1,'SEED_MARKER_COUNT')
    deferred=collect(root/'build.jsonl.gz',fs,em,before,a.source,{},initial_markers=markers)
    require(not deferred['unjoined'],'SEED_INITIALIZER_BODY')
    asks={'bodies':[dict(code=i,payload_sha256=hashlib.sha256(bytes.fromhex(fs[i]['payload_hex'])).hexdigest())
                    for i in selection['requested']]}
    ca,missing=correspondences(fs,em,wr,asks,before,data_dependencies=True,candidate_function_literals=True,
                              deferred=deferred_index(deferred))
    runtime=[r for r in events if r['kind']=='seed-runtime-inputs'];require(len(runtime)==1,'SEED_RUNTIME_RECORD')
    ca+=callback_bodies(runtime[0],fs,em,before,root/'build.jsonl.gz',set(selection['requested']),
                        {r['bootstrap_code'] for r in ca})
    relation,_=pairs(fs,ca);matched=qualify(fs,ca,relation);joined={r['bootstrap_code'] for r in matched}
    assembly=replay_lap(events,fs)
    special=special_bodies(selection,fs,assembly,checkpoints,runtime[0],set(selection['requested'])-joined)
    joined.update(r['function'] for r in special)
    for name,value in [('functions.json.gz',list(fs.values())),('emissions.json.gz',em),('before.json.gz',before),
                       ('final-read-changes.json',changes),('deferred.json.gz',deferred),('matches.json.gz',matched),
                       ('candidates.json.gz',ca),('assembly.json.gz',assembly),('checkpoints.json.gz',checkpoints),
                       ('runtime-inputs.json',runtime),('special-bodies.json.gz',special)]:save(a.output/name,value)
    remaining=[dict(function=i,name=fs[i]['name'],source=fs[i]['source'],source_start=fs[i]['source_start'],
                    bits=fs[i]['bits'],candidate=i not in missing) for i in selection['requested'] if i not in joined]
    save(a.output/'remaining.json',remaining)
    summary=dict(status='PASS',roots=len(selection['roots']),snapshot_functions=len(selection['requested']),
                 source_body_matches=len(matched),remaining=remaining,initializers=len(deferred['placeholders']),
                 special_body_matches=len(special),assembly_definitions=len(assembly),reread_changes=len(changes),
                 final_metadata_updates=sum(any(k!='payload_hex' for k in r['changed']) for r in changes),census_status='BLOCKED')
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('native','source','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():
            (a.output/'failure.txt').write_text(traceback.format_exc())
            (a.output/'seed_bodies.py').write_bytes(Path(__file__).read_bytes())
        raise
