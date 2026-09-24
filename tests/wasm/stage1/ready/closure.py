"""Census the selected READY graph, preserving unresolved and indirect edges."""
from collections import Counter
from pathlib import Path
import json
import hashlib


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def census(probe):
    compiled = probe / 'compiled'
    modules = read(compiled / 'modules.json')
    metadata = {m['module']: m for m in read(probe / 'probe-output/ready-modules.json')}
    for path in (probe / 'probe-output').glob('*.census-wat'):
        if not metadata[path.stem]['function']:
            # FCOMP's IN-PACKAGE toplevel record is not a callable entry.
            assert not any(m['name'] == path.stem for m in modules), path.name
            continue
        assert path.read_bytes() == (compiled / (path.stem + '.wat')).read_bytes(), path.name
    owners = {s['id']: s for s in read(compiled / 'symbols.json')}
    by_module = {m['name']: m for m in modules}
    # Exactly the installer's two ordered binding passes, in class mode.
    bindings = {}
    for mode in (False, True):
        for m in modules:
            if m['function'] and bool(m.get('cplMode')) == mode:
                bindings[m['function']] = m['name']
    def owner_name(owner):
        row = owners[owner]
        return (row['package'] or '#') + '::' + row['name']
    def owner(package, name):
        found = [s['id'] for s in owners.values() if s['package'] == package and s['name'] == name]
        assert len(found) == 1, (package, name)
        return found[0]
    # The public function cells use the same reviewed EQ wrappers as direct
    # class-mode calls. This is an installed binding, not edge pruning.
    aliases = {}
    for package, name, target in read(probe / 'ready-bindings.json'):
        source, destination = owner(package, name), owner('CCL', target)
        assert destination in bindings, ('missing READY binding', target)
        aliases[source] = destination
        bindings[source] = bindings[destination]
    rows = read(probe / 'probe-output/probe-native.json')
    startup = next(r for r in rows if r['definition'] == 'READY-START')
    graph = startup['args'][0]['graph']
    generic_bindings = {n['binding'] for n in graph['nodes'] if n.get('binding')}
    leafs = {owner('CCL', '%WASM-EQ-TABLE-' + op): op for op in ('GET', 'SET', 'REMOVE')}
    trampoline = owner('CCL', 'FUNCALLABLE-TRAMPOLINE')
    roots = [(r['name'], 'startup:' + r['definition']) for r in rows
             if r['definition'] in ('READY-INITIALIZE', 'READY-CHECK', 'READY-START', 'READY-INTEGER-STRINGS', 'READY-LIST-CALLEES', 'READY-TYPE-METHODS', 'READY-INTEGER-MAGNITUDE', 'READY-SYMBOL-LOOKUP', 'READY-CLASS-PROTOCOL', 'READY-SLOT-ERRORS','READY-BIT-VECTORS')]
    roots += [(bindings[owner('COMMON-LISP', name)], 'exercised-function-cell:' + name)
              for name in ('LDIFF', 'MAPC', 'MAPCAR', 'MAPLIST', 'MAPL', 'MAPCAN', 'MAPCON')]
    roots += [(bindings[source], 'ready-binding:' + owner_name(source))
              for source in aliases]
    edges, missing, primitives = [], [], set()
    def follow(who, callee):
        if callee in leafs:
            primitives.add(callee)
            edges.append(dict(caller=who, callee=owner_name(callee), service=leafs[callee]))
            return None
        if callee in generic_bindings:
            target = bindings.get(trampoline)
            kind = 'projected-generic'
        else:
            target = bindings.get(callee)
            kind = 'ready-binding' if callee in aliases else 'function-cell'
        edge = dict(caller=who, owner=callee, callee=owner_name(callee), kind=kind, module=target)
        edges.append(edge)
        if target is None:
            missing.append(edge)
        return target
    def value_functions(value):
        if isinstance(value, dict):
            if isinstance(value.get('value'), dict) and 'function' in value['value']:
                yield value['value']['function']
            else:
                for child in value.values():
                    yield from value_functions(child)
        elif isinstance(value, list):
            for child in value:
                yield from value_functions(child)
    for i, node in enumerate(graph['nodes']):
        for callee in value_functions(node):
            target = follow('image-value:' + str(i), callee)
            if target:
                roots.append((target, 'image-value:' + str(i)))
        callee = node.get('function') or (trampoline if 'generic' in node else None)
        if callee:
            target = follow('image:' + str(i), callee)
            if target:
                roots.append((target, 'image:' + str(i)))
    queue = list(roots)
    reached, indirect = {}, []
    while queue:
        name, reason = queue.pop(0)
        if name in reached:
            continue
        assert name in by_module, ('missing installed module', name)
        assert name in metadata or by_module[name]['primitive'], ('missing compiler metadata', name)
        m = metadata.get(name, dict(dependencies=[], operators=[], children=[], source='', dynamic=False))
        if name in metadata and m['function'] is not None:
            assert m['function'] == by_module[name]['function'], ('module owner identity', name)
        row = dict(module=name, reason=reason, function=by_module[name]['function'],
                   name=owner_name(by_module[name]['function']) if by_module[name]['function'] else None,
                   source=m['source'], operators=m['operators'],
                   imported_symbols=sorted({owner_name(i) for _,i in by_module[name]['symbols']}),
                   wasm_sha256=digest(compiled / (name + '.wasm')))
        reached[name] = row
        if m['dynamic']:
            indirect.append(name)
        for callee in m['dependencies']:
            target = follow(name, callee)
            if target:
                queue.append((target, name))
        for child in m['children']:
            queue.append((child, name + ':nested-code'))
    counts = Counter()
    for row in reached.values():
        for op, count in row['operators']:
            counts[op] += count
    return dict(version=1, roots=[dict(module=n, reason=r) for n, r in roots],
                modules=sorted(reached.values(), key=lambda r:r['module']),
                edges=sorted(edges, key=lambda r:(r['caller'], r['callee'])),
                missing=missing, indirect_modules=sorted(indirect),
                services=sorted(owner_name(p) for p in primitives),
                acode=dict(definitions=len(reached), operators=len(counts),
                           occurrences=sum(counts.values()), by_operator=dict(sorted(counts.items()))),
                inputs={n:digest(probe/n) for n in ('compiled/modules.json', 'compiled/symbols.json',
                        'probe-output/ready-modules.json', 'probe-output/probe-native.json', 'ready-bindings.json')},
                complete=not missing and not indirect,
                scope='Static dependencies plus every projected function and generic trampoline; '
                      'indirect calls are listed, not assumed closed by successful sample execution.')


