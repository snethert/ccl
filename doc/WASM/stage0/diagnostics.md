# Structured Wasm diagnostics — 14 September 2026

Status: executed, awaiting independent review and user acceptance as
S0-LL23-a/full. The fixture uses actual Node/V8 Wasm traps and retains each
binary, interface schema, build manifest and decoded instruction map.

A trap is attributed using the engine's Wasm function index and exact binary
instruction offset. An independent WABT disassembly oracle checks that location
against the expected failing operation. The diagnostic carries the manifest and
binary digests, logical code ID, entry kind, signature, table slot and operation.
The last observer event remains explicitly `CONTEXT_ONLY`: the nested fault
cases deliberately retain an event naming the outer function while the actual
fault is in the leaf.

The two hand-built modules have the same interface and distinct executable
bytes. A small decoder reads the entire supported module shape: types, imports,
function signatures, table/memory bounds, exports, element slots and every code
instruction. It checks the ABI against the decoded signatures and slots. A
retained map must equal that decoding and carry its own manifest-bound digest.
The decoder refuses unsupported shapes; it is not a general Wasm decoder.

| Execution | Required observation |
| --- | --- |
| Normal calls in both builds | Distinct expected return values, no diagnostics |
| Unreachable, memory bounds and divide-by-zero traps through nested calls | Leaf instruction and actual caller frames identified |
| Indirect-call signature and table-bounds traps | Fault is the dispatcher's `call_indirect`, not the unentered target |
| Same fault in the second build | Second manifest/binary identity retained |
| Three successive failures | First failure preserved, all three captured |
| Twenty-five failures | Three diagnostic details retained, 22 counted as dropped; first failure preserved |
| Host import error, unavailable stack, unreadable top frame | No inferred Wasm fault attribution; bounded message and context retained |

There are thirteen execution cases, two normal returns and 37 observed Wasm or
host failures. Three further cases reject a stale binary, a stale map whose
manifest hash was updated, and an ABI signature inconsistent with the binary,
all before instantiation. Twelve one-line reporter mutants are rejected by the
same oracle, covering build and frame identities, operation attribution, first
failure, output bounds and invented attribution when the top frame is unknown.

The reporting surface retains at most three errors, four mapped frames per
error and 160 message characters, under an 8,192-byte JSON budget. The fixture
also retains raw exception observations separately as test evidence; those raw
captures are not the bounded diagnostic interface.

## Production artifact policy

The real result declares all four global artifact roles plus source, ABI,
template, installed binary, host compiler and options. The compiler artifact
records the actual WABT executable digest and version; options identify the
arguments actually used in each bundle directory. Original source, instantiated
binary bytes and interface data are separate retained artifacts.

Ten additional controls remove each required role from this genuine execution
envelope. The production gate refuses every omission with the exact missing-role
diagnostic while leaving the record's execution and review labels unchanged.
This exercises the [new role policy](artifact-policy.md) with real artifacts,
separately from the earlier synthetic mechanism control.

## Scope and reproduction

This is a small scalar diagnostic ABI. Its entry labels and signatures are
explicit fixture metadata, not qualification of CCL's selected B protocol or a
production debugger. It uses one module per invocation on the recorded Node/V8
engine. Browser stack formats, mixed-module/Worker stacks, optimization-tier
coverage, GC and asynchronous failures remain open. Unknown top-frame formats
refuse attribution; they do not borrow a caller or observer identity. S0-LL23-b's
accepted logical-frame and moving-root evidence remains separate and unchanged.

Run from the repository root with an unused output directory:

```sh
python3 tests/wasm/stage0/diagnostics/run.py --output /private/tmp/ccl-diagnostics
python3 tests/wasm/stage0/diagnostics/run.py --verify /private/tmp/ccl-diagnostics
```

The verifier rebuilds and executes both binaries, compares every deterministic
execution output, rechecks the independent disassembly oracle and runs the
production-role omissions without overwriting retained files. No shared compiler
or upstream kernel source changes.

Development found one actual reporting defect. The first parser skipped an
unreadable top-frame line and could attribute the trap to its readable caller.
The retained counterexample uses a real memory-bounds trap with only the first
stack frame obscured. It fails `NO_FALSE_ATTRIBUTION` with the old reporter.
The corrected parser stops at the unreadable first frame; a retained mutant
restores the faulty behavior and is rejected. Original first-run sources,
binaries and observations remain in the compact development archive.

This deliverable leaves Stage 0 at **35 accepted, twelve missing and one
unreviewed required slot out of 48**. LL24 is the next authorized deliverable.
