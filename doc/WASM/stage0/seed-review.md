# Independent review of the proposed startup seeds

Reviewer: Claude Fable 5.1, 13 September 2026, at 55ca26e9. Subject: `tests/wasm/native-census/startup-closure/seeds.json` (13 entrypoints, three required-effect inventories), whose disposition is `PROPOSED_REQUIRES_INDEPENDENT_REVIEW`. Method: enumerate every point at which the U1 kernel or subprims transfer control into Lisp on Darwin x86-64, trace the saved image's cold-start chain in source, and compare both with the proposal. The graph was used only to confirm that the 13 native identities name the functions the proposal says they name.

Disposition: **REVIEWED_WITH_FINDINGS**. The 13 proposed seeds are correct as far as they go; six entry surfaces are missing and one structural condition makes the seed set untestable today. The set is not approved as the reviewed seeds the census contract requires.

## The kernel's entry surface

Every transfer of control from C or assembly into Lisp on this target goes through one of the `nrs` symbols in `lisp-kernel/lisp_globals.h` or one subprim macro. Searching all kernel C and x86-64 assembly for uses gives exactly six live entries:

| Entry | Where the kernel uses it | What it reaches in Lisp | In the proposal |
| --- | --- | --- | --- |
| `%toplevel-function%` value, run under `%toplevel-catch%` | `pmcl-kernel.c:2163`, `toplevel_loop` in `x86-subprims64.s` | The closure chain `save-image` installs (`lib/dumplisp.lisp:173`): set the next toplevel, `restore-lisp-pointers`, then `toplevel-function *application*`, `make-mcl-listener-process`, `%set-toplevel #'housekeeping-loop`, `toplevel` | Partly: `RESTORE-LISP-POINTERS`, `STARTUP-CCL`, `TOPLEVEL-FUNCTION` are named; the closures, `%SET-TOPLEVEL`, `MAKE-MCL-LISTENER-PROCESS`, `HOUSEKEEPING-LOOP`, `TOPLEVEL` and `LISTENER-FUNCTION` are not |
| Thread start, same mechanism per new tcr | `start_lisp` for every created thread | `thread-make-startup-function` (`l1-lisp-threads.lisp:180`), which applies the process's initial function; the listener that runs `startup-ccl` is such a thread | No |
| `cmain` (`nrs_CMAIN`, 20 uses in `x86-exceptions.c`) | Every signal, interrupt, GC notification and suspend | `xcmain` (`x86-trap-support.lisp:463`): `cmain`/`thread-handle-interrupts`, `%err-disp-internal`, `%error`, `handle-gc-hooks` and `*post-gc-hook*` | No |
| `%err-disp` (`nrs_ERRDISP`, `handle_uuo` at `x86-exceptions.c:760`) | Every UUO trap: type, bounds, unbound function, wrong argument count | `%xerr-disp` (`x86-error-signal.lisp`), then `%err-disp-internal`, `%kernel-restart`, `error` | No; `COMMON-LISP::ERROR` is downstream of it |
| `%pascal-functions%` via `_SPcallback` (`x86-spentry64.s:4882`) | Every C-to-Lisp callback, including `xcmain` and `%xerr-disp` themselves | The dispatcher `%pascal-functions%` (`l1-callbacks.lisp:113`) and the callback vector | No; `RESTORE-PASCAL-FUNCTIONS` reinstalls the vector but is not the dispatcher |
| `%builtin-functions%` via `jump_builtin` (21 sites in `x86-spentry64.s`) | Arithmetic, comparison, `eql`, `length`, `sequence-type`, `assq`, `memq`, `logbitp`, `ash`, `%aref1`, `%aset1` subprims on their slow paths | The 23 functions in the vector at `xdump/xfasload.lisp:323` | No |
| `%foreign-thread-control` (`thread_manager.c:1374`, `1855`) | Only when a foreign thread enters or leaves Lisp | `%foreign-thread-control` callback | No, and correctly so under the batch profile, but the exclusion is not recorded |

The remaining `nrs` slots (`eval`, `apply-evaluated-function`, `%defun`, `%defvar`, `%defconstant`, `%macro`, `%kernel-restart`, `%os-init-function%`, `%init-misc%`, `*post-gc-hook*`, `%handlers%`) have no kernel or subprim use on this target. `%kernel-restart` and `*post-gc-hook*` are reached from Lisp, through the entries above.

## Findings

