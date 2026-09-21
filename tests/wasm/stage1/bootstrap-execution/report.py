"""Count executed definitions, known dependencies and explicitly untested bodies."""
import collections,json
from pathlib import Path

def report(out):
    out=Path(out)
    read=lambda p:json.loads((out/p).read_text())
    save=lambda n,x:(out/n).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
    native=read('compiled/native.json')
    modules=read('compiled/modules.json')
    primitive={r['name'] for r in modules if r['primitive']}
    executed={r['definition'] for r in native if not r['definition'].startswith('CORE-') and r['name'] not in primitive}
    cases=collections.Counter(r['definition'] for r in native)
    candidates=read('compiled/closed.json')
    admitted=read('compiled/throughput.json')['functions']
    known={(r['package'],r['name']) for r in candidates}
    known.add(('COMMON-LISP','EQL'))
    missing=collections.Counter(c[1] for r in admitted if r['proposal']=='admitted' for c in r['callees'] if tuple(c) not in known)
    assert missing['NIL']==0, 'computed callee was mistaken for literal NIL'
    required=['%COPY-U8-TO-STRING','%COPY-STRING-TO-U8','1+','1-','LIST-LENGTH','%SIMPLE-STRING=','UTF-8-OCTETS-IN-STRING','UTF-16-OCTETS-IN-STRING','FUNCALL','APPLY','UNION-EQL']
    assert all(n in executed for n in required),set(required)-executed
    assert all(cases[n] for n in ['CORE-BYTE-STORE','CORE-BYTE-ORDER','CORE-ZERO','CORE-COMPUTED-CALL','CORE-COMPUTED-INNER','CORE-COMPUTED-APPLY','CORE-COMPUTED-INNER-APPLY'])
    witnesses=read('compiled/executed-operators.json')
    lowering={op:[r['name'] for r in witnesses if any(name==op for name,n in r['operators'])]
              for op in ['ADD2','SUB2','MUL2','DIV2','NUMCMP','%IZEROP','%TYPED-UVSET']}
    assert all(rows for op,rows in lowering.items() if op!='%IZEROP'),lowering
    assert not lowering['%IZEROP'], 'Update the declared unexecuted lowering when a source witness appears'
    save('lowering-coverage.json',dict(operators=lowering,unexecuted=['%IZEROP'], division_scope='DIV2 and %QUO-1 witnesses use floating operands only. Integer / refuses even for an integral quotient; rational arithmetic is outside this packet.',explanation='The native %izerop source probe becomes EQ in NX1; its success is not a witness for the %IZEROP emitter.',scope='Each listed operator is emitted in a module directly executed against native. This is not instruction or branch coverage.'))
    save('execution-frontier.json',dict(original_definitions_executed=len(executed),names=sorted(executed),
        native_cases=dict(sorted(cases.items())),primitive_definitions_not_counted=sorted({r['definition'] for r in native if r['name'] in primitive}),
        missing_dependencies=dict(missing.most_common()),
        not_executed=[dict(**r,reason='No qualified input/environment recipe; compilation is not execution.') for r in candidates if not r['inputs']],
        static_dependency_closed=sum(r['static'] and r['name']!='EQL' and r['package']!='WASM32-COMPILER' for r in candidates),
        runtime_dispatch_tested=[r['name'] for r in candidates if r['inputs'] and not r['static']],
        scope='Static closure concerns named calls only. Runtime callable inputs are explicitly installed for tested rows. Globals, argument domains and complete bootstrap readiness are not inferred. EQL is the reviewed primitive, not another Lisp definition.'))
    return len(executed)
