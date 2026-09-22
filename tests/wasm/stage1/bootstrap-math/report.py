def pending_reason(name):
    if name in ('%FILE-AUTHOR','ENSURE-OPEN-SHLIB','RESOLVE-CONTAINER','SHARED-LIBRARY-AT','SHARED-LIBRARY-WITH-NAME','SHLIB-CONTAINING-ENTRY','ENTRY->ADDR'):
        return 'Native OS/FFI state is not a portable input recipe; needs target capability or explicit exclusion.'
    if name in ('XP-FLAGS-REGISTER','XP-FPSCR-INFO','%PROGVRESTORE','%ARRAY-INDEX','%SLOT-REF'):
        return 'Raw execution-context or stack/index operands need a representation-specific caller and oracle.'
    if name in ('%ARRAY-HEADER-SUBTYPE','ARRAY-DATA-OFFSET-SUBTYPE','ARRAY-ELEMENT-SUBTYPE','ARRAY-ELEMENT-TYPE','%SET-SIMPLE-ARRAY-P','MIXUP-HASH-CODE','BOOTSTRAPPING-FASL-MIN-VERSION','BOOTSTRAPPING-FASL-MAX-VERSION'):
        return 'Result depends on target representation/constants; direct macOS value equality is not the oracle.'
    if name=='%PATH-MEMBER':
        return 'Native source reads past string end before checking the bound; checked target refusal retained from audit149.'
    if name in ('CLEAR-GF-DISPATCH-TABLE','INVALID-HASH-KEY-P','UNDEFINE-CONSTANT','%UNFHAVE'):
        return 'Marker/function-cell state needs explicit encoding and post-state observation.'
    if name in ('TOPLEVEL','THREAD-PRESET','DBG'):
        return 'Needs controlled process/debugger state; calling the live native entry is not an isolated recipe.'
    groups = [
        (('%16-RANDOM-BITS','%MRG31K3P'), 'Generator mutates unsigned 32-bit state with values above the target fixnum range; UVSET currently admits only fixnum store values. Needs boxed uint32 stores, not a zero-only random-state recipe.'),
        (('%CLOSE-STRING-OUTPUT-STREAM','STRING-INPUT-STREAM-CHARACTER-READ-VECTOR','TRUNCATING-STRING-OUTPUT-STREAM-IOBLOCK-WRITE-CHAR','TRUNCATING-STRING-OUTPUT-STREAM-IOBLOCK-WRITE-SIMPLE-STRING','TRUNCATING-STRING-OUTPUT-STREAM-TRUNCATED-P'), 'Needs stream/ioblock identity and cyclic structure transport with observable state; current scalar/predicate stream recipes do not establish these operations.'),
        (('%FILE-KIND','CYGPATH'), 'Host pathname/provider operation needs the target file-provider implementation or a definition-level exclusion; native filesystem state is not a portable recipe.'),
        (('%GROW-HASH-TABLE-IN-PLACE-P','LOCK-FREE-HASH-TABLE-COUNT'), 'Needs the native HASH-TABLE wrapper and backing-vector transport, including deleted-count semantics. The accepted leaf backing vector alone is not that wrapper.'),
        (('%GVECTOR',), 'Direct call has a runtime subtag, whereas constructor lowering requires a literal admitted layout; generated constructor witnesses do not credit this unmodified self-primitive body.'),
        (('FIND-GF-DISPATCH-TABLE-INDEX',), 'Needs a target class-wrapper/dispatch-table image with wrapper hash indices and obsolete-wrapper state.'),
        (('MAKE-NUMERIC-CTYPE-PREDICATE',), 'Returns a closure; needs a generated consumer that invokes it and compares results, rather than serializing a native function identity.'),
        (('NEXT-CATCH',), 'Requires a live target catch-chain frame and a native frame-aware oracle, not an arbitrary tagged object.'),
        (('IS-COMBINABLE',), 'Combining bitmap contains bignum bitsets; variable LOGBITP beyond fixnum payload remains an arithmetic dependency.'),
    ]
    for names,reason in groups:
        if name in names:return reason
    return 'Recipe not yet qualified: constructor/state or structured result transport remains owed; no execution credit.' 

"""Count executed definitions, known dependencies and explicitly untested bodies."""
import collections,json
from pathlib import Path

