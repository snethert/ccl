# Audit 137 corrections

One follow-up packet covers all four findings in the three unaccepted proposals.
The original fixtures and evidence stay unchanged. No shared compiler, runtime
or kernel changes; no LL15 slot credit. Use the derived host input module and
oracle here rather than the R1 Darwin behavior. Equality binaries are unchanged.
The derived population source removes one redundant predicate and must rebuild
to the exact reviewed binary.

**F1 — target reader conditionals.** The derivation asserts the integrated
backend's `:target-os :wasm` and its four target features. The native oracle reads
HEAP-IMAGE-NAME with those target features before compiling the selected form
on macOS. This excludes both the Darwin precomposition and Windows slash
conversion, just as a Wasm compilation does. Only the two kernel-pointer
acquisitions are then substituted. Native UTF-8 decoding, argv construction,
return values and global writes still run. All ten native image-name answers
must equal the original input code points. The owner now preserves namespace
names unchanged; no composition table or function is imported by its runtime.
The old Darwin table is retained only as a fault input, and both Darwin
composition and generic NFC substitution are rejected. Every generated module
is byte-identical to R1. The full Node/Chromium schedule, GC, TCR and omission
checks rerun. The native branch read is retained in `native-forms.lisp` and the
backend features in `target-profile.json`.

**F2 — NIL versus a cons.** The native matrix gains `(cons nil nil)` as its last
object, preserving every old index and every old predicate answer. Canonical
NIL's own car and cdr are initialized to NIL in the target. All 48 objects run
through both equality modes, primitive and generated calls, both placements
and movement. A focused probe also stores NIL and looks up the cons, then
reverses the roles. Removing the sentinel guard fails that native-false pair.

**F3 — fixed pending-work array.** Car-nested structural keys at depths 1,022 and
1,023 succeed; 1,024 and 3,000 refuse with status 3. Refusal preserves table,
publication words and the entire input key. Both placements run. Removing the
pending-depth guard is rejected at the first over-limit depth. This is a
resource limit for EQUAL traversal, not a native Lisp semantic limit.

**F4 — population admission.** Six directed malformed requests exercise object
tag, exact extent, type-code alignment, publication alignment, publication
aliasing and operation range. Every request must refuse before changing the
object, neighboring canaries or publication storage. Each has a C mutant which
removes its guard and must fail at that named case. These run at both placements.
The original `(base & 7)` check is redundant: `base = object - 6`, so checking
that the object tag equals 6 already proves base alignment. The derived source
removes this redundant expression, asserts binary equality with R1, and then
isolates the remaining tag guard. The original 792 observations and 296
collections replay byte-identically; their six unchanged faults remain bound to
R1. Equality replays its ten existing faults and adds two; host input execution
rejects nine faults; population adds six. There is no claim that the original
redundant predicates could each be distinguished at execution.

The packet binds all three parent manifests, their source pins and their review
replays. It reuses native R6/R6a for the unchanged compiler, recompiles the three
host modules, recompiles both equality binaries and the population binary, and
re-executes the changed native host and equality oracles. The population native
oracle is reused: its semantics and binary have not changed. The native
reference remains macOS; platform-independent behavior is selected with the
port's features rather than importing host-only branches.

```
python3 tests/wasm/stage1/startup-review-137/run.py --output /new/audit137
python3 tests/wasm/stage1/startup-review-137/packet.py verify --packet ../ccl-evidence/2026-09-21-stage1-startup-review-137-r1 --output /new/replay
```

This does not widen any parent scope: bounded equality key kinds/capacity,
ordinary strong-population representation, selected callback snapshot, image
binding obligations and complete LL15 worklist obligations remain as stated.
