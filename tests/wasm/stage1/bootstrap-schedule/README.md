# Generated initializer scheduling

This is an executable prerequisite for S1-LL15-a, with **no slot credit**.
It repeats the accepted Stage 0 initializer-binding discipline through the
integrated compiler and lazy loader. It does not select the native startup
closure. The nine small Lisp initializers exercise the phase protocol; names
such as `seed_fatal` describe state markers, not a new fatal service, reader,
compiler or replacement for a native initializer.

`schedule.mjs` is an isolated portable runtime proposal. The trusted owner binds
a manifest digest, every module digest, completion addresses, required state,
effects and dependencies. Admission validates every binary using the accepted
loader before any installation or memory write. A stable topological sort runs
three phases: loader dependencies, definition effects, activation/workload.
No definition module is installed before all loader-phase completions exist.
Every entry has before/after assertions and a distinct completion word written
by generated code. Completed words and persistent effects are rechecked after
each callback. Ready is written last, with a count and manifest digest prefix.

Installation and invocation callbacks are trusted, synchronous owner adapters.
The scheduler is single-Worker, with exclusive access to its state and ready
regions. It does not provide cross-Worker publication, callback confinement,
rollback, collection or relocation of its raw state addresses. Failure is
terminal and earlier effects remain. The ready word is not a substitute for
the LL13 atomic process/Worker state machine. The expected manifest digest must
come from the independently selected build inventory; computing it from an
untrusted manifest would not establish completeness.

The corpus compiles in disposable pristine U1 with the unchanged integrated
compiler. Native CCL executes the nine initializer bodies; a separate Python
literal oracle checks its answers. Four fresh Workers execute at 4 MiB and
2 GiB. Nine modules implement the positive sequence and five more implement
wrong/missing completion, missing effect, prerequisite corruption and a raised
error. The harness uses the real B entries and checks caller restoration.
It also reverses the manifest to test dependency ordering.

The retained run has 172 generated invocations, 36 native comparisons,
140 refusal checks, twelve scheduler faults and seven publication omissions.
The forged-completion/no-load fault writes all expected words without executing
Lisp; the independent execution oracle still rejects it. The summary counts
are checked against the full result inventory, not accepted as evidence alone.
R6/R6a is reused by exact compiler hash; all new Lisp forms compile and run
natively on every replay. No shared compiler, runtime or kernel file changes.

```
python3 tests/wasm/stage1/bootstrap-schedule/run.py --evidence ../ccl-evidence --output /new/bootstrap-schedule
python3 tests/wasm/stage1/bootstrap-schedule/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-bootstrap-schedule-r1 --output /new/bootstrap-schedule-replay
```

The source list and runtime module list are frozen explicitly. Adding a sibling
fixture or a new runtime module does not change this replay's input enumeration.
Unknown calls in the accepted 167-unit startup worklist remain unknown. LL15-a
still requires selection and disposition of its native entries, implementation
of the selected effects, concrete census queries/witnesses where needed, and
their execution through the actual bootstrap build. This packet supplies the
execution mechanism and its fault controls, not that membership decision.
