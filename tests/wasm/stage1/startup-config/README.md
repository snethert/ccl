# Browser startup configuration

This auxiliary unit implements five nonliteral startup effects: host page size,
clock units per second, nanoseconds per tick, listener stack defaults and spin
settings. It carries no LL15 credit. The 35-row retained callback snapshot keeps
all thirteen accepted literal resets, these five selected adaptations, and
seventeen unresolved callbacks. Native file descriptors, locks, pathname and
process services are not assigned fictitious browser values.

`browserConfiguration` runs inside an actual browser Worker. It reads
`navigator.hardwareConcurrency`, constructs one Wasm memory page to obtain
65,536 bytes, and checks that `performance.now()` supplies finite nondecreasing
samples. Clock units are explicitly milliseconds (1,000 per second), not a
measurement of timer resolution or native `sysconf`. Lisp stack defaults and
an optional override are supplied by the owner; browser JavaScript stack limits
are neither observable here nor substituted for them. The logical processor
count is the browser's report, which may be reduced for privacy or availability.
No Worker scheduler, timer callback or native stack allocation is implemented.

The source contracts are the [HTML hardware-concurrency getter](https://html.spec.whatwg.org/multipage/workers.html#dom-navigator-hardwareconcurrency),
[High Resolution Time](https://www.w3.org/TR/hr-time/), and
[Wasm memory](https://webassembly.github.io/spec/core/syntax/types.html#memory-types).
This uses the existing 64 KiB Wasm memory-page profile, not custom page sizes.

`processConfiguration` validates a complete owner input, snapshots it, clamps
the clock rate to at least 1,000, computes the integer nanosecond period and
halves a positive stack override with FLOOR. Generated code installs the
selected global values; it leaves all three stack defaults intact for a
nonpositive override and computes the single/multiple-CPU spin choice itself.
The last callback returns the timeout symbol, as native `%defglobal` does,
rather than the zero stored into it. This return-identity detail was exposed
and corrected during development.

Every replay reads each selected form at the original retained source position
from pristine U1, checks its name against the actual callback registry, and
compiles that original body natively after replacing exactly its external
page-size, clock-rate, kernel-stack-size or CPU-count read with the case input.
The nanosecond callback reads the global set by the preceding clock callback.
Native MAX, FLOOR, IF, SETQ and `%defglobal` perform the actual computation;
the native oracle does not call the proposed JS owner. These are source-derived
callbacks with explicit host-input substitutions, not executions of untouched
registered native callbacks. Original and substituted forms are retained.
Global state is restored on every exit. An independent Python model checks
every native answer before execution in the target.

Thirty-five directed/seeded configurations cover negative and zero clock input,
the 1,000 clamp boundary, fractional integer divisions, positive/zero/negative
stack overrides, odd maximum fixnums, defaults and multiple CPU reports. A
thirty-sixth comes from the real browser Worker before native compilation.
Each runs with two dirty starts, below and above 2 GiB, through seven unchanged-
compiler modules and the integrated digest-bound schedule installer. Both
Node and the pinned Chromium execute identical cases and records, with a fresh
Worker per placement. The browser is pinned Chromium 145.0.7632.6 from the
accepted portability packet; this is not an engine-matrix qualification.
The browser probe is repeated during replay; a changed report requires a new
qualification rather than silently reusing the retained input.

Each generated entry restores its caller/root/control/allocation state. The
oracle checks all other image bytes, the binding vector, unused allocation
area, TSP and CSP regions. It permits temporary writes within the active value
stack and checks restored pointers there; it is not a memory sandbox. No
allocation or collection occurs during these generated callbacks. Owner symbols
are writable globals with zero binding indices, supplied by identity rather
than reconstructed from production packages. A changed tick value prevents its
dependent callback from completing. Missing modules, malformed configuration,
missing completion and no-load paths refuse without ready; failure is terminal.

Runtime faults target the arithmetic policy, browser reads, generated spin
value and completion, and an extra binding-vector write. Publication controls
remove cases, returns, effects, completion, installed digests and write checks.
The portable assertion helper compares object keys without relying on insertion
order, and all fault cases require their focused diagnostic.

```
python3 tests/wasm/stage1/startup-config/run.py --evidence ../ccl-evidence --output /new/startup-config
python3 tests/wasm/stage1/startup-config/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-startup-config-r1 --output /new/startup-config-replay
```

No compiler/runtime/kernel source is integrated by this proposal. Native R6/R6a
is reused by exact unchanged compiler hash. This is a bounded process-
configuration adaptation, not a bound on the native callback dispatcher or its
future registrations. Production symbol ownership, the other seventeen
callbacks, emitted definition effects, condition activation and complete
bootstrap membership remain open before LL15 and LL14.
