# Audit 188 refusal follow-up

O-134 now returns tagged `-ENOMEM` from the file service when the archive's
generation budget is exhausted. The default budget is two, including the
bootstrap generation. Only `GENERATION_CAPACITY` is translated; unrelated
admission errors still propagate. The file client validates the complete
argument frame, path and thread state before preparing a load, and preparation
finishes before publishing a host request. A refused reservation therefore
opens no host handle and changes no roots, tables, code IDs or session state.

The existing Lisp FASL error path passes negative errno to `%err-disp`, which
reports `checked 4`. This change removes the uncaught JavaScript exception;
it does not add a catchable `file-error` to that path. The runtime README now
documents the budget, its lifetime and this refusal behavior.

O-124 was already fixed by `ea82d8e7` in `bootstrap-class-implicit-runtime`.
`wasm32-compile-file` binds `*b-cpl-conditions*` to true and `b-implicit-runtime`
selects that emitter. It checks `tcr.error_service_mode` alone before calling
the Lisp constructor. The guard cited by audit 188 is in
`prior-numeric-b-implicit-runtime`, the older numeric-condition representation;
it is not the emitter used by startup. The original audit and acceptance
record remain unchanged as historical records. No compiler edit was needed.

The focused loader fixture is freshly compiled from the current compiler.
Its `TARGET-LOADER-EARLY-ERROR` binds a real handler around `(car 17)` with no
Lisp error system installed. Modes 0 and 2 preserve the first `checked 5`,
restore the argument/binding/root heads, and allow the following valid call.
Restoring the old handler-dependent guard in the actual generated class helper
makes this fixture fail: it reports `checked 11` instead of 5. This is a
directed regression check of the active path, not a source-text-only finding.

Verification covers:

- Eleven generation-boundary checks with real archive admission/publication:
  overlap, partial-close reuse, published generations after close, repeated
  exhaustion, complete state preservation, validation precedence, missing
  files, read-only opens and unrelated admission failures.
- The same test against `c6538d37` fails with the original uncaught
  `GENERATION_CAPACITY`; that failure and its source identity are retained.
- The 18-module focused loader fixture, 57 file-admission control groups,
  81 archive controls, 11 asynchronous checks and the retention diagnostic
  (3,922 marked objects, none retained).
- Two fresh Workers reach READY after 83 returned loads each. The post-image
  witness reserves generation two by attempting the native kernel redefinition,
  then twice checks that the Lisp file service returns `-12`. A subsequent
  ordinary LOAD reports `STOPPED / checked 4`, with no abandoned sessions.
  Required-bundle omission and empty-namespace refusals are also checked.

Boot, runtime archives and all 82 reconstructed container digests reuse the
accepted SEP-1 inputs. Only the focused fixture and post-image witnesses are
recompiled. Native R6/R6a and existing-target reader evidence are reused because
no shared Lisp, compiler or kernel source changes. The post-image build runs
its ordinary native oracle. The full compiler corpus is **not run**, as the
user directed. These runs make no new timing or criterion-acceptance claim.

The finalized pack is
`ccl-evidence/2026-09-27-audit188-refusals-r1` beside the checkout. Its
`REPRODUCE.md` gives exact commands and retained-input extraction instructions;
`summary.json` and `index.json` bind results, failures, tools and source hashes.
The [result record](../../../../doc/WASM/stage1/refusal-followup.json) pins that
pack's evidence commit and indexes. Disposable workspaces were removed after
verifying the retained artifacts.
The new host change and regression evidence await user-supplied independent
review. Product Lisp delta is **0 added / 0 removed**; whole-file and acceptance
counters are unchanged.
