"""Check every standalone module against the upstream macro-name index.

This is a conservative name screen, not a substitute for file compilation.
Cross-target definitions with the same name remain visible as candidates.
"""
from collections import Counter
from closure import read, digest
from replacements import upstream_definitions, U1


def census(probe, closure):
    definitions = upstream_definitions()
    macros = {name: [r for r in rows if r['kind'] == 'DEFMACRO']
              for name, rows in definitions.items()
              if any(r['kind'] == 'DEFMACRO' for r in rows)}
    symbols = {r['id']: r for r in read(probe/'compiled/symbols.json')}
    metadata = read(probe/'probe-output/ready-modules.json')
    installed = read(probe/'compiled/modules.json')
    bindings = {}
    for mode in (False, True):
        for module in installed:
            if module['function'] and bool(module.get('cplMode')) == mode:
                bindings[module['function']] = module['name']
    reached = {r['module'] for r in closure['modules']}
    standalone = [r for r in metadata if r['module'].startswith('scan_')]
    rows = []
    for module in standalone:
        for dependency in module['dependencies']:
            symbol = symbols[dependency]
            candidates = macros.get(symbol['name'])
            if not candidates:
                continue
            owner = symbols.get(module['function'])
            effective = bindings.get(module['function'])
            rows.append(dict(module=module['module'],
                caller=(owner['package'] or '#')+'::'+owner['name'] if owner else None,
                callee=(symbol['package'] or '#')+'::'+symbol['name'],
                upstream_macro_candidates=candidates,
                other_upstream_definitions=[r for r in definitions[symbol['name']]
                                            if r['kind'] != 'DEFMACRO'],
                selected_module=effective, reached=module['module'] in reached,
                disposition=('REACHED_REQUIRES_FILE_ENVIRONMENT' if module['module'] in reached
                             else 'SUPERSEDED_BINDING' if effective != module['module']
                             else 'UNREACHED_STANDALONE_CANDIDATE')))
    rows.sort(key=lambda r:(r['module'], r['callee']))
    # INVOKE-TYPE-METHOD has no runtime definition in this file environment.
    # Unlike a missing ordinary function, it must not remain a READY edge.
    assert not any(e['callee']=='CCL::INVOKE-TYPE-METHOD' for e in closure['edges'])
    affected = [r for r in rows if r['callee']=='CCL::INVOKE-TYPE-METHOD']
    assert len(affected)==5 and all(r['disposition']=='SUPERSEDED_BINDING' for r in affected)
    by_module = {r['module']:r for r in metadata}
    for row in affected:
        selected = by_module[row['selected_module']]
        assert selected['source']=='ccl:level-1;l1-typesys.lisp'
        assert all(symbols[i]['name']!='INVOKE-TYPE-METHOD' for i in selected['dependencies'])
    return dict(version=1, upstream=U1, standalone_modules=len(standalone),
                macro_names=len(macros), candidates=rows,
                candidate_modules=len({r['module'] for r in rows}),
                candidate_edges=len(rows),
                dispositions=dict(sorted(Counter(r['disposition'] for r in rows).items())),
                inputs={n:digest(probe/n) for n in ('compiled/modules.json','compiled/symbols.json',
                                                  'probe-output/ready-modules.json')},
                scope='Every scan module screened against all upstream DEFMACRO name sites. '
                      'Reader conditionals, lexical shadowing and same-name native functions '
                      'are not resolved by this index. Unreached candidates carry no READY '
                      'execution credit and require file compilation before use.')


def controls(probe, closure):
    from copy import deepcopy
    altered = deepcopy(closure)
    altered['edges'].append(dict(caller='control', callee='CCL::INVOKE-TYPE-METHOD'))
    try:
        census(probe, altered)
    except AssertionError:
        return dict(status='PASS', checks=['macro function edge rejected'])
    raise AssertionError('macro edge escaped the READY census')
