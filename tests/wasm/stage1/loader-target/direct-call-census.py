"""Classify an indirect-control census by admitted callable shape (DCP M-0).

Arguments: TRACE RAW_BOOT_CODE_SET RUNTIME_ARCHIVE OUTPUT. Input inventories
must be those of the census build, not a subsequent build with shifted IDs.
This is an invocation census, not proof that a call site has a static target.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys


def classify(trace, boot, archive):
    assert trace['ready'] and trace.get('traceFrom') is None
    assert trace.get('censusScope', 'complete-indirect') == 'complete-indirect', 'partial direct-call table trace is not a logical census'
    boot_rows = {r['name']: r for r in boot['modules']}
    units = {u['name']: u for u in archive['units']}
    runtime = {(units[f['unit']]['file'], f['source_name']): f
               for f in archive['functions']}
    totals, rows = Counter(), []
    for call in trace['execution']:
        is_boot = call['file'] == 'boot0'
        definition = (boot_rows[call['module']] if is_boot else
                      runtime[call['file'], call['module']])
        assert call['code'] == (definition['id'] if is_boot else
                               16 + len(boot_rows) + definition['code_offset'])
        raw = definition['arity']
        assert len(raw) == (6 if is_boot else 7)
        if not is_boot:
            assert raw[0] == 1
        required, optional, rest, keys, allow_other, keywords = raw if is_boot else raw[1:]
        name = call.get('callable', {}).get('function')
        trampoline = name == {'symbol': 'FUNCALLABLE-TRAMPOLINE'}
        shape = ('gf-trampoline' if trampoline else 'keyword' if keys else
                 'rest' if rest else 'optional' if optional else 'fixed')
        identity = ('symbol' if isinstance(name, dict) and 'symbol' in name
                    else 'compound-or-anonymous')
        totals[shape] += call['count']
        rows.append({**call, 'shape': shape, 'nameKind': identity,
                     'lambdaList': dict(required=required, optional=optional,
                                        rest=bool(rest), keys=bool(keys),
                                        allowOtherKeys=bool(allow_other), keywords=keywords or []),
                     'captures': definition['captures']})
    return dict(total=sum(totals.values()), byShape=dict(totals),
                invokedDefinitions=len(rows),
                definitions=sorted(rows, key=lambda r: -r['count']),
                scope='Logical invocations in the full indirect control. Named versus computed call sites, '
                      'single-value consumers and leaf effects require compiler evidence. Intrinsics, '
                      'macros and special operators that eliminated calls are absent from this census.')


if __name__ == '__main__':
    trace, boot, archive, output = map(Path, sys.argv[1:])
    result = classify(*(json.loads(p.read_text()) for p in (trace, boot, archive)))
    result['inputs'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (trace, boot, archive)}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('definitions', 'inputs')}))