def controls(probe):
    """Exercise census failures without changing modules, images or evidence."""
    from unittest.mock import patch
    baseline = census(probe)
    real_read = read
    def altered(filename, transform):
        def replacement(path):
            result = real_read(path)
            return transform(result) if str(path).endswith(filename) else result
        return replacement
    checks = []
    entry = next(r['module'] for r in baseline['roots'] if r['reason']=='startup:READY-START')
    with patch(__name__ + '.read', side_effect=altered('ready-modules.json',
            lambda rows:[r for r in rows if r['module']!=entry])):
        try:
            census(probe)
        except (AssertionError, KeyError):
            checks.append('missing startup compiler record')
        else:
            raise AssertionError('missing compiler metadata was accepted')
    symbols = read(probe/'compiled/symbols.json')
    find_class = next(s['id'] for s in symbols if s['package']=='COMMON-LISP' and s['name']=='FIND-CLASS')
    with patch(__name__ + '.read', side_effect=altered('compiled/modules.json',
            lambda rows:[r for r in rows if r['function']!=find_class])):
        bad = census(probe)
        assert any(r['callee']=='COMMON-LISP::FIND-CLASS' for r in bad['missing'])
        assert not bad['complete']
        checks.append('uninstalled named callee stays missing')
    def image_function(rows):
        row = next(r for r in rows if r['definition']=='READY-START')
        row['args'][0]['graph']['nodes'].append(
            {'tag':250, 'fields':[{'value':{'function':find_class}}]})
        return rows
    with patch(__name__ + '.read', side_effect=altered('probe-native.json', image_function)):
        changed = census(probe)
        assert any(e['caller'].startswith('image-value:') and
                   e['callee']=='COMMON-LISP::FIND-CLASS' for e in changed['edges'])
        checks.append('first-class image function enters closure census')
    reached = {r['module'] for r in baseline['modules']}
    unused = next(m['name'] for m in read(probe/'compiled/modules.json') if m['name'] not in reached and not m['function'])
    with patch(__name__ + '.read', side_effect=altered('compiled/modules.json',
            lambda rows:[r for r in rows if r['name']!=unused])):
        reduced = census(probe)
        assert baseline['acode']==reduced['acode']
        checks.append('unselected corpus code cannot inflate census')
    return dict(status='PASS',checks=checks)


if __name__ == '__main__':
    import sys
    result = census(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(modules=len(result['modules']), missing=len(result['missing']),
                          indirect=len(result['indirect_modules']), acode=result['acode'])))
