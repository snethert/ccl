# Host providers, startup callback scope and foreign Wasm modules

```
DOC-ID        HOSTFM-P1
STATUS        PROPOSAL — not adopted, not a decision record, no gate or ledger effect
AUTHOR        Claude (Fable 5.1), 20 September 2026
REVIEWER      Codex (cross-provider review requested by the user)
BASE          wasm2 at 541b4a3f; callbacks reviewed through audit 130 (3cfbfe1e)
UNREVIEWED    44531e64 (startup-db follow-up), 541b4a3f (GC counters) — not covered here
TOUCHES       no shared compiler, runtime, kernel, contract or registered document
```

## 0. What is asked of the reviewer

Every claim, requirement and question below has an ID. Reply per ID with one of
`AGREE`, `DISAGREE`, `AMEND`, `UNVERIFIED`, and the evidence (file and line,
executed probe, or specification link). Section 9 lists the questions that need
an answer before anything here is adopted. Do not implement from this document;
adoption is the user's decision and would be entered in `decisions.md` by the
ordinary route. Until then, §1 is relayed user direction, not a recorded decision.

Claim labels used throughout:

- `[SRC]` verified in this repository at BASE; file and line given.
- `[RUN]` executed by Claude during audits 126–130; the audit is cited.
- `[ENG]` a statement about engines, Node or toolchains from general knowledge,
  **not verified in this repository**. Each needs an engine-matrix row or a probe
  before it carries weight.

## 1. User direction relayed (20 September 2026, user to Claude)

| ID | Words | Context |
| --- | --- | --- |
| U-1 | "What files?!? We are aiming for the browser." | On reading the audit-130 summary of RESET-DB-FILES. |
| U-2 | "We will definitely want to support node, as not everyone will be able to have a cloud server." | After Claude listed CCL features a Node host has and a browser lacks. |
| U-3 | "And separate heap, yes." | Answer to: is a foreign module's memory separate from the Lisp heap by default? |
| U-4 | "Will I want FFI for speaking to WASM modules in other languages?" / "So, callling a C++ to WASM lib, for example." | Questions, not decisions. Claude's answer is §6. |

Also relayed, not recorded in this repository: on 12 September the user told
Claude that the POSIX/OS layer cannot be ported and that this is not a problem.
The outline carries the same effect for the interface database (C-3 below), so
nothing here depends on that ruling being in the record.

## 2. Problem

| ID | Claim |
| --- | --- |
| C-1 | `[SRC]` The startup selection works through one post-restore snapshot of 35 callbacks (`tests/wasm/stage1/startup-config/selection.json`). Thirteen literal resets and five configuration effects are accepted; RESET-WINNERS and RESET-DB-FILES are proposed; fifteen were open at audit 130. |
| C-2 | `[SRC]` Callbacks are being implemented one at a time with no recorded classification of which host, if any, gives each one a meaning. The only host adapter, `runtime/wasm32/browser-config.mjs`, reads browser globals. |
| C-3 | `[SRC]` `outline.md:236`: "Interface database (Stage 1) — Not loaded in the Wasm profile: native #_ resolution is out of scope, so foreign-types initialization must not require the .cdb files. If a later profile needs them, they are named blobs." STAGE1-STARTUP-DB-R1 builds a C leaf, four modules and an arena-admission protocol to clear handles to those files. |
| C-4 | `[SRC]` `tests/wasm/stage1/startup-config/README.md:8` already states the rule that was then not applied: "Native file descriptors, locks, pathname and process services are not assigned fictitious browser values." |
| C-5 | `[RUN]` Claude's audit 130 checked the database unit's internal correctness and harness and did not ask whether the unit belongs in the port. That omission is Claude's; this document is the correction. |
| C-6 | `[SRC]` The outline already anticipates Node as a store provider (`outline.md:237`: "OPFS in browsers, memory or disk under Node") and the UI specification already has a Node process as the developer-machine Host that serves the page with isolation headers (`ui-prototype-spec.md:72`, `:678`). Node is present in the design as a test engine and a file server, not yet as a place where Lisp runs for a user. |

## 3. Why Node is a deployment target (supports U-2)