def report(out):
    out=Path(out)
    read=lambda p:json.loads((out/p).read_text())
    save=lambda n,x:(out/n).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
    native=read('compiled/native.json')
    target_names={r['definition'] for r in native if r.get('targetOnly')}
    modules=read('compiled/modules.json')
    primitive={r['name'] for r in modules if r['primitive']}
    executed={r['definition'] for r in native if not r.get('targetOnly') and not r['definition'].startswith('CORE-') and r['name'] not in primitive and r['definition'] not in ('FULLTAG','LISPTAG','TYPECODE','ASSQ')}
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
              for op in ['ADD2','SUB2','MUL2','DIV2','NUMCMP','%I<>','%IZEROP','%TYPED-UVSET']}
    assert all(rows for op,rows in lowering.items() ),lowering
    assert 'CORE-NUMERIC-IR' in lowering['DIV2']
    assert any(r['definition']=='CORE-NUMERIC-IR' and r['args']==[6,3] for r in native)
    assert cases['CORE-INTEGER-DIVIDE']>=14 and cases['CORE-DIVIDE-ORDER']>=14 and cases['CORE-DIVIDE-ZERO']>=4
    save('dependency-domains.json',dict(calls={'ASSQ':'Native EQ association lookup; Lisp originals REGISTER-ISTRUCT-CELL and ADJOIN-ASSQ execute.', 'LOGAND/LOGIOR/LOGXOR':'Fixnum operands, zero/binary/variadic calls; bignums refuse code 32. Full bignum logical arithmetic remains owed.', '-':'Unary, binary and variadic calls in the accepted integer/single/double numeric subset.', 'TYPEP/REQUIRE-TYPE':'Literal admitted type descriptors use existing native predicate modules and EQL. Dynamic types and other specifiers remain Lisp call dependencies.', 'LDB':'Constant byte specifiers of width at most 29 over fixnum operands; other byte specifiers remain call dependencies, bignum operands refuse code 32.', '%BADARG':'Unchanged Lisp definition executes through the existing TYPE-ERROR service.', 'LENGTH':'Unchanged LENGTH and SEQUENCE-TYPE definitions execute on proper lists, simple strings, bit vectors, u8 vectors and simple vectors. Circular/improper-list error 170 remains checked refusal 45; this does not claim its native condition subclass.'},representation_primitives=['FULLTAG','LISPTAG','TYPECODE','ASSQ'],representation_scope='Native callable entries supply expectations on shared fixnum-tag inputs; these Wasm primitive definitions are exercised but excluded from the original-definition count.',recipe_scope='Member fixtures include native arrays and locks plus native-shaped tagged objects. Per-case global environments and their post-state are compared. Pinned fixture fields are roots; generated istruct constructors allocate in the moving heap. No complete bootstrap claim.'))
    save('lowering-coverage.json',dict(operators=lowering,unexecuted=[], division_scope='DIV2 executes exact integer quotients, mixed real division and float division. %QUO-1 executes integer reciprocals of 1 and -1. Nonintegral integer quotients remain checked refusal 45; rational arithmetic is not implemented.',explanation='Declared fixnum tests select the existing %I<> and %IZEROP emitters after NX1; source modules emit and execute both.',scope='Each listed operator is emitted in a module directly executed against native. This is not instruction or branch coverage.'))
    error_only=sorted(n for n in executed if all(r.get('caught') for r in native if r['definition']==n))
    nil_only=sorted(n for n in executed if all(not r.get('caught') and all(v is None for v in r['values']) for r in native if r['definition']==n))
    non_nil=sorted(n for n in executed if any(not r.get('caught') and any(v is not None for v in r['values']) for r in native if r['definition']==n))
    save('member-witnesses.json',dict(executed=len(executed),non_nil_witness=len(non_nil),nil_only=nil_only,error_only=error_only,
        scope='A non-NIL return is a coverage indicator, not proof of full domain coverage. Type members use native constructors or tagged layout fixtures. Locks and basic streams are tested only as objects, not as operating-system capabilities. EXTENDED-CHAR-P is defined to return NIL on this CCL character representation.'))
    save('execution-frontier.json',dict(original_definitions_executed=len(executed),names=sorted(executed),
        native_cases=dict(sorted(cases.items())),primitive_definitions_not_counted=sorted({r['definition'] for r in native if r['name'] in primitive}),
        missing_dependencies=dict(missing.most_common()),
        not_executed=[dict(**r,reason='No qualified input/environment recipe; compilation is not execution.') for r in candidates if not r['inputs']],
        static_dependency_closed=sum(r['static'] and r['name'] not in target_names and r['name']!='EQL' and r['package']!='WASM32-COMPILER' for r in candidates),
        runtime_dispatch_tested=[r['name'] for r in candidates if r['inputs'] and not r['static']],
        scope='Static closure concerns named calls only. Runtime callable inputs are explicitly installed for tested rows. Globals, argument domains and complete bootstrap readiness are not inferred. EQL is the reviewed primitive, not another Lisp definition.'))
    baseline=Path(__file__).resolve().parents[5]/'ccl-evidence/2026-09-21-stage1-bootstrap-admission-r1/execution/execution-frontier.json'
    before=json.loads(baseline.read_text())
    pending=[r for r in before['not_executed'] if r['static']]
    originals=[r for r in pending if r['package']!='WASM32-COMPILER' and r['name']!='EQL']
    save('progress.json',dict(baseline_executed=382,executed=len(executed),new_executions=sorted(executed-set(before['names'])),
        original_closed_without_inputs_before=len(originals),
        reviewed_closed_count_including_fixture_names=len(pending),
        pending_recipe_dispositions=[dict(name=r['name'],disposition='executed' if r['name'] in executed else pending_reason(r['name'])) for r in originals],
        newly_executed_from_closed=sum(r['name'] in executed for r in originals),
        still_without_inputs=[r for r in originals if r['name'] not in executed],
        fixture_or_primitive_names_excluded=[r['name'] for r in pending if r not in originals],
        reader_files_complete_before=44,reader_files_complete_after=sum(x=='T' for x in __import__('re').findall(r'\("[^"]+" \d+ (T|NIL)\)',(out/'compiled/worklist.sexp').read_text())),
        reader_failures_remaining=[r for r in read('compiled/worklist-throughput.json')['read_errors'] if 'compound-function-name' not in r['message']]))
    return len(executed)
