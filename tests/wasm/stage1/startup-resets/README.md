# Native startup reset effects

This executes thirteen actual startup reset effects from the retained U1
callback inventory. It is an auxiliary LL15 prerequisite, not a complete
startup selection or an LL15 result. No compiler, runtime or kernel file changes.

`selection.json` preserves all 35 callbacks, their four groups and snapshot
identities. Thirteen reset a global to NIL, T or zero. The other 22 stay
`OPEN_NOT_IMPLEMENTED`; none is silently removed or assigned a replacement.
The snapshot is the accepted post-restore inventory, not an assertion about
future registrations or every emitted compile/load initializer.

Every replay binds the inventory and source positions to the retained snapshot,
checks each source file against pristine U1, and reads the selected definition
at that position using native CCL. DEFLOADVAR expands to a static SETQ;
AUTO-FLUSH-STREAMS contains its SETQ explicitly. Native CCL finds exactly one
actual registered callback per name, runs it with two dirty initial states,
checks its complete return values and all thirteen globals after every call,
and restores the original globals. These are real native callbacks, not the
new replacement functions used as their own oracle.

The port replaces each SETQ with generated `(set symbol literal)`, using the
unchanged accepted compiler. Owner admission requires a writable D1 symbol
with binding index zero, so this operation writes its global cell rather than
a dynamic binding. The replacement then writes its distinct completion token.
This is an explicit representation adaptation; the original callback source is
not claimed to compile unchanged. The owner assigns destination symbols to the
selected identities. It does not reconstruct production package membership.

Fifteen modules run through the integrated scheduler and lazy loader: a generated
symbol-access preflight in phase zero, the thirteen resets in retained order
in phase one, and a generated thirteen-value readback workload in phase two.
The last phase does not activate the ordinary condition system. Bootstrap fatal
handling and memory/entry setup are supplied by the accepted runtime harness.
Two fresh Workers, at 4 MiB and 2 GiB, each run both dirty states. Every callback
checks other image bytes for unintended writes, exact returns and global effects,
and caller/root/handler/allocation restoration. The compiler makes no allocation
or collecting call here; moving startup objects are outside this slice.

`install.mjs` is a portable proposal for the schedule's trusted owner adapter.
It owns a private, validated catalog and byte snapshots, uses those bytes to
instantiate through the accepted loader, and checks the loader's installed
digest against the requested plan before returning an invocation callback.
A behaviour-identical binary with an appended custom section is refused even
when the supplied row and record are updated together. Mutation of the caller's
catalog after construction cannot alter installation. This closes audit 124's
catalog substitution gap for this adapter, not for arbitrary callbacks accepted
by BootstrapSchedule. The invocation callback and imported capabilities remain
trusted; the helper is integrity binding, not a sandbox or code signing.

The independent publication checker binds the literal effect inventory, all
completions, refusals, placements and actual compiled module digests. Controls
remove or corrupt generated stores/completions, redirect a store, drop adapter
identity/snapshot checks, reproduce the development admission-offset mistakes,
and forge completion without loading code. Negative publications alter real
reports and must fail the independent checker.

The query tool searches the correlated build for each selected name/source.
All reported candidate bodies contain zero calls. Its compiler identities stay
in CORRELATED-QUERY-BASE-R1; they are not equated with the separate snapshot's
function IDs. No bounded callback dispatcher or whole-program closure is
inferred. The original source forms and native effects establish this literal
replacement; no unresolved computed call is needed by these bodies.

```
python3 tests/wasm/stage1/startup-resets/run.py --evidence ../ccl-evidence --output /new/startup-resets
python3 tests/wasm/stage1/startup-resets/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-startup-resets-r1 --output /new/startup-resets-replay
```

The first query builds a disposable capture index. `run.py --cache /path/to/index`
may reuse one; the qualified query tool checks its input and tool fingerprints.
The index is not evidence. The verifier builds a fresh index. Source lists are
explicit, and native R6/R6a is reused by exact integrated-compiler hash. Every
new module and every native callback scenario is executed again on replay.

Production integration still needs the real symbol owner, the remaining native
callbacks and startup entry dispositions, selected definition/loader effects,
condition activation and the coordinated image. Those remain LL15/LL14 work;
these thirteen effects do not establish ready for that larger bootstrap.
