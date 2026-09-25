> Historical P2-0 proposal A, reviewed in audit 178. Superseded for future
> work by the [consolidated loader design](../loader/README.md). Its target
> witness executes the constant-returning definition; the IN-PACKAGE
> initializer stays queued, and its top-level effect is applied on the host.

# NSL-2 P2-0: real FASL publication and cross-loading

Ordered production files cross-compiled / cross-loaded / target-loaded remain
**0 / 0 / 0**, against the retained **167-unit** native startup denominator.
Independent whole-file probes compile **4 / 21** level-0 inputs; they do not
complete the ordered build. The separate producer fixture is **1 / 1 / 0**.
Accepted originals remain **575 / 535 non-NIL**, with **21 accepted / 12 missing**
Stage 1 criteria. This is a review proposal, without acceptance or boot credit.

The fixture contains an ordinary `DEFUN`, a shared constant, `DEFPARAMETER`,
and `IN-PACKAGE`. CCL's actual `COMPILE-FILE`, under
`with-cross-compilation-target (:wasm32)`, now publishes a nonempty `.w32fsl`.
The ordinary FASL data operations retain the constant pool, sharing, symbols
and top-level effects. A versioned target function operation carries the module
text and symbol imports. No front-end sink intercepts publication.

The fixture source is deleted before a second, fresh CCL process reads that
FASL. The cross-loader uses CCL's target-width heap accessors and real data-op
dispatch. It emits D1 function objects and a simulated heap; the existing
`heap-image.mjs` writer replaces simulated pointers with checked relocations.
The code set uses the existing `bundle.mjs` inventory and materializer.
Package objects add one bounded heap kind: eight fields, forty bytes.

Two fresh Workers admit the image at 2 MiB and 8 MiB, install both modules,
and execute the fixture's definition. Native CCL and Wasm both observe
`((17 23) (29 31 T))`, including the shared cons identity. Checks cover the
four-byte cell/eight-byte cons layout, D1 function metadata, NIL and T, code
identity independent of table slot, and separate instance state. A simulated
64-bit cons write produces the required native-observation mismatch.
The real `IN-PACKAGE` initializer remains queued and has `CCL::SET-PACKAGE`
as its first dependency. Numeric service imports are explicit throwing
sentinels in this witness, with zero calls; no service result is fabricated.

The ordered compiler input list is root level-0 files followed by the Wasm
subdirectory; the loader order is the subdirectory followed by root files.
`frontier/results.json` retains both, source hashes, function names, source
positions where available, and first errors. Each probe starts a fresh host,
delegates to the real compiler, and preserves the first error even when dumper
cleanup signals a second error. The first ordered stop is `%REVIVE-SYSTEM-LOCKS`
in `l0-aprims.lisp`, at source position 884: `:NATIVE-FFI-EXCLUDED`.
The four independently compiled files are `l0-bignum64`, `l0-complex`,
`l0-error` and `l0-init`; a successful file may contain reader-excluded bodies.
Later stops include missing primitive lowering and `:FASL-CHILD-CODE`.

The native comparison covers all 164 FASLs: 130 byte-identical, 32 previously
qualified registration/source-location changes, and two intentionally changed
host dispatch files. Full decoded before/after components are retained for
`FASL-DUMP-FUNCTION`, `XFASLOAD` and `XLOAD-LFUN-NAME`; all other components
compare under the established bounded source-location rule. Qualification
includes 21,843 enabled native tests, five architecture descriptions,
17 target module profiles and restoration of all 164 baseline outputs.
The cold compiler regression runs all 26,048 comparisons. Source identity is
checked across the producer, native qualification and corpus build.

Sixteen runtime controls cover heap/bundle corruption, the new package width,
service import name/signature/uniqueness and the host-width fault. Eight real
FASL refusals cover version, both text-length bounds, non-ASCII text, duplicate
modules and all three pool-shape clauses; each refuses before creating producer
output. Twenty-one direct producer controls cover context/target, representation,
both text positions and array count/kind. Existing heap admission predicates
retain their accepted prerequisite evidence. The child-code refusal is observed
in real level-0 probes; its isolated mutation remains in `admission-debt.json`.
The original development failures,
including native gensym drift from the rejected counter design and the missing
`FASLENV` dependency, are retained.

P2-1/P2-2 are only implemented as needed for this witness. Child-code linking,
the full static symbol population, toplevel/binding-index boot roots, arbitrary
heap kinds and package tracing during moving GC remain later NSL-2 work.
The fixture compares with native macOS CCL; an x8632 cross-load comparison of
the selected production file set remains P2-4 work. No production ordered
cross-load, target `LOAD`, initializer completion or READY claim is made.

Proposed shared-source edits remain generated under this directory and are
applied only in disposable U1 trees. The product compiler/runtime is unchanged
pending Claude's review, as required by `CLAUDE.md`.

```sh
python3 tests/wasm/stage1/cross-load/run.py \
  /private/tmp/ccl-work/codex/cross-load-replay/producer
python3 tests/wasm/stage1/cross-load/run.py \
  /private/tmp/ccl-work/codex/cross-load-native-replay/qualification --native
python3 tests/wasm/stage1/cross-load/run.py \
  /private/tmp/ccl-work/codex/cross-load-corpus-replay/qualification --corpus
```

The finalized evidence packet is
`../ccl-evidence/2026-09-25-cross-load-r1/packet.json`. Its denominator reference
binds `2026-09-15-on-demand-census-r1/packet.json` and the retained startup
compilation summary. `packet.py retain` verifies its copies and deletes the
managed outputs after retention; regenerable binaries are referenced by hash.
