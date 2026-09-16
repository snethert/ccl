"""Adversarial edits to the actual publication; the trusted reference stays fixed.

Each edit also regenerates the file hash. Re-signing a shortened publication
must not turn an omission into qualification. No producer helper builds mutants.
"""
from copy import deepcopy
from pathlib import Path
import tempfile
from publication import check_files, write_publication, save, require


def run(reference, good, out):
    out=Path(out);out.mkdir(); rows=[]
    cases=[]
    def add(name, reason, edit):cases.append((name,reason,edit))
    add('missing-seed','GRAPH_SEEDS',lambda p:p['graph']['seeds'].pop())
    add('missing-node','GRAPH_NODES',lambda p:p['graph']['nodes'].pop())
    add('missing-edge','GRAPH_EDGES',lambda p:p['graph']['edges'].pop(0))
    add('same-count-edge-substitution','GRAPH_EDGES',lambda p:p['graph']['edges'][0].update(targets=p['graph']['edges'][1]['targets']))
    add('extra-module-fanout','GRAPH_NODES',lambda p:p['graph']['nodes'].append(dict(id='invented-module',kind='module')))
    add('unknown-call-promoted','GRAPH_EDGES',lambda p:next(e for e in p['graph']['edges'] if e['resolution']=='unresolved').update(resolution='complete'))
    add('changed-native-implementation-description','GRAPH_NODES',lambda p:p['graph']['nodes'][0].update(implementation='Qualified Wasm implementation'))
    add('deleted-unknown-population','UNRESOLVED_POPULATIONS',lambda p:p['unknowns'].pop('call'))
    add('deleted-body-gap','MISSING_BODY_POPULATION',lambda p:p['missing_bodies'].pop())
    add('unknown-call-reclassified-as-proven','CALL_BOUND_PARTITION',lambda p:p['call_partitions']['proven-native-ir-targets'].append(p['call_partitions']['unresolved-computed-callees'].pop()))
    add('deleted-proven-bound','CALL_BOUND_PARTITION',lambda p:p['call_partitions']['proven-native-ir-targets'].pop())
    add('wrong-startup-namespace','GRAPH_SCOPE',lambda p:p['graph'].update(profile='another execution'))
    add('seed-recipe-omission','SEED_RECIPE',lambda p:p['seed_recipe']['entrypoints'].pop())
    add('missing-required-input','INPUT_SET',lambda p:p['inputs'].pop('packet:lowering'))
    add('substituted-input-hash','INPUT_SET',lambda p:p['inputs']['packet:capture'].update(sha256='0'*64))
    add('unretained-base-substitution','INPUT_SET',lambda p:p['inputs']['packet:startup'].update(path='/tmp/unretained'))
    add('shortened-compile-population','COMPILE_SCOPE',lambda p:p['compile'].update(units=84))
    add('claim-complete-closure','SCOPE_PROMOTION',lambda p:p['claims'].update(complete_closure=True))
    add('claim-bound-from-observation','SCOPE_PROMOTION',lambda p:p['claims'].update(complete_reference_edges_are_not_exhaustive_callee_bounds=False))
    add('invalid-initializer-prerequisite','INITIALIZER_PREREQUISITE',lambda p:p['initializers'][-1]['prerequisites'].append('missing'))
    add('cyclic-initializer','INITIALIZER_PREREQUISITE',lambda p:p['initializers'][0]['prerequisites'].append(p['initializers'][-1]['node']))
    add('initializer-prerequisite-erased','INITIALIZER_RECORDS',lambda p:p['initializers'][-1].update(prerequisites=[]))
    add('initializer-completion-promoted','INITIALIZER_RECORDS',lambda p:p['initializers'][-1].update(completion_assertion='Exhaustive dependency closure complete'))
    add('missing-query','QUERY_SET',lambda p:p['queries'].pop('binding'))
    add('wrong-query-execution','QUERY_IDENTITY body',lambda p:p['queries']['body'].update(namespace='rich-build-r7'))
    add('wrong-query-object','QUERY_RECORDS body',lambda p:p['queries']['body']['records'][0].update(id=-1))
    add('omitted-registry-event','QUERY_RECORDS registry',lambda p:p['queries']['registry']['records'].pop())
    add('omitted-materialization-event','QUERY_RECORDS materialization',lambda p:p['queries']['materialization']['records'].pop())
    add('observed-query-to-bound','QUERY_SCOPE body',lambda p:p['queries']['body'].update(exhaustive=True))
    add('negative-answer-to-positive','QUERY_SCOPE absent',lambda p:p['queries']['absent'].update(status='OBSERVED'))
    add('query-input-hash-substitution','QUERY_INPUTS body',lambda p:p['queries']['body']['evidence']['inputs'].update(**{'run.json':'0'*64}))
    add('witness-source-form-substitution','WITNESS_RECORDS u1-witness',lambda p:p['witnesses']['u1-witness']['native'].update(form='(defun other () nil)'))
    add('witness-evidence-substitution','WITNESS_RECORDS u1-witness',lambda p:p['witnesses']['u1-witness']['evidence'].update(native_sha256='0'*64))
    add('wrong-native-source','WITNESS_IDENTITY u1-witness',lambda p:p['witnesses']['u1-witness'].update(source_sha256='0'*64))
    add('wrong-native-site','WITNESS_IDENTITY u1-witness',lambda p:p['witnesses']['u1-witness']['selections'][0]['site'].update(index=999))
    add('witness-to-bound','WITNESS_SCOPE u1-witness',lambda p:p['witnesses']['u1-witness'].update(exhaustive=True))
    add('unreached-to-positive','WITNESS_SCOPE not-reached',lambda p:p['witnesses']['not-reached'].update(status='PASS'))
    add('truncated-to-positive','WITNESS_SCOPE budget',lambda p:p['witnesses']['budget'].update(status='PASS'))
    add('drop-native-event','WITNESS_EVENTS u1-witness',lambda p:p['witnesses']['u1-witness']['native']['events'].pop())
    add('drop-native-value','WITNESS_SCENARIO_RESULT u1-witness',lambda p:p['witnesses']['u1-witness']['native'].update(scenario_result='(:RETURNED ())'))
    add('broken-restoration','WITNESS_RESTORED_CODE_IDENTICAL u1-witness',lambda p:p['witnesses']['u1-witness']['native'].update(restored_code_identical=False))
    # Never retain 34 duplicate full worklists. Execute all real file-path
    # mutations in temporary quarantine; retain recipes and exact refusals.
    with tempfile.TemporaryDirectory(prefix='ccl-qualification-mutations-') as t:
        base=Path(t)/'positive';write_publication(base,good);require(check_files(base,reference)['status']=='PASS','POSITIVE_PUBLICATION');rows.append(dict(case='complete-publication',status='PASS'))
        for i,(name,reason,edit) in enumerate(cases):
            bad=deepcopy(good);edit(bad);folder=Path(t)/str(i);write_publication(folder,bad)
            try:check_files(folder,reference)
            except ValueError as e:
                require(str(e)==reason,'WRONG_CONTROL_REASON '+name+': '+str(e));rows.append(dict(case=name,status='REJECTED',reason=str(e),candidate_manifest_regenerated=True))
            else:raise ValueError('CONTROL_ESCAPED '+name)
        file=base/'publication.json.gz';file.write_bytes(file.read_bytes()+b'corruption')
        try:check_files(base,reference)
        except ValueError as e:require(str(e)=='PUBLICATION_ARTIFACT','ARTIFACT_REASON');rows.append(dict(case='damaged-artifact',status='REJECTED',reason=str(e)))
        else:raise ValueError('CONTROL_ESCAPED damaged-artifact')
    save(out/'controls.json',rows)
    return rows
