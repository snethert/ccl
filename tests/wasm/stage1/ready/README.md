# Projected-image READY join — R12

This unit executes CCL's native string-output path, including the output branch
of `%PR-INTEGER`. It adds no stream service or replacement stream writer. The
six new original-definition witnesses are WRITE-STRING, WRITE-CHAR,
WRITE-SIMPLE-STRING, GET-OUTPUT-STREAM-STRING and the two string-output ioblock
writers. The generated DEFSTRUCT constructor executes but receives no original
DEFUN credit. The proposed original-execution total rises from **562 / 525
non-NIL** to **568 / 531**. Admission is not recounted by this packet.

## Implementation

The collector admits the native basic-stream subtag with exactly four traced
fields. Streams, their buffers, ioblocks, callbacks and locks survive collection.
Streams are created after image load; this unit does not add them to the image
loader's recognized kinds or define persistent stream restoration.

The file compiler compiles `l1-io.lisp` and `l1-streams.lisp` in their own macro
environments. The fixture constructs the native four-field stream and uses
CCL's generated MAKE-STRING-OUTPUT-STREAM-IOBLOCK. This deliberately leaves
MAKE-STRING-OUTPUT-STREAM's optional thread-local recycling pool and the file,
terminal and foreign-descriptor interfaces owed. The existing 612-class image
supplies the stream class; no generic function or class projection is added.

The native DEFSTRUCT constructor embeds a list of host class cells in its
hidden ancestry slot. The target constant-pool exporter correctly refused
those foreign objects. The isolated compiler now recognizes that slot of a
structure allocation in class mode and constructs its ancestry list using
FIND-CLASS-CELL, the operation in the native class cell's MAKE-LOAD-FORM.
Class-cell identity comes from the target table. The list spine is private to
the new instance; sharing the host's constant ancestry list is not claimed.
Other quoted lists, other vector fields and default mode retain their previous
lowering. This is not general LOAD-TIME-VALUE or MAKE-LOAD-FORM support.

The constructor also exposed an admission gap in TYPEP/REQUIRE-TYPE: target
fixnum slots expand to `(SIGNED-BYTE 30)`, beyond the former 28-bit limit.
The lowering now covers signed widths through 30 and unsigned widths through
29, using inclusive bounds that are representable target fixnums. Native and
target witnesses include both bounds, adjacent bignums, non-integers and the
TYPE-ERROR datum and expected type. Wider types keep their existing fallback.

The same byte-copy primitive used by bignums also grows and extracts native
string buffers. Its checked lowering now accepts simple strings as a second
four-byte payload shape, including empty strings. Digit operations remain
bignum-only; other ivector kinds still refuse. The shared byte-offset checks
run before copying, and overlapping copies use Wasm's memmove semantics.

## Execution and controls

The native/target caller checks class-cell names and identities, empty and
Unicode strings, newline position, substring bounds, buffer growth from zero
and across capacity, extraction and reuse, and output after movement. It prints
24 signed fixnum/bignum and radix pairs through `%PR-INTEGER` into the stream.
An error and a collecting THROW unwind through CCL's output-lock cleanup;
an extra release verifies that the lock is unowned afterwards.

Collector controls check every stream field through movement, wrong field
counts, truncated objects and refusal without publication at both placements.
A compiled count-check omission must fail. Twelve raw copy refusals cover
operand types, source/destination kinds, negative offsets/counts and each
buffer limit, with both buffers unchanged. Nonzero byte offsets and overlapping
Unicode copies match native. The R11 lock controls, R10 complex
controls, low-bit-first bit-vector byte check and generated READY admission
control remain in the run. The first constructor failure is retained.

Shared compiler, runtime and CCL files in the checkout remain unchanged; the
isolated proposal carries the changes above. R10 and R11 remain unreviewed
predecessors in this stack. Native qualification binds the final proposed
backend and source files. Full target
regression executes once; retention does not claim another execution.

The final run passes 26,048 fresh corpus comparisons, four cold boots with
1,490 collections, 60 support comparisons and 20 boot refusals. Native
R6/R6a passes 21,843 tests and restores all 164 FASLs, bound to the exact
35-file proposal. The static walk has 814 modules, 57 missing edges and
53 indirect modules; it includes the two IOBLOCK writers as explicit callback
roots. The initial author script stopped only in the final attribution report
when those roots were missing. The corrected reports reuse that completed
execution, with the failure and phase provenance retained. Reader and control
wall times were not saved before the reporting failure and remain unrecorded.
No class/GF expansion or LL15 slot credit is claimed.

## Reproduce

```sh
python3 tests/wasm/stage1/ready/packet.py verify ../ccl-evidence/2026-09-24-stage1-ready-join-r12 /private/tmp/ccl-work/claude/ready/verify
```

Native qualification can be rebuilt with `native.py` under a managed output
root. Historical packets replay at their recorded commits. LL15 remains open:
closure edges, indirect calls, replacement attribution and the 35 startup
callback dispositions still need completion.
