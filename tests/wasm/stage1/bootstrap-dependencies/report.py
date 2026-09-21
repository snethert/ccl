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
    executed={r['definition'] for r in native if not r['definition'].startswith('CORE-') and r['name'] not in primitive and r['definition'] not in ('FULLTAG','LISPTAG','TYPECODE')}
    cases=collections.Counter(r['definition'] for r in native)
    candidates=read('compiled/closed.json')
    admitted=read('compiled/throughput.json')['functions']
    known={(r['package'],r['name']) for r in candidates}
    known.add(('COMMON-LISP','EQL'))
    missing=collections.Counter(c[1] for r in admitted if r['proposal']=='admitted' for c in r['callees'] if tuple(c) not in known)
    assert missing['NIL']==0, 'computed callee was mistaken for literal NIL'
    required=['%COPY-U8-TO-STRING','%COPY-STRING-TO-U8','1+','1-','LIST-LENGTH','%SIMPLE-STRING=','UTF-8-OCTETS-IN-STRING','UTF-16-OCTETS-IN-STRING','FUNCALL','APPLY','UNION-EQL']
    required+=['LENGTH','REGISTER-ISTRUCT-CELL','SET-ISTRUCT-CELL-INFO','ADJOIN-ASSQ','LAST','NTH','NTHCDR','SYMBOL-PACKAGE','BOUNDP','%SYM-VALUE','MOVE-STRING-BYTES','STRINGP']
    assert len(executed)>=240
    assert all(cases[n] for n in ['CORE-ASSQ','CORE-LOGICAL','CORE-SUBTRACT-CALL','CORE-TYPE-TESTS','CORE-REQUIRE-INTEGER','CORE-BADARG','CORE-REGISTER','CORE-SYMBOL-STATE','TYPECODE'])
    assert all(n in executed for n in required),set(required)-executed
    assert all(cases[n] for n in ['CORE-BYTE-STORE','CORE-BYTE-ORDER','CORE-ZERO','CORE-COMPUTED-CALL','CORE-COMPUTED-INNER','CORE-COMPUTED-APPLY','CORE-COMPUTED-INNER-APPLY'])
    witnesses=read('compiled/executed-operators.json')
    lowering={op:[r['name'] for r in witnesses if any(name==op for name,n in r['operators'])]
              for op in ['ADD2','SUB2','MUL2','DIV2','NUMCMP','%IZEROP','%TYPED-UVSET']}
    assert all(rows for op,rows in lowering.items() if op!='%IZEROP'),lowering
    assert 'CORE-NUMERIC-IR' in lowering['DIV2']
    assert any(r['definition']=='CORE-NUMERIC-IR' and r['args']==[6,3] for r in native)
    assert cases['CORE-INTEGER-DIVIDE']>=14 and cases['CORE-DIVIDE-ORDER']>=14 and cases['CORE-DIVIDE-ZERO']>=4
    assert not lowering['%IZEROP'], 'Update the declared unexecuted lowering when a source witness appears'
    save('dependency-domains.json',dict(calls={'ASSQ':'Native EQ association lookup; Lisp originals REGISTER-ISTRUCT-CELL and ADJOIN-ASSQ execute.', 'LOGAND/LOGIOR':'Fixnum operands, zero/binary/variadic calls; bignums refuse code 32. Full bignum logical arithmetic remains owed.', '-':'Unary, binary and variadic calls in the accepted integer/single/double numeric subset.', 'TYPEP/REQUIRE-TYPE':'Literal admitted type descriptors use existing native predicate modules and EQL. Dynamic types and other specifiers remain Lisp call dependencies.', 'LDB':'Constant byte specifiers of width at most 29 over fixnum operands; other byte specifiers remain call dependencies, bignum operands refuse code 32.', '%BADARG':'Unchanged Lisp definition executes through the existing TYPE-ERROR service.', 'LENGTH':'Unchanged LENGTH and SEQUENCE-TYPE definitions execute on proper lists, simple strings, bit vectors, u8 vectors and simple vectors. Circular/improper-list error 170 remains checked refusal 45; this does not claim its native condition subclass.'},representation_primitives=['FULLTAG','LISPTAG','TYPECODE'],representation_scope='Native callable entries supply expectations on shared fixnum-tag inputs; these Wasm primitive definitions are exercised but excluded from the original-definition count.',recipe_scope='Type/structure predicates without admitted instance recipes are tested on nonmembers. Native globals are explicitly bound where the target fixture supplies empty state. No general instance, package topology or complete bootstrap claim.'))
    save('lowering-coverage.json',dict(operators=lowering,unexecuted=['%IZEROP'], division_scope='DIV2 executes exact integer quotients, mixed real division and float division. %QUO-1 executes integer reciprocals of 1 and -1. Nonintegral integer quotients remain checked refusal 45; rational arithmetic is not implemented.',explanation='The native %izerop source probe becomes EQ in NX1; its success is not a witness for the %IZEROP emitter.',scope='Each listed operator is emitted in a module directly executed against native. This is not instruction or branch coverage.'))
    save('execution-frontier.json',dict(original_definitions_executed=len(executed),names=sorted(executed),
        native_cases=dict(sorted(cases.items())),primitive_definitions_not_counted=sorted({r['definition'] for r in native if r['name'] in primitive}),
        missing_dependencies=dict(missing.most_common()),
        not_executed=[dict(**r,reason='No qualified input/environment recipe; compilation is not execution.') for r in candidates if not r['inputs']],
        static_dependency_closed=sum(r['static'] and r['name']!='EQL' and r['package']!='WASM32-COMPILER' for r in candidates),
        runtime_dispatch_tested=[r['name'] for r in candidates if r['inputs'] and not r['static']],
        scope='Static closure concerns named calls only. Runtime callable inputs are explicitly installed for tested rows. Globals, argument domains and complete bootstrap readiness are not inferred. EQL is the reviewed primitive, not another Lisp definition.'))
    return len(executed)
