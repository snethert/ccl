# Collecting floating-point owner capability (auxiliary proposal)

`float-service.mjs` adapts the accepted raw floating service to the accepted
single-Worker collector owner. This is **not integrated**, changes no compiler,
and claims no LL16 slot. The service, detector and collector binaries are reused
by their reviewed hashes; this unit implements only the owner boundary. Generated
Lisp calls, loader admission and Lisp condition delivery remain next work.

```
python3 tests/wasm/stage1/float-owner/run.py --evidence ../ccl-evidence --output /tmp/float-owner-run
python3 tests/wasm/stage1/float-owner/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-19-stage1-float-owner-r1 --output /tmp/float-owner-replay
```

## Capability and roots

The factory binds one owner, memory, TCR and checked-error tag to explicitly
pinned float and detector bytes. It checks the imported capabilities and runs
both numeric modules over a private four-page unshared memory. Arithmetic never
runs on the Lisp heap; staged numeric bytes contain no pointers. The owner must
supply authentic object starts, immutable pinned-region ownership and exclusive
heap authority. Digest checking is against the trusted owner's expected digest,
not code signing. The input pinned-region list is copied.

The returned `(operation, root, safety) -> i32` function accepts a topmost rooted
frame with four tagged words. Operands occupy offsets 8 and 12; offsets 16 and 20
must initially be NIL. It publishes the result at offset 16 and preserves the
operands (their addresses may change). Unary coercions ignore the second operand.
Operation numbers are the accepted primitive's 0–11. Safety is exactly 0 or 1.
The capability reads the production TCR `fp_control` at offset 200 **on each
invocation**, refusing unsupported bits even in unchecked mode.

The raw i32 return packs the selected condition in bits 0–4, detected flags in
5–9, stage in 10–11, operand-A flags in 12–16 and operand-B flags in 17–21. It is
not a Lisp root. A selected condition leaves the result NIL and allocates nothing;
so do boolean results apart from publishing NIL/T. The future Lisp adapter must
decode the status and signal while the two operands remain rooted. This unit
does not deliver conditions or implement the two declared native-compatibility
adjustments from the primitive packet.

For a boxed result, the capability asks the owner for its exact 8- or 16-byte
extent inside a synchronous safepoint. It then reloads the allocation pointer
and memory view, copies the private result, advances the heap and publishes the
root with no intervening call. It never caches a heap pointer across assurance.
Refused assurance may already have moved operands; the current roots remain
valid and no result is published. A nested owner boundary refuses. Service
refusals become checked codes 41 (capability/options), 42 (type/malformed),
43 (primitive capacity), 45 (unsupported operation), or 6 (assurance/allocation).
These codes are not Lisp conditions. Re-entry is refused with 41.

## Evidence

The runner pins and selects 1,585 rows from accepted float-core R2: every 157th
row, every named signed-coercion boundary, and both coercions for the first thirty
random inputs under all masks and safety modes. The original expected bits and
flags are retained unchanged; the native and rational oracles are reused from
that reviewed packet, not recomputed or relabelled as a new native run.

Each row runs below and above 2 GiB, normally and with a real collection before
every result allocation: 6,340 comparisons and 2,834 forced collections. Every
seventh row has pinned-image operands; the rest have heap operands. Retired
spaces are poisoned before publication. Every call checks both operand byte
strings, exact result/status, root links/count, padding and FP-word preservation.
The assurance count is zero for booleans/conditions and one for boxed results.

Thirty-six scenario records include that matrix and focused checks: real memory
growth with both operands live, movement of the published result, three dependent
numeric calls with collection between them, a refused growth after operand
movement, live mask changes, invalid roots/types/capabilities, nested boundaries,
re-entry, a no-room owner and recovery after refusal. Growth runs at the low
placement; the reviewed collector's 32,769-page maximum leaves no growth room
above 2 GiB. Twelve runtime faults are rejected using required failure locations
and diagnostic assertions, with literal focused inputs required to pass first.

No new R6 build is needed: compiler, native code and integrated runtime files are
unchanged. This proposed module is a standalone JS capability exercised against
the accepted binaries. The native overflow/infinity differences, non-nearest
rounding, generalized real arithmetic and generated compiler integration remain
outside its claim.

## Development

The first harness requested a memory maximum above the reviewed collector's
32,769 pages; instantiation correctly refused. The harness now stays within that
bound and tests growth at the low placement. A later control runner assumed
WebAssembly exceptions have a message property; the stale-pointer fault threw
code 6 without one. Failures now retain the exception code explicitly and the
control requires it. Both original failing captures and source versions are
retained. Neither failure changed the proposed capability.
