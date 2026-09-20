# Numeric calls with allocation retry and trusted loader admission

Auxiliary composition for LL16; no slot credit or shared runtime integration.
The accepted integer-condition R2 compiler is unchanged, at SHA-256
`d328c6bc7882631d98bb49a878110c3b90b691583405a021e79ebef1f9192df4`.
The driver enables its existing allocation-retry special around the existing
numeric compiler entry. Native R6/R6a is reused from that exact reviewed R2
compiler; every native corpus oracle is executed again in disposable U1.

The runtime proposal adds a read-only TCR identity accessor to CollectorOwner,
a factory that binds allocation and integer services to one owner, memory,
TCR and error tag, and `wasm32-shared-B-integer-owner-v1` loader admission.
The factory uses a private WeakMap and returns a frozen pair. The loader
requires the actual pair and exact imported function identities. A copied
pair, wrappers, functions from another factory invocation, a wrong TCR or a
foreign error tag refuse before table publication. The integer binary is
independently pinned to the accepted service in the runner and packet inputs;
the factory verifies the owner's supplied digest. This is trusted-owner
identity and integrity checking, not authentication of a hostile owner.

Only this profile admits both `owner.ensure : (i32) -> ()` and
`integer.calculate : (i32,i32) -> i32`. Both are mandatory, with exact names,
types and catalog imports. The older profiles still refuse numeric imports.
Start functions, data/element sections and defined runtime state stay refused.
Cold installation cannot call either capability or write Lisp memory. Failed
installation leaves the stubs and memory intact; retry with correct bytes
succeeds. Invoke generated code outside an active owner boundary: shortage
inside that boundary refuses with code 6, including conditions and bindings.
Assurance is still not a rollback and may move roots or grow memory first.

## Execution

The corpus retains all 423 R2 cases and adds 21 cases composing numeric calls
with restarts, heap-valued specials, PROGV, closures, handlers and pending cons
values. Eighty modules run below and above 2 GiB, normally and with garbage
filling unused heap before invocation and owner assurance. Retired spaces are
poisoned. Binding indices 31, 63, 127 and 255 force actual vector growth.
Eager and cold execution must produce identical values and owner observations.
All modules, including inner functions, are cold-installed at least once; each
case then resets to cold stubs before invocation. Instantiation checks cover
all declared memory regions, including high-address semispaces.

A separate test-only derivative injects a nonmoving garbage-fill import before
each raw constructor preflight, following the reviewed constructor-retry
technique. Only the compiler's emitted allocation path can then collect.
Every constructor kind must actually move objects. These instrumented modules
are refused by the production loader for their extra function import and run
only eagerly. They are not substituted for the uninstrumented cold evidence.

There are 1,777 comparisons per ordinary or cold run, and another 1,777 under
constructor pressure; ordinary execution records 797 copies and one growth,
while constructor pressure records 1,615 copies. Constructor hooks execute
412 binding growths, 28 restart constructions and 388 condition constructions.
Thirty-two admission checks and ten runtime faults cover capability identity,
signatures, binary integrity, actual allocation assurance and numeric dispatch.
The high-address tiny-heap case retains refusal after movement with roots and
caller state restored. The low tiny-heap case grows real memory.

The sealed condition registry, explicit-constructor arithmetic field oracle,
NIL-divisor convention, two-invalid-operand priority differences, and
wrong-class reader convention remain those of accepted integer conditions R2.
Floating-point arithmetic, broader numeric arities and full LL16 qualification
remain open. This unit adds no performance claim, cross-Worker publication,
semispace reuse, general CLOS registry or new collector object kind.

```sh
python3 tests/wasm/stage1/integer-owner/run.py \
  --evidence ../ccl-evidence --output /tmp/integer-owner-run
python3 tests/wasm/stage1/integer-owner/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-integer-owner-r1 \
  --output /tmp/integer-owner-replay
```

Outputs must be new directories. `derive.py` pins its runtime baselines and
retains the generated runtime proposal with the packet. Development failures
retain their actual harnesses and logs; unchanged compiled inputs are stored
once. Replaying from the committed tree uses only pinned repository and
evidence inputs, not any development directory.
