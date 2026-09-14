# Static source-coverage analysis — 14 September 2026

Status: **executed analysis, not evidence of execution.** No gate credit, no
`S0-*` obligation discharged, no acceptance claimed or implied. Authored by
Claude; under the [standing rules](../../../CLAUDE.md) it requires adversarial
review from a different model or provider before any use beyond planning.

This answers a question asked of the Stage 0 work: how confident can we be that
the census process is catching every corner case? It measures the denominator
the census is working against, and separates the corner-case families the
existing obligations already name from those that appear to have no obligation
assigned.

No native build, image or shared-source patch is involved. The
[tool](../../../tests/wasm/native-census/source-coverage/README.md) opens
pristine U1 source read-only and emits
[`evidence/source-coverage-summary.json`](../evidence/source-coverage-summary.json).

Input identity: baseline `c994217adc56b3f8a564526cee4695893ac84d86`, analysed at
head `9285ee40`, corpus digest
`2a643250b2732968b1542d8616bede67f57417e39143f782bb6d0136c182b86a`.
25 controls pass, two runs identical.

## The denominator

Top-level forms, counted by a strict lexer that reproduces the reviewed first
traversal's published count for `lib/dumplisp.lisp` exactly.

| Bucket | Files | Top-level forms |
| --- | ---: | ---: |
| All analysed `.lisp` source | 287 | 19,473 |
| Not marked for another target by path | 206 | 13,794 |
| Of those, reachable in a cold boot (excludes `REQUIRE`-only `tools/`) | **201** | **13,149** |

Cold-slice forms by subtree: `compiler` 3,492, `level-1` 3,947, `lib` 2,984,
`library` 1,427, `level-0` 906, `xdump` 393.

Against that, [`source-traversal.md`](source-traversal.md) reports the reviewed
first driver accounting for **16 top-level forms in one file** — 0.12% of
cold-slice forms, 0.5% of files. The follow-on
[description](target-descriptions.md), [macro](target-macros.md),
[expander](source-expanders.md), [helper](target-helpers.md) and
[type](target-types.md) slices extend the target environment rather than the
form inventory.

This is not a criticism of pace; the slices are doing the hard part. It sizes
what "complete source traversal" in [`plan.md`](plan.md) step 2 actually means,
and it says the current stop rate is the signal to extrapolate from: 8 of 12
definitions in the *first* file stopped at a target gap, and the driver reports
only the first error per definition, so that gap list is explicitly a lower
bound on one file.

## What a single observation run cannot read

The census reads source through one reader, with one feature set, on one host.

| Reader-conditional sites, cold slice | Count |
| --- | ---: |
| Branch read under darwinx8664 | 818 |
| Branch **not** read | **1,045** |
| Compound `#+(and ...)`, not evaluated by this tool | 135 |

Largest unread families: `#+32-bit-target` 199, `#+windows-target` 172,
`#+arm-target` 102, `#+big-endian-target` 84, `#+x8632-target` 66,
`#+ppc-target` 64, `#+linux-target` 19, `#+futex` 16, `#+solaris-target` 14.

Two consequences are specific to this port rather than generic:

1. A `wasm-target` feature produces a branch selection **no existing CCL
   configuration has ever read**. The census node set is derived from a run in
   which those branches were absent from the text the reader consumed.
2. A small set of branches is live for a non-x86, non-Darwin target and dark to
   every run in the evidence chain — `#-x86-target`, `#-x8664-target`,
   `#-darwin-target`. Two of them are in `lib/nfcomp.lisp` (`:1141`, `:1765`),
   one of the three files the accepted r5 instrumentation patches.

I did not find this family named in [`contracts/census.md`](../contracts/census.md),
which addresses conditional *loads*, `REQUIRE` and trace-only files, but not
read-time branch selection. That is the one gap here with no obligation
attached to it.

## Construct families, cold slice

Counts are regex matches over source text — families to investigate, not
resolved edges. `contracts/census.md` is explicit that LL15-b accepts the joined
instrumented graph and not source regex counts; nothing below is offered as a
substitute for it.

| Family | Sites | Why a single run under-determines it |
| --- | ---: | --- |
| `target::` symbol references | 1,829 | every one is a layout/ABI constant that must be re-derived, not inherited from the host |
| `defmethod` / `defgeneric` | 1,062 / 31 | applicable-method sets are computed at runtime; the census records only invoked methods |
| `#.` read-time eval | 804 | the FASL records the *result*; the dependency on the evaluator, and on whether it ran with host or target semantics, is absent from the artifact the census joins against |
| `macptr` | 606 | foreign pointer representation with no engine analogue |
| `REQUIRE` | 586 | modules compiled into the tree but not loaded by a cold boot |
| `eval` / `compile` call sites | 289 / 61 | runtime code construction, unresolvable statically |
| `ff-call` / `external-call` / `defcallback` | 167 / 30 / 12 | no `dyld` in the engine |
| `deffaslop` / `defxloadfaslop` | 70 / 64 | loader dispatch indexed by a byte from a file: a sound candidate set is every opcode, not the subset the observed 164 FASLs happened to contain |
| `define-condition` / `unwind-protect` / `no-applicable-method` | 106 / 114 / 33 | error and non-local-exit paths a successful boot does not take |
| `without-interrupts` / `%current-tcr` / `%stack-block` | 108 / 54 / 84 | native machine and thread state |
| `intern` / `find-symbol` / `symbol-function` / `fdefinition` | 71 / 55 / 40 / 49 | computed names |
| `load-time-value` / `make-load-form` | 54 / 52 | load-phase evaluation ordering |
| `set-(dispatch-)macro-character` | 42 | read-time behaviour that changes what later forms *are* |
| `defloadvar` / `def-ccl-pointers` | 37 / 9 | save/restore lifecycle, not the boot lifecycle |

