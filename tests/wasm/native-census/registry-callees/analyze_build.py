"""Resolve correlated native body, loader and method dependencies in one pass."""
from collections import Counter
from pathlib import Path
import hashlib
import sys
import traceback
from payloads import capture,rows,before_functions,correspondences,prefix_check,read,save,require
from registry import replay
from bodies import extract,make,apply,needed_matches,PREFIX
from loader import collect as loader_collect
from source_map import build as source_coordinates
from accessors import prototypes
from methods import assemble as method_bodies
from nested_bodies import closure,pairs,qualify,materialized_candidates

HERE=Path(__file__).resolve().parent


def run(capture_dir,base_path,evidence,output):
    output.mkdir(parents=True,exist_ok=False)
    record=read(capture_dir/'run.json')
    require(record['status']=='PASS' and record['source_restored'] is True and record['restored_fasls']==164,
            'CORRELATED_BUILD_NOT_COMPLETE')
    require(record['baseline_tests']['passed']==record['observed_tests']['passed']==21843
            and not record['r6']['unexplained'],'CORRELATED_NATIVE_BEHAVIOUR')
    source=Path(record['commands'][0]['cwd'])
    prefix_check(capture_dir/'build.jsonl.gz',evidence/'2026-09-14-resident-bodies-r1/first-prefix.jsonl.gz')
    print('Reading the completed compiler and native function capture.',flush=True)
    f,em,checkpoints,wrappers,counts=capture(capture_dir/'registries.jsonl.gz')
    late={};before=before_functions(capture_dir/'build.jsonl.gz',em,late)
    coords=source_coordinates(source)
    save(output/'compiler-index.json.gz',dict(before=before,late_notes=late))
    save(output/'source-coordinate-map.json',coords)
    print('Joining loader versions and replaying method stores.',flush=True)
    loaded,unjoined=loader_collect(capture_dir/'build.jsonl.gz',em,before)
    save(output/'loader-body-joins.json.gz',dict(joins=loaded,unjoined=unjoined))
    registry,reg_summary=replay(rows(capture_dir/'registries.jsonl.gz'),f,em,before,loaded)
    save(output/'registry-joins.json.gz',registry);save(output/'registry-summary.json',reg_summary)
    sample=next(iter(read(evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))
    operators={int(k):v for k,v in sample['operators'].items()}
    templates=prototypes(f,em,before,source)
    selection=[dict(compiler_records=[dict(e,before=before[e['afunc']]) for e in t['compiler_records']])
               for t in templates.values()]
    _,calls=extract(capture_dir/'build.jsonl.gz',selection,operators)
    for t in templates.values():
        ids={e['afunc'] for e in t['compiler_records']};actual=[c for c in calls if c['function'] in ids]
        require(len(actual)==1 and actual[0]['dependency']['category']=='global-binding'
                and actual[0]['symbol']['id']==t['callee']['symbol'],'ACCESSOR_REAL_IR_CALL')
        t['call']=actual[0]
    save(output/'accessor-templates.json',templates)
    initial_methods=method_bodies(f,em,before,loaded,rows(capture_dir/'registries.jsonl.gz'),templates,[])
    original={r['code']:r for r in read(evidence/'2026-09-14-resident-bodies-r1/bodies.json.gz')['bodies']}
    population=closure(f,set(original)|{r['prototype'] for r in initial_methods if r['witness'] is None})
    requested={'bodies':[original[k] if k in original else dict(code=k,
        payload_sha256=hashlib.sha256(bytes.fromhex(f[k]['payload_hex'])).hexdigest()) for k in sorted(population)]}
    print('Qualifying resident bodies and their nested function literals.',flush=True)
    combined=materialized_candidates(f,em,loaded)
    candidates,_=correspondences(f,combined,wrappers,requested,before,late,coords,
                                 data_dependencies=True,candidate_function_literals=True)
    relation,requirements=pairs(f,candidates);all_matches=qualify(f,candidates,relation)
    matches=[m for m in all_matches if m['bootstrap_code'] in original]
    support=[m for m in all_matches if m['bootstrap_code'] not in original]
    body_result=dict(matches=matches,support_matches=support,
        remaining_codes=sorted(set(original)-{m['bootstrap_code'] for m in matches}),
        relation=[dict(bootstrap=a,compiled=b,requires=[list(p) for p in sorted(requirements[(a,b)])])
                  for a,b in sorted(relation)])
    save(output/'body-correspondences.json.gz',body_result)
    methods=method_bodies(f,em,before,loaded,rows(capture_dir/'registries.jsonl.gz'),templates,all_matches)
    expected={m['id']:m for g in registry['registries'] for m in g['methods']}
    require({r['method']['id']:r['method'] for r in methods}==expected,'METHOD_REGISTRY_POPULATION')
    save(output/'method-body-joins.json.gz',methods)
    body_count=len(matches);method_counts=dict(Counter(r['witness']['kind'] if r['witness'] else 'UNRESOLVED' for r in methods))
    print('Body joins:',body_count,'; method witnesses:',method_counts,flush=True)
    # The complete payload arrays are no longer needed by the graph builder.
    del f,em,combined,before,late,candidates,registry,initial_methods
    families,calls=extract(capture_dir/'build.jsonl.gz',needed_matches(matches,support),operators)
    save(output/'ir.json.gz',dict(functions=families,calls=calls))
    base=read(base_path);delta=make(base,matches,families,calls,support);graph=apply(base,delta)
    original_gaps=sum(e['evidence'].startswith('binding-versions/body/') and e['resolution']=='unresolved'
                      and not e['targets'] for e in base['edges'])
    save(output/'delta.json.gz',delta);save(output/'census.json.gz',graph)
    print('Checking the joined census structure.',flush=True)
    sys.path.insert(0,str(HERE.parent/'closure'))
    from support import load_module
    errors=load_module('resolved_census_contract',HERE.parents[3]/'doc/WASM/tools/check-census.py').validate(graph)
    prefixes=('unresolved reachable edge from ','unimplemented reachable node ')
    require(all(e.startswith(prefixes) for e in errors),'CORRELATED_GRAPH_STRUCTURE')
    summary=dict(status='PASS',census_status='BLOCKED',body_gaps_joined=body_count,
        remaining_original_body_gaps=original_gaps-body_count,remaining_readonly_bodies=len(original)-body_count,
        original_computed_call_population_unchanged=True,borrowed_caller_bounds=0,
        method_population=len(methods),method_body_witnesses=method_counts,
        native_loader_reads_joined=sum(len(v) for v in loaded.values()),native_loader_reads_unjoined=len(unjoined),
        data_dependencies=sum(n['id'].startswith(PREFIX+'data:') for n in delta['nodes']),
        function_literal_nodes=sum(n['id'].startswith(PREFIX+'literal-code:') for n in delta['nodes']),
        calls=dict(Counter(c['dependency']['category'] for c in calls)),
        graph_nodes=len(graph['nodes']),graph_edges=len(graph['edges']),
        unresolved_edges=sum(e.startswith(prefixes[0]) for e in errors),
        unimplemented_nodes=sum(e.startswith(prefixes[1]) for e in errors))
    save(output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path)
    p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence');a=p.parse_args()
    try:run(a.capture,a.base,a.evidence,a.output)
    except BaseException:
        if a.output.exists():
            with (a.output/'failures.log').open('a') as log:traceback.print_exc(file=log)
        raise
