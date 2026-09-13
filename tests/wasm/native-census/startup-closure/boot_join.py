"""Add native boot events to census v1 without merging process identities."""
import json
from collections import defaultdict
from urllib.parse import quote

SCOPE = 'Observed boot event boundaries, binding states and cold source origins; not static dependency closure or Wasm implementation.'
GAP = 'identity:build:gap:boot-process'
FIELDS = ('nodes', 'edges', 'initializers', 'unobserved_modules')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def key(kind, value):
    return 'boot:' + kind + ':' + quote(str(value), safe='/@.-_')


def node(i, kind, implementation, evidence, reason='', unresolved=False):
    return dict(id=i, kind=kind, disposition='unresolved' if unresolved else 'implemented',
                required=True, implementation=implementation, evidence=evidence,
                reason=reason, tests=['S0-LL15-b', 'S0-LL15-c'])


def edge(source, targets, evidence, origin='observed'):
    return {'from': source, 'targets': sorted(set(targets)), 'phase': 'load',
            'origin': origin, 'resolution': 'complete', 'evidence': evidence}


def claim(event, active):
    kind = event['kind']
    text = 'Observed native ' + kind + ' boundary at event ' + str(event['sequence']) + '.'
    if kind.endswith('-enter'): text += ' Entry witnessed; this assertion does not claim its return.'
    if kind == 'binding-removing': text += ' Pre-clear intent; subsequent replay and final checkpoint are separate witnesses.'
    if kind == 'handoff': text += ' Still active, with no recorded returns: ' + canonical(active) + '.'
    return text


def make_delta(base, rows, boot, files, origins, binding):
    nodes, edges, initializers = {}, [], []
    surface = key('module', '@execution')
    def add(record):
        i = record['id']
        if i in nodes and nodes[i] != record: raise ValueError('NODE_CONFLICT')
        nodes[i] = record
        return i
    add(node(surface, 'module', 'Separate reviewed native boot process', 'boot/capture', SCOPE))
    add(node(key('gap', 'closure'), 'function', None, 'boot/scope',
             'Full target traversal, calls, opaque value contents and Wasm dispositions remain unqualified.', True))
    edges += [edge(GAP, [surface], 'boot/separate-process-witness', 'conservative'),
              edge(surface, [key('gap', 'closure')], 'boot/dependency-closure', 'conservative')]
    objects = {r['id']: r for r in boot['objects']}
    def value(i):
        description = objects[i]; kind = description['kind']; opaque = kind == 'opaque'
        return add(node(key('object', i), 'function' if kind == 'function' else 'store',
                        None if opaque else 'Recorded native ' + kind + ' identity',
                        'boot/objects/' + str(i), canonical(description), opaque))
    def cell(i):
        return add(node(key('cell', i), 'store', 'Observed native function cell',
                        'boot/symbols/' + str(i), canonical(objects[i])))
    by_file = {r['file']: r for r in files['files']}
    aliases = defaultdict(list)
    for r in files['files']: aliases[r['relative_path']].append(r)
    for path, records in sorted(aliases.items()):
        if len({(r['sha256'], r['bytes']) for r in records}) != 1:
            raise ValueError('FILE_ALIAS_BYTES')
        add(node(key('fasl', path), 'module', 'Retained boot loader input',
                 'boot/files/' + path, canonical(sorted(records, key=lambda r:r['file']))))
    for r in origins['sources']:
        i = add(node(key('source', r['path']), 'module', 'Source bytes bound by reviewed xload origin witness',
                     'boot/origin-sources/' + r['path'], canonical(r)))
        # Inventory membership by logical path, expressly not cross-run code or
        # source-byte equivalence. This also makes both representations explicit.
        prior = 'module:' + quote(r['path'], safe='/@.-_')
        if not any(n['id'] == prior and n['kind'] == 'module' for n in base['nodes']):
            raise ValueError('SOURCE_INVENTORY_MEMBERSHIP')
        edges.append(edge(prior, [i], 'boot/source-inventory-path/' + r['path'], 'conservative'))
    active = [{'family': r['family'], 'enter': r['enter']} for r in boot['handoff']]
    frames = {r['enter']: r for family in ('cold_initializers', 'loads', 'readers', 'calls', 'handoff') for r in boot[family]}
    returns = {r['return']: r for r in frames.values() if 'return' in r}
    stores = {r['event']: r for r in boot['bindings']}
    events = [r for r in rows if 'sequence' in r]
    previous = None
    for event in events:
        seq, kind, p = event['sequence'], event['kind'], event['payload']; i = key('event', seq)
        add(node(i, 'initializer', 'Observed native ' + kind + ' boundary', 'boot/event/' + str(seq), canonical(p)))
        initializers.append({'node': i, 'prerequisites': [] if previous is None else [previous],
                             'rank': seq, 'completion_assertion': claim(event, active)})
        previous = i
        frame = frames.get(seq) or returns.get(seq)
        if frame:
            if frame['parent'] is not None:
                edges.append(edge(i, [key('event', frame['parent'])], 'boot/enclosing/' + str(seq)))
            if 'file' in frame:
                edges.append(edge(i, [key('fasl', by_file[frame['file']]['relative_path'])], 'boot/file/' + str(seq)))
            for role in ('function', 'reader'):
                if role in frame: edges.append(edge(i, [value(frame[role])], 'boot/' + role + '/' + str(seq)))
            if 'table' in frame:
                t = add(node(key('table', frame['table']), 'store', 'Observed reader dispatch table identity',
                             'boot/table/' + str(frame['table']), 'Identity only; table contents are not enumerated by this event slice.'))
                edges.append(edge(i, [t], 'boot/table/' + str(seq)))
        if seq in stores:
            r = stores[seq]
            edges.append(edge(i, [cell(r['symbol'])], 'boot/cell/' + str(seq)))
            for role in ('old', 'new'): edges.append(edge(i, [value(r[role])], 'boot/' + role + '/' + str(seq)))
            if r['parent'] is not None:
                edges.append(edge(i, [key('event', r['parent'])], 'boot/enclosing/' + str(seq)))
    edges.append(edge(surface, [key('event', r['sequence']) for r in events], 'boot/event-coverage'))
    for label in ('initial', 'final'):
        for r in boot[label + '_bindings']:
            edges.append(edge(cell(r['symbol']), [value(r['value'])], 'boot/' + label + '-binding/' + str(r['symbol'])))
    cold = {r['function']: r for r in boot['cold_initializers']}
    for r in origins['entries']:
        function = value(r['boot_function']); source = key('source', r['source']); effect = cold[r['boot_function']]
        evidence = 'boot/cold-origin/' + str(r['position'])
        edges.append(edge(function, [source], evidence))
        edges.append(edge(key('event', effect['enter']), [source], evidence + '/entry'))
    modules = sorted(i for i, n in nodes.items() if n['kind'] == 'module')
    return {'version': 1, 'scope': SCOPE, 'input_binding': binding,
            'nodes': [nodes[i] for i in sorted(nodes)], 'edges': edges, 'initializers': initializers,
            'unobserved_modules': [{'node': i, 'reason': 'Separate boot/xload witness; not a file observation in the original external clean-image trace.'} for i in modules],
            'cold_origins': origins['entries'], 'active_handoff': active}


def apply_delta(base, delta):
    graph = dict(base)
    for field in FIELDS: graph[field] = base[field] + delta[field]
    graph['profile'] += '; separate native boot execution and source origins (closure unqualified)'
    return graph
