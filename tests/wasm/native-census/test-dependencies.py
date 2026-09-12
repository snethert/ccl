#!/usr/bin/env python3
"""Native dependency/redefinition probes, unchanged-output comparison and graph controls."""
import argparse
import bisect
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
from analyze import functions
from reversible import digest, save

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('dependency_graph', HERE / 'dependency-graph.py')
graph_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(graph_module)


def qualify(events):
    graph, summary = graph_module.collect(events)
    categories = summary['call_observations_by_category']
    if not all(categories.get(k, 0) for k in ['self', 'lexical', 'function-variable']):
        raise ValueError('missing recursion, lexical or unresolved indirect call witness')
    local_ids = {n['id'] for n in graph['nodes'] if 'COMMON-LISP-USER::DEPENDENCY-LOCALS' in n['names']}
    same = [t for c in graph['calls'] if c['caller'] in local_ids and c['dependency']['category'] == 'lexical'
            for t in c['dependency']['targets']]
    if len(same) != 2 or len({t['id'] for t in same}) != 2 or len({t['name'] for t in same}) != 1:
        raise ValueError('same-name lexical functions were conflated')
    for name, namespace in [('DEPENDENCY-VERSION', 'function'), ('DEPENDENCY-MACRO', 'macro')]:
        row = next(d for d in graph['source_definitions'] if d['name'].endswith('::' + name) and d['namespace'] == namespace)
        if {l['layer'] for l in row['locations']} != {'L0', 'L1', 'L2/library'}:
            raise ValueError('lost a layer of source definition history')
        loaded = [h for h in graph['binding_history'] if h['name'].endswith('::' + name) and h['reason'].startswith('loaded-')]
        key = 'macro_id' if namespace == 'macro' else 'function_id'
        if len(loaded) != 3 or len({h['state'][key] for h in loaded}) != 3:
            raise ValueError('lost a native binding replacement')
    if any(d['name'] and d['name'].endswith('::DEPENDENCY-QUOTED') for d in graph['definition_forms']):
        raise ValueError('quoted data was classified as a definition')
    if not any(d['operator'] == 'CCL::%FHAVE' and d['implementation_name'] == 'COMMON-LISP-USER::DEPENDENCY-BOOTSTRAP'
               for d in graph['definition_forms']):
        raise ValueError('lost the bootstrap alias installation form')
    return graph, summary


def write_events(path, rows):
    old_sequences = [e['sequence'] for e in rows]
    if old_sequences != sorted(set(old_sequences)): raise ValueError('ambiguous control event order')
    for i, e in enumerate(rows, 1):
        if e['kind'] == 'binding-checkpoint' and e['payload']['previous_sample_sequence'] is not None:
            e['payload']['previous_sample_sequence'] = bisect.bisect_right(old_sequences, e['payload']['previous_sample_sequence'])
        e['sequence'] = i
        if e['kind'] == 'complete': e['payload']['events_before_complete'] = i - 1
    path.write_text(''.join(json.dumps(e) + '\n' for e in rows))


