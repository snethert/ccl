# Source-wide census collection

This driver advances LL15-b/c from the image-restore file to all 164 recorded
native compilation units, including four additional included files. It does
**not** produce an accepted census. Native file sessions are independent;
their identities are not relabeled as the original r7 build identities.

It calls U1's real file compiler, retaining every recursive top-level form,
compile-time effect, include and macro selection. Native mode observes and
forwards the original native pass 2. Wasm mode replaces only the census backend's
pass 2 with distinct refusal functions, so the file compiler can traverse more
than its first definition without emitting executable target code. The FASL
publication entry is guarded. All temporary bindings and entry points unwind;
the source/bootstrap copy is compared in full afterwards.

`layout.lisp` supplies 161 source-derived integer descriptions, a 37-row data
subtype table, sixteen architecture fields and eight data architecture macros.
It does not inherit native function-code layout, stack/TCR offsets or foreign
interfaces. These descriptions enable observation; they do not implement the
represented objects. The wider macro/helper environment remains unqualified.

The flat graph avoids recursive serialization limits. `analysis.py` joins its
functions, calls, variable identities and operator counts to the earlier observer.
`bounds.py` proves only immutable lexical bindings with checked ownership and
body dominance; parameters, writes and unsupported values remain unresolved.
Native LAP output functions that bypass Lisp pass 2 are explicitly unjoined.
Successful reading does not imply a valid replacement or target implementation.

Run from the CCL repository root on macOS x86-64 with a fresh work path:

```sh
python3 tests/wasm/native-census/source-closure/run.py --evidence-root ../ccl-evidence --work /tmp/ccl-source-census --prepare
python3 tests/wasm/native-census/source-closure/survey.py --evidence-root ../ccl-evidence --work /tmp/ccl-source-census --output /tmp/ccl-census-native --mode native
python3 tests/wasm/native-census/source-closure/survey.py --evidence-root ../ccl-evidence --work /tmp/ccl-source-census --output /tmp/ccl-census-target --mode continue
python3 tests/wasm/native-census/source-closure/analyze_survey.py /tmp/ccl-census-native /tmp/ccl-native-analysis
python3 tests/wasm/native-census/source-closure/analyze_survey.py /tmp/ccl-census-target /tmp/ccl-target-analysis
python3 tests/wasm/native-census/source-closure/probe_run.py --evidence-root ../ccl-evidence --work /tmp/ccl-source-census --output /tmp/ccl-census-probes
```

`continue` catches failures at top-level compiler-form boundaries and marks
every subsequent capture with the preceding failed forms. Reader failures still
stop the file; EOF and successful compilation are separate fields. Neither
continuing after failure nor completing a file grants qualification.

The probe suite exercises PROGN, EVAL-WHEN, source macros and DEFTYPE,
MACROLET, structures, classes, methods, includes, target reader conditionals,
deferred initializer ownership, callback binding/scope, exceptional restoration
and refusal to execute a guard or publish a FASL. The native reference uses no
observation wrappers and compares all 3,168 output code bytes for 26 functions.
This does not compare arbitrary constant objects or perform a full native build.

Verify a retained packet with one new extraction path:

```sh
python3 tests/wasm/native-census/source-closure/verify.py ../ccl-evidence/2026-09-14-source-closure-r1 --work /tmp/ccl-source-census-verify
```

The verifier hashes this packet and its direct sources only, then recomputes both
call worklists and all probe checks. It does not scan the evidence repository or
rehash accepted result envelopes. `finalize.py --help` describes publication of
one packet; original failures and exact raw repetitions are retained. Eight
native diagnostic print previews differ only in printed heap addresses. Every
other field, including the complete IR and emitted code, compares exactly;
both original previews are kept. No source, FASL or code bytes are normalized.

See the [report](../../../../doc/WASM/stage0/source-closure.md) for the remaining
closure obligations and [development record](development.md) for original
failures and the disclosed early interactive-checker retention limitation.
