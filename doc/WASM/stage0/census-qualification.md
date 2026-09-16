# LL15-b/c — on-demand census instrument qualification

Execution: PASS; Claude review and project acceptance pending. Packet
`CENSUS-INSTRUMENT-R1`. All 33 capture checks, 20 native cases, 42 publication
rejection controls and 16 production artifact-role omissions pass.

This qualifies the instrument under [census contract v0.2](../contracts/census.md).
It does not qualify an exhaustive native or Wasm bootstrap closure. The two
native records require Claude's independent review and project acceptance.

One [runner](../../../tests/wasm/native-census/qualification/README.md) combines
fixed reviewed inputs with fresh capture queries and private native call-site
observation. The retained 167-unit compilation, native rebuild and R6 recovery
are reused; no new full CCL build is claimed. The native probe starts from a
fresh disposable U1 archive and pristine bootstrap image. Shared source and
FASLs remain unchanged.

The publication contains the complete 16,169-node, 36,848-edge startup worklist
and all 32 roots. The seed recipe and same-execution seed links are checked.
Its call records are partitioned without promoting observations to bounds:

| Population | Sites | Meaning |
| --- | ---: | --- |
| Proven native IR targets | 395 | Self, lexical and lexical-function-value calls with known local targets; target implementation remains separate. |
| Known symbol designators | 13,641 | Initial values are witnessed; future binding values remain unbounded. |
| Builtin calls | 561 | Seven distinct lowering obligations remain unqualified. |
| Unresolved computed calls | 614 | 326 variable callees and 288 computed expressions remain unresolved. |

Other retained unknowns are 272 missing bodies, 2,859 binding-value obligations,
394 future registry-state obligations and 415 runtime-transfer obligations.
All 7,403 unresolved nodes retain their full reasons and dispositions. Native
`implemented` nodes and `complete` reference edges do not claim target
implementation or exhaustive callable bounds.

The complete initializer and operator/lowering joins remain pinned inputs.
The publication also carries the actual 70-record cold-process boundary chain,
with its observed order and original completion assertions. It does not join
that separate execution to the startup snapshot by name or invent a complete
bootstrap prerequisite graph. The external trace, its original raw files and
the reviewed loader-context reconciliation are pinned separately. Remaining
lifecycle, initializer-effect and target/profile obligations stay explicit.

The checker takes its expectations from fixed reviewed artifacts in
`qualification/inputs.json`, independently of candidate hashes or summaries.
Publication controls remove seeds, nodes, edges, inputs, known bounds and
unknowns; substitute identities; introduce invalid initializer prerequisites;
promote observations to bounds; and falsify native witness scope or behavior.
Each content mutation is written through the real file interface with a newly
matching manifest hash before checking. Removing evidence cannot pass merely
by regenerating its summary or hash.

The existing 33 capture checks compare query answers with original native events.
The 20 native cases check literal values and effects, argument evaluation order,
late symbol redefinition, closure calls, nonlocal exits, restoration, missing
sites, unreached scenarios and truncation. Four actual native observer mutants
omit events/instrumentation, discard values or swallow a nonlocal exit. The
publication additionally compares complete native witness records with their
reviewed reference observations. A negative answer remains a negative answer.

The unchanged complete-closure checker must still return BLOCKED on this graph.
The two new HOST COMPILATION/native records can pass instrument qualification
while LL15's later implementation worklist remains open. Image and host-compiler
artifacts identify the actual executed pristine image/kernel and retained input
archives; they avoid copying the existing bootstrap again. Derived SQLite
caches are disposable, never retained as qualifying evidence.

Reproduce from the repository root:

```sh
python3 tests/wasm/native-census/qualification/run.py \
  --evidence ../ccl-evidence --output /new/qualification --work /new/native-work
python3 tests/wasm/native-census/qualification/run.py \
  --evidence ../ccl-evidence --verify /path/to/retained/qualification
```

Verification checks source/artifact identities, builds a fresh query index,
executes the native scenarios and all publication controls again, and compares
the publication bytes and deterministic assessments. It does not rescan the
historical evidence catalog or repeat the full native rebuild.
