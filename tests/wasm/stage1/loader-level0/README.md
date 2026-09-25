# LOADER: SET-PACKAGE and whole-file prefix

Proposed successor to the integrated P2-0 loader (`50cd8ea1`). The original
CCL `SET-PACKAGE` and `FIND-PACKAGE` bodies execute on the target. Fifteen cold
initializers run in their saved order, including two fixture files that switch
to COMMON-LISP and KEYWORD and record the package active during each effect.
Four placement/collection runs match native observations. This is a review
proposal under `files/`, not another product integration or a completed boot.

## Design

The package lookup loop is unchanged. Its native package-list reader lock
remains on every existing target; Wasm uses `PROGN` at that boundary for the
adopted single-Worker profile, with scheduling disabled and no concurrent
package writers. A concurrent profile must supply synchronization there.
The lookup supports canonical names, nicknames, symbol/package designators,
missing-name lookup and dynamically bound `*PACKAGE*` in this witness.
Missing-package restarts and package-local nicknames are not qualified here.

CCL emits an `EQL` call during character comparison. The compiler now handles
identity and comparisons involving a non-miscellaneous D1 value directly.
All D1 numbers requiring a non-identity numeric comparison are boxed misc
objects. Two distinct misc values still call the ordinary `EQL` function;
there is no partial Lisp replacement. This incomplete image lacks that general
function. A directed boxed case reaches its checked refusal, while the full
compiler corpus uses the existing EQL runtime and checks ordinary behavior.
Operand order and single evaluation have a target/native witness.

The whole-file prefix exposed three loader issues before package execution:

* Four earlier class-table definitions duplicated their already-adopted later
  replacements in `w32-prims.lisp`. The compiler returned a FASL **and failure-p**.
  Remove only those earlier definitions; require all four compilation results.
* Code-record v3 carries keyword names as indices into the FASL imported-value
  vector. Cross-loading converts them to module-local symbolic wires. V2 still
  accepts its original empty-key scope. The runtime validates wire types,
  the key flag and wire membership before publication.
* `APPLY`'s `expected_proper_list` import now carries the ordinary CCL type
  specifier `(SATISFIES CCL::PROPER-LIST-P)` as FASL data, alongside FUNCTION.

Larger modules also required a larger objdump output buffer in `loader/d2.mjs`.
The diagnostic owner explicitly provides a larger collector update log; this
does not alter the collector or weaken its capacity checks.

## Evidence and limits

The actual `cross-xload-level-0` entry point is run first, without bypassing its
stop: **`level-0/l0-aprims.lisp`, `:NATIVE-FFI-EXCLUDED`**. Its compiler order
starts in the common directory, although its load order starts in the target
subdirectories. The old independent 12/21 probes were not an ordered build
and did not qualify the compiler's failure-p result.

Separately, the real directory compiler produces the two Wasm level-0 files:
58 and 104 top-level modules, including their nested code in the saved image.
The package witness adds 20 complete original definitions read from seven
source files, plus observation fixtures. This selection is temporary test
scaffolding; it neither rewrites function bodies nor qualifies those seven
whole files. `package-origins.json` and the exact assembled source are retained.
All FASL input source paths are removed before a fresh host cross-load. Generated
support and compatibility sources use logical `CCL:` names, just like the
production inputs, so temporary directory names do not enter their FASLs.

The prefix image has **209 modules**. Each of four fresh target runs executes
all **15 initializers** and **25 native-equal observation rows**. Each collecting
run performs **40 moving collections**, poisoning retired space. Package order,
nickname identity and dynamic binding restoration are checked. Omitting the
initializer calls is caught after starting the target in KEYWORD via Lisp.
The independent keyword image has six modules and eight native-equal rows in
each of four runs: defaults, supplied-p, explicit non-keyword names, duplicate
keys, allowed extra keys, a captured closure, APPLY and v2 compatibility.
Its IN-PACKAGE initializer stays queued because it has no package bootstrap.

Five malformed FASLs are refused with restored host parameters and no output.
Three image refusals preserve memory and both tables; each single-clause
deletion is caught by actual acceptance of its isolated malformed image.
P2-0 is rerun with the proposal: six observations in four runs, 68 image checks,
two FASL-version checks, the keyword mutant and 19 inherited D2 checks pass.

Fresh R6/R6a binds all **43 proposed compiler/CCL sources**: **21,843 native
tests**, 164 FASLs restored, 45 unchanged FASLs and 119 decoded-equal FASLs
under the established gensym bijection. Seventeen existing-target reader
profiles compare the complete prefix through `%FIND-PKG`; the remainder is
identical to the integrated source outside that function. Removing the Wasm
reader guard is caught. The final compiler passes **26,048 fresh comparisons**.
The Git-free replay from another absolute path compares FASLs, heaps, static
areas, code sets, D2 templates/modules and every target observation exactly.

Original failures, intermediate source identities and explicit scope limits
are retained in one evidence packet. The former truncate/FAST-MOD skips become
positive rows after immediate EQL lowering; the original failures remain.
No target-side LOAD, complete BOOT0, general boxed EQL, or full level-0 build
is claimed. Diagnostic whole-file compile/cross-load counts are 2/2; accepted
production counts remain **0/0/0**, originals **575/535**, ledger **21/12**.

## Reproduce

Run from this checkout with the pinned sibling evidence store and macOS tools:

```sh
python3 tests/wasm/stage1/loader-level0/run.py /private/tmp/ccl-work/codex/loader-level0/run
python3 tests/wasm/stage1/loader-level0/exercise.py /private/tmp/ccl-work/codex/loader-level0/run
python3 tests/wasm/stage1/loader-level0/controls.py /private/tmp/ccl-work/codex/loader-controls/run /private/tmp/ccl-work/codex/loader-level0/run
python3 tests/wasm/stage1/loader-level0/replay.py /private/tmp/ccl-work/codex/loader-replay/run /private/tmp/ccl-work/codex/loader-level0/run
python3 tests/wasm/stage1/loader-level0/qualify.py native /private/tmp/ccl-work/codex/loader-native/run
python3 tests/wasm/stage1/loader-level0/qualify.py corpus /private/tmp/ccl-work/codex/loader-corpus/run
python3 tests/wasm/stage1/loader-level0/readers.py /private/tmp/ccl-work/codex/loader-readers/run
python3 tests/wasm/stage1/loader-level0/regression.py /private/tmp/ccl-work/codex/loader-regression/run
```

`run.py OUT --baseline` retains the integrated loader's original ordered and
duplicate-definition failures. `packet.py --help` lists the retention inputs.
The sibling store's `2026-09-25-loader-set-package-r1/packet.json` binds reports,
sources and compressed evidence. Regenerable binaries have size/hash entries.
The next implementation work is the ordered build's native-FFI boundary.
