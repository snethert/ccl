# Direct-call startup experiment: rejected

The user adopted Claude's supplied rollback recommendation on 27 September
2026. Retain the audit-190 implementation at `824f060d`: separate boot and
runtime archives, ordinary indirect calls, seven product modules and eleven
instances at READY. The combined core, guarded dispatch, specialized entries
and fixed-core sealing are rejected for this pass.

This closes the work by user-directed rejection. It does **not** claim that
all P-6a–d qualifications or ablations were completed. The earlier requirement
to finish those items is superseded by the rollback instruction. No prototype
implementation is accepted, and no Claude process was invoked by Codex.

The rejection record and retained analysis scripts were committed first as
`5cd3e3f5`, after evidence preservation. The selective rollback then restored
all 20 modified implementation files byte-for-byte to audit 190 and removed
26 prototype-only files. The experiment's RAM workspace was cleared after
persistent retention and verification.

A fresh restored-baseline run passes READY: **81 loads, seven modules, eleven
instances**, four collections, no leaked files/sessions. All **81 archive
controls** and **11 async checks** pass. The retained analysis scripts reproduce
their complete census and profile results. The accepted native/reader/corpus
evidence is reused by exact product-source identity. This smoke run is not a
new timing series. Details and hashes are in the
[machine-readable result](direct-call-results.json).

## Measured end-to-end results

Every run starts a fresh Node process and Lisp state and completes the same
81 returning runtime loads. Full census and direct-hit counters are off;
default Node 25.6.1 / V8 14.1 flags and 32 MiB spaces are held constant.
Compilation/qualification jobs were kept out of the timing intervals. OS file
caches are uncontrolled. Each pair uses the same compiler products and host
adapter in both arms. The specialized series uses newer compiler products
than M-1; compare arms **within** each series.

The combined-core series has five alternating-order pairs: the prescribed
two extra pairs followed an indistinguishable first three. Each other series
has three alternating-order pairs. Spread means maximum minus minimum, not a
confidence interval. These results establish the selection under the plan's
rule; they are not a statistical proof about every engine or future compiler.

### Combined core

| Arm | READY runs (s) | Median (s) | Spread (s) | Lisp median (s) | READY RSS median (MB) |
|---|---|---:|---:|---:|---:|
| split | 26.537, 26.430, 25.954, 26.290, 26.107 | 26.290 | 0.583 | 22.957 | 2232.6 |
| core | 26.687, 26.189, 26.246, 26.116, 26.186 | 26.189 | 0.571 | 22.670 | 2305.6 |

Candidate minus control: **-0.101 s (-0.38%)**, with **+73.0 MB** median READY RSS. REJECTED: no demonstrated speedup; retain simpler split archives.

### Guarded dispatch

| Arm | READY runs (s) | Median (s) | Spread (s) | Lisp median (s) | READY RSS median (MB) |
|---|---|---:|---:|---:|---:|
| indirect | 26.401, 26.083, 26.384 | 26.384 | 0.318 | 22.561 | 2309.6 |
| guarded | 27.205, 26.731, 27.265 | 27.205 | 0.534 | 22.938 | 2545.5 |

Candidate minus control: **+0.821 s (+3.11%)**, with **+235.8 MB** median READY RSS. REJECTED: end-to-end regression exceeds either observed arm spread.

### Compiler-owned specialized entries

| Arm | READY runs (s) | Median (s) | Spread (s) | Lisp median (s) | READY RSS median (MB) |
|---|---|---:|---:|---:|---:|
| indirect | 26.535, 26.663, 26.384 | 26.535 | 0.279 | 22.975 | 2349.9 |
| specialized | 29.439, 29.493, 29.310 | 29.439 | 0.183 | 24.627 | 2833.4 |

Candidate minus control: **+2.904 s (+10.94%)**, with **+483.5 MB** median READY RSS. REJECTED: end-to-end regression exceeds either observed arm spread.

RSS is process-wide; MB here is decimal. The raw records retain bytes, peak
RSS, per-run phases and memory journals. No forced GC is added at READY.

## What the evidence supports

