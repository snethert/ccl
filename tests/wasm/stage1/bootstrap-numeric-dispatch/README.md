# Original bignum algorithms and method combination

This proposal increases executed original definitions from 507 to **531**, and
non-NIL witnesses from 472 to **496**, over 21,432 comparisons. Admission stays
2,059 of 2,231. No earlier
execution is lost. This is execution work towards LL15, not LL15 qualification.

`w32-bignum.lisp` supplies the target equivalents of native bignum LAP entries.
CCL's original `l0-bignum32.lisp` supplies addition, subtraction, logical
operations, shifts, normalization and byte extraction. The backend supplies
checked digit access, zeroed subtag-7 allocation, header shortening and digit
copy. Shrinking leaves aligned empty-vector objects in the released tail so
the existing collector can still walk the allocation. Even-sized digit
payloads have zero padding. Inputs include signed carry/borrow boundaries and
32,800-bit additions/subtractions beyond the integer service's capacity.
The 16-bit half-digit primitives do not use that service for wide operands.

`w32-dispatch.lisp` supplies a callable trampoline and the three method-context
application entries. The trampoline calls `gf.dcode` through ordinary rooted
`&REST`/`APPLY`. Native CCL's `&LEXPR` entries return one value; a development
attempt to change that was withdrawn. Ordinary `&LEXPR` behavior is unchanged.
CCL's unchanged `%%before-and-after-combined-method-dcode` runs from the whole
`l1-dcode` file, using real native method instances projected to their accessed
slots. Four cases cover presence/absence of before and after methods, order,
mutation, and multiple values. Additional callers change dcode and cross a
cleanup and nonlocal exit under collection. These callers and target LAP
replacements receive no original-definition credit. No constant-stack claim
is made for the target `%apply-lexpr-tail-wise` entry.

Each original credited here is joined to a whole-file module and an installed
module in `source-proof.json`. Native and target outputs run at both placements,
with and without movement. `bignum-check.mjs` adds direct refusal and heap-walk
checks. The unchanged structural collector checks run too. Native R6/R6a on
the final proposed compiler and source passes 21,843 tests and restores all
164 FASLs; the retained verifier reuses it only after exact source comparison.
The proposal changes no shared runtime file and adds no C service.

From the repository root:

```sh
python3 tests/wasm/stage1/bootstrap-numeric-dispatch/packet.py verify --packet ../ccl-evidence/2026-09-22-stage1-bootstrap-numeric-dispatch-r1 --output /tmp/ccl-numeric-dispatch-replay
```

The verifier re-executes the native oracle and target corpus and recounts the
worklist. It binds all emitted worklist modules by digest, retains the numeric
and dispatch modules, and reuses unchanged retained artifacts from the previous
packet. Necessary development failures are retained as logs, not repeated build
trees. Non-deterministic logs, host paths and compiler source-position read
diagnostics are not compared as deterministic outputs.

The requested work remains larger than recipes: full GF method selection and
caches, remaining bignum multiplication/division and float dependencies, logical
function bits/name metadata beyond the already implemented keyword vector,
additional condition classes, kernel-global owners, package/type-descriptor
literals and the image/READY join remain unfinished. The report
`requested-frontier.json` separates dependency blockers from missing recipes;
its recursive missing-name list is diagnostic, not a closure proof. None of
these obligations receives credit from executing the method-combination body.
