# Module consolidation P-0 — 27 September 2026

One bounded fresh-process baseline reached **READY in 341.087 seconds**
(5 minutes 41 seconds), with **4.833 GiB peak process RSS** and **4.688 GiB
RSS at READY**. The timeout was 600 seconds. The process exited successfully
after 342.199 seconds. This is an instrumented observation, not a forecast
for the consolidated loader or a browser/download measurement.

The plan import is committed as `75e48478`. This run starts from `fcab125e`
(the intervening commit records the user's RAM-disk rule) with the optional
measurement hooks pinned in the evidence. Lisp inputs remain the READY
commit's retained `boot-r21` and `bundles-r18`; no Lisp was rebuilt. The engine
was Node 25.6.1 / V8 14.1.146.11-node.19 on macOS x86-64.

## Time

Lisp's top-level entry began 36.950 seconds after process launch and took
304.137 seconds to signal READY. Those 304 seconds include on-demand code
admission, installation, host services and collection.

These are exclusive Worker times; nested phases are removed from their
parents. The residual includes unmeasured host work, the existing boot
observer and instrumentation overhead as well as Lisp execution.

| Work | Seconds |
| --- | ---: |
| Allocate and register root cells (8,816 units) | 115.076 |
| Collector copies (2,029) | 64.854 |
| Lisp and unmeasured host/observer work | 62.639 |
| Runtime compile/materialization and module checks | 41.974 |
| Decode runtime bundles at LOAD admission | 13.926 |
| Build Worker namespace: bundle decoding | 13.942 |
| Boot-image admission | 5.963 |
| Other install-service work | 3.967 |
| Instantiate/publish runtime functions | 0.735 |

Main-thread namespace decoding separately took 14.135 seconds. Input bundle
bytes were 547,797,092. Worker construction took 0.333 seconds; send-to-Worker
start was 0.868 seconds, including cloning, thread startup and imports. Main
and Worker timings overlap and must not be added indiscriminately. Full
inclusive spans, remaining phases and per-file exclusive times are retained
in `timing.json`.

The slowest files by attributed Worker time were `source-files` (70.94 s),
`l1-streams` (46.91 s), `foreign-types` (21.66 s), `lispequ` (17.56 s) and
`l1-error-system` (12.88 s). Attribution includes each file's namespace decode
and admission, and assigns execution to the innermost open file.

Root allocation is the largest measured cost. The present `rootCells` path
re-enumerates roots and scans occupied external cells for every unit. P-1's
generation root block must be assessed against this cost as well as module
compilation. Collection and residual execution also remain substantial;
module-construction measurements alone cannot predict READY time (plan D-4).

## Memory

| Measurement at READY | Value |
| --- | ---: |
| Process RSS | 4.688 GiB |
| Linear memory byte length | 119.75 MiB |
| Current pair of collector heap spaces | 16 MiB |
| Current collector scratch extent | 32 MiB |
| Allocated bytes in active movable Lisp heap | 6.286 MiB |
| Live movable Lisp data at last collection | 5.973 MiB |
| Main / Worker JS heap used | 195.73 / 754.87 MiB |
| Main / Worker external memory | 1,052.35 / 1,073.34 MiB |
| Main / Worker ArrayBuffer memory | 1,050.35 / 1,070.87 MiB |

The last collection preceded READY by 51 milliseconds. Live movable data
excludes static/image objects and runtime metadata. No extra collection was
forced. The collector also retained 125,203 registered external root cells.

These rows are **not additive**. RSS covers the whole process; the remaining
Node counters are per thread, with ArrayBuffer memory already included in
external memory. Linear memory and collector extents describe allocation,
not resident pages. Old heap/scratch extents remain within linear memory
after relocation. The main-thread sample was taken on receipt of the result;
the Worker sample was taken at READY. See the
[Node counter definitions](https://nodejs.org/api/process.html#processmemoryusage).

The earlier 330-second / 4.46-GiB run remains a separate observation. This
single run does not isolate instrumentation overhead or establish a regression.
It does not support a memory projection for the archive loader.

## Evidence and verification

[Evidence pack](/Users/buildsomething/Source/ccl-evidence/2026-09-27-module-consolidation-p0-r1/README.md)
contains raw journals, the unchanged READY report format, per-file `timing.json`,
OS resource usage, input/source hashes, exact instrumentation sources and
focused check results. The [index](module-consolidation-p0.json) binds the pack.

Verification passed: actual top-level handoff, 81 returned nested LOADs,
82 balanced file opens/closes, class error mode, released collection
inhibition, and 2,029 measured copies matching the collector counter. All
measured source hashes still matched the checkout after completion. The
focused loader check and all 59 collector checks passed; collector reports
were identical with timing disabled and enabled. A truncated-journal control
retained a partial per-file breakdown without another Lisp run. The timeout
kill branch was not exercised by this successful baseline.

This completes the executed P-0 measurement gate. New instrumentation is
author-verified and available for adversarial review; no review acceptance is
claimed. No shared Lisp/compiler or upstream kernel source changed, so native
R6/R6a results were reused. P-1 implementation has not begun.
