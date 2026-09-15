# Registry changes joined to compiler bodies — 15 September 2026

Status: executed diagnostic; reviewed by Claude's fifty-fourth audit at `f7d2f73a` without defect. The 77 construction gaps are the 45 reader and 32 writer accessor methods; the setter hook does not see the lazy reader-optimization store. No gate credit.

The [registry checkpoint](dispatch-registry.md) could not connect its fresh
objects to compiler bodies in the earlier build. This witness records both
in one native execution. It reloads the full pinned U1 `lib/describe.lisp`, then
adds, replaces, warms and removes a specialization of a private generic function.
All work runs in a disposable release-image process with unchanged U1 source.

| Observed item | Count |
| --- | ---: |
| Native pass-2 entries / emitted functions | 225 / 401 |
| Method additions / removals | 240 / 239 |
| Dcode setter calls / behavioral calls | 12 / 3 |
| Touched generic functions / final installed methods | 118 / 335 |
| Installations joined to compiler bodies | 163: 160 during the source reload, three in the probe |
| Installations without a compiler-body witness | 77, all during the source reload |
| Ordered events / referenced function records | 1,435 / 936 |

## What the join proves

The observer captures the actual front-end IR before invoking the original
native pass 2, and the emitted functions and complete native code prefixes after
it returns. Standard method installation/removal and the dcode setter record
nested entry and completion events with before/after state. One strong EQ table
assigns all object IDs and retains the objects throughout the session.

For each joined installation, the method's function resolves to the same
prototype object the compiler emitted, that compiler completion precedes the
installation, and the installed prototype's code bytes equal the captured
emission. Names do not establish these links. A replaced method's old object,
its nested removal and its replacement all remain distinct records. The checker
checks exact method-list transitions and owner changes, then compares the last
observed lists with the live final registries.

The 77 other installations stay `UNRESOLVED_CONSTRUCTION`. Their function
identities are known; this execution supplied no corresponding compiler IR.
They need a construction/template witness, not a guessed link by printed name.
The output also retains uninitialized allocation state: the dcode setter can
run before a new GF's standard slots are bound. Such a state is never treated
as an initialized empty method list.

## Verification and reversibility

Four fresh native processes execute the unit: two observations, a reference
without installed hooks, and a real omission of the method-addition hook.
Both observation captures reproduce byte-for-byte. The reference's initial
1,514 method-code records (411,368 code bytes) and the changed rows for 14 GFs
(152 methods, 42,352 code bytes) equal the observed run. These are native code
prefix and signature comparisons, not complete heap/function-payload equality.
The reference loads the same fixture definitions and reload policy.

The three probe calls preserve both values: `30,31` after replacement and when
warmed, then `10,11` after removing the specialization. Twenty-three checker
controls reject damaged identities, event nesting/completion, owners, emissions,
installed bytes, results, joins and scope. The actual omitted-hook run is
rejected because the final method lists cannot be accounted for. The verifier
re-executes all four sessions and compares seven deterministic outputs.

The backend slot and three function cells are restored with `unwind-protect`.
A deliberate nonlocal exit independently checks restoration of all four
bindings. The release image, kernel and eight inspected upstream sources remain
unchanged. No source patch, native rebuild, FASL publication or image save runs.
Original development failures and their executed fixture sources are retained
in this deliverable's compact packet; earlier evidence is reused by identity.

## Remaining scope and next work

These are observed installation-to-body links in a new execution. They do not
retroactively identify the original rich build's 465 dynamic objects or replace
its unresolved edges. The dynamic phase label covers helper compilation during
the reload as well as source definitions; reported source notes are separate.
The initial/final registry set consists of the GFs touched by these hooks,
not every GF in the process.

The dcode setter hook does not intercept inline stores. Method boundary snapshots
retain their resulting selection, but cache invalidation, effective-method
construction/calls, class hierarchy changes and custom method combinations are
not yet an exhaustive dispatch witness. No callee bound follows from the 163
body joins. Loading native inspector source for observation does not include
all its native operations in the browser profile; Swink remains excluded.

Claude's fifty-third audit further established that U1's stale dcode defect
applies to any removal that empties a method registry, whatever dcode was
previously selected. The Wasm disposition must require the appropriate
no-applicable-method behavior for **every empty registry**. This unit retains
the last universal method and does not claim to repair or qualify that defect.

Next: trace the 77 installed functions without compiler bodies through their
construction paths, and extend this same-execution mechanism to effective-method
cache construction/invalidation and the larger census capture. Keep original
execution namespaces distinct until an actual identity witness connects them.
The ledger remains **40 accepted, 8 missing, 0 unreviewed of 48**; LL15-b/c are
still missing. Reviewed without defect in Claude's fifty-fourth audit.
