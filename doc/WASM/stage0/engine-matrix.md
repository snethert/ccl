# Engine and profile matrix — 15 September 2026

Status: S0-ENGINE-a [complete-report] EXECUTED and PASSING at its stated
scope; awaiting Codex's adversarial review under the 15 September role switch,
then the user's acceptance decision. Packet `ENGINE-MATRIX-R1` in the evidence
repository. Stage 0 is **40 accepted, two missing and six unreviewed of 48** after the later executions.

Authorship: Claude Fable 5.1 wrote this fixture on branch `wasm2-claude`. The
user directed on 15 September that Claude author the non-census Stage 0 slots
while Codex continues the census and reviews this work. No shared compiler or
upstream kernel source changed; the fixture lives under `tests/wasm`.

## What executes

One hand-built wasm32 module, `features.wat`, carries every required feature:
multivalue function and block results, `return_call` and
`return_call_indirect` chains of depth 10,000,000, final exception handling
with `try_table`, `catch`, `catch_ref`, `catch_all`, `catch_all_ref`, `throw`
and `throw_ref`, a passive data segment with `memory.init`, `memory.copy`,
`memory.fill` and `data.drop`, and `i32` atomic read-modify-write,
compare-exchange, load, store, `memory.atomic.wait32` and
`memory.atomic.notify`. It is assembled twice: as the canonical unshared
template and as the shared variant that differs only in the memory flag. A
second module, `suspend.wat`, calls a suspending host import from nested
frames with a live local, twice per entry and once under a tail-called frame.

The same driver, `matrix.mjs`, runs under Node/V8 and inside each browser
page. Per engine it records the API surface, `WebAssembly.validate` results
for six one-feature probes plus two informational probes and one deliberately
invalid binary, the executed feature semantics, and the three profiles:

| Profile | What is exercised |
| --- | --- |
| Full | Shared memory with explicit maximum; a real Worker blocks in `memory.atomic.wait32`; the supervisor writes the mailbox and `Atomics.notify` reports exactly one waiter woken; wake code 0, timed-out code 2 and not-equal code 1 observed in the same Worker; growth keeps the old `SharedArrayBuffer` at its old length. |
| Single-thread JSPI | `WebAssembly.Suspending` wraps the import and `WebAssembly.promising` wraps the export; three suspensions return 105 and 50 with the live local intact; the export called outside `promising` fails with the engine's suspend error. |
| Precompiled callback | Unshared memory: atomic RMW, compare-exchange, load and store succeed; `memory.atomic.wait32` traps with `RuntimeError`; growth detaches the old buffer. |

Browsers load the page from a loopback HTTP server twice: once with COOP and
COEP headers and once without. The plain page must report
`crossOriginIsolated` false and the full profile unavailable, which is the
hosting constraint the outline records for the full profile.

## Matrix

| Engine | Version | Full | Single-thread JSPI | Precompiled callback | Legacy EH validates | memory64 validates |
| --- | --- | --- | --- | --- | --- | --- |
| Node/V8 (reference) | v25.6.1 / V8 14.1.146.11-node.19 | admitted | admitted | admitted | yes | yes |
| Chrome (headless) | 153.0.8010.36 | admitted when isolated | admitted | admitted | yes | yes |
| Firefox (headless) | 147.0.4 | admitted when isolated | not admitted: `WebAssembly.Suspending` absent | admitted | yes | yes |
| Safari | 26.3 | admitted when isolated | not admitted: `WebAssembly.Suspending` absent | admitted | yes | no |

All four engines execute every required feature identically: ordered
multivalue results, both tail-call chains at full depth, the nested exception
payload with one recorded passage through the rethrowing frame, `catch_all`
selecting the untagged exception, a Wasm exception reaching JavaScript with
its tag and payload, a JavaScript error caught by `catch_all` and rethrown as
the same object, and the bulk-memory region byte for byte with `memory.init`
trapping after `data.drop`. The invalid binary validates false everywhere, so
detection is discriminating. The seven matrix rows are in `matrix.json`.

## Encoding pin and JSPI API shape

Every emitted binary is disassembled with `wasm-objdump`. The pin refuses any
binary containing a legacy `try`, `catch`, `catch_all`, `delegate` or
`rethrow` mnemonic and requires `try_table` in the feature modules. All four
engines still validate the legacy encoding, so the pin is a project policy
enforced on emitted bytes, not an engine limitation. The prohibited probe is
retained only as the refused case. The JSPI shape recorded is the standardized
`Suspending`/`promising` pair; the historical Node 22 / V8 12.4 probe results
are superseded by this matrix.

## Controls

Seven mutants of the modules or driver execute on the reference engine, and
the unchanged oracle names the first failing check for each: a direct tail
call replaced by an ordinary call (`TAIL direct`), the rethrow omitted
(`EH nested`), multivalue results swapped (`MULTIVALUE pair`), the wait
replaced by an immediate return (`FULL woken`), the bulk copy omitted
(`BULK bytes`), the live local clobbered across suspension (`JSPI run`), and
feature detection short-circuited to true (`DETECTION invalid`). Each mutant
bundle retains its mutation record, binaries and observations. Nine
production artifact-role omissions on the genuine envelope are refused by the
unchanged gate, which otherwise reports only `unreviewed S0-ENGINE-a`.

## Evidence and reproduction

The packet holds 397 files (2.9 MB): the complete bundle with template,
sources, binaries, disassemblies, encoding-pin classification, options and
host-compiler record; seven mutant bundles; per-engine observations for eight
Node executions and six browser pages; the matrix; environment identity with
executable digests for Node, WABT and the three browsers; the bound result
envelope; slot-gate and role-omission records. The verifier re-executes every
engine and compared 361 deterministic files byte for byte; timings are never
recorded. Producer and verifier each take about fifteen seconds.

Limits. Chrome and Firefox run headless; Safari runs through `open` and leaves
its tabs open. The browsers are the versions installed on the reference Mac on
the run date; a browser update changes `environment.json` and the verifier
then refuses with `ENGINE_CHANGED` rather than comparing across versions.
Only Node executes the mutants. Nothing here qualifies CCL object layouts,
generated B code, garbage collection, production packaging or any hosting
deployment; it fixes the engine facts the emitter and the later Stage 0 slots
build on.
