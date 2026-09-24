"""Check every compiled module against the upstream macro-name index.

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
    for module in metadata:
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
    assert not any(e['callee'].split('::')[-1] in macros for e in closure['edges']), 'macro name in READY closure'
    affected = [r for r in rows if r['callee']=='CCL::INVOKE-TYPE-METHOD']
    assert len(affected)==5 and all(r['disposition']=='SUPERSEDED_BINDING' for r in affected)
    by_module = {r['module']:r for r in metadata}
    for row in affected:
        selected = by_module[row['selected_module']]
        assert selected['source']=='ccl:level-1;l1-typesys.lisp'
        assert all(symbols[i]['name']!='INVOKE-TYPE-METHOD' for i in selected['dependencies'])
    remaining = {'CCL::%INTEGER-ABS': ('CCL::NUMBER-CASE', 'ccl:level-0;l0-int.lisp'),
                 'CCL::%GET-HASHED-HTAB-SYMBOL': ('CCL::HTVEC', 'ccl:level-0;nfasload.lisp')}
    for name, (macro, source) in remaining.items():
        matches = [r for r in rows if r['caller']==name and r['callee']==macro]
        assert len(matches)==1 and matches[0]['disposition']=='SUPERSEDED_BINDING', name
        selected = by_module[matches[0]['selected_module']]
        assert selected['source']==source
        assert all(symbols[i]['name']!=macro.split('::')[-1] for i in selected['dependencies'])
    assert all(r['disposition']=='SUPERSEDED_BINDING' for r in rows)
    return dict(version=2, upstream=U1, screened_modules=len(metadata), standalone_modules=len(standalone),
                macro_names=len(macros), candidates=rows,
                candidate_modules=len({r['module'] for r in rows}),
                candidate_edges=len(rows),
                dispositions=dict(sorted(Counter(r['disposition'] for r in rows).items())),
                inputs={n:digest(probe/n) for n in ('compiled/modules.json','compiled/symbols.json',
                                                  'probe-output/ready-modules.json')},
                scope='Every compiled module screened against all upstream DEFMACRO name sites. '
                      'Reader conditionals, lexical shadowing and same-name native functions '
                      'are not resolved by this index. Unreached candidates carry no READY '
                      'execution credit and require file compilation before use.')


def controls(probe, closure):
    from copy import deepcopy
    from unittest.mock import patch
    checks = []
    altered = deepcopy(closure)
    altered['edges'].append(dict(caller='control', callee='CCL::NUMBER-CASE'))
    try:
        census(probe, altered)
    except AssertionError:
        checks.append('any macro name in the READY closure is rejected')
    else:
        raise AssertionError('macro edge escaped the READY census')
    original = read
    def changed(path):
        rows = original(path)
        if str(path).endswith('ready-modules.json'):
            rows = deepcopy(rows)
            symbols = original(probe/'compiled/symbols.json')
            macro = next(row['id'] for row in symbols if row['name']=='NUMBER-CASE')
            module = next(row for row in rows if row['module'] in
                          {r['module'] for r in closure['modules']} and
                          row['source'].startswith('ccl:') and not row['module'].startswith('scan_'))
            module['dependencies'].append(macro)
        return rows
    with patch.dict(census.__globals__, read=changed):
        try:
            census(probe, closure)
        except AssertionError:
            checks.append('whole-file macro-as-callee rejected')
        else:
            raise AssertionError('whole-file module escaped macro screen')
    return dict(status='PASS', checks=checks)
