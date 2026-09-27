# Startup execution remediation

Implementation of [SEP-1](startup-execution-plan.md), excluding direct calls.
The measured 32 MiB launch reaches READY in **27.631 seconds**, compared with
50.204 seconds before these changes: 45.0% less elapsed time. Host changes alone
reach READY in 35.492 seconds. All three runs return from the same 81 runtime
loads. A separate complete census falls from 84,119,399 to 44,724,264 Lisp calls.
The plan's 10–15 second estimate and 25–30 million call estimate were not reached.

The user accepted the host and Lisp/compiler changes after audit 188; the
[acceptance record](acceptance-audit-188.json) binds the supplied review.
These are author measurements on macOS, not a statistical performance guarantee.
The reviewer reproduced the exact census and measured 25.8 seconds to READY.
The timed launches use fresh Node processes,
the same 32 MiB layout, RAM-backed inputs and timing journals, without the full
call observer. The final compiler build was paused during the isolated timing.
A prior revision without the compact-dispatch-table fix measured 26.334 seconds
in isolation and 26.298 seconds during compilation. Those provisional results
are retained; the comparison above uses the corrected revision. Exact engine/toolchain identities, commands, source
hashes and raw journals are in the evidence pack described by
[the machine-readable result](startup-execution-results.json).

| Measurement | Before | Final |
|---|---:|---:|
| Launch to READY | 50.204 s | 27.631 s |
| Lisp-start to READY | 44.713 s | 24.214 s |
| Complete traced calls | 84,119,399 | 44,724,264 |
| `%FASL-READ-BYTE` calls | 5,753,223 | 0 |
| `%SIMPLE-FASL-READ-BYTE` calls | 5,753,223 | 752 |
| `%AREF1` calls | 7,745,230 | 1,369,850 |
| `MEMQ` calls | 2,908,082 | 95,602 |
| `SORT-METHODS` calls | 393,986 | 76,467 |
| `%FIND-PKG` calls | 230,147 | 143,062 |
| Default observer instances | 1,042 | 3 |
| Product modules / instances | 7 / 11 | 7 / 11 |
| Peak process RSS | 1,861,373,952 bytes | 2,219,110,400 bytes |

The final launch performs four collections. Memory is a tradeoff: the runtime
archive grows from 64,642,870 to 68,972,499 bytes, and this run's peak RSS rises.
The remaining census is dominated by instance slots, sequence type/length,
class/CPL access and FASL dispatch. The calling convention remains indirect.

## Disposition of the samples

| Item | Implemented decision |
|---|---|
| H-1 | Observe only the boot functions used by the READY report; `--trace` still wraps the whole boot and subsequently installed functions. Three of the four named functions exist in this boot image. |
| H-2 | Drain the entries from the latest publication instead of enumerating every installed entry after each function install. The existing full enumeration API remains available. |
| H-3 | Use native asynchronous SHA-256 for archive admission and native SHA-256 for transferred metadata. Explicit ownership of freshly parsed manifests avoids the large defensive clone. **Body/helper/metadata hash checks remain.** The sample deleting authentication checks was rejected. |
| H-4 | Reuse DataViews, replacing them when the memory buffer changes, in integer, archive and target-load services. |
| H-5 | Buffer 256 timing rows; flush at checkpoints, memory milestones and finish. A killed Worker can lose up to 255 pending rows. |
| L-1 | Inline the common byte path with typed byte-vector access. Word/count/string loops inherit that expansion; alternate FASL APIs and refill/EOF handling retain their fallback. Keep checked generic count arithmetic. Reject raw byte copying into D1's 32-bit character strings. |
| L-2 | Cache the most recent package name and package; copy the mutable input name and recheck current names and registry membership after rename/deletion. |
| L-3 | Cache the most recent istruct name/cell with the authoritative alist head. Preserve the alist order and invalidate when the registry binding/head changes. Both caches start as `nil` and allocate on first use, before level-1 initialization. |
| L-4 | Store the most recent class tuple and effective standard combined method in the existing GF dispatch table. Check current CPL identities; clear on the existing update paths, including removal of the last method. Tables with fewer than two entry cells, EQL-specialized methods and nonstandard combinations use the original computation. Keyword checks still run on hits. |
| L-5 | Use a 64 KiB FASL input buffer. The existing file protocol caps an individual transfer at 8,128 bytes, so actual refills fall from 2,848 to 752; the plan's roughly 110-read estimate does not apply to this transport. |
| C-1 | Admit the native predicate compiler macros and add ordinary Lisp expansions for list `LENGTH` and `MEMQ`. Preserve single evaluation, evaluation order, result identity, vector/fill-pointer behavior and improper-list conditions. |
| C-2 | Retain CCL definition information, including lexical macro environments, across successful target file compilations. Scoped hooks are restored on exit and redefinitions remove stale expansions. The raw-lambda sample was rejected because it loses lexical macros. |
| C-3 | Inline widened span checks; remove repeated symbol/function validation from `resolve`; return early from `stack_guard` only after structural owner checks. Reject the sample that bypasses alignment, range and backing validation. |
| C-4a/b | Publish and initialize exact argument root counts while retaining padded reservations; use a one-word store for one returned value and retain the multiple-value copy. |
| C-4c/d | Retain body-entry checks because exported tail entries remain callable boundaries. Retain checks for the distinct public and tail tables. Constant-callee caching needs redefinition/generation guards and belongs with direct calls; no stale resolved slot is cached here. The actual repeated object validation is removed by C-3. |

