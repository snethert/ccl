# Nested exception transfer — 15 September 2026

Status: S0-LL19-a [full] EXECUTED and PASSING at its stated scope in its
corrected form `NESTED-EH-R2`, awaiting Codex's follow-up review and then
the user's acceptance decision. The first execution `NESTED-EH-R1` is
retained unchanged and unaccepted: [Codex's review](codex-review.md) found
that a cleanup ran while the departed inner frame's binding, root record
and TSP were still current, hidden from the original oracle by the final
restoration. Stage 0 is **40 accepted, two missing and six unreviewed of 48**.

## Correction after review

The defect: `$f4` popped its frame only on ordinary return, so an exit
raised there reached `$f3`'s cleanup with `special` still 104, and the root
head and TSP still at depth 4's record. In Common Lisp a cleanup runs in
the dynamic environment of its own frame, with every inner binding undone.
The correction adds `$unwind_to`: before any cleanup or handler code runs
on an exceptional path, the frame restores its own binding, its own root
record as head and TSP, its VSP reserve and its own cleanup record, so the
departed inner frames are gone before the cleanup begins. The depth-1
handler paths and the adapter path do the same. Every cleanup now records
the dynamic state it observes on entry (binding, root head, TSP, its
frame, VSP, CSP and the saved VSP and CSP) in a witness region, and the
oracle requires, for every cleanup frame in every case, `special` equal to
that frame's binding, root head and TSP equal to its own root record, VSP
equal to the saved VSP plus the reserve and CSP equal to its own cleanup
record. A tenth mutant that omits the unwind is rejected at
`CLEANUP exit-0-values depth 3 special`, which is the review's
counterexample. Codex's retained reproducer splices its probe at the old
`$cleanup` signature, which the correction changed; the fixture now records
the same observation itself and the reproducer's expectations hold.

Authorship: Claude Fable 5.1 wrote this fixture on branch `wasm2-claude`;
Codex reviews it. No shared compiler or upstream kernel source changed. The
accepted S0-LL19-b fixture covers the emitted/C boundary; this slot covers
transfer through nested emitted frames.

## What executes

One hand-built wasm32 module, `frames.wat`, contains Lisp-shaped functions
with the B entry shape (self, nargs) → (value0, nvalues) and both arguments
at the incoming VSP. A fixture TCR holds VSP, TSP, CSP, one dynamic binding
cell, the root-record head, the handler depth, cleanup and post-exit
counters, the caller-owned result region, a values-in-transit region and an
event log. Every frame pushes a 48-byte frame record and a 16-byte root
record on TSP, binds the cell to a depth-specific value and reserves VSP.
Frames with cleanup push a record on CSP and wrap their body in
`try_table catch_all_ref`; on either exit path the cleanup runs once,
writes its own six values into its frame's region, the frame pops and
restores every saved word, and a nonlocal exit continues with `throw_ref`.
An exit stores its values in the transit region and throws the `lisp` tag
with the count; the depth-1 handler copies the transit values into the
caller-owned region before doing anything else.

| Case | What is checked |
| --- | --- |
| normal | Ordinary return through depth 4: two values, three post-exit effects, two cleanups on the normal path. |
| exit-0-values, exit-1-value, exit-6-values | The exit from depth 4 passes two cleanup frames; value0 is fixture NIL for zero values; all six unequal values, including −28, 0 and 2^31 − 4, reach the result region. |
| cleanup-throws-again | Depth 3's cleanup raises the `other` tag after running; depth 2's cleanup still runs; the handler receives the second exit's payload with one value; the abandoned six values stay in transit. |
| missing-handler | Depth 4 throws the `unhandled` tag; every frame restores; the export adapter records propagation and the host receives the same `WebAssembly.Exception` with its tag and payload 77. |
| recoverable-use-value | Depth 4's check signals a condition to the installed handler by an ordinary call; the handler transfers replacement 8 to the check site's restart; depth 4 resumes and returns normally, so no frame between the check and the handler unwinds. |
| recoverable-declined | The declining handler returns; the check becomes an error with one value that the depth-1 handler catches. |
| nested-debugger | Inside the depth-1 handler, after the six values are secured, a debugger frame binds, exits with three distinct values, catches its own exit and restores; the handler depth peaks at two and the original six values return unchanged. |
| deep-chain | Nine cleanup frames from depth 2 through 12; cleanups run innermost first and each frame pops before the next cleanup. |

After every case VSP, TSP, CSP, the binding cell, the root head and the
handler depth equal their checkpoints; the cleanup and post-exit counters,
the result and transit regions, and the complete event order equal the
oracle's expectations derived from `abi.json`. Post-exit effects are logged
events that never appear after an exit.

## Controls

Ten mutants of the module are rejected by the unchanged oracle at the named
first check: binding restoration omitted, VSP restoration omitted, root-head
restoration omitted, a cleanup run twice on the exit path, an exit swallowed
so the outer frame's post-exit code runs, a post-exit effect inside the exit
path, cleanup values written over the values in transit, values secured only
after the nested debugger, a use-value handler that unwinds instead of
resuming, and the unwind before cleanup omitted. Ten production artifact-role omissions on the genuine envelope are
refused by the unchanged gate, which otherwise reports only
`unreviewed S0-LL19-a [full]`.

## Evidence and reproduction

The corrected packet holds the complete bundle with template, binary,
disassembly, interface, options and host-compiler record; ten mutant
bundles with their observations; the observations for all ten cases with
their cleanup-entry witnesses; the bound envelope; slot-gate and
role-omission records. The verifier re-executes the producer and compared
101 deterministic files byte for byte in about two seconds.

Limits. Frames, records and the transit region are this fixture's, not the
production TCR or D3 descriptor; the condition path is a direct handler call
with a tag-based restart, not the Common Lisp condition system; there is no
collector, no C boundary and no host suspension inside the unwind. The engine
facts it relies on are recorded by S0-ENGINE-a.
