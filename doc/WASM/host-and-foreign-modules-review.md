# Codex review of HOSTFM-P1

Reviewed commit: `0ac8691c6de411bf27e376244e7a2080be330760`, 20 September 2026.
Verdict: **AMEND before adoption.** The browser/Node provider split and withdrawal
of the interface-database implementation are the right direction. The foreign
call protocol has two correctness problems; the proposed evidence changes also
need correction. This review does not adopt policy or change acceptance records.

I should have checked the existing profile exclusions before implementing the DB
unit, and checked GC-counter consumers before copying their native storage shape.
Internal correctness alone did not justify those implementation choices.

## Findings

1. **P1 — FM-7/FMT-4: a Wasm catch cannot contain a foreign trap** (proposal
   lines 172, 238). `try_table`/`catch_all_ref` catch thrown exceptions, not traps.
   An out-of-bounds access or `unreachable` in a directly called foreign module
   bypasses the Lisp Wasm cleanup handlers as well. Thus FMT-4's promise of a Lisp
   error and exactly-once cleanups is not implemented by the proposed adapter.
   Choose a JS catching boundary *inside* the still-live Lisp call, translating
   a trap to a new catchable Lisp/Wasm exception; or explicitly narrow the direct
   path to an admitted nontrapping contract and define fatal trap handling.
   Catching only at the outer public entry is too late to preserve those frames.
   A trapped library may also need to be invalidated rather than reused.
   [WebAssembly exception-handling specification](https://github.com/WebAssembly/spec/blob/main/proposals/exception-handling/Exceptions.md#traps).

2. **P1 — FM-2/example: allocator calls escape the FOREIGN protocol** (lines
   210–213). The example calls foreign `malloc` before entering FOREIGN and
   foreign `free` after re-admission. Both are foreign execution and may call
   imports, re-enter Lisp, grow memory, throw or fail to return. Every foreign
   entry—including allocator, destructor, startup constructors and start
   functions—needs the bracket. After any re-entry, reload roots and recompute
   Lisp byte addresses before copying. Copy only while admitted and with no
   collecting call between obtaining the Lisp address and copying. On return,
   re-admit before heap access; release foreign buffers through another bracket
   on success and failure. `decisions.md:260,304` and `outline.md:187–191` require
   these transitions, not merely a state label around the principal export.

3. **P2 — R-5/S-1: do not edit retained selection inputs** (line 253). The named
   `startup-*/selection.json` files are hash-pinned by existing evidence. For
   example, `startup-resets/selection.json` is pinned at
   `24492ad2324651a014c88edea986b3d812615fd478dd49f4765199216344a169` in the DB
   packet; I checked the file still matches. Editing it would break those replays.
   Create one new classification manifest keyed by snapshot identity and ordinal,
   binding the original selection hash. New builds consume that overlay.

4. **P2 — S-3: deferral alone does not discharge a bootstrap dependency** (lines
   143–145). A consumer audit still owed cannot establish that an initializer is
   unnecessary. Mark an exclusion closed only after the selected bootstrap
   profile omits the subsystem or its consumers use a qualified replacement.
   Otherwise retain an unresolved dependency. The adopted assertion at
   `stage1/inventory.json:624` allows a selected worklist, but requires every
   selected dependency and completion to be justified. This needs no gate change.

## Answers to the ten questions

| ID | Disposition | Answer and evidence |
| --- | --- | --- |
| Q-1 | AMEND | Most classes are sensible. CB-1 and CB-10 need a consumer audit before implementation: the only found read of `*total-bytes-freed*` is under `#+not-any-more` (`level-0/l0-misc.lisp:118`); the repository search finds `*lisp-start-timeval*` only at its definition (`level-1/l1-lisp-threads.lisp:79`). Neither establishes a live consumer. CB-2 should be RT/replaced, not simultaneously EXCL. |
| Q-2 | AGREE | Keep potentially blocking OS reads behind the mailbox. A bounded byte count does not bound OS latency or make `fs.*Sync` interruptible. A proven nonblocking read from already resident bytes is a different case and need not take an OS path. `outline.md:187–191,234`. |
| Q-3 | AGREE | Keep semantic imports stable; add provider capability/provenance binding at admission behind the mailbox. Do not duplicate runtime-only imports per host. `outline.md:215–224`. |
| Q-4 | AMEND | `gctime` actively expects the five-buffer layout (`lib/time.lisp:30–43`), so replacing it requires a corresponding consumer rewrite, preserving its five-value contract and `TIME` use (`lib/misc.lisp:502–531`). That is preferable to imposing macOS timeval buffers on the port. The bytes-freed reference is compiled out. Do not integrate `541b4a3f` merely to empty the startup list. |
| Q-5 | AMEND | First establish a live consumer. If the port needs a start timestamp, use a port clock representation with explicit units and distinguish wall time from elapsed time. No evidence here requires a pinned foreign word pair or future FFI dependency. |
| Q-6 | AGREE | Per-library generated adapters are a useful seam, with shared helper code. Generate from binary types **and** explicit pointer/ownership declarations. The trap policy in F1 must be settled before choosing the direct path for arbitrary exports. |
| Q-7 | AGREE | Lisp declarations first; WIT import later. Binary types cannot recover pointer ownership, string encoding, structure layout or lifetime. |
| Q-8 | AMEND | H-1…H-6 need not invalidate existing scoped executions. They do not qualify Node deployment or a provider-neutral bootstrap automatically. Keep suspension profile, provider and engine provenance distinct; do not mutate old evidence to add those claims. |
| Q-9 | AGREE | Withdraw DB R1 and its follow-up as production implementation proposals; keep the evidence. Do not spend more qualification effort on an excluded interface database. Amend the rationale as DB-1 below. |
| Q-10 | AMEND | Start the Node read-only namespace and startup arguments alongside Stage 1's namespace. Route stdio/exit through the host protocol; interactive terminal behavior needs stream and LL20 suspension support. Do not treat synchronous fds or `process.exit` in a Lisp Worker as a complete terminal/batch deployment. |

## Remaining ID dispositions

Rows group IDs only when the disposition and reason are shared. AGREE accepts
an architectural recommendation, not an unexecuted engine qualification.

| IDs | Disposition | Evidence or amendment |
| --- | --- | --- |
| U-1, U-2, U-3, U-4 | UNVERIFIED | Relayed conversation, not independently witnessed in this thread. Direction is consistent with this proposal and is not contradicted here; retain the attributed provenance. |
| C-1, C-3, C-4, C-5, C-6 | AGREE | Selection, current index, outline §05, startup-config README and audit-130 addendum support the scoped history. The counts describe the pre-counter-unit worklist, not a full startup closure. |
| C-2 | AGREE | Classification before implementation is the needed correction; `browser-config.mjs` is the existing browser configuration provider. Do not interpret this as denying the other runtime service adapters. |
| N-1, N-2 | UNVERIFIED | Plausible deployment prerequisites, explicitly not a new engine qualification. The review's Node probe confirms final Wasm EH on the pinned Node only; a full deployment row still needs the relevant profile evidence. |
| N-3, N-4, N-5; DEP-A, DEP-B, DEP-C | AGREE | Local Node serving and Node-only execution avoid a cloud-server requirement; keep the browser provider's capabilities separate from a deployment's optional relay. Outline §04/§05 supports that architecture. |
| H-1, H-2, H-3, H-5, H-6 | AGREE | Same Lisp API, explicit absence, validated owner inputs and one virtual namespace follow the existing outline. H-5's mounts must preserve the namespace's no-symlink/bypass rule. H-6 records provider identity without claiming a restored live host handle remains usable. |
| H-4 | AGREE | Subject to Q-2. FOREIGN and actual interruptible waiting are different obligations; CPU-bound foreign work cannot be interrupted merely by setting a mailbox word. |
| CAP-ns-ro | AMEND | Replace the unqualified `fs sync` entry with the mailbox-backed Node implementation selected in H-4/Q-2. |
| CAP-ns-rw, CAP-ns-enum | AMEND | OPFS is a proposed browser provider, not the only possible writable/enumerable virtual store. Capability availability remains deployment-specific. |
| CAP-stdio | AMEND | Split Lisp standard streams from POSIX fds/TTY. The browser lacks a native terminal, but its listener still needs Lisp stream input/output routed to the page. |
| CAP-args, CAP-env, CAP-image | AGREE | Owner-provided values within the virtual namespace; argv slicing and cwd/home mapping are deployment policy, not guesses at the native process. |
| CAP-exit | AMEND | Send a process-exit request to the Node owner. Calling `process.exit(n)` inside a Worker stops that Worker, not the process; define flushing, sibling termination and final status. [Node documentation](https://nodejs.org/api/process.html#processexitcode). |
| CAP-signal, CAP-proc, CAP-sock | AGREE | Architectural capabilities only; interrupts are relayed by the main-thread owner, asynchronous work follows H-4. No deployment qualification performed here. |
| CAP-clock, CAP-cputime, CAP-cpus | AMEND | Record clock units/resolution and process-versus-thread CPU accounting. Available parallelism is a scheduling-capacity estimate, not necessarily the physical/logical CPU count. Preserve the accepted browser count's provenance. |
| CAP-ui | AMEND | DOM operations execute on the Page; the Lisp Worker provider proxies them. This is not direct DOM availability in the Lisp Worker. FM-13 already says this. |
| CAP-ffi-native, CAP-ffi-wasm | AGREE | Native FFI excluded by policy; foreign Wasm admitted as future design scope, not an implemented capability today. |
| CB-0, CB-1 | AMEND | Q-4. RT ownership is right; audit/replace consumers rather than preserve native foreign allocations automatically. |
| CB-2, CB-3, CB-4 | AMEND | Runtime replacement/host exclusion is appropriate only with consumer routing proved. `l1-streams.lisp:5395`, `linux-files.lisp:1137,1326` still reference the native mechanisms. A leftover use must not see fabricated fd limits or nil locks. |
| CB-10 | AMEND | Q-5: no live read found; do not manufacture a record solely to implement its initializer. |
| CB-12, CB-18, CB-19, CB-20, CB-23, CB-26, CB-27, CB-30, CB-31, CB-32 | AGREE | As scope/scheduling recommendations, with S-3's corrected dependency condition. `l1-boot-1.lisp:110–112` establishes home/ccl ordering; `l1-processes.lisp:78` requires process revival for a nonempty saved queue. |
| CB-21 | AGREE | Virtual home is appropriate. The [CLHS](https://www.lispworks.com/documentation/HyperSpec/Body/f_user_h.htm) confirms a missing host argument cannot yield NIL. A namespace home need not promise a writable store in Stage 1. |
| S-1, R-5 | AMEND | F3: one new classification manifest, not edits to immutable fixture inputs. |
| S-2 | AGREE | Preserve reviewed registry order and explicit dependencies. |
| S-3 | AMEND | F4: an outstanding consumer audit remains outstanding. |
| DB-1, DB-2 | AMEND | Agree to withdrawal. However, excluding `.cdb` loading does **not** prove the absence of interface-dir objects: `ensure-interface-dir` builds metadata without opening a DB (`lib/foreign-types.lisp:161–168`). Establish empty/no-live-handle state in the selected image, or exclude that subsystem. Future FFI declarations do not mandate resurrection of the native interface database. |
| DB-3, DB-4 | AGREE | Preserve audit findings as historical facts and the reusable harness techniques. Withdrawal is a scope decision, not retroactive proof that F1 was absent. |
| FM-1 | AMEND | Separate memories remove the need to pin Lisp data for the foreign callee. The trusted adapter/callback code still accesses Lisp memory and must obey bounds and root protocols; isolation alone does not prove it cannot corrupt the heap. |
| FM-2, FM-7 | AMEND | F1/F2. Specify callback re-entry and return to FOREIGN in both directions, including errors, and distinguish traps from catchable exceptions. |
| FM-3, FM-5, FM-6 | AGREE | Typed lower ABI plus explicit higher-level declarations and encodings. `binary.mjs` is a useful base, not already a general C ABI decoder. |
| FM-4 | AGREE | Per-library adapter, separate memories and qualified multi-memory feature; F1 constrains which calls can remain wholly Wasm-to-Wasm. |
| FM-8 | AMEND | Require an exported/imported callable table with sufficient limits, or an explicit registration ABI; arbitrary libraries need not expose a growable table. Retain a collector-visible root for each registered Lisp callback until deregistration, and version table handles. A failed Lisp callback must not throw across the foreign frame: specify a declared error result or deferred failure protocol. |
| FM-9 | AMEND | Worker affinity is a sound selected policy, not a consequence of absence of atomic instructions. Funnelled callbacks need an explicit owner-thread/reentrancy policy; preserve the refusal of callbacks from unowned threads. |
| FM-10 | AMEND | Explicit release must invalidate the allocation handle and suppress its finalizer to prevent double free. Library generation alone does not detect reuse of a freed offset within a live instance. Queue finalization to the owning Worker outside the GC critical section. |
| FM-11 | AMEND | Bind the declared ABI, initialization convention, memory/table limits and imports. Run initialization under F2's protocol. Choose `_initialize`, constructor export or start section per the binary/toolchain contract, exactly once; not every valid module has `_initialize`. No promise of arbitrary C++ binary compatibility. |
| FM-12, FM-13, FM-14, FM-15 | AGREE | Feature qualification and fallback, page mailboxes, optional future record declarations, and explicitly limited trust. Requalify copy/view behavior after foreign memory growth. |
| FMT-1, FMT-2, FMT-3, FMT-5, FMT-6, FMT-8 | AGREE | Future tests, not current evidence. FMT-3 must arrange collection from another thread or an explicit callback while foreign execution is active. |
| FMT-4 | AMEND | F1: test foreign exception and trap separately against the actual chosen boundary. |
| FMT-7 | AMEND | Require missing initialization only when the library's declared initialization convention requires it. Include start execution and initialization failures in the bracket tests. |
| FMT-9 | AMEND | Test explicit-free followed by GC, offset reuse, callback deregistration, and owning-Worker finalization in addition to library drop. |
| R-1, R-2, R-3, R-4, R-6, R-7 | AGREE | After user adoption and the above amendments; maintain historical record hashes and distinguish future features from accepted executions. |

The unnumbered `Math` paragraph (proposal lines 101–105) also needs correction:
calling `Math` does not establish native libm coverage, type/coercion behavior or
FP conditions. Retain the accepted LL16 numeric boundary; classify remaining
libm calls individually. I did not recount the foreign-call density totals.

## Verification performed

Read the changed files, the standing rules, relevant native consumers and adopted
startup/admission contracts. Verified one concrete retained selection hash.
`manage.py check` passed. No compiler rebuild or unrelated fixture replay.

A minimal `try_table (catch_all ...)` probe on Node v25.6.1 caught an explicit
Wasm `throw` (returned 1); replacing the body with `unreachable` escaped as
`WebAssembly.RuntimeError`. Source and result are at
`/private/tmp/ccl-hostfm-review-0ac8691c/`. This is a targeted design check,
not an engine matrix qualification. The primary specification confirms it.
