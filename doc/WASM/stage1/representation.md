# Generated cons representation — 16 September 2026

**S1-LL04-a executed; awaiting Claude review and user acceptance.**
The proposed backend remains under `tests/wasm/stage1/representation`.
The integrated 1A compiler and upstream kernel are unchanged.

CCL's real front end now reaches proposed CAR/CDR and RPLACA/RPLACD lowerings.
Each operand is evaluated once, left to right, into its own local. Reads of
NIL return NIL; mutation of NIL refuses. The source grammar remains bounded
and unsupported forms still refuse before front-end folding and at pass 2.

| Evidence | Result |
| --- | --- |
| Generated functions | 19 |
| Native/logical comparisons | 153: 115 returns, 38 type errors |
| Target checks | 740: 612 repetitions of the native cases, 128 additional raw-tag probes |
| Placements | Low, straddling 2 GiB, above 2 GiB, final aligned region of 32,769 pages |
| Compiler mutants | 15 rejected by the unchanged physical/native oracle |
| Genuine-record artifact-role omissions | 12 rejected by the production gate |
| Native suite with the proposed backend loaded | 21,843 passed, 75 upstream-disabled |
| R6 | 162/164 FASLs identical while registered; two exact explained registration changes; 164/164 identical after removal |
| R6a | Five architecture operator tables and seventeen module profiles preserved |
| Retained verifier | PASS; native qualification, recompilation, identical binaries, positive executions and all mutants |

The native baseline is **reused from accepted 1A**, not a newly claimed
baseline run. The registered native suite and removal build are new. The
verifier reuses the full-build reports and runs fresh native-image qualification.
The ABI artifact directly binds the accepted B decision.

The independent Python model and native Lisp use logical `(car, cdr)` pairs.
The target oracle writes literal CDR-first words with unequal payloads and
checks whole resulting graphs, result ownership and guard bytes. It covers
proper/dotted lists, nesting, sharing, cycles, NIL and nested mutation effects,
including value-operand effects before an invalid-pair failure. Fresh instances
must not alter memory. High placements are real loads and stores. The raw-tag
probes exercise all eight tags independently of native Lisp values.

Mutants change the compiler, not expected results: one-sided field swaps,
NIL/type checks, fulltag masking, temporary aliasing, evaluation order, return
identity, store omission, displacement, high-bit truncation, count publication,
exception publication and condition kind. Every mutant is recompiled through
CCL and fails at the same first oracle assertion on replay.

## Scope and remaining obligations

There is no allocation, collection, heap image or general B call protocol in
this slice. Invalid types use an imported Wasm exception tag `(datum, kind)`;
Lisp condition objects, handlers and restarts remain 1C. No poll or call occurs
while the tagged locals are live. Heap-field and result-root stores are
classified in `coverage.json`; collector/barrier work remains mandatory as
those paths enter the implementation. Every generated-access schema row is
checked against literal target probes; unused schema descriptions are not
claimed as exercised. High runs compare the low prefix and graph guard, not
all otherwise untouched bytes of 2 GiB.

Development failures were in the fixture setup: missing native interface
files, an unmatched export-helper parenthesis, a mistyped canonical-T oracle
constant and an overlong end-of-memory guard. Original sources and logs are
retained. The final emitter was unchanged by these corrections.

[Commands and verifier](../../../tests/wasm/stage1/representation/README.md).
Packet: `ccl-evidence/2026-09-16-stage1-representation-r1`. The next slot is
S1-LL07-a: separate generated conversions for fixnums, addresses, code IDs and
typed slots, including the exclusive array-size limit.
