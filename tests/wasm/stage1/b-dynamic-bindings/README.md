# Generated special parameters and PROGV

This auxiliary proposal extends the reviewed special-binding implementation to
required, optional, rest and keyword parameters declared SPECIAL, including
supplied-p variables, inlined literal lambdas and local functions. It also lowers
PROGV through CCL's real front-end IR. No inventory slot is claimed.

Required parameters bind in order. Optional defaults see earlier parameters;
each supplied-p binding follows its parameter. Keyword matching stages values
and flags in private rooted slots, then installs the parameters in lambda-list
order, evaluating missing defaults in that environment. Lexical captured keys
keep their cell identity. Every parameter binding lives inside one unwind extent,
including partially initialized calls. Inlined lambda operands are evaluated
before entering that extent. Active bindings prevent tail transfer; callees may
still run proper tail chains.

PROGV recognizes the exact CHECK-SYMBOL-LIST call U1 inserts before the values
form. It checks a finite proper symbol list, symbol eligibility, owner-assigned
indices and the complete binding-record budget before evaluating values. It
rechecks the list after values, since that expression can mutate the list. Each
binding uses the reviewed 32-byte rooted record; repeated symbols restore in
reverse order. Missing values bind the distinct unbound marker, and excess
values are ignored. Normal return, checked error and THROW all unwind the chain.
The symbol flags and offsets derive from pinned U1 definitions and D1, not the
host's object layout.

The corpus compares native CCL, an independent Python evaluator and generated
Wasm at low and above-2-GiB stack placements. It includes ordered defaults,
supplied flags, keyword duplicates, rest lists, partially failed initialization,
escaping closures, local recursion, APPLY, nested/repeated PROGV, mutated symbol
lists, cleanup, nonlocal exits, zero and 130 values, 128 simultaneous bindings
and a 3,000-step tail child under a binding. All previous call/control cases
remain. Explicit closure byte expectations distinguish escaping objects from
inlined lambdas and SELF recursion without captures.

Twenty-four target-only probes cover constant/global/non-fixnum symbol flags,
a symbols list made cyclic by values evaluation, insufficient record capacity
before values effects, and a malformed values tail after a binding. These are
checked refusals, not native comparisons on undefined input. They assert full
vector and chain restoration. The earlier 44 metadata/capacity controls and
three development regressions remain. Twenty-one compiler mutants use the same
literal oracle; the inline-extent mutant reproduces this unit's real leak.

The loader, binary reader and stub are unchanged reviewed bytes. Lazy composition
uses the same owner setup and corpus. Both native R6/R6a and retained verification
are required. The older non-B emitter prefix must remain byte-identical.

Scope remains explicit: three privately named symbols, preassigned indices and
a fixed owner vector; no automatic index assignment, vector growth, package
installer or global proclamations. PROGV uses checked explicit-stack capacity
rather than U1's native stack-derived 169-symbol limit; native comparisons stop
at 128. Refusals use checked exception codes, not complete Lisp condition objects.
There is no GC, safepoint, handler dispatch, multi-Worker binding qualification
or host re-entry. Saved symbols/values and current vector entries remain collector
obligations. Local RETURN-FROM and other declarations remain refused. Recovery
from corrupt owned binding records is not promised.

```sh
python3 tests/wasm/stage1/b-dynamic-bindings/native.py --evidence ../ccl-evidence --work /tmp/dynamic-native-work --output /tmp/dynamic-native
python3 tests/wasm/stage1/registration/qualify.py --output /tmp/dynamic-native --inputs ../ccl-evidence/macos-u1-inputs --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 --destination /tmp/dynamic-qualified
python3 tests/wasm/stage1/b-dynamic-bindings/run.py --evidence ../ccl-evidence --native /tmp/dynamic-native --qualification /tmp/dynamic-qualified --output /tmp/dynamic-run
python3 tests/wasm/stage1/b-dynamic-bindings/verify.py --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-17-stage1-b-dynamic-bindings-r1
```

Developed only in disposable pristine U1 copies. This proposal awaits Claude's
review before integration; the accepted predecessor is already integrated.
