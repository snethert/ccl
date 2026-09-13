"""Bound every graph addition independently of the projection's construction."""
from collections import defaultdict
import json
from exchange import ident
from identity_join import key
from lowering_join import node_record, SCOPE


def check(base, delta, facts, base_sha256):
    if set(delta) != {'version', 'base_sha256', 'scope', 'nodes', 'edges'} or delta['version'] != 1 or delta['base_sha256'] != base_sha256 or delta['scope'] != SCOPE:
        raise ValueError('DELTA_BASE_SCOPE')
    existing = {r['id']: r for r in base['nodes']}; required = {}; expected = {}
    surface = key('build', 'module', '@execution')
    def record(row):
        if row['id'] not in existing: required[row['id']] = row
    def relation(label, source, targets):
        expected['emission:build/' + label] = {'from': source, 'targets': sorted(targets), 'phase': 'compile',
                                             'origin': 'observed', 'resolution': 'complete',
                                             'evidence': 'emission:build/' + label}
    for t in facts['templates']:
        record(node_record(key('build', 'template', t['id']), 'vinsn', t['name'], f"build/template/{t['id']}",
                           f"Observed native template identity; attributes {t['attributes']}. Static emission and Wasm lowering remain unqualified."))
    for f in facts['emitters']:
        fid = key('build', 'afunc', f['function'])
        record(node_record(fid, 'function', 'Recorded front-end function: ' + f['name'], f"build/emitter/{f['function']}",
                           'Emission identity only; complete call dependencies remain unqualified.'))
        relation(f"emitter/{f['function']}", surface, [fid])
        relation(f"function-templates/{f['function']}", fid, [key('build', 'template', t) for t in f['templates']])
    for h in facts['handlers']:
        hid = key('build', 'code', h['code'])
        record(node_record(hid, 'function', 'Recorded native handler code; origin ' + h['origin'], f"build/handler/{h['code']}",
                           'Live frame membership, not exact leaf dispatch.'))
        relation(f"handler-templates/{h['code']}", hid, [key('build', 'template', t) for t in h['templates']])
    for o in facts['operators']:
        op = o['record']; oid = key('build', 'operator', op['id'])
        record(node_record(oid, 'operator', 'Evaluated native slot ' + str(op['id']), f"build/operator/{op['id']}",
                           json.dumps(op, sort_keys=True, separators=(',', ':'))))
        relation(f"operator/{op['id']}", surface, [oid])
        relation(f"operator-codes/{op['id']}", oid, [key('build', 'code', c) for c in o['codes']])
    calls = defaultdict(set)
    for c in facts['subprimitive_calls']:
        if c['name'] is not None:
            target = ident('subprimitive', c['name']); node = existing.get(target, {})
            if node.get('kind') != 'subprimitive' or node.get('implementation') != 'native table offset ' + str(c['offset']):
                raise ValueError('SUBPRIMITIVE_TABLE_BINDING')
        else:
            target = key('build', 'unknown-subprimitive', c['offset'])
            row = node_record(target, 'subprimitive', None, f"build/subprimitive-offset/{c['offset']}", 'Recorded operand has no entry in the same-kernel table.')
            row['disposition'] = 'unresolved'; record(row)
        calls[c['function']].add(target)
    for f, targets in calls.items(): relation(f'subprimitive-targets/{f}', key('build', 'afunc', f), targets)
    actual = {n['id']: n for n in delta['nodes']}
    if len(actual) != len(delta['nodes']) or actual != required: raise ValueError('DELTA_NODE_RECORDS')
    edges = {e['evidence']: e for e in delta['edges']}
    if len(edges) != len(delta['edges']) or edges != expected: raise ValueError('DELTA_EDGE_RECORDS')
    universe = set(existing) | set(actual)
    if any(e['from'] not in universe or set(e['targets']) - universe for e in edges.values()): raise ValueError('DELTA_REFERENCE')
    return {'status': 'PASS', 'nodes': len(actual), 'edges': len(edges)}