Outside all of it: the C kernel, 120 files and roughly 75,700 lines, including
156 `_spentry` subprimitive entries (plus five `_startfn`) in `x86-spentry64.s`. The census enumerates the
Lisp side's view of that boundary (222 opcode identities, 17 UUO names); the
kernel's own behaviour is covered, where it is covered, by the separate
hand-built [runtime-boundary](../../../tests/wasm/stage0/runtime-boundary/README.md)
and [integrated-runtime](integrated-runtime.md) fixtures, and
[`STATUS.md`](../STATUS.md) already records the engine matrix as INCOMPLETE.

## Two methodological limits

These are not coverage gaps and would not close by traversing more source.

**Closure is currently non-discriminating.**
[`startup-seed-revision.md`](startup-seed-revision.md) reports 329,036 reachable
nodes and **0 of 13 seeds whose individual omission changes reachability**;
removing all 208 membership edges still leaves 9 of 13 non-discriminating. A
fixed point that cannot detect a wrong seed set cannot detect a missing corner
case either. The document states this and declines to narrow the graph before
the replacements exist, which is the right call — but it means closure is
supplying no falsification today, and the gate result should not be read as if
it were.

**The omission mutants test the consumer, not the producer.**
[`contracts/census.md`](../contracts/census.md) says it directly: the checker
"does not prove that compiler instrumentation discovered every edge." The 23
controls in [`joined-census.md`](joined-census.md) are mutations injected into a
graph the producer already built. If the producer never discovered an edge, no
mutant can remove it. The retained-independent-expectation design mitigates
this; it does not close it, and LL15-c's requirement that the *complete
instrumentation and gate path* reject the mutants is the part still outstanding.

A third point is empirical rather than methodological: the harness perturbs what
it measures, twice demonstrably. [`rich-census.md`](rich-census.md) records an
added helper `DEFUN` consuming three compiler gensyms and shifting downstream
generated names, and the logger's own helpers (`%LFUN-INFO-INDEX`, then
`STRING-DOWNCASE`) being redefined mid-build into an unbound interval. Both were
caught by FASL byte comparison under R6, not by census design. Identical-FASL
counts vary across runs (156, 161, 163 of 164). R6 is doing more of the
corner-case detection than the census is.

## Assessment

Framed as three separate questions, because they have different answers.

| Question | Assessment |
| --- | --- |
| Will the framework catch a corner case once the construct enters the traversal? | **High confidence.** The controls, mutants, R6 comparisons, refusal to widen, and the consistent "no gate credit" / "collection gap, not a disposition" discipline are unusually rigorous for this stage. |
| Has the present evidence *enumerated* the corner cases? | **Low confidence.** 0.12% source traversal, 1,045 unread branches, 804 unresolved read-time evals, 1,729 acknowledged unqualified dynamic calls. |
| Would closure, as currently widened, *flag* a missing one? | **Near zero**, by the project's own reachability diagnostic. |

The most useful observation for scheduling: the two most recent slices
([`target-helpers.md`](target-helpers.md), [`target-types.md`](target-types.md))
both found real defects — inherited host-width assumptions in `EQL`, unsafe `EQ`
for declared boxed integers — and both found them with **targeted probes, not
with the graph**. Probe-driven discovery is currently outperforming
graph-driven discovery. That argues for continuing to fund the probe slices,
and for treating the joined graph as an accounting structure rather than as the
instrument expected to surface the next defect.

The single unassigned item is the reader-conditional family: 1,045 unread
branch sites, a target whose branch selection has never been read by anyone,
and no obligation covering it. Everything else above is already visible in
`STATUS.md` or the contract as open work.

## Limits of this analysis

Surface counts over source text. The lexer is not a reader: it does not expand
macros, evaluate `#.`, select branches or resolve packages, so a top-level
macro form counts as one form however many definitions it produces — every form
count here is a **lower bound**. Compound reader conditionals are not evaluated.
The assumed feature set is an approximation, not a captured `*features*`. Target
exclusion is by path marker and conservative. Regex construct counts are not
resolved call sites. Controls and limits are enumerated in the
[tool README](../../../tests/wasm/native-census/source-coverage/README.md).
