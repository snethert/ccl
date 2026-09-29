# Startup latency is blocking

User correction, 28 September 2026: “this is absurd. either startup is instant
or a huge problem.” The browser foreign-function delivery demonstrates functional
execution. It does **not** establish an acceptable launch path. Increasing a test
timeout is a diagnostic action, not a startup fix. Further foreign-layer breadth
must not displace this startup problem.

## What the executed path does

`tests/wasm/stage1/loader-target/boot-worker.mjs` admits the level-0 heap, admits
both code archives, calls the real `%TOPLEVEL-FUNCTION%`, then target-loads 81
runtime files before READY. The separate FFI witness is loaded after READY.
Every fresh test Worker repeats this bootstrap. It has no initialized-runtime
launch artifact to restore.

The adopted definition of [successful boot1](../host-and-foreign-modules.md#11-adoption-and-amendments--25-september-2026)
means completion of the ordered level-1 load and its initializers. It does not
mean that an initialized boot image has been saved. General application saving
was scheduled for Stage 5. That scheduling does not make this launch cost
acceptable. An initialized runtime launch artifact and its safe re-entry path
are missing; general application save/restore remains a separate obligation.

The prior [startup census](../stage1/startup-execution-results.md) counted
44,724,264 Lisp calls and measured 27.631 seconds to READY in an isolated Node
run. The current browser diagnostics execute the same bootstrap architecture.
They are not a new full census and do not imply the exact old call count still
holds after later compiler changes.

## Comparable complete runs

The user correctly rejected comparing Chromium startup against Firefox's full
startup-plus-test duration. A fresh sequential run now measures the same phases
in Chromium and Firefox, then WebKit separately with identical binary inputs
and unchanged Worker/runtime/timing sources, without overlapping builds,
browser tests or diagnostic probes. [Bound results](startup-comparison-results.json).

| Phase | Chromium 145.0.7632.6 | Firefox 146.0.1 | WebKit 26.0 |
| --- | ---: | ---: | ---: |
| Preparation before Lisp entry | 8.249 s | 13.718 s | 14.922 s |
| Lisp initialization to READY | 14.676 s | 468.115 s | 392.311 s |
| **Total startup to READY** | **22.925 s** | **481.833 s** | **407.233 s** |
| Post-READY FFI witness and cleanup | 6.010 s | 32.061 s | 16.450 s |
| Startup plus FFI witness | 28.935 s | 513.894 s | 423.683 s |
| Runtime archive materialization/compilation (within preparation) | 1.823 s | 5.567 s | 0.731 s |

Startup begins at the host launch request, before input preload and Worker
creation, and ends when Lisp signals ProcessReady. It excludes building Lisp
sources, launching the browser application, initial page navigation and directed
input-refusal tests. Preparation plus Lisp initialization equals total startup;
the FFI witness begins after READY. The archive subphase includes hashing and
validation and excludes boot archive compilation; it is not a pure or complete
Wasm compiler timer. All three runs return the same 81 runtime loads and pass the
61-row FFI witness. These are one observation per engine, not medians.

Firefox startup is 21.0 times Chromium's in these observations. Most of the
Firefox delay occurs in Lisp initialization, after the preparation phase.
The timing isolates that phase; it does not yet establish the underlying cause.
This supersedes the earlier mismatched browser comparison. Startup remains
unresolved; no performance acceptance follows from successful correctness checks.

The native Lisp reference takes **0.118 s median** for LOAD plus the same 61
result checks, excluding startup (three fresh-process runs: 0.133195, 0.116676,
0.117975 s). It models the foreign-library operations in Lisp, so this is **not**
an equivalent native FFI/foreign-boundary GC benchmark and must not be used to
claim a native-versus-Wasm FFI slowdown ratio.
[Native reference timing](native-reference-timing.json).

## Earlier diagnostic measurements

The ordinary browser FFI run completes in all four engines with 61 equal Lisp
rows, 99 foreign entries, 74 FOREIGN collections and nine RUNNING collections.
Firefox takes approximately nine minutes for the complete run, including the
post-READY witness; its first attempt exceeded the three-minute test limit.
The subsequent ten-minute limit allowed diagnosis and completion. It grants
no performance acceptance. WebKit also takes minutes.

A short phase probe uses the shared Worker's existing timing capability. It
changes neither the Lisp sources nor initializers and does not skip a load:

| Phase | Chromium | Firefox |
| --- | ---: | ---: |
| Runtime archive compilation | 1.934 s | 6.901 s |
| Runtime archive admission, including compilation | 3.129 s | 7.905 s |
| Lisp-start to READY | 16.046 s | probe ended before READY |
| Lisp execution excluding measured child services | 14.328 s | incomplete |
| `l1-cl-package` load | 0.074 s | 1.728 s |
| `l1-clos` load | 0.527 s | 7.015 s |
| `l1-unicode` load | 0.270 s | 4.018 s |

The Chromium probe completes the FFI witness too. The Firefox probe is explicitly
limited to 45 seconds and reaches `l1-streams`; it is not a failed correctness
run or a complete startup timing. A separate 60-second call trace reaches four
million observed calls. A read-only root sampler also observes advancing loader
state. These rule out simply treating the original timeout as a dead Worker.

The phase probes overlapped another engine's qualification run, so their wall
times are diagnostic, not an isolated benchmark or a statistically established
engine ratio. They locate substantial cost in ordinary Lisp initialization,
beyond archive compilation and provider work. They do not yet explain every
engine-specific slowdown. Raw probes, source recipes and original failures are
retained with [the browser result binding](foreign-browser-results.json).

## Required next delivery

1. Produce an initialized runtime artifact once per bound compiler/runtime/input
   identity. Keep the complete cold bootstrap as its build and regression proof.
   A normal launch must not replay the 81-file runtime load sequence.
2. Reconstruct the collector owner, code-entry mapping, root blocks, tables and
   host capabilities in a fresh Worker. Retain ordinary Lisp roots, closures,
   packages and code identities. Do not serialize engine stacks or JavaScript
   handles, copy a live Worker blindly, repair bindings, or skip required resets.
3. Keep process-once initialization distinct from fresh-Worker setup. Restore two
   independent instances, prove their mutation independence and moving collection,
   then execute the existing foreign witness through ordinary post-READY loading.
   This is not multi-Worker D5 acceptance.
4. Measure bootstrap production, cold launch, already-resident code launch and
   the FFI witness separately. Any compiled-code caching must be explicit and
   identity-bound; do not hide compilation in a reported “instant” launch.
5. Demonstrate the user's instant-start requirement before closing this blocker.
   The present correctness pass, a longer timeout, and earlier Stage 1 acceptance
   do not close it. Exact latency criteria still need an explicit measured
   definition; no arbitrary numeric budget is silently adopted here.

This is a concrete missing launch path, not a completed snapshot implementation
or an acceptance of slow startup. No FMT, LL or Stage 2 completion credit is taken.
