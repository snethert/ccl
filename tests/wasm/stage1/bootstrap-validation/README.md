# P4 validation tooling

No new original-definition execution or LL15 credit. This tooling packet
implements the user's P4 plan over the unchanged, pending class-growth
proposal at `78b187ba`. It does not integrate that proposal.

## Commands

Run from the CCL checkout beside `ccl-evidence`. Outputs must be new directories.
The default cache is `~/Library/Caches/ccl-wasm-validation`; `--cache` selects
another directory. Use an empty cache for a completely cold build.

```sh
python3 tests/wasm/stage1/bootstrap-validation/run.py --cache /tmp/p4-cache build /tmp/p4-base --cold --jobs 4
python3 tests/wasm/stage1/bootstrap-validation/run.py verify /tmp/p4-base --tier full --workers 4
python3 tests/wasm/stage1/bootstrap-validation/run.py verify /tmp/p4-base --tier identity
```

Reviewers can restore the retained compiler session, assembled modules and
executed inputs without compiling the corpus:

```sh
python3 tests/wasm/stage1/bootstrap-validation/packet.py restore ../ccl-evidence/2026-09-23-stage1-bootstrap-validation-r1 /tmp/p4-review --cache /tmp/p4-cache
python3 tests/wasm/stage1/bootstrap-validation/run.py --cache /tmp/p4-cache probe /tmp/p4-review tests/wasm/stage1/bootstrap-validation/examples/probes.lisp tests/wasm/stage1/bootstrap-validation/examples/inputs.lisp /tmp/p4-probes --mode default --workers 4 --jobs 4
```

`probe` compiles and executes its batch. It snapshots the submitted files and
starts a fresh process from the retained image for each batch. Every named
DEFUN must have an explicit nonempty input entry, including helpers. The
`VALIDATION-PROBE-CASES` function returns `(name inputs &optional globals)` entries; globals are explicit
`(symbol . value)` bindings used for native and target execution. Toplevel forms
are declarations, definitions and their PROGN/MACROLET/compile-time wrappers;
load-time work without an execution entry refuses. The native side compiles
and **loads** a real FASL, resolving load-time values. The target side uses
CCL's file compiler, with its local macro and symbol-macro environments.
`--mode class` selects the proposal's default-off class path; its existing
initialized-class/owner-graph requirements still apply.

The example covers a file-local macro, a symbol macro, a named helper, bignum
results, a collecting division-by-zero handler and mutation of a special
variable. It compiles only the four
submitted definitions, plus CCL's compile-time support forms. The unchanged
corpus is not compiled or executed by that batch. Standalone controls have
separate setup rows and counts.

For a delta, keep the previous report and its `.identity.json` sidecar and use:

```sh
python3 tests/wasm/stage1/bootstrap-validation/run.py verify /tmp/p4-next --tier focused --parent /tmp/p4-review/execution-report.json --workers 4
```

Identity verifies recorded inputs and reports **zero new execution**. Focused
executes every changed row and 32 unchanged rows sampled by SHA-256 with seed
`0x42545034`; it reports fresh, sampled and inherited comparisons separately.
Full executes every selected corpus row. A missing parent or missing sidecar
causes execution; an inconsistent existing report fails. Parent report hashes
and locators are carried into inherited evidence. Retention is a separate
command and never claims that its identity checks executed code.

## Identities and isolation

The session key includes the pinned kernel and image, pristine U1 inputs,
complete proposal/source pins, ordered drivers, architecture/compiler sources,
modes and builder code. It caches a whole session, never standalone DEFUNs.
Any environment change invalidates that session. WABT has a separate cache
keyed by WAT bytes, executable digest and flags. Entries are published by an
atomic rename and their inventories and hashes are checked before use.
Concurrent identical assembly jobs may publish the same key. Corruption is
an error, not a cache miss.

