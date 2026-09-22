# Original bignum GCD and numeric restarts

Execution rises from 537 to 547 unchanged CCL definitions, and from 502 to 512
with a non-NIL return witness. Admission is 2,044 of the same 2,231 definitions,
down from 2,060: sixteen constant condition constructions now refuse explicitly
instead of compiling unresolved calls. No previously executed definition is lost.
The source proof and admission-change lists name each change.

This is an unreviewed proposal over the accepted audit-159 integration. It adds
no C or JavaScript service and earns no LL15 slot credit. The ordinary Lisp
bignum GCD algorithm is CCL's own whole-file definition, using the accepted
half-digit primitives. Dense seeded operands, shared factors, digit boundaries,
and both signs exercise it at both placements before and after movement.

The target adds the portable `%INIT-MISC` definition from x8632, a fixnum
declaration on its existing `%FIXNUM-GCD`, and a bignum arm in generic UVREF/UVSET.
That arm reuses typed access: full span and index checks, unsigned word reads
boxed when necessary, and stores restricted to nonnegative target fixnums.
Wider/negative digit stores use the existing half-digit primitives. No store
occurs until all checks pass. Direct checks cover boxing, movement, bad indices,
bad values and unbacked headers/digits.

`%KERNEL-RESTART` gets a Wasm-only call to target Lisp. The numeric type-error
fallback uses CCL's RESTART-CASE, with USE-VALUE and validation of a replacement.
A second invalid replacement signals again. Existing registered hooks run first;
there is no native frame pointer, so a hook receives NIL in that argument. Only
canonical numeric type names and the wrong-type kernel code have a built-in
fallback; other requests refuse. This is not the full kernel-restart API.

MAKE-CONDITION and the constant-class/list-arguments CONDITION-ARG path share
the existing rooted condition constructor. The latter preserves CCL's actual
condition-to-restart association. INVOKE-RESTART, FIND-RESTART, RESTART-NAME,
APPLICABLE-RESTART-P and %ACTIVE-RESTART run from CCL's file-compiled definitions.
The tests cover a distinct condition that must not find the associated restart,
collection during handlers, repeated replacement, custom hooks and exact error
payloads. The too-many-arguments path signals the native SIMPLE-ERROR with
`"Too many arguments."` and NIL format arguments. It is not PROGRAM-ERROR.

The native oracle uses the original CCL restart functions. Observer callers
create and inspect native restarts; they do not replace those functions.
Condition constructors have directed refusal controls. Literal NIL retains an ordinary unresolved MAKE-CONDITION call and receives no execution credit. PROGRAM-ERROR's new
constructor row has an executed signalling witness.

## Limits

Generic GCD/GCD-2 is still blocked by ABS's complex-number dependencies.
COMPUTE-RESTARTS has an input observer but is not callee-closed and earns no
execution credit. `%KERNEL-RESTART` is compiled in its real file environment;
the later excluded `#_exit` still stops that file, and its prefix is retained
with that stop. No claim of complete file compilation is made.

The condition mask is unchanged and full. Its successor remains real TYPEP
against class precedence lists, not another mask. Generic method selection,
image installation, startup joining and READY are unfinished. The accepted
NO-REM behavioural branch is unchanged; this proposal adds no behavioural
change for existing native targets.

## Reproduce

From the checkout root:

```
python3 tests/wasm/stage1/bootstrap-gcd/packet.py verify \
  --packet ../ccl-evidence/2026-09-22-stage1-bootstrap-gcd-r1 \
  --output /tmp/ccl-gcd-replay
```

The verifier recompiles the whole-file corpus, runs native comparisons, moving
target execution and direct checks, and reruns the file-environment count.
R6/R6a is reused only after asserting final proposal sources byte for byte.
The sole new native-source conditional has a textual reader proof: removing
exactly the Wasm arm and complementary guard reproduces the integrated file.
Native decoded code and data also compare equal; source positions alone differ.

The packet is a delta over the accepted division packet. Source pins use the
post-integration tree and bind the integration record. Source pins are checkout-relative; evidence dependencies are relative to the
evidence store. Tool executable paths remain absolute and digest-bound. `development.json` retains the relevant original
failures without duplicating complete scratch builds.