def run(native, source, work, output):
    for p in [work, output]:
        p.mkdir(parents=True, exist_ok=True)
        if any(p.iterdir()): raise ValueError('work/output must be new and empty')
    fixture = output / 'runner'
    shutil.copytree(HERE, fixture, ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(fixture / 'redefinition-probe', work / 'ccl')
    shutil.copyfile(fixture / 'dependency-probe.lisp', work / 'ccl/dependency-probe.lisp')
    commands = []; fasls = {}
    for variant in ['baseline', 'observed']:
        observed = variant == 'observed'; dest = output / variant; dest.mkdir()
        body = '(load (compile-file ' + json.dumps(str(work / 'ccl/dependency-probe.lisp')) + ')) '
        body += '(assert (= 5 (cl-user::dependency-self 5))) (assert (equal (cl-user::dependency-locals 3) (list 14 25))) '
        body += '(assert (= 9 (cl-user::dependency-indirect (cl-user::dependency-capture 4) 5))) (assert (eq :right (cl-user::dependency-mutual 5))) '
        for folder, value in [('level-0', 11), ('level-1', 21), ('lib', 31)]:
            body += '(load (compile-file ' + json.dumps(str(work / 'ccl' / folder / 'definitions.lisp')) + ')) '
            if observed: body += '(ccl-startup-census::checkpoint ' + json.dumps('loaded-' + folder) + ') '
            body += '(assert (= ' + str(value) + ' (cl-user::dependency-version 1))) '
            body += '(assert (= ' + str(value) + " (eval '(cl-user::dependency-macro 1)))) "
            if folder == 'level-0': body += "(defparameter cl-user::*dependency-old-function* #'cl-user::dependency-version) "
        body += '(assert (= 11 (funcall cl-user::*dependency-old-function* 1))) '
        expression = '(progn ' + ('(ccl-startup-census::start) ' if observed else '')
        expression += '(let ((*gensym-counter* 100000)) ' + body + ') '
        expression += ('(ccl-startup-census::finish) ' if observed else '') + '(format t "DEPENDENCY-PROBE-PASS~%") (ccl:quit))'
        command = [str(source / 'dx86cl64'), '--image-name', str(native / variant / 'build/dx86cl64.image'),
                   '--no-init', '--batch', '--load', str(fixture / 'observer.lisp'), '--load', str(fixture / 'dependencies.lisp'), '--eval', expression]
        env = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C', 'CCL_DEFAULT_DIRECTORY': str(source),
               'CCL_CENSUS_EVENTS': str(dest / 'events.jsonl')}
        with (dest / 'native.log').open('wb') as f:
            r = subprocess.run(command, cwd=source, env=env, stdout=f, stderr=subprocess.STDOUT, timeout=60)
        commands.append({'variant': variant, 'command': command, 'environment': env, 'exit_code': r.returncode})
        save(output / 'commands.json', commands)
        if r.returncode or 'DEPENDENCY-PROBE-PASS' not in (dest / 'native.log').read_text():
            raise ValueError('native probe failed: ' + variant)
        fasls[variant] = {}
        for p in sorted((work / 'ccl').rglob('*.dx64fsl')):
            rel = p.relative_to(work / 'ccl'); target = dest / rel; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, target); fasls[variant][str(rel)] = digest(target)
    if fasls['baseline'] != fasls['observed'] or len(fasls['baseline']) != 4:
        raise ValueError('unchanged native probe FASLs differ')
    events = output / 'observed/events.jsonl'; graph, summary = qualify(events)
    save(output / 'graph.json', graph); save(output / 'summary.json', summary)
    rows = [json.loads(line) for line in events.open()]
    controls = []
    repeated = copy.deepcopy(rows)
    empty = copy.deepcopy(next(e for e in repeated if e['kind'] == 'before-pass2' and e['payload']['calls']))
    empty['payload']['calls'] = []; empty['payload']['inner_functions'] = []
    empty['payload']['function_references'] = []
    empty['sequence'] = repeated[-1]['sequence']; repeated[-1]['sequence'] += 1
    repeated.insert(-1, empty); write_events(output / 'repeated-empty-body.jsonl', repeated)
    union, _ = qualify(output / 'repeated-empty-body.jsonl')
    if union['calls'] != graph['calls']: raise ValueError('later empty observation erased earlier dependencies')

    def mutation(name, change):
        modified = copy.deepcopy(rows); change(modified)
        dest = output / 'controls' / name; dest.mkdir(parents=True)
        write_events(dest / 'events.jsonl', modified)
        try: qualify(dest / 'events.jsonl')
        except (ValueError, StopIteration) as e:
            result = {'name': name, 'status': 'REJECTED', 'reason': type(e).__name__ + ': ' + str(e)}
        else: raise ValueError('control escaped: ' + name)
        save(dest / 'result.json', result); controls.append(result)

    def call(rows, category):
        return next(c for e in rows if e['kind'] == 'before-pass2' for f in functions(e['payload'])
                    for c in f['calls'] if c['dependency']['category'] == category)

    mutation('wrong-self-target', lambda rs: call(rs, 'self')['dependency']['targets'][0].update(id=999999999))
    mutation('fabricated-indirect-target', lambda rs: call(rs, 'function-variable')['dependency']['targets'].append(
        {'kind': 'global-binding', 'name': 'COMMON-LISP::CONS'}))
    mutation('unknown-category', lambda rs: call(rs, 'self')['dependency'].update(category='trusted-by-name'))
    mutation('wrong-lexical-name', lambda rs: call(rs, 'lexical')['dependency']['targets'][0].update(name='COMMON-LISP::CONS'))

    def missing_body(rs):
        fid = call(rs, 'lexical')['dependency']['targets'][0]['id']
        def prune(f):
            f['inner_functions'] = [c for c in f['inner_functions'] if c['function_id'] != fid]
            for child in f['inner_functions']: prune(child)
        rs[:] = [e for e in rs if e['kind'] not in ['frontend', 'before-pass2'] or e['payload']['function_id'] != fid]
        for e in rs:
            if e['kind'] in ['frontend', 'before-pass2']: prune(e['payload'])
    mutation('missing-exact-callee-body', missing_body)
    mutation('lost-l0-declarations', lambda rs: rs.__setitem__(slice(None), [e for e in rs if not
             (e['kind'] == 'definition-form' and '/level-0/' in (e['source'] or ''))]))
    mutation('binding-history-collapse', lambda rs: rs.__setitem__(slice(None), [e for e in rs if not
             (e['kind'] == 'binding-checkpoint' and e['payload']['reason'] == 'loaded-level-1')]))
    mutation('missing-completion', lambda rs: rs.pop())
    result = {'status': 'PASS', 'native_variants': 2, 'identical_fasls': fasls['baseline'], 'controls': controls,
              'repeated_empty_observation_preserves_dependencies': True,
              'scope': 'Native source/redefinition and dependency extraction probes; not complete bootstrap binding instrumentation or LL15 acceptance'}
    save(output / 'results.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['native', 'source', 'work', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); print(json.dumps(run(*(getattr(a, k).resolve() for k in ['native', 'source', 'work', 'output'])), indent=2))