| ID | Claim |
| --- | --- |
| N-1 | `[SRC]` The full profile requires SharedArrayBuffer with COOP/COEP (`outline.md:195`). `[ENG]` Those are HTTP response headers: a page opened from `file://` cannot be cross-origin isolated, so every browser user needs an HTTP origin that sends them. That origin is either a remote server or a process on localhost. |
| N-2 | `[ENG]` Node provides `SharedArrayBuffer`, `worker_threads`, `Atomics.wait` on any thread including the main one, and WebAssembly exception handling and tail calls without an isolation condition. The full profile can run with no server. `[SRC]` Every Stage 1 fixture already executes under Node Workers. |
| N-3 | Three deployment shapes follow. **DEP-A** browser, remote origin. **DEP-B** browser, localhost origin served by a Node Host (the UI prototype's shape). **DEP-C** Node alone: terminal REPL, batch compile, scripts, CI. A user without a cloud server has DEP-B and DEP-C. |
| N-4 | In DEP-B the Node Host can also be the browser image's route to host files and sockets (the UI specification already names it as the WebSocket-to-TCP relay). That is a capability of the *deployment*, not of the browser provider: the browser image still sees only what its provider offers (§4). |
| N-5 | Consequence for acceptance: "macOS is the sole reference platform" (CLAUDE.md) is unaffected; Node on macOS is an engine on that platform. The engine matrix owes a pinned Node row as a *deployment* engine, not only a probe engine. |

## 4. One host contract, two providers

Requirement IDs `H-n`. The Lisp side sees one contract. A provider is the
JavaScript that implements it for one host.

| ID | Requirement |
| --- | --- |
| H-1 | The Lisp-visible host contract is identical in the browser and under Node. Differences are confined to the provider and surface as capabilities present or absent, never as a different Lisp API. |
| H-2 | An absent capability signals an explicit unsupported condition (`outline.md:238` wording) or yields a value the Common Lisp standard permits for "unknown". It is never a fabricated native-looking value and never a silent no-op. |
| H-3 | Provider inputs are validated, snapshotted and frozen by an owner function in the style of `processConfiguration` (`runtime/wasm32/config.mjs`), and the provider records provenance per field as `browserConfiguration` does. |
| H-4 | Anything that can block without bound (terminal input, sockets, pipes, a slow remote fetch) goes through the FOREIGN state and the Atomics mailbox (`outline.md:187`) under both providers, so that GC admission and R2 interruptible I/O hold on Node exactly as in the browser. See Q-2 for the bounded-file-read shortcut. |
| H-5 | The file surface is the outline's virtual namespace (`outline.md:234–238`) under both providers. Under Node the namespace may be *mounted* on real directories; Lisp still sees namespace paths, a host-supplied current directory and a `ccl:` root. No provider exposes raw host paths that bypass the namespace. |
| H-6 | Provider selection is an owner decision at instantiation, recorded in the materialization or startup record. Generated code and images do not branch on the provider. |

Capability table. "Absent" means H-2 applies.

| Cap ID | Capability | CCL surface (main source) | Browser provider | Node provider |
| --- | --- | --- | --- | --- |
| CAP-ns-ro | Read-only namespace | `l1-streams`, `l1-pathnames`, loader | fetched named blobs | blobs or mounted directories (`fs` sync) |
| CAP-ns-rw | Writable store (Stage 3) | `compile-file`, `save-application` | OPFS `[ENG]` | memory or disk |
| CAP-ns-enum | List, delete, rename (Stage 3, gated) | `directory`, `delete-file`, `rename-file` | OPFS only `[ENG]` | mounted directories |
| CAP-stdio | Standard streams, terminal | `l1-streams`, `l1-boot-2` | absent; listener is page UI | fds 0/1/2, TTY |
| CAP-args | Command line | `*command-line-argument-list*` | owner-supplied list, default empty | `process.argv` tail |
| CAP-env | Environment, cwd, home, user, hostname | `linux-files`, `misc` | absent except namespace cwd and a virtual home (see CB-21) | `process.env`, `os.*`, mapped into the namespace |
| CAP-exit | Exit status | `quit` | absent; terminate Workers, report to page | `process.exit(n)` |
| CAP-signal | OS interrupt to break | `l1-lisp-threads`, trap support | absent; UI control posts the same interrupt | SIGINT on the main thread posts the interrupt |
| CAP-proc | External processes | `run-program` | absent | `child_process` `[ENG]`; asynchronous pipes need H-4 |
| CAP-sock | TCP/UDP, listen, DNS, interfaces | `library/sockets.lisp` | absent; WebSocket/fetch are a different, later surface | `net`, `dgram`, `dns`, `os.networkInterfaces()` `[ENG]`; all asynchronous, need H-4 |
| CAP-clock | Wall and monotonic time | `lib/time.lisp` | `Date.now`, `performance.now` (coarsened) | same, finer |
| CAP-cputime | CPU time, resource usage | `get-internal-run-time`, `time`, `room` | absent; wall clock substitutes only where the standard allows | `process.cpuUsage`, `resourceUsage` `[ENG]` |
| CAP-cpus | Logical processors | `cpu-count` | `navigator.hardwareConcurrency` (accepted, R2) | `os.availableParallelism()` `[ENG]` |
| CAP-image | Image source and name | `*heap-image-name*`, loader | namespace name of a fetched blob | namespace name of a mounted file |
| CAP-ui | Page surface: DOM, canvas, input, clipboard | CLIM IDE (`ui-overview.md`) | present | absent |
| CAP-ffi-native | Native C libraries, ObjC, JNI, GTK, pty, ELF/Mach-O tools | `%ff-call` users, `library/*` | absent | absent |
| CAP-ffi-wasm | Foreign Wasm modules (§6) | new | present | present |

`[SRC]` for the CCL-surface column: foreign-call density ranks
`level-1/linux-files.lisp` 132, `level-1/l1-numbers.lisp` 62 (libm; both
providers cover it through `Math`, last-bit differences possible),
`library/sockets.lisp` 43, `level-0/l0-cfm-support.lisp` 28, `l1-streams` 14,
`lib/time.lisp` 13.

## 5. Startup callback classification

Classes. **LIT** literal reset (accepted). **CFG** owner configuration
(accepted, R2). **RT** port-runtime internal: meaningful on both providers, owned
by the port's collector, thread or stream runtime, no host input. **HOST**
host-input value through §4. **DEFER** belongs to a subsystem not yet built;
record, do not implement. **EXCL** no meaning on either provider.

`[SRC]` Source forms read at the snapshot positions; native execution order is
ascending ordinal (audit 129: `restore-lisp-pointers` runs the reversed system
registry, equal to the snapshot's 34 ordinals).

| ID | Ord | Callback | What the native form does | Class | Browser | Node | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CB-0 | 0 | `*total-gc-microseconds*` | `malloc` of five timevals the kernel GC writes into | RT | same | same | The port's collector owns GC time. Represent as collector counters, not a foreign buffer; consumers (`gctime`, `room`) read them. 541b4a3f is unreviewed. |
| CB-1 | 1 | `*total-bytes-freed*` | `malloc` of 8 bytes, zeroed | RT | same | same | As CB-0. |
| CB-2 | 2 | `kernel-locks` | revives macptrs to two kernel recursive locks | RT/EXCL | — | — | D5 replaces kernel locks. Expected: no effect; record as replaced-by-D5, confirm no Lisp caller needs the macptrs. |
| CB-3 | 3 | `*fd-set-size*` | kernel import, `select()` bitmap size | EXCL | absent | absent | No `select` on either provider. Leave unbound or bind per H-2; audit consumers in `l1-streams`. |
| CB-4 | 4 | `*max-os-open-files*` | `getdtablesize` | EXCL | absent | absent | `[ENG]` Node exposes no equivalent. As CB-3. |
| CB-10 | 10 | `*lisp-start-timeval*` | `gettimeofday` into a foreign `:timeval` record | HOST | CAP-clock | CAP-clock | Needs a record representation decision (it is a macptr natively). Value from the provider's wall clock at start. |
| CB-12 | 12 | `initial-thread` | `init-thread-from-tcr` for the current TCR | RT | same | same | Threads stage (LL20). DEFER until then. |
| CB-18 | 18 | `*event-dispatch-task*` | installs the 3 Hz periodic task that flushes interactive streams | DEFER | — | — | Depends on periodic tasks and interactive streams; both providers need a timer path through H-4. |
| CB-19 | 19 | `*heap-image-name*` | kernel global | HOST | CAP-image | CAP-image | Namespace name under both providers. |
| CB-20 | 20 | `*command-line-argument-list*` | walks kernel `argv` | HOST | CAP-args | CAP-args | Owner-supplied list of strings; empty in the browser unless the embedder supplies one. |
| CB-21 | 21 | `*user-homedir-pathname*` | `(user-homedir-pathname)` | HOST | virtual home | CAP-env | CLHS: with no host argument the function never returns NIL, so the browser provider must supply a virtual home in the namespace (writable store root once it exists). |
| CB-23 | 23 | `init-logical-directories` | sets `home:` and `ccl:` translations | HOST | namespace | namespace | Follows CB-21 and the `ccl:` root of `outline.md:235`. Reads CB-21's effect: registry order matters here. |
| CB-26 | 26 | `reset-winners` | `clrhash` of a strong EQ compiler cache | RT | same | same | Proposed unit reviewed; qualification complete after audit 130. Acceptance is the user's. |
| CB-27 | 27 | `reset-db-files` | clears seven cached `.cdb` handles per interface directory | DEFER | — | — | §5.1. |
| CB-30 | 30 | `*static-cons-address*` | macptr to a kernel global | DEFER | — | — | Static conses are a kernel/GC facility the port has not scoped. Record; decide with the collector. |
| CB-31 | 31 | `*free-static-cons-address*` | as CB-30 | DEFER | — | — | As CB-30. |
| CB-32 | 32 | `startup-shutdown-processes` | re-creates threads for processes shut down at image save | DEFER | — | — | Application image save/restore is Stage 5. |

Requirement **S-1**: before another callback is implemented, the selection
record gains a `class` and a per-provider disposition for all 35 rows, reviewed
once, so that implementation effort goes only to RT and HOST rows whose
subsystem exists. **S-2**: later joins follow registry order (audit 129 finding,
already accepted by Codex in the winners-review README). **S-3**: a DEFER or
EXCL row is a recorded disposition with its reason and the consumer audit it
owes, not an open item counted against LL15.

### 5.1 Disposition of STAGE1-STARTUP-DB-R1 (and its follow-up 44531e64)

| ID | Statement |
| --- | --- |
| DB-1 | Recommend **withdraw as an implementation**. No interface directory exists in the Wasm profile (C-3), so natively-shaped RESET-DB-FILES iterates an empty list and stores nothing. |
| DB-2 | Record CB-27 as DEFER with reason "interface database not loaded; outline §05". It returns only if CAP-ffi-wasm later adopts wasm32 interface databases (FM-14), and then the callback's own Lisp body, compiled by the port's compiler over structure accessors, is the implementation — not a C leaf with an owner-admitted arena. |
| DB-3 | Audit-130 F1 (membership and complete-list checks not isolated) is moot if DB-1 is adopted. 44531e64 answers F1; Claude has not reviewed it and proposes not to, unless the user keeps the unit. |
| DB-4 | Worth keeping from the unit as harness practice, independent of its subject: complement-poisoned publication words, validate-everything-before-first-store, refusal cases that assert an unchanged image. |

## 6. Foreign Wasm modules (CAP-ffi-wasm)

Scope: calling code that was compiled to WebAssembly from another language —
C, C++, Rust, Zig — and, by the same mechanism, JavaScript host functions the
IDE needs. Not native libraries. Not Stage 1. U-3 fixes the memory model.

### 6.1 Requirements

| ID | Requirement |
| --- | --- |
| FM-1 | **Separate memory (U-3).** A foreign module instance has its own linear memory. It never receives a Lisp heap address. Arguments and results are scalars, or byte ranges copied between memories. Consequence: the moving collector needs no pinning for foreign calls, and a foreign module cannot corrupt the Lisp heap. |
| FM-2 | **FOREIGN bracket.** A Lisp thread enters FOREIGN before a foreign call and re-admits under D5 after it (`outline.md:187`), exactly as for host I/O. A thread inside foreign code cannot poll; the collector treats it as parked. `[SRC]` The TCR already carries `foreign_descriptor` and `c_stack_pointer` (`contracts/tcr.v2.json`). |
| FM-3 | **Two layers.** Lower: a typed call to a named export with i32/i64/f32/f64 arguments and results, plus copy-in/copy-out of byte ranges and access to the library's `malloc`/`free`. Upper: CCL's surface — `external-call`/`ff-call`-style forms, macptrs addressing *a foreign memory* (library identity plus offset), `rlet`/`pref`-style record access, `defcallback`. |
| FM-4 | **One adapter module per library.** Each Lisp function is its own Wasm module importing `env.memory` `[SRC]` (every generated `.wat` in the Stage 1 fixtures). Rather than give each of them a second memory import, a per-library adapter imports both memories and the library's exports, does copies with `memory.copy`, and calls Wasm-to-Wasm. This generalizes `runtime/wasm32/hash-adapter.wat`, which today carries one fixed eight-word signature. `[ENG]` Requires the multi-memory feature; see FM-12. |
| FM-5 | **Signatures from the binary.** Export and import names and function types come from the module's own sections; `runtime/wasm32/binary.mjs` already reads imports and exports `[SRC]`. No database is needed for scalar signatures. The binary cannot say which i32 is a pointer, a length or a handle: that comes from declarations (FM-14). |
| FM-6 | **Encodings are declared.** `outline.md:244`: "The foreign/host boundary uses declared encodings and payload schemas." String arguments name an encoding; the copy-in helper encodes, never guesses a storage width. |
| FM-7 | **No unwinding across the boundary.** The adapter catches everything a foreign call throws and raises a Lisp error carrying what is known. A Lisp THROW, RETURN-FROM or GO never passes through foreign frames; a callback that would do so is caught at the callback boundary. `[SRC]` Generated code already uses `catch_all_ref` in places, so a foreign exception would run Lisp cleanups but be misattributed without this rule. |
| FM-8 | **Callbacks.** `[ENG]` A C or C++ function pointer is an index into the library's own function table. Passing a Lisp function means growing that table and installing a trampoline of exactly the expected Wasm type; the trampoline re-admits into Lisp under D5 on the calling thread only. Callbacks from a thread Lisp does not own are unsupported. |
| FM-9 | **Thread ownership.** `[ENG]` A library built without atomics has unshared memory and belongs to the Worker that instantiated it. Policy choices, to be declared per library: one instance per Lisp Worker (separate state), or one owning Worker with calls funnelled through the mailbox. Libraries built with a pthreads runtime that expects its own worker pool are out of scope. |
| FM-10 | **Lifetime.** Foreign objects are integer handles or foreign-memory macptrs on the Lisp side. Release on collection uses the port's equivalent of `library/macptr-termination.lisp`; explicit release is always available. Dropping a library instance invalidates its macptrs detectably (generation in the library identity). |
| FM-11 | **Loading is digest-bound.** A foreign module is a named blob in the namespace under both providers, admitted by digest the way `bootstrap-install.mjs` admits generated modules, instantiated once per policy, and initialized (`_initialize` or `__wasm_call_ctors` `[ENG]`) before any export is callable. Its imports are an explicit, minimal set — a small WASI shim (clock, random, a stderr sink) — never a toolchain's JavaScript glue object. |
| FM-12 | **Engine features are qualified, not assumed.** Multi-memory, and the exception-handling encoding a C++ library was built with, each need an engine-matrix row for every deployment engine including Node (N-5). Fallback for FM-4 without multi-memory: a host copy helper in JavaScript, slower, same semantics. |
| FM-13 | **JavaScript host functions use the same lower layer.** DOM, canvas and clipboard calls for the IDE (CAP-ui) are typed imports with copied payloads. `[SRC]` "The main thread never runs Lisp" (`outline.md:187`), so page calls from a Lisp Worker are mailbox requests to the page; anything answered by a Promise is a mailbox request or, in the deferred profile, JSPI. |
| FM-14 | **Record layouts, later.** `pref` over C structs from a wasm32 library needs header translations for the wasm32 ABI. That is the one place `lib/db-io.lisp` and interface directories could return: wasm32 databases as named blobs (C-3's last sentence). It is optional, after FM-1…FM-11 work with hand-written declarations. |
| FM-15 | **Trust.** `outline.md:224`: "Untrusted code requires separate processes and memories." FM-1 gives separate memory; it does not give a separate process. A foreign module is trusted to the extent of the imports it is handed and the CPU it can burn. Do not claim sandboxing. |

### 6.2 Worked example: a C++ library

A tokenizer class. The Lisp forms are a **sketch of FM-3's upper layer; none of
these operators exist**.

```cpp
// C++ has no callable ABI across modules (mangled names, hidden `this`,
// private std::string layout). The library ships an extern "C" shim.
extern "C" {
  Tokenizer* tok_new()                                         { return new Tokenizer; }
  int32_t    tok_feed(Tokenizer* t, const char* p, int32_t n)  { return t->feed({p,(size_t)n}); }
  void       tok_free(Tokenizer* t)                            { delete t; }
}
// Build: wasi-sdk reactor or Emscripten STANDALONE_WASM; libc++ linked in;
// export malloc, free, memory and the shim; -fno-exceptions or -fwasm-exceptions;
// no pthreads; wasm32, not memory64.                                    [ENG]
```

```lisp
(open-wasm-library "tokenizer" :name "lib/tokenizer.wasm" :sha256 "…")  ; FM-11
(defun tokenize (string)
  (with-foreign-bytes ((p n) string :library "tokenizer" :encoding :utf-8) ; FM-1, FM-6
    (let ((h (wasm-call "tokenizer" "tok_new" :i32)))                      ; FM-3 lower
      (unwind-protect
           (wasm-call "tokenizer" "tok_feed" :i32 h :i32 p :i32 n :i32)    ; FM-2 bracket
        (wasm-call "tokenizer" "tok_free" :i32 h :void)))))
```

Sequence for one `tok_feed`: encode the string to UTF-8 in Lisp memory → adapter
calls the library's `malloc` → `memory.copy` Lisp→library → thread enters FOREIGN
→ direct Wasm call → D5 re-admission, roots reloaded → result boxed → library
`free`. The collector may run and move the Lisp string during the call; nothing
foreign refers to it.

C++-specific hazards, each `[ENG]`: static constructors do not run unless
`_initialize` is called (FM-11); an uncaught C++ exception surfaces as a foreign
Wasm exception (FM-7); Emscripten's default exception scheme needs JavaScript
glue and is excluded (FM-11); a library compiled with the legacy exception
encoding needs its own matrix row (FM-12).

### 6.3 Non-goals

Native `dlopen`/`%ff-call` to platform libraries; the ObjC, JNI and GTK bridges;
pty; ELF and Mach-O tooling; sharing the Lisp heap with foreign code; pthreads
libraries with their own worker pools; memory64 modules; depending on Component
Model runtime support. Interface-typed, copy-by-value calls are the *convention*
FM-1 already imposes and are Component-Model-shaped; adopting WIT as a
declaration format is left open (Q-7).

### 6.4 Proposed future test inventory (not an amendment to the Stage 1 inventory)

| ID | Test |
| --- | --- |
| FMT-1 | Scalar call round trip, all four value types, both placements, browser and Node. |
| FMT-2 | Byte-range copy in and out; non-ASCII and supplementary characters per `outline.md:244`. |
| FMT-3 | Collection forced during a foreign call moves the argument's Lisp source; result correct; no foreign reference to Lisp memory exists (checked by poisoning retired space, as the hash-table fixtures do). |
| FMT-4 | Foreign trap and foreign exception become Lisp errors; cleanups run once; TCR fully restored (the audit-127 full-TCR check). |
| FMT-5 | Lisp nonlocal exit attempted through a callback is refused at the boundary. |
| FMT-6 | Callback re-admission under D5 with a collection pending. |
| FMT-7 | Digest mismatch, missing `_initialize`, undeclared import and wrong signature each refuse before any call; remove-one-check mutants of the admission code each fail a directed case (audit-130 lesson). |
| FMT-8 | Two Workers, per-Worker instances: independent state; funnelled policy: serialized calls, interruptible wait (R2). |
| FMT-9 | Handle release on collection and on explicit free; use after library drop is detected. |

## 7. Effect on existing records if adopted

| ID | Record | Effect |
| --- | --- | --- |
| R-1 | `decisions.md` | New dated entry quoting U-2 and U-3; provider contract H-1…H-6 as a decision; CAP-ffi-wasm admitted as future scope. Registered document: regenerate through `tools/manage.py`. |
| R-2 | `outline.md` §05 | File-system table gains the provider column already implied by line 237; a host-capability table replaces per-feature prose; interface-database row gains FM-14's condition. |
| R-3 | `contracts/kernel-imports.v1` | Today profiled by suspension profile only `[SRC]`. Needs a provider dimension for the host-service rows, or a statement that provider differences live wholly behind the mailbox. Q-3. |
| R-4 | `stage0/engine-matrix.md` | Node as deployment engine (N-5); multi-memory and C++ exception-encoding rows (FM-12). |
| R-5 | `tests/wasm/stage1/startup-*/selection.json` | `class` and per-provider disposition for all 35 rows (S-1). |
| R-6 | `doc/WASM/evidence/index.json`, STATUS | STAGE1-STARTUP-DB-R1 and its follow-up marked withdrawn if DB-1 is adopted; packets stay retained as history. |
| R-7 | CLAUDE.md | No change needed. Codex's authorship, R6/R6a and the review rule apply unchanged. |

## 8. What this document does not claim

No execution was performed for it beyond the audits cited. Every `[ENG]` row is
unverified here. The capability table is a classification, not a schedule: it
does not move any capability into Stage 1, and it does not reopen accepted
units. Sockets and subprocesses under Node are expensive because their Node APIs
are asynchronous and CCL's are blocking; listing them as present under Node says
they are possible, not that they are planned.

## 9. Questions for the reviewer

| ID | Question | Claude's recommendation |
| --- | --- | --- |
| Q-1 | Is any CB row misclassified? Name the consumer in U1 source that shows it. | — |
| Q-2 | Under Node, may bounded namespace reads call `fs.*Sync` inside the Lisp Worker, bracketed by FOREIGN, instead of the mailbox? | Not at first. One protocol under both providers until a measurement shows the mailbox cost matters; then admit the shortcut only for operations that cannot block without bound, with R2 untouched. |
| Q-3 | Does the kernel-import census need a provider dimension (R-3), or can all 24 full-profile host-service rows keep one classification with provider differences behind the mailbox? | The latter, if H-1 holds; say so in the contract. |
| Q-4 | CB-0/CB-1: is there a Lisp consumer that needs the native foreign-buffer shape, or can `gctime`/`room` read collector counters? 541b4a3f chose an approach Claude has not read. | Counters, unless a consumer forces the buffer. |
| Q-5 | CB-10: what represents a `:timeval` record before FM-3 exists — a Lisp-side struct, or a port-owned pinned word pair? | Port-owned pinned words; revisit with FM-3. |
| Q-6 | FM-4: is a per-library adapter the right seam given lazy installation and the digest-bound installer, or should the generic adapter take the library as data? | Per-library, generated from the binary's export section, admitted by digest like any module. |
| Q-7 | Should declarations for FM-5/FM-14 use WIT, a Lisp `def-foreign` form, or both? | Lisp form first; WIT import later if libraries ship it. |
| Q-8 | Is there any accepted Stage 1 unit whose claims change under H-1…H-6? | Claude found none; `browser-config.mjs` becomes the browser provider's first member and needs a Node sibling for CAP-cpus. |
| Q-9 | DB-1…DB-3: agree to withdraw? If not, state the consumer that needs RESET-DB-FILES before CAP-ffi-wasm exists. | Withdraw. |
| Q-10 | Which stage owns the Node provider's first deliverable (namespace mount plus stdio plus args, enough for DEP-C batch use)? | Alongside the Stage 1 read-only namespace, since the fixtures already run there; stdio and args are small. The user decides. |
