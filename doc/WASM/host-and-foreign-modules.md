# Host providers, startup callback scope and foreign Wasm modules

```
DOC-ID        HOSTFM-P2 (P1 was 0ac8691c; P2 amends it after Codex's review — see §10)
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
| CAP-ns-ro | Read-only namespace | `l1-streams`, `l1-pathnames`, loader | fetched named blobs | blobs or mounted directories, served through the mailbox (H-4, Q-2); already-resident bytes need no OS path |
| CAP-ns-rw | Writable store (Stage 3) | `compile-file`, `save-application` | a virtual store; OPFS is one candidate `[ENG]`; availability is per deployment | memory or disk |
| CAP-ns-enum | List, delete, rename (Stage 3, gated) | `directory`, `delete-file`, `rename-file` | within the virtual store only | mounted directories |
| CAP-stdio | Lisp standard streams | `l1-streams`, `l1-boot-2` | present: listener input and output routed to the page | present: routed by the Node owner to fds 0/1/2 |
| CAP-tty | POSIX fds and terminal behaviour | `l1-streams`, `pty` | absent | owner-side only; interactive terminal needs stream and LL20 suspension support |
| CAP-args | Command line | `*command-line-argument-list*` | owner-supplied list, default empty | `process.argv` tail |
| CAP-env | Environment, cwd, home, user, hostname | `linux-files`, `misc` | absent except namespace cwd and a virtual home (see CB-21) | `process.env`, `os.*`, mapped into the namespace |
| CAP-exit | Exit status | `quit` | absent; terminate Workers, report to page | an exit *request* to the Node owner, which flushes, terminates sibling Workers and sets the status. `[ENG]` `process.exit` inside a Worker stops only that Worker. |
| CAP-signal | OS interrupt to break | `l1-lisp-threads`, trap support | absent; UI control posts the same interrupt | SIGINT on the main thread posts the interrupt |
| CAP-proc | External processes | `run-program` | absent | `child_process` `[ENG]`; asynchronous pipes need H-4 |
| CAP-sock | TCP/UDP, listen, DNS, interfaces | `library/sockets.lisp` | absent; WebSocket/fetch are a different, later surface | `net`, `dgram`, `dns`, `os.networkInterfaces()` `[ENG]`; all asynchronous, need H-4 |
| CAP-clock | Wall and monotonic time | `lib/time.lisp` | `Date.now`, `performance.now` (coarsened) | same, finer |
| CAP-cputime | CPU time, resource usage | `get-internal-run-time`, `time`, `room` | absent; wall clock substitutes only where the standard allows | `process.cpuUsage`, `resourceUsage` `[ENG]` |
| CAP-cpus | Processor count | `cpu-count` | `navigator.hardwareConcurrency` (accepted, R2; provenance kept) | `os.availableParallelism()` `[ENG]` — a scheduling-capacity estimate, recorded as such |
| CAP-image | Image source and name | `*heap-image-name*`, loader | namespace name of a fetched blob | namespace name of a mounted file |
| CAP-ui | Page surface: DOM, canvas, input, clipboard | CLIM IDE (`ui-overview.md`) | present *on the Page*; the Lisp Worker reaches it by proxy (FM-13) | absent |
| CAP-ffi-native | Native C libraries, ObjC, JNI, GTK, pty, ELF/Mach-O tools | `%ff-call` users, `library/*` | absent | absent |
| CAP-ffi-wasm | Foreign Wasm modules (§6) | new | present | present |

`[SRC]` for the CCL-surface column: foreign-call density ranks
`level-1/linux-files.lisp` 132, `level-1/l1-numbers.lisp` 62 (libm; governed by
the accepted LL16 numeric boundary — calling `Math` does not by itself establish
libm coverage, coercion behaviour or FP conditions; classify each call),
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
| CB-0 | 0 | `*total-gc-microseconds*` | `malloc` of five timevals the kernel GC writes into | RT | same | same | `[SRC]` `gctime` (`lib/time.lisp:30–43`) `memmove`s the five-timeval buffer and returns five values. Replace the consumer with one that reads collector counters and keeps the five-value contract; do not impose macOS timeval buffers on the port, and do not integrate 541b4a3f merely to empty the list. |
| CB-1 | 1 | `*total-bytes-freed*` | `malloc` of 8 bytes, zeroed | RT | same | same | `[SRC]` The only Lisp read is under `#+not-any-more` (`level-0/l0-misc.lisp:118`); natively the kernel writes it (it is in the x86 kernel-symbol list). No live Lisp consumer: nothing to implement until one exists. |
| CB-2 | 2 | `kernel-locks` | revives macptrs to two kernel recursive locks | RT (replaced) | — | — | D5 replaces kernel locks. Closed only when consumer routing is proved: a leftover use must not see nil locks. |
| CB-3 | 3 | `*fd-set-size*` | kernel import, `select()` bitmap size | EXCL | absent | absent | No `select` on either provider. `[SRC]` Still consumed at `linux-files.lisp:1326` (`%stack-block ((in-fd-set *fd-set-size*))`). Closed only when that path is excluded or replaced; never a fabricated size. |
| CB-4 | 4 | `*max-os-open-files*` | `getdtablesize` | EXCL | absent | absent | `[ENG]` Node exposes no equivalent. `[SRC]` Consumed at `linux-files.lisp:1137` (fd-closing loop before `%execvp`), which belongs to CAP-proc. As CB-3. |
| CB-10 | 10 | `*lisp-start-timeval*` | `gettimeofday` into a foreign `:timeval` record | HOST | CAP-clock | CAP-clock | `[SRC]` Repository search finds the symbol only at its definition (`l1-lisp-threads.lisp:79`): no live consumer. Do not manufacture a record to implement the initializer. If the port needs a start timestamp, use a port clock value with explicit units, wall time distinguished from elapsed. |
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

Requirement **S-1**: before another callback is implemented, **one new
classification manifest** — keyed by snapshot identity and ordinal and binding
the original selection's hash — gives a `class` and a per-provider disposition
for all 35 rows, reviewed once. The existing `startup-*/selection.json` files are
hash-pinned by retained packets `[SRC]` and are not edited, so that implementation effort goes only to RT and HOST rows whose
subsystem exists. **S-2**: later joins follow registry order (audit 129 finding,
already accepted by Codex in the winners-review README). **S-3**: a DEFER or
EXCL row records its reason and the consumer audit it owes. It is **closed** only
when the selected bootstrap profile omits the subsystem or its consumers use a
qualified replacement; until then it remains an unresolved dependency under
`S1-LL15-a:initializers` (`stage1/inventory.json:624`). No gate change.

### 5.1 Disposition of STAGE1-STARTUP-DB-R1 (and its follow-up 44531e64)

| ID | Statement |
| --- | --- |
| DB-1 | Recommend **withdraw as an implementation**. Corrected in P2: excluding `.cdb` loading (C-3) does not make the directory list empty. `[SRC]` `ensure-interface-dir` builds directory metadata without opening a database (`lib/foreign-types.lisp:161–168`); `[RUN]` a native image holds one directory, `:LIBC`, with no database open. The reset's effect is nil-to-nil as long as nothing opens a `.cdb`. Owed before closure: establish that the selected image has no live handle, or exclude the subsystem (S-3). |
| DB-2 | Record CB-27 as DEFER with reason "interface database not loaded; outline §05". Foreign declarations (FM-5, FM-14) do not by themselves require the native interface database to return. If wasm32 databases are ever adopted, the callback's own Lisp body, compiled by the port's compiler over structure accessors, is the implementation — not a C leaf with an owner-admitted arena. |
| DB-3 | Audit-130 F1 (membership and complete-list checks not isolated) is moot if DB-1 is adopted. 44531e64 answers F1; Claude has not reviewed it and proposes not to, unless the user keeps the unit. |
| DB-4 | Worth keeping from the unit as harness practice, independent of its subject: complement-poisoned publication words, validate-everything-before-first-store, refusal cases that assert an unchanged image. |

## 6. Foreign Wasm modules (CAP-ffi-wasm)

Scope: calling code that was compiled to WebAssembly from another language —
C, C++, Rust, Zig — and, by the same mechanism, JavaScript host functions the
IDE needs. Not native libraries. Not Stage 1. U-3 fixes the memory model.

### 6.1 Requirements

| ID | Requirement |
| --- | --- |
| FM-1 | **Separate memory (U-3).** A foreign module instance has its own linear memory. It never receives a Lisp heap address. Arguments and results are scalars, or byte ranges copied between memories. Consequence: the moving collector needs no pinning for the foreign callee. The trusted adapter and callback code still touch Lisp memory and must obey the bounds and root protocols; separation alone does not prove the heap safe. |
| FM-2 | **FOREIGN bracket on every foreign entry.** Allocator, destructor, constructor, start function and the principal export alike: each is foreign execution that may call imports, grow memory, throw, trap or not return, and each is entered from FOREIGN and followed by D5 admission (`outline.md:187–191`, `decisions.md:260,304`). Lisp bytes are copied only while admitted, with no collecting call between obtaining the Lisp address and the copy; after any re-entry, roots are reloaded and addresses recomputed. Callbacks make the reverse transitions, on errors too. A thread inside foreign code cannot poll; the collector treats it as parked. FOREIGN is not interruptibility: CPU-bound foreign work cannot be interrupted by a mailbox word. `[SRC]` The TCR already carries `foreign_descriptor` and `c_stack_pointer` (`contracts/tcr.v2.json`). |
| FM-3 | **Two layers.** Lower: a typed call to a named export with i32/i64/f32/f64 arguments and results, plus copy-in/copy-out of byte ranges and access to the library's `malloc`/`free`. Upper: CCL's surface — `external-call`/`ff-call`-style forms, macptrs addressing *a foreign memory* (library identity plus offset), `rlet`/`pref`-style record access, `defcallback`. |
| FM-4 | **One adapter per library.** Each Lisp function is its own Wasm module importing `env.memory` `[SRC]` (every generated `.wat` in the Stage 1 fixtures). Rather than give each of them a second memory import, a per-library adapter imports both memories and the library's exports, does copies with `memory.copy`, and calls Wasm-to-Wasm. This generalizes `runtime/wasm32/hash-adapter.wat`, which today carries one fixed eight-word signature. P2: FM-7 puts a JavaScript frame between Lisp and foreign frames for any export that can trap; that frame can also copy between memories, so **multi-memory is an optimization for admitted non-trapping exports, not a baseline dependency**. Adapters are generated from binary types *and* explicit pointer/ownership declarations. |
| FM-5 | **Signatures from the binary.** Export and import names and function types come from the module's own sections; `runtime/wasm32/binary.mjs` already reads imports and exports `[SRC]`. No database is needed for scalar signatures. The binary cannot say which i32 is a pointer, a length or a handle: that comes from declarations (FM-14). |
| FM-6 | **Encodings are declared.** `outline.md:244`: "The foreign/host boundary uses declared encodings and payload schemas." String arguments name an encoding; the copy-in helper encodes, never guesses a storage width. |
| FM-7 | **Traps and exceptions are different, and neither unwinds across the boundary.** `[RUN]` Under the pinned Node a `try_table`/`catch_all` catches a Wasm `throw` but an `unreachable` or out-of-bounds access escapes it as `WebAssembly.RuntimeError` (Codex's probe and Claude's independent one agree; the exception-handling specification says traps are not caught). A direct Wasm-to-Wasm call therefore cannot turn a foreign trap into a Lisp error, and the trap would bypass Lisp cleanups too. Baseline: each foreign entry passes through a JavaScript boundary *inside* the live Lisp call that catches thrown exceptions and traps and rethrows a catchable exception on the port's tag; a library that trapped is invalidated, not reused. Direct calls are admitted only for exports declared non-trapping, with fatal handling defined if the declaration is false. A Lisp THROW, RETURN-FROM or GO never passes through foreign frames; a callback that would do so is caught at the callback boundary. `[SRC]` Generated code already uses `catch_all_ref` in places, so a foreign exception would run Lisp cleanups but be misattributed without this rule. |
| FM-8 | **Callbacks.** `[ENG]` A C or C++ function pointer is an index into the library's own function table. Passing a Lisp function means growing that table and installing a trampoline of exactly the expected Wasm type; the trampoline re-admits into Lisp under D5 on the calling thread only. P2: the library must export or import a table with sufficient limits, or offer a registration ABI — not every library has a growable table. Each registered Lisp callback is a collector-visible root until deregistered, and table handles are versioned. A Lisp error inside a callback never throws through the foreign frame: it returns a declared error result or is deferred to the caller's boundary. Callbacks from a thread Lisp does not own are unsupported. |
| FM-9 | **Thread ownership.** `[ENG]` An instance whose memory is unshared cannot leave the Worker that instantiated it (the determinant is the memory's shared flag, not whether the code uses atomic instructions). Worker affinity is the selected policy in every case; funnelled calls need a stated owner-thread and re-entrancy rule. Policy choices, to be declared per library: one instance per Lisp Worker (separate state), or one owning Worker with calls funnelled through the mailbox. Libraries built with a pthreads runtime that expects its own worker pool are out of scope. |
| FM-10 | **Lifetime.** Foreign objects are integer handles or foreign-memory macptrs on the Lisp side. Release on collection uses the port's equivalent of `library/macptr-termination.lisp`; explicit release is always available. Dropping a library instance invalidates its macptrs detectably (generation in the library identity). P2: explicit release invalidates the handle and suppresses its finalizer, so nothing is freed twice; a library generation does not detect reuse of a freed offset inside a live instance, so allocation handles carry their own validity; finalization is queued to the owning Worker outside the collector's critical section. |
| FM-11 | **Loading is digest-bound.** A foreign module is a named blob in the namespace under both providers, admitted by digest the way `bootstrap-install.mjs` admits generated modules, instantiated once per policy, and initialized exactly once, under FM-2's bracket, by the convention its declaration names (`_initialize`, a constructor export, or the start section `[ENG]` — not every module has `_initialize`) before any export is callable. The admission record binds the declared ABI, initialization convention, memory and table limits and the import set. No promise of arbitrary C++ binary compatibility. Its imports are an explicit, minimal set — a small WASI shim (clock, random, a stderr sink) — never a toolchain's JavaScript glue object. |
| FM-12 | **Engine features are qualified, not assumed.** The exception-handling encoding a C++ library was built with needs an engine-matrix row for every deployment engine including Node (N-5); multi-memory needs one only if FM-4's optimization is taken. Copy and view behaviour is requalified after foreign memory growth. |
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

Sequence for one `tok_feed` (P2, corrected per FM-2 and FM-7): encode the string
to UTF-8 in Lisp memory → **FOREIGN{** library `malloc` **}** → admit, reload
roots, recompute the Lisp byte address → copy Lisp→library with no collecting
call in between → **FOREIGN{** `tok_feed` through the catching boundary **}** →
admit, reload roots, box the result → **FOREIGN{** library `free` **}**, on the
failure path as well. The collector may run and move the Lisp string during any
bracket; nothing foreign refers to it. P1 had `malloc` and `free` outside the
bracket and the copy inside it; both were wrong.

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
| FMT-3 | Collection forced during a foreign call — from another thread or from an explicit callback, while foreign execution is active — moves the argument's Lisp source; result correct; no foreign reference to Lisp memory exists (checked by poisoning retired space, as the hash-table fixtures do). |
| FMT-4 | Foreign *exception* and foreign *trap*, tested separately against the chosen FM-7 boundary: each becomes a Lisp error, cleanups run once, TCR fully restored (the audit-127 full-TCR check), and the trapped library is refused afterwards. |
| FMT-5 | Lisp nonlocal exit attempted through a callback is refused at the boundary. |
| FMT-6 | Callback re-admission under D5 with a collection pending. |
| FMT-7 | Digest mismatch, missing initialization where the declared convention requires it, initialization failure, undeclared import and wrong signature each refuse before any call; start execution is inside the bracket tests; remove-one-check mutants of the admission code each fail a directed case (audit-130 lesson). |
| FMT-8 | Two Workers, per-Worker instances: independent state; funnelled policy: serialized calls, interruptible wait (R2). |
| FMT-9 | Handle release on collection and on explicit free; explicit free followed by collection frees once; offset reuse is detected; callback deregistration; finalization runs on the owning Worker; use after library drop is detected. |

## 7. Effect on existing records if adopted

| ID | Record | Effect |
| --- | --- | --- |
| R-1 | `decisions.md` | New dated entry quoting U-2 and U-3; provider contract H-1…H-6 as a decision; CAP-ffi-wasm admitted as future scope. Registered document: regenerate through `tools/manage.py`. |
| R-2 | `outline.md` §05 | File-system table gains the provider column already implied by line 237; a host-capability table replaces per-feature prose; interface-database row gains FM-14's condition. |
| R-3 | `contracts/kernel-imports.v1` | Today profiled by suspension profile only `[SRC]`. Needs a provider dimension for the host-service rows, or a statement that provider differences live wholly behind the mailbox. Q-3. |
| R-4 | `stage0/engine-matrix.md` | Node as deployment engine (N-5); multi-memory and C++ exception-encoding rows (FM-12). |
| R-5 | new classification manifest | One new file binding the original selection hash (S-1). Retained `selection.json` inputs are untouched. |
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
| Q-8 | Is there any accepted Stage 1 unit whose claims change under H-1…H-6? | Claude found none; existing executions keep their scope and gain no Node or provider-neutral claim; `browser-config.mjs` becomes the browser provider's first member and needs a Node sibling for CAP-cpus. |
| Q-9 | DB-1…DB-3: agree to withdraw? If not, state the consumer that needs RESET-DB-FILES before CAP-ffi-wasm exists. | Withdraw. |
| Q-10 | Which stage owns the Node provider's first deliverable (namespace mount plus stdio plus args, enough for DEP-C batch use)? | Alongside the Stage 1 read-only namespace, since the fixtures already run there; stdio and args are small. The user decides. |

## 10. Review record (P1 → P2)

Codex reviewed P1 (0ac8691c) in `doc/WASM/host-and-foreign-modules-review.md`,
uncommitted when Claude read it, sha256
`f77afb260e8ae222076f79048fa365dc416cf79f759c8dfa5ca49d862be124ab`. Verdict: AMEND before adoption.
Claude verified the review's factual claims before accepting them.

| Codex item | Claude's verification | Disposition in P2 |
| --- | --- | --- |
| Finding 1 (P1): a Wasm catch cannot contain a foreign trap | `[RUN]` Independent probe under Node v25.6.1: `catch_all` returned 1 for a `throw`; `unreachable` and an out-of-bounds load each escaped as `RuntimeError`. Codex is right; P1's FM-7 and FMT-4 were wrong. | FM-7, FMT-4, FM-4, FM-12 rewritten. Added consequence Codex did not state: with a JavaScript boundary in the baseline, multi-memory stops being a dependency. |
| Finding 2 (P1): allocator calls escape the FOREIGN protocol | `[SRC]` `decisions.md:260,304` and `outline.md:187–191` read as cited. P1's sequence also copied Lisp bytes while in FOREIGN, which is the same error from the other side. | FM-2 and the §6.2 sequence rewritten. |
| Finding 3 (P2): do not edit retained selection inputs | `[SRC]` `startup-resets/selection.json` hashes to 24492ad2…, and the database packet pins both selection files. | S-1, R-5: new overlay manifest. |
| Finding 4 (P2): deferral does not discharge a dependency | `[SRC]` `stage1/inventory.json:624` reads as cited. | S-3 rewritten. |
| Q-1, Q-4, Q-5 consumer audits | `[SRC]` `*total-bytes-freed*` read only under `#+not-any-more`; `*lisp-start-timeval*` found only at its definition; `gctime` copies the five-timeval buffer. | CB-0, CB-1, CB-10 rewritten; CB-2, CB-3, CB-4 now cite the live consumers. |
| DB-1 amendment: `.cdb` exclusion does not empty the directory list | `[RUN]` Native image: one directory, `:LIBC`, no database open. `[SRC]` `foreign-types.lisp:161–168` as cited. P1's "iterates an empty list" was wrong. | DB-1, DB-2 rewritten; withdrawal stands, with the no-live-handle condition owed. |
| CAP-exit: `process.exit` in a Worker | `[ENG]` Consistent with Node's documented behaviour; not executed here. | CAP-exit rewritten as an owner request. |
| CAP-ns-ro, CAP-ns-rw, CAP-ns-enum, CAP-stdio, CAP-cpus, CAP-ui, the `Math` paragraph, FM-1, FM-8, FM-10, FM-11, FMT-3, FMT-7, FMT-9, Q-8 | Read against the outline and the accepted units; no contrary evidence. | Adopted as written above. CAP-stdio is split into CAP-stdio and CAP-tty. |
| FM-9: affinity "is not a consequence of absence of atomic instructions" | Partly. The determinant is the memory's shared flag, as Codex implies; but an instance with unshared memory genuinely cannot move between Workers, so for such a library affinity is forced, not only chosen. | FM-9 states both. |
| U-1…U-4, N-1, N-2 marked UNVERIFIED | Correct labels: the first are relayed conversation, the second are unexecuted engine statements. | Unchanged. |

Still open for the user after P2: adoption of H-1…H-6 and the provider split;
withdrawal of STAGE1-STARTUP-DB-R1 and 44531e64; not integrating 541b4a3f
(Codex's own review now advises against it); who authors the classification
manifest; and Q-10's staging of the first Node deliverable.