The separate indirect profile attributes 2,153 samples to `stack_guard` and
610 to `resolve`, over 22,019 total samples. The full logical census contains
44,724,264 calls: 39,373,587 fixed-arity, 2,940,806 optional, 1,926,556 rest,
99,281 keyword and 384,034 GF-trampoline invocations. Callable shape does not
establish static call-site eligibility, and helper self samples do not measure
all removable call overhead.

The M-1 guard leaves the full frame protocol intact and adds speculative
loads, comparisons and helper work. Its median Lisp interval increases by
0.377 s within a total 0.821 s regression. The binary grows from 79,351,275 to
85,152,168 bytes. The rest of the regression occurs outside the Lisp interval;
the measurements do not isolate engine admission as its sole cause.

The measured compiler-owned specialized build grows from 79,364,401 to
117,000,916 bytes and duplicates full and specialized bodies. Its Lisp median
increases by 1.652 s. It also reserves separate parent root slots for each
scalar site. Unlike the older linker prototype, eligible compiler fast paths
do skip the per-call context; parent rooting and result delivery remain.
That narrower frame improvement did not pay for the added code and protocol
costs in this implementation. The measurements do not separately quantify
each cause. The subsequent root-slot reuse edit was only compiled in a focused
fixture: it was never qualified or timed and is removed with the experiment.

Fixed-core startup and several mutation checks executed, but its qualification
and three-arm timing were unfinished. It is withdrawn with its supporting
machinery by user direction; no separate fixed-core speed result is claimed.
Additional timing of these rejected configurations is not required to make
the requested selection.

## Selective rollback and independent findings

Remove all combined-core support, direct-call lowering and imports, compiler
call metadata and specialized entries, fixed-core sealing/publication rules,
mutation preflights and compiler store guards, and direct-entry/fixed-core
witnesses and tooling. Restore the accepted compiler, cross-loader, runtime,
linker and startup harness. Keep the two standalone census/profile analysis
scripts and this rejection record. No product Lisp changes survive this pass.

`%copy-function` is an independent candidate: source inspection finds the
generic-function branch of `lib/encapsulate.lisp` calls it, while audit-190 has
no Wasm definition. The candidate detaches a funcallable instance's immediate
vector so encapsulation can preserve the old dispatch. The combined prototype
passed the real encapsulation witness after this addition; this is not an
isolated before/after qualification on the restored baseline. Its source and
witness are preserved for a separate fix/review, and it is removed from this
rollback's product. The empty-result host-adapter adjustment and its original
failure evidence are likewise retained in the pack, without accepting an
unrelated runtime change here.

Cheaper general compiler frames and a supported image saved after READY remain
possible future directions, not measurements or implementations from this
pass. A shipped saved image would need its own startup contract and validation;
it must not replace the 81-load correctness workload in this record.

## Retained evidence and replay

One persistent pack contains this experiment:
`/Users/buildsomething/Source/ccl-evidence/2026-09-27-direct-call-r1`.
Its original M-0/M-2 reports and failures remain unchanged historical evidence.
`rejection/` adds both later timing series with every raw run, command, source
hash, journal and report; exact measured launch binaries and containers; the
pre-rollback tracked patch and all new sources; qualification reports and
original failures; and the independent candidate source. The prior plan and
unfinished root-reuse compiler are historical snapshots, not active directions.

The three result files are `m2-pairs.json`, `rejection/m1-timing/result.json`
and `rejection/first-specialized-timing/result.json`. Their SHA-256 identities
and measured archive identities are in [direct-call-results.json](direct-call-results.json).
`rejection/REPRODUCE.md` explains how to replay the archived experimental
runner in a disposable RAM checkout, without restoring it to the product.
`rejection/index.json` inventories the new retained evidence.

The retained `direct-call-census.py` requires the original indirect trace and
its own compiler inventories; it rejects explicitly partial direct-call traces.
`direct-call-profile.py` attributes samples by both function index and body
offset. Replaying them uses their recorded input identities, not inventories
from a later build with shifted IDs. The original accepted native/reader/corpus
qualification is reused once product sources are restored exactly; rejection
adds no criterion credit.
