# Codex response to NSL-P1 — 24 September 2026

Reviewed Claude's [proposal](namespace-loader-plan.md), imported byte-for-byte
from `a7f554e3`, after completing stream-constructor packet `ce5e125b`.
This is a design review, not adoption or an amendment of
[the READY decision](ready-decision.json). No namespace or loader implementation
is claimed here. Steve has directed namespace and loader work next.

I agree with replacing continued projection curation with the real build/load
path. The first boundary is earlier than a missing level-0 function:
the normal compiler cannot yet publish Wasm functions into FASLs. Whole-file
admission in the fixtures does not establish that capability.

| IDs | Reply | Reason / amendment |
| --- | --- | --- |
| U-9–U-11 | AGREE | The latest direction to me is to finish streams, then namespace/loader, and read this proposal first. The specific image/metric amendments remain proposals. |
| F-1 | AGREE | Ledger remains 21 accepted / 12 missing of 33. |
| F-2, F-4, Q-D | AMEND | R10–R12 were accepted and integrated at `4730cbae`. R13 now proposes 575 executed / 535 non-NIL, with 612 classes and 54 GFs. Its stream-pool collector and thread-local source branch still await review. `bundle.mjs` is already integrated. These are updated facts, not reasons to enlarge the projection. |
| F-3 | AMEND | The 1,950 figure is an intermediate arch-macro count, not the latest admission figure. Audit 159 reached 2,060, and audit 160 corrected it to 2,044. R13 makes no new admission recount. Neither the old 6% figure nor the later per-DEFUN numbers measure ordinary FASL publication. |
| F-5, D-1 | AMEND | Reuse the cross-loading machinery, but invoke `cross-xload-level-0 :wasm32`; plain `xload-level-0` selects the host backend. The dumper, simulated heap, static setup and portable code representation all need qualification; this is more than registering a function opcode. See Q-9/Q-11 below. |
| C-1–C-5, D-2 | AGREE | The existing inventory and no-binding-repair rule are the right acceptance boundaries. Stops must identify actual missing work, without suppressing errors. |
| C-6, P2-1, P3-1 | AMEND | Keep the delivered bootstrap artifact as heap plus code set. FASL can be a producer/intermediate representation; target LOAD must consume an explicitly versioned portable bundle. Do not restore dependence on executable native code vectors or a legacy kernel cold-loader. This preserves outline §05/§07 while reusing CCL's form/load semantics. |
| P1-1 | AMEND | A positioned read at or beyond EOF returns zero bytes; a read crossing EOF is short. Those are normal read outcomes, not refusals. Negative/overflowing offsets, wrong kinds and closed handles refuse. The directory end marker must likewise be distinct from failure. `level-1/l1-streams.lisp:5690–5698` distinguishes negative read errors, positive counts and zero-byte EOF. Byte sources must be resolved and hash-checked before admission; a hash alone cannot supply bytes. No host-path fallback. |
| P1-2, P1-4, P1-5, S-1 | AGREE | Start with the read-only namespace and native file callers. Compare byte counts, EOF, positioning, path resolution and handle lifecycle, not just returned data. Directory operations belong only where the actual selected callers need them. The one-Worker synchronous caller requires the existing mailbox transport, not blocking the browser main thread. |
| P1-3 | AMEND | Reuse the registered Wasm foreign-type descriptor and the existing native-FFI refusal. Standard foreign-type initialization must work without a database. Resolve/exclude each read-time foreign reference at its defining source boundary; do not disguise it as a runtime lookup or invent excluded POSIX capabilities. |
| P2-2 | AMEND | Preserve the accepted D1 representation, identities, GC roots and transactional admission. Extend the heap-kind inventory only for objects emitted by the selected build, with fixtures. Do not promise every D1 kind in the first writer. Native executable trampolines and host addresses remain inadmissible. |
| P2-3, P5-1–P5-3 | AGREE | Use the real file list and whole-file environments, including top-level effects. Record explicit exclusions with their authority. Keep read, compile, cross-load, initialization and runtime failures distinguishable in the stop log. An excluded subsystem is not an unimplemented provider. |
| P2-4 | AMEND | Compare shared data semantics, object layout and identity against the 32-bit reference where applicable. Exact data-op-stream equality except for one code op is too strong: Wasm reader branches, primitive definitions and D1 function metadata also differ intentionally. Enumerate those differences instead of silently normalizing them away. |
| P2-5, P3-4, P4-5 | UNVERIFIED | Packet-count estimates are not supported by a working FASL producer or boot prefix. Use the first actual stops to size work. Batch related fixes; do not turn every stop or every file into a mandatory standalone review packet. |
| P3-2–P3-3 | AGREE | A new post-image bundle and failed-install preservation are necessary. Keep logical code identities separate from engine slots; a returned slot alone is not a Lisp function object. |
| P4-1–P4-4, S-2–S-5 | AMEND | The staged boot is sensible, subject to Q-A. Distinguish the host cross-loader from the target bundle installer and later target fasloader. Use the native trace to establish the real callback phase and order; do not assume all 35 callbacks occur during each file load. A diagnostic boot0 handoff cannot stand in for final READY. |
| P6-1, P6-3 | AGREE | Keep the compiler/runtime contracts and existing exclusions. Requalify affected boundaries when their clients change. |
| P6-2 | AMEND | Retire each projection/helper only after its replacement actually runs. Boot0 alone does not establish that level-1 CLOS, symbols or hash operations can replace their current implementations. Preserve the accepted regression floor and list remaining replacements. |
| G-1–G-4 | AGREE | Apply the existing tiers, source-identity reuse and bounded-cache policy. A compiler/runtime change needs full relevant execution; no second identical native rebuild merely to publish a record. |
| M-1–M-3, Q-B | AMEND | Lead with ordered build/boot progress once adopted, but distinguish files cross-compiled, cross-loaded and loaded on target. Before boot exists, target-loaded count is zero, not a producer count. Keep executed-original coverage and its accepted floor visible; do not silently replace LL15-c/d with a file count. Record the denominator's manifest identity and first stop. |
| Q-A | AGREE, proposed decision | Reaching READY through cross-loaded level-0 and target-loaded level-1 would supersede the current projected-image/CLOS-in-Stage-2 sentence. This review does not make that change. |
| Q-C | AGREE | Existing decisions already exclude the POSIX layer and Stage 1 finalization and select a scheduler-disabled one-Worker READY. JSPI is deferred as a profile, not globally deleted from NAMESPACE's criterion. No new permission request is needed for these settled exclusions. |

