#!/usr/bin/env python3
"""Resolve observed call identities and retain a conservative, unfinished worklist."""
import argparse
import collections
import json
from pathlib import Path
from analyze import functions, snapshot
from reversible import save, digest


def module_name(source):
    if source is None: return None
    return source.split('/ccl/', 1)[-1] if '/ccl/' in source else source


def layer(source):
    if source and source.startswith('level-0/'): return 'L0'
    if source and source.startswith('level-1/'): return 'L1'
    if source and source.startswith('lib/'): return 'L2/library'
    return 'compiler/tooling/other'


def collect(path):
    nodes, calls, references = {}, {}, {}
    snap = None; complete = False; count = 0; observations = 0; unknown_before = 0
    categories = collections.Counter(); resolution = collections.Counter()
    declarations = []; history = []; states = {}
    with path.open() as stream:
        for line in stream:
            e = json.loads(line); count += 1
            if complete or e['sequence'] != count: raise ValueError('event sequence/completion mismatch')
            if e['kind'] == 'complete':
                if e['payload']['events_before_complete'] != count - 1: raise ValueError('event count mismatch')
                complete = True
            if e['kind'] == 'snapshot':
                if snap is not None: raise ValueError('duplicate snapshot')
                snap = snapshot([e])
                if snap.get('dependency_format') != 1: raise ValueError('dependency extension missing')
            if e['kind'] == 'definition-form':
                declarations.append({**e['payload'], 'sequence': count, 'source': module_name(e['source']),
                                     'source_position': e['source_position']})
            if e['kind'] == 'binding-checkpoint':
                p = e['payload']; previous = states.get(p['name'])
                if previous is None:
                    if p['previous'] is not None or p['previous_sample_sequence'] is not None:
                        raise ValueError('binding history has no initial sample')
                elif (p['previous'] != previous['state'] or
                      not previous['sequence'] <= p['previous_sample_sequence'] < count):
                    raise ValueError('binding history is discontinuous')
                row = {**p, 'sequence': count, 'source': module_name(e['source']),
                       'source_position': e['source_position']}
                states[p['name']] = row; history.append(row)
            if e['kind'] != 'before-pass2': continue
            for f in functions(e['payload']):
                fid = f['function_id']; source = module_name(e['source'])
                if type(fid) is not int or fid < 1: raise ValueError('invalid function identity')
                node = nodes.setdefault(fid, {'id': fid, 'names': set(), 'sources': set(), 'parents': set(),
                    'observations': 0, 'locations': set(), 'operators': set(), 'variables': set()})
                node['names'].add(f['name']); node['sources'].add(source); node['parents'].add(f['parent_id'])
                node['observations'] += 1; node['locations'].add((source, e['source_position']))
                node['operators'].update(r['id'] for r in f['operators'])
                node['variables'].update((v['id'], v['name'], v['ordinal']) for v in f['variables'])
                for kind, rows, into in [('call', f['calls'], calls), ('function-reference', f['function_references'], references)]:
                    for call in rows:
                        dep = call['dependency']; targets = dep['targets']
                        sid = call['site_id']
                        if type(sid) is not int or sid < 1: raise ValueError('invalid call-site identity')
                        exact = ['self', 'lexical', 'lexical-function-value']
                        global_kinds = ['global-binding', 'builtin']
                        unresolved = ['unrecognized-callee', 'cyclic-callee-form', 'unrecognized-function-value',
                                      'literal-without-binding', 'function-variable', 'unrecognized-variable', 'computed-callee']
                        category = dep['category']
                        if category not in exact + global_kinds + unresolved:
                            raise ValueError('unknown dependency category')
                        if category in unresolved and targets:
                            raise ValueError('unresolved call carries fabricated targets')
                        if kind == 'call':
                            expected = {'CCL::SELF-CALL': 'self', 'CCL::LEXICAL-FUNCTION-CALL': 'lexical',
                                        'CCL::BUILTIN-CALL': 'builtin'}.get(call['operator'])
                            if expected is not None and category != expected:
                                raise ValueError('call operator and dependency category disagree')
                        if dep['category'] in ['self', 'lexical', 'lexical-function-value']:
                            if len(targets) != 1 or targets[0]['kind'] != 'function': raise ValueError('exact callee missing')
                            if dep['category'] == 'self' and targets[0]['id'] != fid: raise ValueError('self-call targets another function')
                        if dep['category'] in ['global-binding', 'builtin']:
                            if len(targets) != 1 or targets[0]['kind'] != 'global-binding': raise ValueError('binding target missing')
                        if dep['category'] == 'builtin':
                            index = dep['builtin_index']
                            if snap is None or type(index) is not int or not 0 <= index < len(snap['builtin_bindings']):
                                raise ValueError('invalid builtin table index')
                            if targets[0]['name'] != snap['builtin_bindings'][index]['name']:
                                raise ValueError('builtin mapping differs from evaluated table')
                        signature = json.dumps(dep, sort_keys=True, separators=(',', ':'))
                        key = (fid, sid, signature)
                        row = into.setdefault(key, {'caller': fid, 'site': sid, 'kind': kind,
                            'dependency': dep, 'observations': 0, 'first_sequence': count,
                            'source': source, 'source_position': e['source_position']})
                        row['observations'] += 1
                        if kind == 'call':
                            observations += 1; categories[dep['category']] += 1
                            if call['target'] is None:
                                unknown_before += 1
                                resolution['now_resolved' if targets else 'still_unresolved'] += 1
    if not complete or snap is None: raise ValueError('incomplete observation stream')
    # Keep a union when the same compiler object is observed more than once.
    # A later parent observation can have an empty, already-compiled child body;
    # replacing its earlier record would silently lose dependencies.
    for node in nodes.values():
        node['variables'] = [dict(zip(['id', 'name', 'ordinal'], v)) for v in sorted(node['variables'])]
        for field in ['names', 'sources', 'parents', 'locations', 'operators']:
            node[field] = sorted(node[field], key=lambda x: json.dumps(x))
    all_edges = list(calls.values()) + list(references.values())
    missing = sorted({t['id'] for c in all_edges for t in c['dependency']['targets']
                      if t['kind'] == 'function' and t['id'] not in nodes})
    if missing: raise ValueError('exact callee has no observed function body: ' + str(missing[:8]))
    for c in all_edges:
        for t in c['dependency']['targets']:
            if t['kind'] == 'function' and t['name'] not in nodes[t['id']]['names']:
                raise ValueError('exact callee identity and observed name disagree')
    unknown = [c for c in calls.values() if not c['dependency']['targets']]
    bindings = collections.defaultdict(set)
    # Candidate source versions only. Names do not establish active function
    # cells, macro/function namespace equivalence or a complete runtime target set.
    for f in nodes.values():
        if None in f['parents']:
            for name in f['names']:
                if name != 'NIL': bindings[name].add(f['id'])
    used_bindings = sorted({t['name'] for c in all_edges for t in c['dependency']['targets'] if t['kind'] == 'global-binding'})
    versions = []
    for name, ids in bindings.items():
        locations = {(s, pos) for fid in ids for s, pos in nodes[fid]['locations']}
        if len(locations) > 1:
            versions.append({'name': name, 'function_ids': sorted(ids),
                             'locations': [{'source': s, 'source_position': pos, 'layer': layer(s)}
                                           for s, pos in sorted(locations, key=lambda x: json.dumps(x))],
                             'scope': 'Potential source definitions/recompilations; active replacement not inferred'})
    declared = collections.defaultdict(list)
    for d in declarations:
        if d['name'] is not None:
            namespace = 'macro' if d['role'].startswith('macro') else 'method' if d['role'] == 'method' else 'function'
            declared[(d['name'], namespace)].append(d)
    source_definitions = []
    for (name, namespace), rows in sorted(declared.items()):
        locations = collections.defaultdict(list)
        for r in rows: locations[(r['source'], r['source_position'])].append(r)
        source_definitions.append({'name': name, 'namespace': namespace,
            'locations': [{'source': s, 'source_position': pos, 'layer': layer(s),
                           'observations': locs} for (s, pos), locs in locations.items()],
            'scope': 'Source forms and expanded declarations; compilation is not installation'})
    graph = {'version': 1, 'scope': 'Observed native compiler dependencies; not the accepted LL15 closure format',
        'source_log_sha256': digest(path), 'nodes': sorted(nodes.values(), key=lambda n: n['id']),
        'calls': list(calls.values()), 'function_references': list(references.values()),
        'operators': snap['operators'], 'builtin_bindings': snap['builtin_bindings'],
        'startup_groups': snap['startup_groups'], 'definition_forms': declarations,
        'source_definitions': source_definitions, 'binding_history': history,
        'global_binding_candidates': [{'name': name, 'function_ids': sorted(bindings.get(name, [])),
            'resolution': 'UNQUALIFIED_CANDIDATES'} for name in used_bindings],
        'missing_function_observations': missing, 'unresolved_calls': unknown,
        'definition_versions': sorted(versions, key=lambda v: v['name'])}
    summary = {'status': 'PASS', 'census_acceptance': 'BLOCKED', 'events': count,
        'function_observations': sum(n['observations'] for n in nodes.values()), 'distinct_function_objects': len(nodes),
        'call_observations': observations, 'distinct_call_records': len(calls),
        'original_unnamed_target_observations': unknown_before, 'original_unnamed_target_resolution': dict(resolution),
        'call_observations_by_category': dict(categories),
        'remaining_unresolved_observations': sum(c['observations'] for c in unknown),
        'remaining_distinct_unresolved_calls': len(unknown),
        'unresolved_calls_by_category': dict(collections.Counter(c['dependency']['category'] for c in unknown)),
        'function_reference_records': len(references), 'missing_function_observations': len(missing),
        'global_bindings_referenced': len(used_bindings),
        'global_bindings_without_matching_compilation': sum(not bindings.get(n) for n in used_bindings),
        'names_with_multiple_source_locations': len(versions), 'definition_forms': len(declarations),
        'declared_namespaces': len(source_definitions),
        'declared_redefinitions': sum(len(d['locations']) > 1 for d in source_definitions),
        'cross_layer_source_redefinitions': [d for d in source_definitions if
             len({l['layer'] for l in d['locations']} & {'L0', 'L1', 'L2/library'}) > 1],
        'binding_samples_with_changes': sum(h['previous'] is not None for h in history),
        'sampled_native_bindings': len(states),
        'cross_layer_definition_candidates': [v for v in versions if len({l['layer'] for l in v['locations']}
                                                   & {'L0', 'L1', 'L2/library'}) > 1],
        'remaining': ['Resolve runtime function-variable/computed targets conservatively',
                      'Establish global binding namespaces, installation epochs and missing target bodies',
                      'Qualify loader/startup seeds, full lowering/effect joins and external trace reconciliation',
                      'Independent review; no S0-LL15-b/c acceptance claim']}
    return graph, summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--events', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
    if any(a.output.iterdir()): p.error('output must be new and empty')
    graph, summary = collect(a.events)
    save(a.output / 'graph.json', graph); save(a.output / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if not k.startswith('cross_layer_')}, indent=2))
