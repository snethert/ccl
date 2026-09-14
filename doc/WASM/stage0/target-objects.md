# Native object serialization witness — 13 September 2026

Status: executed; independent review pending. Packet `NATIVE-TARGET-OBJECTS-R1`
is retained as `2026-09-13-target-objects-r1` through the
[evidence index](../evidence/index.json). This is the census deliverable following
Claude's thirty-fourth audit, alternating with the standing controls.

The two runtime object references observed in the image-restore macro expansions
already have symbolic serialization paths in U1. The class cell is saved as a
deferred class-registry lookup. The registered restart cell is saved by its
symbol, without its native wrapper. This slice witnesses those existing paths;
it finds no defect requiring a compiler correction.

| Observed object | Uses in the restore expansion trace | Executed serialization witness |
| --- | --- | --- |
| IOBLOCK class cell | Twelve outputs: six TYPEP expansions and their STRUCTURE-TYPEP expansions | MAKE-LOAD-FORM yields `(CCL::FIND-CLASS-CELL 'CCL::IOBLOCK T)`; the real FASL scanner/writer emits it under deferred EVAL |
| RESTART wrapper in its registered cell | Two REGISTER-ISTRUCT-CELL outputs | ISTRUCT-CELL-P recognizes the registered cons by identity; opcode 71 carries only the RESTART symbol |
| Lexical environment | Three DEFVAR/DECLAIM outputs | Every observed output occurrence is inside compile-toplevel-only EVAL-WHEN; its implementation is not qualified here |

The [driver](../../../tests/wasm/native-census/target-objects/driver.lisp) runs the
actual target front end with the previously reviewed private expanders and
corrected helpers. It retains all 293 events and joins the literal identities to
the real image registries before dumping. It uses the actual class cell and
registered restart pair, not descriptions reconstructed from their names.

The native scanner/writer emits seven tiny data FASLs, each assigning a
dynamically bound fixture variable. The positive file is 132 bytes and holds the
class cell, the restart cell, and a second reference to the same class cell.
An independent Python decoder reads the complete file, including its header,
expression table, symbolic creation form, reference sharing and end marker.
Its opcode allowlist excludes native function/code payloads. This deliberately
small decoder is an oracle for this corpus, not a general FASL reader.

The actual native loader executes five positive roundtrips: original registries,
fresh private registries, a repeat in those registries, absent keys, and a repeat
after creation. Fresh or absent keys yield cells distinct from the original
objects, with empty class/wrapper payloads. Both repetitions preserve keyed
identity, and every load preserves the repeated class-cell reference. The global
registry tables, original entries and restart-pair contents remain unchanged.

Two additional dumps replace the registered restart cell's native wrapper with
NIL and a keyword sentinel in private registry lists. Both files are byte-equal
to the original. Four negative inputs use the same native writer and loader:
wrong class key, wrong restart key, an unregistered lookalike cons, and a creation
recipe stored as an ordinary list. The literal identity/type oracle rejects all
four, and the decoder checks the exact corresponding change to the bytes.
Sixteen checker controls reject damaged identity joins, sharing, restoration
claims, payload erasure, scope, case coverage and FASL encoding.

## Relationship to target materialization

U1's native paths are in `lib/nfcomp.lisp`, `level-0/nfasload.lisp`,
`level-0/l0-pred.lisp` and the class-cell MAKE-LOAD-FORM method in
`level-1/l1-clos.lisp`. The corresponding cold handlers in `xdump/xfasload.lisp`
also recognize these keys: the class recipe creates or finds an early class
cell, while opcode 71 creates or finds an early istruct cell. Those source
handlers are a static implementation lead, not an executed target claim in this
packet. All named U1 sources are pinned and match the disposable source archive.

The port must materialize these registries as target objects, preserve identity
and sharing, supply the class/wrapper contents, and join the recipes and their
initialization prerequisites into the census graph. None of that is established
by a native data-FASL roundtrip. Arbitrary object constants, lexical-environment
helpers, remaining type-system helpers and full macro-environment qualification
remain open. The original literal descriptions retain their unqualified flags;
this separate witness narrows what is known about their serialization.

The restore traversal still captures seven definitions with five boundary stops,
22 prototypes, 74 calls, twelve references and seven unbounded calls. No widening
edge is replaced, no Wasm is emitted and no LL15 gate credit is claimed.

## Reproduction and retained development

Run from the repository root, with unused work/output paths:

```sh
python3 tests/wasm/native-census/target-objects/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --work /private/tmp/ccl-target-objects-work \
  --output /private/tmp/ccl-target-objects-result
python3 tests/wasm/native-census/target-objects/run.py \
  --verify /private/tmp/ccl-target-objects-result
```

Two fresh native sessions reproduce both captures and all seven data files
byte-for-byte. The retained verifier checks the new packet and direct source
pins. The disposable U1 sources and existing FASLs are unchanged; no shared
source patch, native rebuild or saved image is produced.

Development retained a missing compile-time opcode constant, a setup call folded
by REGISTER-ISTRUCT-CELL's own compiler macro, and a checker refusal of nested
macro events recorded in completion order. The fixes use the pinned literal
opcode, invoke the registry function at runtime, and sort events by their
existing sequence numbers. Original sources, logs and captures remain in the
compact development archive, including the successful process exit whose
fresh-registry identity observation was wrong. A zero process exit is not
reported as proof of that attempted case.

This execution left Stage 0 at 33 accepted, 14 missing and one unreviewed required
slot. The user subsequently [accepted S0-LL01-a](project-acceptance.md), bringing
the ledger to **34 accepted, 14 missing and zero unreviewed**. This object witness
remains a diagnostic input awaiting independent review.
The next scheduled deliverable is a standing control, then the census returns
to helper qualification, the five boundary contracts and broader traversal.
