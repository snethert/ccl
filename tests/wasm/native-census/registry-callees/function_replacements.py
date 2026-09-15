"""Recover source-less resident bodies through actual function-cell stores.

A before-build value and a completed later installation share an exact symbol
identity. Equal executable bodies and a closed function-literal relation connect
the old code to the installed code's real compiler input. This is neither a
claim that the binding remains fixed nor a transfer of a closure environment.
"""
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import sys
from payloads import read,save,require,capture,dependency_body_key,source_key
from nested_bodies import materialized_candidates
from method_reload_join import body_pairs
from method_graph import reload_match
from bodies import extract,make,apply,with_initializers,needed_matches

HERE=Path(__file__).resolve().parent


def candidates(bindings,requested,functions,compiled,before):
    cells=defaultdict(list);stores=defaultdict(list)
    for b in bindings:
        if b['symbol'].get('kind')!='symbol' or b['value']['role']!='function':continue
        symbol=b['symbol']['id']
        if b['kind']=='resident-binding' and b['stage']=='before' and b['value']['code'] in requested:
            cells[symbol].append(b)
        elif b['kind']=='binding-installed':stores[symbol].append(b)
    result=[]
    for symbol,old in cells.items():
        for initial in old:
            a=initial['value']['code']
            for installed in stores[symbol]:
                b=installed['value']['code']
                if b not in functions or not any(e['afunc'] in before for e in compiled.get(b,[])):continue
                if dependency_body_key(functions[a],True)!=dependency_body_key(functions[b],True):continue
                require(initial['symbol']==installed['symbol'] and initial['sequence']<installed['sequence'],
                        'FUNCTION_REPLACEMENT_CELL_IDENTITY')
                records=[e for e in compiled[b] if e['afunc'] in before and
                         before[e['afunc']]['event']<e['event']<installed['sequence']]
                if not records:continue
                unit=source_key(installed['loading_source'])
                if unit is None:continue
                pairs=body_pairs(functions,compiled,before,[(a,b)],unit)
                require(all(e['event']<installed['sequence'] for p in pairs for e in p['compiler_records']),
                        'FUNCTION_REPLACEMENT_BODY_ORDER')
                result.append(dict(initial=initial,installed=installed,source=unit,pairs=pairs))
    return result


def controls(bindings,requested,functions,compiled,before,expected):
    result=[];w=expected[0];a=w['initial']['value']['code'];b=w['installed']['value']['code']
    def loses(name,bs=bindings,fs=functions,cs=compiled):
        found=candidates(bs,requested,fs,cs,before)
        require(not any(r['initial']['value']['code']==a for r in found),'FUNCTION_REPLACEMENT_CONTROL '+name)
        result.append(dict(name=name,status='REJECTED'))
    def changed_store(**fields):
        return [dict(r,**fields) if r==w['installed'] else r for r in bindings]
    loses('same-spelling-other-cell',changed_store(symbol=dict(w['installed']['symbol'],id=-1)))
    loses('removal-intent-is-not-installation',changed_store(kind='binding-removing'))
    loses('final-inventory-is-not-installation',changed_store(kind='resident-binding',stage='after'))
    loses('missing-installation',[r for r in bindings if r!=w['installed']])
    loses('macro-wrapper-not-callable',changed_store(value=dict(w['installed']['value'],role='macro-wrapper')))
    damaged=dict(compiled);damaged.pop(b)
    loses('missing-compiler-provenance',cs=damaged)
    damaged=dict(functions);raw=bytearray.fromhex(functions[b]['payload_hex']);raw[8]^=1
    damaged[b]=dict(functions[b],payload_hex=raw.hex())
    loses('different-executable-body',fs=damaged)
    damaged=dict(functions);damaged[b]=dict(functions[b],prototype=a)
    loses('borrow-closure-environment',fs=damaged)
    for name,rows,reason in [
        ('store-before-initial-inventory',changed_store(sequence=w['initial']['sequence']-1),'FUNCTION_REPLACEMENT_CELL_IDENTITY'),
        ('change-descriptor-of-exact-cell',changed_store(symbol=dict(w['installed']['symbol'],name='SUBSTITUTED')),
         'FUNCTION_REPLACEMENT_CELL_IDENTITY')]:
        try:candidates(rows,requested,functions,compiled,before)
        except ValueError as e:require(str(e)==reason,'FUNCTION_REPLACEMENT_CONTROL_REASON '+name)
        else:raise ValueError('FUNCTION_REPLACEMENT_CONTROL_ESCAPED '+name)
        result.append(dict(name=name,status='REJECTED'))
    return result


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    functions,emissions,_,_,_=capture(a.capture/'registries.jsonl.gz')
    index=read(a.previous/'compiler-index.json.gz');before={int(k):v for k,v in index['before'].items()}
    loader={int(k):v for k,v in read(a.previous/'loader-body-joins.json.gz')['joins'].items()}
    combined=materialized_candidates(functions,emissions,loader)
    old=read(a.bodies/'body-correspondences.json.gz');requested=set(old['remaining_codes'])
    bindings=read(a.bindings)
    witnesses=candidates(bindings,requested,functions,combined,before)
    require(witnesses,'FUNCTION_REPLACEMENT_NO_PROGRESS')
    checks=controls(bindings,requested,functions,combined,before,witnesses)
    pairs={};roots=set()
    for w in witnesses:
        roots.add(w['initial']['value']['code'])
        for p in w['pairs']:
            key=p['bootstrap_code'];m=reload_match(p)
            require(key not in pairs or pairs[key]==m,'FUNCTION_REPLACEMENT_AMBIGUOUS_BODY');pairs[key]=m
    support={m['bootstrap_code']:m for m in old['matches']+old['support_matches']};support.update(pairs)
    matches=[pairs[k] for k in sorted(roots)];extra=[v for k,v in support.items() if k not in roots]
    deferred=read(a.bodies/'deferred-initializers.json.gz')['placeholders']
    ops={int(k):v for k,v in next(iter(read(a.evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))['operators'].items()}
    families,calls=extract(a.capture/'build.jsonl.gz',with_initializers(needed_matches(matches,extra),deferred),ops)
    base=read(a.base)
    delta=make(base,matches,families,calls,extra,deferred,namespace='replaced-functions:')
    graph=apply(base,delta)
    require(graph==apply(base,make(base,matches,families,calls,extra,deferred,namespace='replaced-functions:')),
            'FUNCTION_REPLACEMENT_GRAPH')
    for name,value in [('witnesses.json.gz',witnesses),('controls.json',checks),('ir.json.gz',dict(functions=families,calls=calls)),
                       ('delta.json.gz',delta),('census.json.gz',graph),('remaining.json',sorted(requested-roots))]:
        save(a.output/name,value)
    from support import load_module
    errors=load_module('replacement_contract',HERE.parents[3]/'doc/WASM/tools/check-census.py').validate(graph)
    require(all(e.startswith(('unresolved reachable edge from ','unimplemented reachable node ')) for e in errors),
            'FUNCTION_REPLACEMENT_GRAPH_STRUCTURE')
    summary=dict(status='PASS',census_status='BLOCKED',new_bodies=len(roots),remaining_readonly_bodies=len(requested-roots),
                 controls=len(checks),cell_value_bounds_transferred=False,caller_bounds_transferred=False)
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','previous','bodies','bindings','base','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