Product Lisp changes total **226 inserted / 41 removed lines** across five
files. Host/service changes are separately committed as `d3d122f4`.

## Verification and evidence

Both fresh Workers pass the ordinary startup and post-image loads (83 returned
loads each). The native/target assertions cover predicate expansions, list and
vector length, fill pointers, malformed lists, evaluation order, package
rename/deletion, istruct registry rebinding, repeated generic dispatch, method
addition/removal, class redefinition, keyword validation, EQL specialization,
zero-argument methods, zero-slot table sentinel preservation and cross-file
inline expansion with a local macro.
Required-bundle omission and an empty namespace both refuse READY.

Native R6/R6a passes 21,843 enabled tests, with 75 pre-existing disabled tests,
164 qualified/restored FASLs, five existing architectures and 17 module profiles.
The 45-file reader matrix passes 765 comparisons. A final compile-only inline
declaration correction is rebound with 219 identical decoded native functions
and all 17 existing readers, without repeating the unchanged native test suite.
The final compact-table correction is in the Wasm-only primitive file; the
native target-selection driver and shared native inputs remain unchanged.

Archive equivalence independently assembles fresh unlinked compiler WAT and
compares it byte-for-byte with reconstructed archive functions: 1,048 boot and
10,891 runtime functions. Separate reassembly checks bind delivered archives to
their templates. Recompiling all 82 runtime files after the producer-hook fix
produces identical records and FASL bytes. Hot-helper comparison covers 122
success/refusal cases, including state preservation. Host verification retains
81 archive controls, 11 async/hash/mutation checks, publication/GC smoke tests
and the forced-GC retention diagnostic with no marked reachable input objects.

The compiler/runtime corpus passes **26,204 fresh comparisons**: 6,551 cases
at two placements, each with and without movement. No comparisons are inherited
or sampled. Audit 188 reused this record by source identity: the independent
corpus replay ran out of RAM-volume space at the cold-compiler image save.
The stale Codex workspaces have since been cleared; this acceptance does not
claim a new corpus run. Its
collection probe is regenerated from this compiler's actual leaf; the inserted
import and collection call are checked to reverse exactly to the original WAT.
The former fixed-parent hook is still required when regeneration is not
explicitly requested. No case or comparison is skipped to accommodate the new
backend.

Original failures remain in the evidence pack: initialization before level-1
services, native raw-lambda macro scope, scratch-space exhaustion, the obsolete
GC-hook identity, the corpus snapshot with the pre-fix cache initialization,
and the compact dispatch table whose end sentinel was mistaken for a cache key.
The final READY and corpus records are distinguished from those failures.

The supplied plans are retained unchanged on `wasm2`; the two plan branches
were deleted after import, with the clean Claude worktree left detached.
Audit 188 supplies the commit-level adversarial review; the user accepted both
groups with “Accept all four”. O-124 fault masking and O-134 generation-capacity
refusal remain next producer work; O-136 records the cache-clear witness gap,
and O-139 carries the reader-dispatch marker hazard into future dcode work.
The standing rules prohibit invoking Claude; review is supplied by the user.