`driver/compile.lisp`, `driver/native.lisp` and `probe.lisp` are written entry
points, not another patch stack. The remaining support drivers are extracted
from the hash-bound parent. Compile, oracle, assembly and execution records
are emitted after their respective phases finish. The native image is a
**review tool**, never the port's bootstrap heap. It is checkpointed before
input construction; saving after native input construction crashed the pinned
native kernel, with logs retained. The cause inside the native save path was
not isolated.

Execution identity includes all installed modules and bindings, services,
symbols, pools, globals and class graphs, oracle rows, FP mode 7, placements,
movement settings, Node executable, graph codecs, installer and all harness
support. A compiler, runtime or shared-driver change therefore invalidates all
row keys. Changed oracle rows invalidate their own keys. Native R6/R6a is
reused from the parent only because the proposal source identity is unchanged.

Execution defaults to four workers, with four WABT jobs configured separately.
Each worker owns its memory, instances, mutable services and JS state. Every
case and movement variant restores the full declared mutable memory regions,
resets bindings and class-cell maps, and reconstructs numeric owners/services.
Results merge by stable content identity and duplicate ordinal. Both memory
placements (8 MiB and near 2 GiB) and both movement variants remain present.
Standalone owner/refusal checks run independently of row partitions, at both
corpus placements; the parent's separate 40-check collector suite also runs.

Probe module IDs, symbol IDs, existing pool objects and roots keep their
identities when appended. The module registry and conservative image/symbol
capacity checks run before installation. Graphs remain explicit recipe inputs;
this tooling adds neither a class initializer nor a new graph codec. A fresh
class-graph probe encountered the pending runtime's checked-error boundary;
the failed inputs are retained, not counted as successful execution.

## Qualification

`qualify.py BASE OUTPUT` performs the full comparison against the retained
sequential corpus, followed by focused parallel/sequential runs in opposite
orders and a separate set of growing-table, condition and mutable-global
cases. It preserves values, mutations, condition behavior and invocation
thread-state assertions. `controls.py` checks identity invalidation and cache
corruption; `probe_controls.py` checks omitted entries, missing file macros
across fresh batches and capacity refusal before installation.

The compiled module list, symbol list and pool graph equal the parent's.
Reloading the saved native environment changes 69 projected class-graph rows.
These are treated as changed inputs: all 69 execute, alongside the fixed
32-row sample. They are not inherited by weakening a graph identity.

The packet retains the session, compiled review inputs, full author execution,
focused reports, probe inputs/results and original development failures.
`packet.py restore` checks those archives, seeds checked caches and validates
the restored execution identity. It does not execute code. The author record
has a clean full parallel run; retention itself is an identity operation.

Measured phase times and cache/comparison counts are in `build.json`,
`warm.json`, `qualification.json` and `probe.json`. They describe validation on
this machine. There is no speedup guarantee or generated-code performance claim.
Cross-dumped classes, READY and production module granularity remain the next
runtime work.

The retained author measurements are (`probe-warm.json` holds the warm-image batch):

| Operation | Seconds | Work |
| --- | ---: | --- |
| Compiler session process | 116 | Whole-file compilation and checkpoint |
| Native oracle process | 112 | Oracle rows and diagnostic scans |
| Warm unchanged build | 29 | Zero compiler, oracle or WABT subprocesses |
| Focused, four workers | 58 | 276 fresh + 128 sampled comparisons |
| Same focused rows, one worker in reverse order | 129 | Identical results |
| Example probe compiler/oracle after restore | 32 | Four submitted definitions only |
| Same probe with a warm image cache | 3 | Four submitted definitions only |
| Example probe execution | 30 | 40 comparisons plus standalone controls |

The session build reused valid assembly entries left by a failed publication
attempt; its 818 WABT subprocesses are not presented as an empty-cache assembly
measurement. Full parallel qualification compares all 26,048 results with the
retained sequential run. Focused validation inherits the other 25,644 comparisons
with their parent identity. Worker startup, resets and standalone controls are
included in execution times.
