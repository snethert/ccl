# Kernel-import census v1

Status: generated deliverable of the D6 kernel-import census, executed by
Claude on 15 September 2026 as a diagnostic and awaiting Codex's review; no
inventory slot and no gate credit. The machine-readable census is
[kernel-imports.v1.json](kernel-imports.v1.json). Regenerate it with
`python3 tests/wasm/stage0/kernel-imports/run.py --generate`; the producer
refuses when the committed file differs from the regeneration.

## Derivation

The C table is the `defimport` list in `lisp-kernel/imports.s` and the Lisp
table is the `KERNEL-IMPORT-` enumeration in
`compiler/X86/X8632/x8632-arch.lisp`; both are pinned to their U1 blobs. The
two tables are joined by index, each pair's offset is checked, and each
pair's spellings must name the same entry after the `lisp_` and `x`
prefixes and three explicit aliases are accounted for. Every Lisp source
line under level-0, level-1, lib, library and compiler that names a
`kernel-import-` constant is recorded with its form (`ff-call`,
`int-errno-ffcall`, `%kernel-import`, comment) and whether it applies to
x8632; PPC, ARM and x8664 files do not. Every C or assembly definition in
`lisp-kernel` is located and C call sites are counted. D6's rule stands: this
is source inspection; the evaluated compiler census resolves target
conditionals and reachability.

## Ledger

`tests/wasm/stage0/kernel-imports/dispositions.json` gives each of the 65
imports its D6 group, one disposition per profile from the D6 vocabulary
(Wasm runtime, JavaScript host service, atomics/memory implementation,
explicitly unsupported), a closure phase (loader, definitions, runtime or
none), a replacement, the regression obligations it continues under, and
the expected number of Lisp caller sites, which the scan must reproduce.
Building the census fails on any missing entry, so the ledger is closed.

| Profile | Wasm runtime | Host service | Atomics | Unsupported |
| --- | --- | --- | --- | --- |
| Full | 10 | 24 | 15 | 16 |
| Single-thread JSPI | 6 | 26 | 10 | 23 |
| Precompiled callback | 6 | 6 | 10 | 43 |

Forty-two imports have x8632 Lisp callers over 63 sites; 57 are required in
the bootstrap closure (they have callers or a closure phase), 10 in the
loader phase, 3 in the definitions phase and 36 at runtime. Notable rows:

- The read-only file namespace (open, read, lseek, close, fstat, stat,
  lstat, opendir, readdir, closedir, realpath) is a host service in the full
  and JSPI profiles; write is a host output sink for console and diagnostic
  streams, and fchmod, ftruncate and pipe are unsupported until the Stage 3
  writable store.
- Semaphores, recursive locks, rwlocks and the futex are atomics on owned
  words in the full profile. Locks keep their owner and count semantics in
  the single-thread profiles, where a contended wait cannot occur; the futex
  and the semaphore wait are unsupported where memory is unshared.
- Thread creation and disposal are host services in the full profile and
  unsupported in the single-thread profiles; suspend and resume are replaced
  by the D5 admission and rendezvous protocol, which the four C-side entries
  never reach from Lisp by name.
- Shared-library loading, symbol lookup, the dynamic-linker debug structure,
  the JVM entry and native symbolication are unsupported. The six
  `GetSharedLibrary` and four `FindSymbol` call sites in `l0-cfm-support`
  are reached from shared-library revival at startup, so the evaluated
  closure must route those callers through this unsupported disposition
  explicitly rather than lose them.
- The FP-context and vector-register entries are assembly-defined with no
  Lisp caller and are unsupported; the D6 floating-point policy specifies
  explicit checks instead. `lisp_egc_control` returns EGC unavailable.

## Census nodes

`census_nodes` carries one node per import in the shape of
[census.schema.json](census.schema.json): id `import:<c name>`, kind
`import`, disposition `replaced` or `unsupported`, `required` when the
import has x8632 callers or a closure phase, the replacement as
implementation, this contract as evidence, and S0-LL15-b/c as tests. The
working development graph currently carries one unresolved placeholder,
`gap:imports`; these nodes are its content, and joining them to the
evaluated callers is census work under S0-LL15-b.
