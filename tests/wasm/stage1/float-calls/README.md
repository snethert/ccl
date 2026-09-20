# Generated floating calls and Lisp conditions

Auxiliary proposal for LL16, not a slot execution or an integrated compiler.
The off-by-default floating mode compiles real U1 front-end IR into calls to
the reviewed collecting float capability. Its loader profile binds allocation,
integer and floating services to one trusted owner. The shared compiler and
runtime remain unchanged by this proposal.

## Run and replay

From the repository root, with the sibling evidence repository present:

```sh
python3 tests/wasm/stage1/float-calls/run.py --evidence ../ccl-evidence --output /tmp/float-calls --qualify
python3 tests/wasm/stage1/float-calls/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-19-stage1-float-calls-r1 --output /tmp/float-calls-replay
```

The replay rebuilds the proposed compiler, positive and faulty modules, the
native oracle, cold-loader composition and default-mode comparison. It also
requalifies retained native R6/R6a evidence. `native.py` produces the registered
and restored builds; the unchanged baseline is referenced from the accepted
1A packet. Each native suite has 21,843 passes, 162 of 164 registered FASLs
are unchanged and all 164 are restored. The compiler used there must equal
the compiler generated for this packet.

## Admitted operations and publication

`compile-float-call-form` takes a form, name, links and an optional safety value
of one (checked) or zero (unchecked). It enables the existing integer,
allocation-retry and callable-metadata modes together with floating calls.
Two-argument `+`, `-`, `*`, `/`, `<`, `<=`, `=`, `/=`, `>=` and `>` are admitted,
as is two-argument `FLOAT` with a literal single or double prototype. Local
function shadows retain their lexical meaning. Integer-only addition,
subtraction and multiplication use the accepted integer emitter.

Each floating call roots both operands before evaluation can collect, calls
one owner capability, and reads the published result or constructs and signals
a Lisp condition. Original operands stay rooted while building the condition's
operand list. The sealed native-derived class inventory gains invalid-operation,
overflow, underflow and inexact classes; division-by-zero uses the existing
class. Arithmetic condition OPERATION and OPERANDS describe the source operation
and original arguments. They do not claim to reproduce x86 trap metadata or
CCL's intermediate coercion-call payload. STATUS retains its native default.

The runtime adapter preserves two native library conventions around the
unchanged mathematical primitive: integer-to-float overflow is signalled even
when unchecked or masked, and integer/infinity comparisons use CCL's effective
infinity magnitude of 2^1024, including its equality behavior. The source pins
include the native numeric implementations. Same-format `FLOAT` returns its
input object without allocation, after nonallocating frame and object validation.
Mixed arithmetic itself remains in the reviewed Wasm service; the adapter uses
BigInt only to apply the native integer conversion/comparison conventions.

The live TCR enable word supplies checked-operation masks. In unchecked mode
the primitive validates the enable word but does not apply it; native explicit
coercion errors remain separate. Of 116 independently joined policy rows, one
has a declared native difference: unmasked x86 traps on an exact least-single
subnormal conversion, while the adopted D6 tiny-and-inexact policy returns that
subnormal. `native-observed.json` retains the original native answer, and
`policy-join.json` names the sole adjustment. The join refuses any other
difference. This applies the approved policy, not a new compatibility decision.

`wasm32-shared-B-floating-owner-v1` admits exactly three function imports:
`owner.ensure`, `integer.calculate` and `floating.calculate`, bound by identity
to a frozen capability bundle. It retains the loader's byte validation and
restrictions on instantiation side effects. Older profiles refuse the floating
namespace. Bundle identity is trusted-owner admission, not code signing. The
packet independently pins the primitive binaries; digests computed by the
execution harness are not a separate trust anchor.

## Evidence

The corpus compiles 36 modules and runs 475 native cases below and above 2 GiB,
with and without forced movement: 1,900 comparisons, 744 collections and 1,488
assurance entries per eager or cold run. Eager and cold observations are
byte-identical. Cases compose arithmetic with closures, dynamic bindings,
multiple values, cleanup, handlers and restarts, including same-format identity,
unchecked coercion, and 96 directed bignum/infinity comparisons. Assertions check
value bits and restored stack, roots, handlers and bindings. This harness does
not claim a new memory-growth witness; the accepted owner packet covers growth.

Eight recompiled compiler faults and three adapter faults must fail their named
function oracles. Those oracles use a function-name substring and required
process failure, not an exact diagnostic, and some generator substitutions
change more than one matching emission site. Sixty default-mode Wasm/WAT files
remain byte-identical to the reviewed default corpus. Admission checks refuse
an older profile, a missing or copied bundle and a replaced floating capability.
Retained development evidence includes the actual same-format identity failure
and its rejected old-adapter control, along with compile, oracle and harness
failures. The passing pre-controls run is identified separately.

## Boundaries

This is not the complete LL16 numeric family. Ratios, complex arithmetic,
integer-only division, general numeric dispatch, unary/n-ary forms and dynamic
FLOAT prototypes are not supplied by this mode. A nonnumeric operand reaches
the Lisp type-error path; unsupported numeric kinds and malformed owner/service
state retain checked refusals. Operand selection follows the existing target
order rather than every native optimization policy's diagnostic order. Private
readers retain their existing wrong-class convention.

Every floating operation currently reserves a root frame and crosses the owner
capability into private arithmetic memory. No timing or inline-floating claim is
made. A refused assurance can already have moved live objects, and a masked raw
conversion can allocate an unused result before the adapter selects native's
explicit conversion error. The owner contract guarantees valid roots, not
rollback or minimal allocation on those paths. General LL16 qualification and
the adopted D6 cost measurement remain due.
