# Initializer binding — 15 September 2026

Status: S0-LL15-a [full] EXECUTED and PASSING at its stated scope; awaiting
Codex's adversarial review under the 15 September role switch, then the
user's acceptance decision. Packet `INITIALIZER-BINDING-R1` in the evidence
repository. Stage 0 is **40 accepted, two missing and six unreviewed of
48**; the two missing slots are the census's LL15-b and LL15-c.

Authorship: Claude Fable 5.1 wrote this fixture on branch `wasm2-claude`;
Codex reviews it. No shared compiler or upstream kernel source changed. The
accepted S0-LL01-a control covers failing initializers and diagnostic
continuation; this slot covers the binding of initializers to prerequisite
state and completion, the seeding of the loader's own dependencies, omitted
required modules and the no-load path.

## What executes

`closure.json` declares a hand-built bootstrap closure: three phases, four
wasm32 modules and nine required initializers, each with its module, phase,
prerequisites, required service state and completion value. Phase 0 is the
loader's own dependencies: `loader-core` owns the event log, the completion
ledger in memory and the code-installation service, and every bundle
imports its `note`, `complete` and `completed` services, so no bundle can be
instantiated before it exists. Phase 1 installs definitions while the error
service stays in its early mode; phase 2 activates the ordinary error
service only after the compiler stubs exist and then finalizes.

The loader validates the manifest against the supplied modules before it
instantiates anything: unknown prerequisites, cycles, forward phase
dependencies, loader dependencies outside phase 0, bundles inside phase 0,
deferred modules that an initializer needs, omitted modules, import
mismatches and missing initializer exports are all refused with a named
reason and no initializer runs. It then instantiates the loader module,
runs the phase-0 initializers, instantiates the bundles, and runs the rest
in a topological order within each phase. Before each initializer it reads
every prerequisite's completion word from memory and every required state
word, and after the call it requires the returned code, the completion word
and the execution counter to agree with the manifest. Ready is written to
memory only after a final pass over every completion word.

Each initializer also checks its own prerequisites physically and refuses
with a distinct event when they are absent, so the loader's binding and the
module's binding are independent witnesses. The complete bootstrap publishes
generation 1 with nine completions and checksum 16459; the memory image
carries the region table, canonical NIL and T at their schema addresses, the
symbol, reader, handler and stub tables, the mode transition from early to
full and the finalization summary.

## Controls

Fourteen refusals, each named and each before dependents run: an omitted
required module, a missing initializer export, an import mismatch, a
deferred required module, an unknown prerequisite, a cycle (naming only the
cycle members, not the initializers it blocks), a forward phase dependency,
an unseeded loader dependency, a bundle in the loader phase, a wrong
completion value, a completion returned but not written, an initializer that
raises after a partial write, a completion word clobbered by a later
initializer, and a required service state that does not hold.

Eight loader mutants are rejected by the unchanged oracle, which
reconstructs every case's whole two-page memory image from the manifest and
compares it byte for byte. The no-load path fakes every completion and
state check and still publishes ready; the oracle catches it because the
services, tables and canonical objects were never written. The other seven
omit the prerequisite check, load bundles before seeding the loader, trust
returned codes without the physical completion, publish ready before the
definitions run, omit the module-omission check, omit the export check, or
drop the loader-phase rule; each is caught at its named first check, three
of them because a control that must be refused early instead runs, crashes
or is refused later for a different reason. Ten production artifact-role
omissions are refused; the slot gate otherwise reports only
`unreviewed S0-LL15-a [full]`.

## Evidence and reproduction

The packet holds 847 files (5.9 MB): the complete bundle with the loader,
manifest, interface, sources, binaries and disassemblies, the seven control
manifests and six control modules, fifteen case observations with their
compressed memory snapshots, eight mutant bundles with all of their cases,
the bound envelope, slot-gate and role-omission records. The verifier
re-executes everything and compared 812 deterministic files byte for byte
in a few seconds.

Limits. This closure is a hand-built model of the bootstrap phases the
design review proposes; the qualified census closure, its seeds and its
initializer ranks are S0-LL15-b/c. There is no image, no cross-loader, no
lazy installation, no collector and no Worker; the production loader will
bind the census's initializers with the same discipline through generated
code in Stage 1.


Project acceptance recorded 16 September 2026 after Codex review `81345b28`
and the user's conditional approval. See [acceptance scope](project-acceptance.md).
Original execution envelopes remain unchanged.
