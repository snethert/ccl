# Template materialization — 15 September 2026

Status: S0-LL21-c [shared-template] and [unshared-template] EXECUTED and
PASSING at their stated scope from one execution; awaiting Codex's
adversarial review under the 15 September role switch, then the user's
acceptance decision. Packet `MATERIALIZATION-R1` in the evidence repository.
Stage 0 is **40 accepted, four missing and four unreviewed of 48** after the later executions.

Authorship: Claude Fable 5.1 wrote this fixture on branch `wasm2-claude`;
Codex reviews it. No shared compiler or upstream kernel source changed.

## What executes

`template.wat` is a hand-built Lisp-code stand-in: it imports one unshared
wasm32 memory with explicit limits 1–4 pages and the profile runtime's
`request` function, and exports `entry`, `grow` and `size`. Its `entry`
tail-calls a worker that increments an atomic serial, calls `request` and
returns two values. The materializer inspects the template's own bytes to
find the memory import's flags byte, rejects anything but a single canonical
unshared explicit-maximum `env.memory` import, checks the import and export
inventories against the interface in `abi.json`, and takes the template's
feature requirements from a disassembly classification supplied by the
runner. The manifest records template hash, offset, original byte, limits,
inventories, features and materializer version. Materialization for the full
profile changes exactly the flag byte at offset 41 from 1 to 3; the unshared
profiles keep the template bytes. Each result records profile, patched byte,
limits, inventories, features and the final binary hash; installation checks
that hash and refuses the template hash as a shared binary's identity.

Recorded from the engine on Node/V8:

| Case | Observation |
| --- | --- |
| Byte difference | Length preserved; one differing byte at the recorded offset; unshared and callback binaries identical to the template. |
| Import limits | Matching, larger-minimum and smaller-maximum memories link; a larger maximum, an unbounded memory and a shared-flag mismatch in either direction raise `LinkError`. |
| Growth | Both profiles grow from one page to the four-page maximum, return −1 beyond it, and report four pages and 262,144 bytes. |
| Full profile | A real Worker instantiates the shared runtime and the shared binary; `request` blocks in `memory.atomic.wait32`; the supervisor answers, clears the flag and observes exactly one waiter woken, twice; results (43, 2) then (44, 2). |
| Single-thread JSPI | The unshared binary calls the JSPI runtime whose import is `WebAssembly.Suspending`; two suspensions through `WebAssembly.promising`; the same (43, 2) and (44, 2). |
| Precompiled callback | The unshared binary calls a synchronous runtime; the same (43, 2) and (44, 2). |

The three runtimes are emitted per profile, not materialized: the full
runtime declares shared memory and waits; the two unshared runtimes declare
unshared memory and contain no wait or notify instruction. The runtime check
refuses a runtime carrying a wait path for an unshared profile, a full runtime
without one, and a memory declaration that does not match the profile.

## Controls

Twenty-three refusals, each with its specific reason: wrong offset, wrong
original byte, wrong template hash, a tampered template with an appended
custom section, wrong maximum, import and export inventory mismatches,
feature mismatch, stale materializer version, unknown profile, a profile not
admitted on the target engine (the single-thread JSPI profile on Firefox's
row from the engine matrix), an already-shared template, a defined rather
than imported memory, an unbounded template, a template containing a wait, a
wrong entry signature, a stale binary hash, the template hash offered as an
installed-binary identity, a stale install version, the full runtime offered
to the JSPI profile, an unshared runtime that waits, a synchronous runtime
offered to the full profile, and a shared no-wait runtime offered to an
unshared profile. One execution witness bypasses the runtime check and shows
the unshared wait trapping with `RuntimeError`.

Seven mutants execute on the reference engine and are rejected by the
unchanged oracle at the named first check: hash check omitted (the wrong-hash
control escapes), manifest offset trusted (the wrong-offset control patches
the minimum byte and escapes), import check omitted, feature check omitted,
installation identity check omitted, wait rule omitted, and the template's
increment removed (the full-profile results change). Ten production
artifact-role omissions on the genuine two-variant envelope are refused by
the unchanged gate, which otherwise reports only the two unreviewed variants.

## Evidence and reproduction

The packet holds 408 files (3.9 MB): the complete bundle with template,
runtime and control sources, binaries, section and code disassemblies,
classification, admission rows, interface, options and host-compiler record;
the materialized shared and unshared binaries; seven mutant bundles with
their observations; the bound two-variant envelope; slot-gate and
role-omission records. The verifier re-executes the producer and compared 370
deterministic files byte for byte in about eight seconds.

Limits. This is one hand-built template and three small runtimes on Node/V8;
production module granularity, the D3 entry descriptor, image identity and
browser deployment are Stage 1 and Stage 5 work. Feature classification is
derived from WABT's disassembly and supplied to the materializer by the
runner; the materializer trusts that classification only after checking it
against the manifest. The engine admission rows come from the engine-matrix
contract and are pinned as a source of this fixture.
