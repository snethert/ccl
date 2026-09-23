# Growing class tables and class-based implicit conditions

This proposal adds protocol execution; it does not claim new original-definition
credit or recount admission. The standing original headline is 550 executed,
515 with non-NIL witnesses. Class mode remains off by default.

The completed run has 6,512 native rows and 26,048 comparisons (64 new),
19,854 collections, 30 directed owner checks and 40 collector checks.
The 24 condition callers cover 45 native cases. Final-source R6/R6a passes
21,843 tests and restores all 164 FASLs. These results add no slot credit.

SETF GETHASH and REMHASH use the accepted strong EQ leaf. The Lisp wrapper
checks the native wrapper's comparison mode and read-only flag. On a full
vector, an existing key is updated without growth. A new key causes allocation
of a vector twice as large, copies live entries through the accepted setter,
and replaces NHASH.VECTOR only after copying succeeds. Deletion uses the
leaf's existing operation 2, including tombstones and cache invalidation.

The compiler adds allocation of the accepted strong-owner hash-vector shape.
It initializes the complete prefix, buckets and zero padding between safepoints.
It does not allocate a native weak table or change the collector's contract.
Lisp uses CCL's existing NHASH accessors; a small marker predicate recognizes
the accepted leaf's empty/deleted encodings, 243 and 251. Those are service
markers, not the backend's general unbound or slot-unbound values.

Capacity doubles through 16,384 entries, the accepted service and collector
limit. A new entry at that ceiling signals an error; updates and deletion
remain available. This is bounded growth, not an unbounded table implementation.
The adapter's private scratch reservation is enlarged to cover that capacity.
No new C or JavaScript runtime algorithm is introduced.

Native comparisons create 1,500 and 3,500 additional class cells from fresh
uninterned names. The larger case crosses 2,048 and 4,096 entries, looks up every
name, removes and recreates all new cells, collects with tombstones, and uses
the resolved class to construct a condition. Native graph capture follows the
wrapper's current vector after growth. Separate removal cases test presence,
absence, evaluation order, cache invalidation and read-only refusal.

Class objects remain projected from the native image. These tests allocate
cells on the target heap; they do not implement DEFCLASS, class finalization,
the cross-dumped image or the READY join. Legacy mode retains the old registry. In class mode it is replaced as described below.

```
python3 tests/wasm/stage1/bootstrap-class-growth/run.py /tmp/class-growth
python3 tests/wasm/stage1/bootstrap-class-growth/native.py /tmp/class-growth-native
```

The packet also adds the class owner's target constructor and CLRHASH.
The constructor allocates both wrapper and backing vector on the moving heap.
A caller starts at four slots, builds all 612 cells through FIND-CLASS-CELL,
replaces its image root, resolves every name after collection, removes/restores
a class name and constructs a condition. This avoids projecting the wrapper,
vector or cells for that path. The class objects remain projected identities.
The constructor's native reference is MAKE-HASH-TABLE, explicitly recorded as
a reference for new target code rather than an original-definition witness.
CLRHASH publishes an empty vector at the old capacity and returns the table;
its replacement is allocated before the old vector is detached.

Class-mode implicit failures now call a Lisp reason-code dispatcher, which uses
MAKE-CONDITION and the live class table. Matching and readers already use the
same classes. Class-mode Wasm modules import no condition registry and emit no
registry allocator or mask reader. The comparison includes implicit CAR type
errors, integer division by zero, unbound variables and undefined functions,
with cleanup and collection. For these cases every old registry row is replaced by NIL. The type-error caller builds its own table and all 612 cells first.

The default-off boundary remains: legacy modules retain their existing registry
until the image/bootstrap join is qualified. This is not a claim that the flag
has been removed. BREAK-ON-SIGNALS, debugger integration, the re-entry contract
and real cross-dumped class objects remain separate obligations.

Constructor boundaries check tag, range, parity and power-of-two capacity before
allocation. Prefix, bucket and padding checks cover capacities through 16,384.
A full table admits replacement, refuses a new key without changing the table,
and admits a new key after deletion. These are target owner-contract checks;
they are reported separately from comparisons with native CCL.

The undefined-function witness checks the exact class for FDEFINITION and the
UNDEFINED-FUNCTION membership and name for FUNCALL. Native FUNCALL constructs
CCL::UNDEFINED-FUNCTION-CALL; the existing target boundary constructs its base
UNDEFINED-FUNCTION. This inherited subclass/argument-payload difference remains
open, and is not counted as exact native class agreement. The development run
that exposed it is retained. Floating overflow and division-by-zero also run
with the registry unavailable, through class-mode numeric definitions.

Development evidence retains the premature execution attempt, the native
literal-class cache probe correction, the oracle's anonymous-caller correction,
the initially omitted handler accessors, the late-generated symbol-pool
failure, and the initially mixed-mode numeric callees. The symbol-pool failure
made PREPARE-TO-DESTRUCTURE refuse compilation;
generated constructor symbols now use existing symbol imports. No failure is
counted as a successful comparison.

Retained replay (from this proposal's source revision, beside the evidence store):

```
python3 tests/wasm/stage1/bootstrap-class-growth/packet.py verify \
  --packet ../ccl-evidence/2026-09-23-stage1-class-growth-r1 \
  --output /tmp/class-growth-replay
```

The verifier rebuilds execution by default and reuses native qualification only
with identical final proposal sources. `--reuse-output` validates an existing
completed run and explicitly records `execution_rebuilt: false`.

The P4 directive and its measured-phase addendum were read from commits
`a0b2fb05` and `bbafc488` before completing this run, and imported verbatim.
They remain marked awaiting adoption. This packet changes the compiler and
driver, so a full run is appropriate even under P4's proposed tiers. The
completed author run is retained once; identity validation is not reported as
a second execution. WABT assembly uses four workers, each writing separate
outputs; target execution still uses one worker. `review-artifacts.tar.gz`
retains the compiled compiler and complete generated drivers, with file hashes
in `review-artifacts.json`. These are review inputs, not a completed compile
cache or focused-probe command. No generated-code or startup timing is claimed.

The class-mode numeric closure is compiled from the complete l0-numbers,
l0-float, l0-bignum32, l1-numbers and w32-lap files, in addition to w32-prims.
A class-mode caller must not silently return through an old registry-dependent
numeric body.

The unbound-variable witness uses a special reference under an unbound PROGV
binding. SYMBOL-VALUE's separate kernel-restart path was tried and remains
unsupported; its failure is retained, not credited. The kernel's interactive
unbound-variable restart defaults are still owed. FDEFINITION's constant
$XFUNBND error code now enters the class-based undefined-function boundary.
The symbol and selected ordinary FUNCALL/APPLY/function-reader definitions
are compiled in class mode along with the numeric callees.

Floating witnesses check overflow through EXP, zero-divisor LOG through the
accepted double-float leaf (generic LOG remains unadmitted), and invalid SQRT.
The first class dispatcher transcribed the three floating reason codes in the
wrong order; these witnesses exposed it. The corrected order is 35 invalid,
36 overflow, 37 underflow, matching the accepted backend. The failing run is
retained. The undefined-call subclass's lazy keyword metadata is initialized
natively before capturing the image; its subclass difference remains declared.