1. **Cold-start chain.** The actual seed is the closure stored in `%toplevel-function%` at image save, not `RESTORE-LISP-POINTERS`. The proposal names three functions the closure chain calls and leaves the rest to "the candidate universe" through generic dispatch of `TOPLEVEL-FUNCTION`. Either seed the saved closure by identity or name the whole chain: `%SET-TOPLEVEL`, `RESTORE-LISP-POINTERS`, `TOPLEVEL-FUNCTION` with its two applicable methods on `lisp-development-system`, `MAKE-MCL-LISTENER-PROCESS`, `HOUSEKEEPING-LOOP`, `TOPLEVEL`, `LISTENER-FUNCTION`, `STARTUP-CCL`.
2. **Thread start.** `THREAD-MAKE-STARTUP-FUNCTION` is a kernel entry for every process, including the listener that runs startup. Seed it.
3. **Signal and interrupt entry.** Seed `XCMAIN` (phase `run`). Nothing in the proposal reaches it except by widening.
4. **Trap entry.** Seed `%XERR-DISP` (phase `run`). This is the path attempt 1 lost when `%err-disp` was left unbound and the image died silently; `COMMON-LISP::ERROR` alone does not cover it.
5. **Callback dispatcher.** Seed `%PASCAL-FUNCTIONS%` (phase `run`) and record the callback vector at image save as a required load-time binding, so its members are its bounded dynamic targets rather than open calls.
6. **Builtin vector.** Seed the 23 functions in `%builtin-functions%` or record the vector as a required binding with all members as targets. For the Wasm target these are the fallback paths of every arithmetic subprim under the B ABI, so their absence would surface as the first overflow.
7. **Explicit exclusion.** Record `%FOREIGN-THREAD-CONTROL` as excluded under the batch profile with the reason, rather than omitting it.
8. **Structural: the seed set is untestable today.** In the current graph every one of the 327,961 nodes is reachable from the 13 seeds, because `module:@clean-image` carries one conservative edge to all 15,424 resident functions (`members/@clean-image`) and `module:tools/asdf.lisp` another to 15,036. While those widening edges exist, no seed omission changes reachability and the LL15-c "removes a loader seed" mutant would be rejected only by the record check, not by closure. The reviewed seed set has no effect until the widening is replaced by the static traversal and bounded dynamic-call sets. Fixing findings 1 to 7 is necessary; finding 8 is what makes them matter.

No finding concerns the compile-side seeds. `READ`, `LOAD`, `%FASLOAD`, `COMPILE-FILE` and `REBUILD-CCL` are the right workload entrypoints for the native census profile, and the four pre-callback operations under `RESTORE-LISP-POINTERS` are correct but redundant with it. The four startup callback groups in `required_effects` match `restore-lisp-pointers` in source.

## What closes this review

A revised `seeds.json` carrying findings 1 to 7, with a new review disposition field for this reviewer to set, and a graph in which the clean-image and asdf widening edges are gone so that the seed set is discriminating. The revision invalidates any closure result computed under the old set, as the census contract requires. This review confers no LL15 credit.

## Addendum — revision 2 reviewed, 13 September 2026

Codex's revision 2 (`seeds.json`, revision `2026-09-13-kernel-entry-surfaces`, commit 2ef830cb) carries findings 1 to 7: the explicit cold-start chain, `THREAD-MAKE-STARTUP-FUNCTION`, `XCMAIN` and `%XERR-DISP` as callback-kind seeds joined through the callback vector with trampoline checks, the `%PASCAL-FUNCTIONS%` dispatcher, the 23 builtin slots as a required binding in U1 order, the three applicable `TOPLEVEL-FUNCTION` methods, and a recorded exclusion for `%FOREIGN-THREAD-CONTROL`. The root union of 49 prototypes was re-derived independently and matches. Disposition of the seed set: **REVIEWED_APPROVED** for the stated profile, pristine U1 Darwin x86-64 batch startup with `--no-init` plus the pinned rebuild workload.

Finding 8 is restated, not closed. Codex's diagnostic shows that removing the two largest membership edges leaves every seed omission masked, and removing all 208 membership edges makes only four of thirteen detectable, because reaching any function reaches its module and the build-execution module fans out to 116,385 nodes. The replacement must therefore cover every conservative widening family, not two edges. That is the static traversal and call-bound work, and it stays open.

Two residuals, disclosed by Codex and accepted: the callback and builtin vectors are observed after restore, so equality with image-save contents is an obligation, not a fact; and the foreign-thread callback is excluded as an independent root while remaining in the root union, which is conservative. The `review_disposition` field inside `seeds.json` still reads proposed because it is pinned by hash in the retained run; Codex may set it to reviewed, citing this addendum, and re-run the inspector to refresh the pin.
