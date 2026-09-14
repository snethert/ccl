#!/usr/bin/env python3
"""Join retained sequential-build IR to its actual emitted code identities."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import gc
import hashlib
import json
from pathlib import Path
import re
import platform
import shutil
import sys
import traceback

from flow import HERE, extract, require

ROOT = HERE.parents[3]
HEADER = re.compile(rb'^\{"version":2,"sequence":([0-9]+),"kind":"([a-z0-9-]+)"')
INPUT = '2026-09-12-rich-census-r1/observed-r4.jsonl.gz'
INPUT_SHA = '23b63396031cca638f845822d15d2b7af927aa8d0c5d193ae4c03df70b120a7b'
BASE_SHA = '5ad5f785a7db7288d6db2cfc2ccefbd88722498b50b5e39348a9597aacab69ab'
CALLBACK_SHA = '63f2ca47914e20ade411a493b571bd0fc5d34f8fc6a6ddadb72b805c3e139e2d'


def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()


def save(path, value):
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()
    path.write_bytes(gzip.compress(raw, mtime=0) if path.suffix == '.gz' else raw)


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())


def project(base, fs, calls):
    import importlib.util
    from links import make, check, apply
    delta=make(base,fs,calls,BASE_SHA); check(delta,base,fs,calls,BASE_SHA)
    graph=apply(base,delta)
    spec=importlib.util.spec_from_file_location('build_flow_contract',ROOT/'doc/WASM/tools/check-census.py')
    contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
    errors=contract.validate(graph)
    prefixes=('unresolved reachable edge from ', 'unimplemented reachable node ')
    other=[e for e in errors if not e.startswith(prefixes)]
    require(not other,'EXCHANGE_INVARIANT '+str(other[:2]))
    require(all(graph[k]==v for k,v in base.items() if k not in ('nodes','edges','profile')),
            'BASE_METADATA_CHANGED')
    require(graph['nodes'][:len(base['nodes'])]==base['nodes'] and graph['edges'][:len(base['edges'])]==base['edges'],
            'BASE_RECORD_CHANGED')
    return delta, dict(graph_nodes=len(graph['nodes']),graph_edges=len(graph['edges']),
        added_nodes=len(delta['nodes']),added_edges=len(delta['edges']),prior_records_preserved=True,
        unattached_functions=len(delta['unattached_functions']),
        structural_contract='PASS',closure='BLOCKED',
        errors={p.strip():sum(e.startswith(p) for e in errors) for p in prefixes})


def collect(path, limit=None):
    counts = Counter(); operators = None; builtins = None; complete = False; last = 0
    observations = {}; calls = {}; materialized = {}; code_events = {}; captures = 0
    frontend = {}; previous_event = {}; graph_objects = 0; fallback = 0; samples = {}
    def capture(row, basis):
        nonlocal graph_objects, captures, fallback
        sequence = row['sequence']
        fs, cs = extract(row['payload'], operators, builtins)
        graph_objects += len(row['payload']['ir']['objects']); captures += 1
        fallback += basis == 'frontend'
        for f in fs:
            i = f['function_id']
            require(i not in observations, 'REPEATED_PRE_PASS2_FUNCTION')
            observations[i] = dict(function_id=i, parent_id=f['parent_id'], name=f['name'],
                event=sequence, process=row['process'], source=row['source'], basis=basis,
                operators=f['operators'], variables=f['variables'], function_references=f['function_references'],
                source_position=row['source_position'], loading_source=row['loading_source'])
            previous_event[i] = sequence
        for c in cs:
            key = (c['function_id'], c['site_id'])
            require(key not in calls, 'DUPLICATE_CALL_SITE')
            calls[key] = dict(c, event=sequence)
            if 'lexical_bound' in c:
                b = c['lexical_bound']
                label = b.get('reason') or b['bindings'][0]['operator']
                if label not in samples: samples[label] = dict(row=row, operators=operators, builtins=builtins)
        # The inherited recursive resolver has closure cycles. Collect them in
        # bounded batches rather than retaining every IR family until EOF.
        if captures % 128 == 0: gc.collect()
    with gzip.open(path, 'rb') as stream:
        for line in stream:
            match = HEADER.match(line)
            require(match is not None, 'EVENT_HEADER')
            sequence = int(match[1]); kind = match[2].decode()
            require(sequence == last + 1 and not complete, 'EVENT_SEQUENCE')
            counts[kind] += 1; last = sequence
            if kind not in ('snapshot', 'before-pass2', 'frontend', 'function-materialized', 'complete'): continue
            row = json.loads(line); require(row['sequence'] == sequence and row['kind'] == kind, 'EVENT_HEADER_JOIN')
            if kind == 'snapshot':
                table = {n['id']: n['name'] for n in row['payload']['operators']}
                require(len(table) == len(row['payload']['operators']), 'OPERATOR_DUPLICATE')
                require(operators is None or operators == table, 'OPERATOR_TABLE_CHANGED')
                operators = table
                table = {n['index']: n['name'] for n in row['payload']['builtin_bindings']}
                require(len(table) == len(row['payload']['builtin_bindings']), 'BUILTIN_DUPLICATE')
                require(builtins is None or builtins == table, 'BUILTIN_TABLE_CHANGED'); builtins = table
            elif kind == 'frontend':
                frontend[row['payload']['function']['function_id']] = row
            elif kind == 'before-pass2':
                require(operators is not None, 'MISSING_OPERATOR_TABLE')
                capture(row, 'before-pass2')
                frontend.pop(row['payload']['function']['function_id'], None)
                if limit and captures >= limit: break
            elif kind == 'function-materialized':
                ident = row['payload']['root']['ref']
                if ident not in observations:
                    require(ident in frontend, 'MATERIALIZATION_WITHOUT_IR')
                    capture(frontend.pop(ident), 'frontend')
                ns = {n['id']: n for n in row['payload']['objects']}
                require(len(ns) == len(row['payload']['objects']), 'MATERIALIZATION_DUPLICATE')
                for n in ns.values():
                    if n['kind'] != 'afunc' or n['function'] is None: continue
                    code = ns[n['function']['ref']]
                    require(code['kind'] == 'function', 'MATERIALIZATION_KIND')
                    ident = n['id']; code = code['code']
                    require(ident in observations and previous_event[ident] < sequence, 'MATERIALIZATION_BEFORE_IR')
                    require(code not in materialized or materialized[code] == ident, 'MATERIALIZATION_CONFLICT')
                    materialized[code] = ident; code_events.setdefault(code, sequence)
            else:
                expected = {r['kind']: r['count'] for r in row['payload']['counts']}
                actual = dict(counts); del actual['complete']
                require(expected == actual and row['payload']['events_before_complete'] == sequence - 1, 'COMPLETION_COUNTS')
                complete = True
    require(complete or limit, 'MISSING_COMPLETION')
    if not limit: require(set(materialized.values()) == set(observations), 'UNMATERIALIZED_IR')
    emitted = {}
    for code, ident in materialized.items(): emitted.setdefault(ident, []).append(dict(code=code, event=code_events[code]))
    for ident, f in observations.items(): f['emitted'] = sorted(emitted.get(ident, []), key=lambda r:r['code'])
    rows = [calls[k] for k in sorted(calls)]
    dynamic = [c for c in rows if not c['dependency']['targets']]
    bounded = [c for c in dynamic if c.get('lexical_bound', {}).get('targets')]
    for c in bounded:
        c['target_code'] = [dict(afunc=t, emitted=observations[t]['emitted']) for t in c['lexical_bound']['targets']]
    summary = dict(events=last, completed=complete, before_pass2_captures=captures-fallback,
        frontend_only_captures=fallback, functions=len(observations),
        frontend_only_functions=sum(f['basis']=='frontend' for f in observations.values()),
        materialized_codes=len(materialized), calls=len(rows), computed_calls=len(dynamic), lexical_bounds=len(bounded),
        computed_calls_open=len(dynamic)-len(bounded), graph_objects=graph_objects,
        call_categories=dict(Counter(c['dependency']['category'] for c in rows)),
        global_calls_with_symbol_identity=sum(c.get('global_symbol') is not None for c in rows),
        open_lexical_reasons=dict(Counter(c['lexical_bound']['reason'] for c in dynamic if c.get('lexical_bound', {}).get('reason'))),
        assignment_flags='NOT_RECORDED; structural family scan', namespace='identity:build',
        original_r7_bounds_changed=False, census_gate_credit=False, target_qualification=False)
    return sorted(observations.values(), key=lambda r:r['function_id']), rows, summary, samples


def run(args):
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    paths = sorted(HERE.glob('*.py')) + [HERE.parent/'source-closure'/n for n in ('analysis.py','bounds.py')]
    paths += [ROOT/'doc/WASM/tools/check-census.py', ROOT/'doc/WASM/contracts/census.schema.json',
              ROOT/'compiler/nx.lisp',ROOT/'compiler/nx1.lisp',ROOT/'compiler/nxenv.lisp',
              HERE.parent/'rich-observation/observer.lisp',HERE.parent/'observer.lisp',HERE.parent/'dependencies.lisp']
    pins = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    (out/'sources').mkdir()
    for p in paths:
        target=out/'sources'/p.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(p,target)
    save(out/'run.json', dict(started=datetime.now(timezone.utc).isoformat(), command=sys.argv,
        input=dict(path=INPUT, sha256=INPUT_SHA), base_sha256=BASE_SHA, callback_sha256=CALLBACK_SHA,
        python=platform.python_version(),python_executable_sha256=digest(Path(sys.executable)),
        host=platform.platform(),source_sha256=pins,limit=args.limit))
    try:
        require(digest(args.evidence/INPUT) == INPUT_SHA, 'INPUT_DIGEST')
        require(args.limit or args.base and args.callbacks,'FULL_RUN_INPUTS')
        gc.disable()
        fs, calls, summary, samples = collect(args.evidence/INPUT, args.limit)
        if args.base:
            require(digest(args.base)==BASE_SHA,'BASE_DIGEST')
            base=read(args.base);delta, integration = project(base,fs,calls)
            save(out/'delta.json.gz',delta); summary['integration']=integration
        if args.callbacks:
            from controls import run as controls
            require(digest(args.callbacks)==CALLBACK_SHA,'CALLBACK_INPUT')
            result=controls(samples,read(args.callbacks),base,fs,calls,BASE_SHA)
            save(out/'controls.json',result);shutil.copyfile(args.callbacks,out/'callback-capture.json.gz')
            summary['controls_rejected']=result['controls_rejected'];summary['callback_probes']=len(result['callback_probes'])
        save(out/'functions.json.gz', fs); save(out/'calls.json.gz', calls); save(out/'summary.json', summary)
        save(out/'samples.json.gz', samples)
        print(json.dumps(summary, sort_keys=True), flush=True)
    except BaseException:
        (out/'failure.txt').write_text(traceback.format_exc()); raise
    finally: gc.enable()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--limit', type=int)
    p.add_argument('--base',type=Path)
    p.add_argument('--callbacks',type=Path)
    run(p.parse_args())
