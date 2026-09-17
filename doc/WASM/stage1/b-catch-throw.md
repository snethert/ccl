# Generated nonlocal exits — 16 September 2026

The [isolated proposal](../../../tests/wasm/stage1/b-catch-throw/README.md)
adds CATCH/THROW through CCL's real front end and publishes catch/cleanup records
in the production TCR's handler checkpoint. The user accepted this auxiliary unit after Claude’s seventy-fifth audit;
the backend and loader files are integrated byte-identically. No LL05 or LL19
slot is claimed.

A tag is evaluated before the catch is established. THROW evaluates its tag and
all values, searches for the nearest live EQ tag, stores values in that catch's
rooted buffer and raises a distinct shared Wasm exception carrying the target
record address. The target remains live while intervening cleanup runs. Cleanup
can replace the exit, handle a nested throw without losing pending values, or
propagate another checked failure. Missing catch is a checked CONTROL refusal;
constructing and signalling Lisp condition objects remains separate work.

Catch and cleanup extents each reserve `align16(48 + 4*capacity)` bytes. Their
records carry the previous control head, kind, capacity, count, root location,
saved unwind state and a version marker. The tag and values are tagged roots.
The TCR unwind state distinguishes ordinary execution, nonlocal transfer and
other exceptions; nested handled exits restore the enclosing state. Public
entries restore the host's original head/state. Compiled calls retain the direct
continuation path and never enter the public wrapper. Tail transfer remains
legal inside called functions, but cannot discard an active catch or cleanup.

The corpus has 350 modules and 1,110 native/model cases, producing 4,440 target
comparisons over low and above-2-GiB placements. Cases cover identity and nearest
matching tags, zero and 130 values, cross-module FUNCALL/APPLY, defaults,
closures, local functions, escaped tags, retired catches, cleanup replacement,
and recursive calls. At calls, a general observer walks live control records
against the actual root chain. It performs 19,280 control inspections; separate
Lisp effect probes check 18 unwind states and 22 injected corrupt/missing-chain
cases exercise the generated validator. The inherited cleanup observer checks
150 cleanup entries and remains specialised to the named cleanup helper.

The loader extension requires a distinct owner-supplied `nonlocal_exit` tag and
the new module profile. The binary reader accepts exnref in internal signatures;
imports and public export roles remain exact. Nine focused refusals and four
loader mutants cover capability identity, profile and binary/manifest joins.
Cold loading reproduces all corpus comparisons and 36 long tail chains, with
4,804 installations per observation mode. Installation remains within one Worker
against a trusted catalog, without a code-signing claim.

Eighteen compiler mutants reject illegal tail transfer, lost values or target
identity, omitted publication/retirement, wrong unwind state, tag matching and
control-chain validation, plus regressions in the direct call path. Three
exploratory omissions remain uncounted: two restorations are overwritten before
any call/poll, and a header-bound omission is still refused by later guards.
Their original runs are retained, with collector-time inspection left open.

Fresh native R6/R6a passes: 162 unchanged FASLs, two explained registration
artifacts, all 164 restored, 21,843 native tests, five architecture tables and 17
existing-target module profiles. The pristine baseline is reused. The final
producer and retained verifier pass, including byte-identical recompilation of
the positive corpus and all 18 mutant compilers, first-failure reproduction,
the two inherited regression controls and the loader composition.

No safepoint or collection is introduced. Exception-reference roots, transient
locals, stack-temporary callables and inspection during restoration remain
collector obligations. The records do not yet implement debugger frames, special
binding, separate control-stack bounds or condition-handler dispatch. Local
RETURN-FROM also remains open. Engine traps cannot provide Lisp cleanup semantics.

Packet: `ccl-evidence/2026-09-16-stage1-b-catch-throw-r1`.

The audit also carries a host-re-entry obligation: a nonlocal exit crossing a
public wrapper currently restores its incoming unwind state. Generated code
cannot re-enter the host today; settle in-flight state before adding that path.
The exit classifier rethrows once, a cost for later measurement.
