# Late-Worker shared-state preservation — 14 September 2026

Status: S0-LL13-b [full] executed; reviewed by Claude's forty-sixth audit at `8cb81f6b` without defect; project acceptance
pending. Packet `LATE-WORKER-R1` contains one complete 24-transition scenario,
eleven refused scenarios, nine rejected semantic mutants and ten production
artifact-role omissions. Stage 0 is **39 accepted, eight missing and one
unreviewed of 48**.

## What executes

Four real Node Workers each instantiate the same hand-built kernel module over
one 64 KiB shared Wasm memory. Each has an eight-slot table and private mutable
Wasm globals for its owner, TLS/TCR addresses and stack pointers. The first two
Workers exist before process data, BSS, heap, staging and their private regions
are mutated. The third starts after code publication and another shared-state
mutation. The fourth starts after a further mutation and the third Worker's
private-state update. All earlier instances are inspected again at the end.

The memory starts with a nonzero repeating byte pattern, apart from the two
control words. This exposes accidental clearing of unused space. The kernel
binary exports its emitter-owned region addresses and sizes. The loader reads
them with the unchanged runtime-boundary binary reader, checks bounds, alignment,
minimum sizes and disjoint ownership, and derives the reserved table prefix from
the final element segment. No guessed gap separates the static and private data.
An independent literal layout in the Python oracle checks the resulting map.

The kernel has one passive data segment and no start function. Instance creation
may install the reserved function in that instance's own table, but may not write
linear memory. An explicit exported process initializer uses an atomic claim
before copying data and clearing BSS. A retry from the late Worker returns
without writing. Private setup validates the owner index and claimed base before
writing the four owned regions; guard gaps and other Workers' regions remain
untouched. The supervisor refuses a duplicate live owner before creating a Worker.

The stack and TLS labels describe owned storage and instance pointer globals.
This fixture does not execute a C activation, use compiler-generated C TLS, or
suspend existing Workers inside live Wasm stack frames. Those are distinct from
the shared-memory preservation checked here and the earlier accepted C-boundary
work. No shared compiler or upstream kernel source changed.

## Lazy installation and publication

The first Worker installs a module with one scalar entrypoint. The loader checks
its final bytes, memory import, signature, absence of initialization effects and
slot ownership before installation. The supervisor then writes its digest to
the shared code record and publishes generation one atomically. The existing
peer and both later Workers acquire that record, validate their supplied bytes
and install the function in slot two. Slot zero remains reserved and null;
slot one retains the kernel function in every table.

The lazy function reads current heap memory. Its result changes after subsequent
heap mutations, while the reserved function returns a distinct value. This
checks actual callable table contents rather than relying on declared role
labels. Ready publication occurs only after private setup and any required code
installation. Refused lazy installation in an already-ready Worker leaves the
process's new code generation unpublished.

Module bytes are supplied to each Worker by the fixture; the shared publication
record carries identity and generation, not module bytes. This is one immutable
code generation and an ordered schedule. Simultaneous process initialization,
Worker retirement/reuse, code replacement/reclamation, browser behavior and
production B entry conventions remain outside this slot's demonstrated bounds.

## Independent checks and controls

After each command completes, the supervisor retains the entire shared memory.
The Python oracle constructs the expected image from literal initial bytes,
region effects and case inputs. It checks all 65,536 bytes, including unused
space, and separately checks each reported instance's pointers, readiness,
generation and the values returned through every occupied table slot. Snapshots
are compressed together per scenario; no complete native build is retained or
rerun. The successful scenario covers all 24 transitions.

Eleven invalid scenarios exercise active kernel data, a kernel start/BSS writer,
overlapping and misaligned regions, undersized TLS, duplicate owners, wrong
binary identity, a foreign private base, lazy data/start effects and a reserved
slot. Every refusal leaves the memory at that step unchanged and withholds the
corresponding ready or code publication. Faulty modules have fresh matching
manifests, except for the intentionally wrong-digest case, so those checks do not
pass merely by detecting a stale hash.

Nine separately retained implementation mutations remove active/start checks,
remove the process-once guard, initialize another Worker's region, overrun or
omit TLS clearing, omit late code installation, allow a lazy start writer, or
ignore the reserved-slot check. The unchanged oracle detects the actual clobber
or missing/wrong callable entry at its named first failing transition. The
active/start mutations therefore also witness what the engine really writes
when the preflight prohibition is bypassed.

The first producer attempt reached the last mutant but was refused by the
occupied-slot safeguard: removing the reservation check alone did not permit
replacing the live function in slot one. The corrected control uses reserved
slot zero, which is empty, isolating the reservation guard. The original run,
case outputs and exact sources are retained in the development archive. The
loader, Wasm modules and oracle were unchanged; only that control's slot changed.

The second producer passes. A fresh verifier rebuilds and re-executes every
scenario, reproducing 289 deterministic files byte for byte. Eleven direct
source pins and all new artifact identities check. The unchanged production
gate refuses each of ten required-role omissions on the genuine envelope and
reports only `unreviewed S0-LL13-b [full]` for the complete slot. Only LL13-b's
runner registration changes its contract digest; all 39 accepted bindings remain
current. The live ledger checker passes at 39/8/1 without rescanning historical
accepted payloads.

Next under the alternating plan is the census: finish the remaining startup
boundary replacements and generalize traversal beyond the image-restore file.
