# Bootstrap condition and foreign-entry frontier

Original CCL definitions executed against native rise **484 → 486**. The two new entries, `STREAM-IS-CLOSED` and `SIGNAL-PACKAGE-ERROR`, are error-only witnesses; the non-NIL return count remains **451**. Admission rises **2,043 → 2,051 of the fixed 2,231-definition cohort**. Sixteen native pointer/FFI definitions are explicitly conditionalized; fifteen belong to that cohort and are counted as `TARGET-EXCLUDED`, never as accepted.

This proposal stacks on the pending introspection packet. Neither proposal is integrated. It changes no shared compiler, runtime or CCL source and claims no LL15, method-dispatch or READY credit.

## Conditions

The backend admits nine further classes: STREAM-ERROR, END-OF-FILE, FILE-ERROR, PACKAGE-ERROR, SIMPLE-PACKAGE-ERROR, STREAM-IS-CLOSED-ERROR, BAD-SLOT-TYPE, INACTIVE-RESTART and RESTART-FAILURE. Native CCL supplies the class precedence lists, slot order and default values. `class-proof.py` independently joins those lists to the compiler's distinct bits and checks every new slot index. The registry contains 28 rows; existing rows and bit assignments are unchanged. The nine new bits use the remaining positive fixnum mask range, so this is still a bounded class set, not a complete condition hierarchy.

The constructor roots all supplied slots, calls the existing collecting allocator, reloads every supplied value, and leaves omitted initargs at the native defaults. BAD-SLOT-TYPE exercises five slots, including its native FORMAT-CONTROL default. All publication follows allocation; intervening `condition_slots` calls only validate and locate slots and cannot allocate. Stream and file readers select their native slot; the package reader accounts for SIMPLE-PACKAGE-ERROR's inherited slot position. Reader misuse retains the existing checked-reader convention.

Ten generated observers exercise all nine classes, inherited handlers, a declining handler, collection in initargs and handlers, source evaluation order, and default preservation. They compare actual values with native. The two original error-signalling functions also execute through generic error-catching callers. Those original rows establish that an error is delivered; they do not independently compare every condition slot. The typed observers provide the additional field comparisons.

The full run passes **17,660 comparisons** at low and above-2-GiB placements, before and after movement. Four focused faults reject an omitted fifth slot, overwritten native default, wrong inherited package offset and wrong stream handler bit. The stream-bit fault must change the raising module: changing a calling module does not alter another module's signal search. The initially ineffective control is retained in development evidence.

## Foreign entries

`exclusions.json` names each definition guarded by `#-wasm32-target`. It covers native macptr loads/stores, foreign symbol lookup, malloc/free, xmacptr disposal registration, C-string/composite-pointer helpers, malloc-backed vectors, native fd-set helpers, macptr printing and callback-pointer allocation. No native numeric constant is substituted, and no success stub is introduced.

This withdraws native implementations, not their callers' requirements. `ffi-exclusions.json` lists remaining emitted callers. Required file IO, stream buffers, synchronization, scheduling, bignum scratch storage and host exit remain target implementation obligations. The dependency listing covers emitted direct calls; refused bodies and dynamic calls may contain further callers. Exclusion alone does not establish dependency closure or make those APIs available.

## Qualification and replay

Native R6/R6a passes **21,843 tests**, with **140/164** byte-identical FASLs and all **164 restored**. The edited CCL files have identical decoded native code under the adopted source-location allowance. There are **153 local reader comparisons** over nine files and seventeen existing target profiles; exact inverse edits bind the unchanged source bodies. Runtime files are unchanged from the accepted tree.

```
python3 tests/wasm/stage1/bootstrap-condition-frontier/packet.py verify \
  --packet ../ccl-evidence/2026-09-22-stage1-bootstrap-condition-frontier-r1 \
  --output /tmp/condition-frontier-review
```

The packet retains changed artifacts and binds unchanged artifacts to the introspection packet, instead of copying the whole predecessor. Replay recompiles the file environments and execution corpus, runs the comparisons and four controls, checks final source equality against the native qualification, and compares deterministic artifacts.

Still open: the remaining numeric and CLOS dependency closure, eight condition-class refusals in the complete file records, owner-backed kernel globals, heap constants and lexpr spread calls. The recipe report distinguishes missing inputs from missing implementations. The FFI exclusions do not count as new execution.
