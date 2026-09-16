# Nested exception transfer — 16 September 2026

Status: S0-LL19-a [full] EXECUTED and PASSING at its stated scope in its
second corrected form `NESTED-EH-R3`, awaiting Codex's follow-up review and
then the user's acceptance decision. The two earlier executions are
retained unchanged and unaccepted: `NESTED-EH-R1` ran a cleanup with the
departed inner frame's binding and roots still current, and `NESTED-EH-R2`
restored an invented cleanup record before the handler ran; [Codex's
reviews](codex-review.md) found both. Stage 0 is **40 accepted, two
missing and six unreviewed of 48**.

## Second correction after review

The R2 defect: `$unwind_to` always restored CSP to the frame's saved CSP
minus one record, the state of a frame that pushed its own cleanup. The
depth-1 handler frame pushes no cleanup, so its handler ran with CSP one
record below the true value, hidden by the final pop; the nested debugger
then saved that wrong value as its incoming CSP, and the R2 cleanup oracle,
which compared each witness against the saved fields, could not see it.

The correction makes ownership explicit. Every frame record now carries
`own_csp`, the cleanup state the frame owns: its saved CSP at push, replaced
by its own record when it pushes a cleanup. Unwinding restores `own_csp`, so
a handler-only frame gets back exactly the CSP it saved. Every handler
entry point (the `lisp` and `other` catches, the propagation path of the
unhandled tag, and debugger entry and return) records the state it observes
before delivering values, entering the debugger or rethrowing. The oracle
no longer trusts any saved field: it walks each case's expected events with
a frame model (64 bytes of TSP per live frame, 8 bytes of VSP reserve per
live frame, 8 bytes of CSP per live cleanup record, which frames own one)
and derives the binding, root head, TSP, frame address, VSP and CSP that
every cleanup and every handler must observe, including the values the
records must have saved. Three more mutants are rejected at the named first
check: the R2 defect itself at `HANDLER exit-0-values 63 csp`, a cleanup
record pushed without taking ownership at
`CLEANUP exit-0-values depth 2 csp`, and the handler witness taken after
delivery at `HANDLER exit-0-values 63 event_count`. Codex's R2 probe, run
unchanged against this checkout, observes CSP 16384 in the handler for both
of its modes, equal to the saved and expected values
(`CODEX-R2-PROBES-ON-R3`).

## First correction after review

The R1 defect: `$f4` popped its frame only on ordinary return, so an exit
raised there reached `$f3`'s cleanup with `special` still 104, and the root
head and TSP still at depth 4's record. In Common Lisp a cleanup runs in
the dynamic environment of its own frame, with every inner binding undone.
The correction added `$unwind_to`: before any cleanup or handler code runs
on an exceptional path, the frame restores its own binding, its own root
record as head and TSP, its VSP reserve and its owned cleanup state, so the
departed inner frames are gone before the cleanup begins. Every cleanup
records the dynamic state it observes on entry in a witness region. The
mutant that omits the unwind is rejected at
`CLEANUP exit-0-values depth 3 special`, the first review's counterexample.

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
Frames with cleanup push a record on CSP, take ownership of it in their
frame record, and wrap their body in `try_table catch_all_ref`; on either
exit path the cleanup runs once, writes its own six values into its frame's
region, the frame pops and restores every saved word, and a nonlocal exit
continues with `throw_ref`. An exit stores its values in the transit region
and throws the `lisp` tag with the count; the depth-1 handler unwinds to its
own frame, records the state it observes, and copies the transit values
into the caller-owned region before doing anything else.

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
oracle's expectations derived from `abi.json`. Inside every cleanup and at
every handler entry (ten handler witnesses across the cases) the observed
binding, root head, TSP, VSP and CSP equal the frame model's values for the
frames live at that moment. Post-exit effects are logged events that never
appear after an exit.

## Controls

Thirteen mutants of the module are rejected by the unchanged oracle at the
named first check: binding restoration omitted, VSP restoration omitted,
root-head restoration omitted, a cleanup run twice on the exit path, an exit
swallowed so the outer frame's post-exit code runs, a post-exit effect
inside the exit path, cleanup values written over the values in transit,
values secured only after the nested debugger, a use-value handler that
unwinds instead of resuming, the unwind before cleanup omitted, the unwind
restoring an invented cleanup record, a cleanup record pushed without
ownership, and the handler witness taken after delivery. Ten production
artifact-role omissions on the genuine envelope are refused by the
unchanged gate, which otherwise reports only `unreviewed S0-LL19-a [full]`.

## Evidence and reproduction

The corrected packet holds the complete bundle with template, binary,
disassembly, interface, options and host-compiler record; thirteen mutant
bundles with their observations; the observations for all ten cases with
their cleanup-entry and handler-entry witnesses; the bound envelope;
slot-gate and role-omission records. The verifier re-executes the producer
and compared 128 deterministic files byte for byte in about two seconds.

Limits. Frames, records and the transit region are this fixture's, not the
production TCR or D3 descriptor; the condition path is a direct handler call
with a tag-based restart, not the Common Lisp condition system; there is no
collector, no C boundary and no host suspension inside the unwind. The engine
facts it relies on are recorded by S0-ENGINE-a.