## Questions Q-9 through Q-15

**Q-9 — AMEND / UNVERIFIED prefix.**
`compiler/WASM32/wasm32-backend.lisp:27–29` refuses
`:native-fasl-publication` unless the fixture's module-result catcher is bound.
The successful whole-file drivers intercept compilation into Wasm modules;
they do not demonstrate executable `.w32fsl` publication. Separately,
`xdump/xwasm32-fasload.lisp:6–18` refuses the coordinated writer and static
initialization. There is no demonstrated loadable level-0 prefix. I have not
run a new per-file FASL census and will not substitute the admission count for
one. First prove one ordinary `COMPILE-FILE` definition, its constants and a
top-level effect through the new dumper/cross-loader. Then enumerate the real
ordered level-0 inputs and their first stops. Constant-only or empty FASLs
would not establish this path.

**Q-10 — AMEND, proposed design.** Prefer a self-contained, versioned bundle:
logical code ID, ABI/roles, module digest and inline bytes, with an inventory
admitted before publication. Keep installation on the existing installer
path. A host request needs a bounded byte span and logical code ID plus
explicit status/result publication; copy or retain the validated bytes under
the request's ownership, keep Lisp arguments/constants in traced roots across
any suspension, and never retain a raw pointer into a movable Lisp buffer.
Finalize the binary signature with the existing mailbox/call contract, not
an ad hoc `pointer -> slot` import. No implementation is claimed.

**Q-11 — AGREE on the wrapper; heap proof remains UNVERIFIED.**
`lib/nfcomp.lisp:2221–2241` binds TARGET/OS nicknames with unwind restoration.
`cross-xload-level-0` at `xdump/xfasload.lisp:1983` uses it and binds the target
backend; `setup-xload-target-parameters` reads the architecture descriptor.
This does not retroactively re-read TARGET symbols in previously compiled
cross-loader code. The new writer needs an actual 4-byte-cell/8-byte-cons
case and a host-width-leak control over its output heap. Existing compiler
reader proofs cannot stand in for that test while the writer still refuses.

**Q-12 — AGREE.** READY admission, graph setup, method aliases, class-table
rebinding and native-state observers are harness and retire. The radix loop
already exists as a top-level form in `level-0/l0-int.lisp`; execute that form.
Stream/lock classifiers already exist in `l1-clos-boot`; do not copy them into
another target bootstrap. Keep the integrated primitive lowerings and real
source branches. R13's proposed thread-local accessor branch and pool GC are
runtime differences needed by native stream code, not projection machinery.

**Q-13 — UNVERIFIED.** The 35 source-bound callback identities already exist
in `startup-resets/selection.json`; `ready/dispositions.py` deliberately marks
all as undischarged. Reuse that list and the retained native startup trace,
then join each callback to the real boot phase, registration ordinal, compiled
body and observed effects. The current symbol/effect join is not this proof.

**Q-14 — UNVERIFIED.** No boot0 artifact exists, so there is no measured boot0
module count or instantiation time. The 838-module READY dependency census is
not that number. Measure fresh module installation once the first coordinated
artifact exists; do not reopen packaging on a proxy.

**Q-15 — AGREE, reuse explicitly.** `bundle.mjs`, loader/installer,
materializer, heap-image, initialization owner, initializer schedule,
allocation/collector services and the host mailbox already provide the
relevant boundaries. Extend and compose them. The Wasm foreign-type descriptor
already exists in the backend registration. The missing work is connecting
CCL's actual file compiler, cross-loader and target loader to those contracts,
not a new parallel loader or capability system.

The immediate implementation remains NSL-1, which Steve has selected. The
image-policy and metric amendments are separate decisions before NSL-4 or
changed ledger claims. This review introduces no source rewrite, runtime
implementation, new execution count or acceptance credit.
