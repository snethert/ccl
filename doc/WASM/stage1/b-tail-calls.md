# Generated proper tail calls — 16 September 2026

The isolated proposal emits Wasm `return_call_indirect` for eligible named,
FUNCALL, APPLY, lexical, self and mutual calls. Observation wrappers also use
`return_call`. The public B signature is unchanged. One private continuation
per ordinary call preserves the caller's arguments and result reservation;
tail calls reuse its argument/root area. Pending effects and retained values
keep an ordinary frame. The paired internal entry and table are described in
the [fixture](../../../tests/wasm/stage1/b-tail-calls/README.md) and its layout.
They are owner-supplied here; production loader authentication remains open.

Literal APPLY now uses a checked, nonescaping stack callable rather than a
heap callable. Tail transfer moves that object with the arguments and rebases
its environment pointer. Captured cells still use conservative heap storage:
the uncaptured case allocates nothing, while the existing captured example
drops from forty bytes to eight. A nested closure escaping the applied lambda
keeps its own heap storage and survives stack overwrite. This does not remove
real per-step allocations such as rest lists, or qualify collection of stack
temporaries.

The corpus has 202 source functions, 270 modules, 741 native/model cases and
2,964 target comparisons. Thirty-six further runs each execute 100,000 steps
within a 2 KiB Lisp-stack budget at low and above-2-GiB placements, plain and
observed. They cover changing arities up to 130, zero and 130 returned values,
local mutual calls and a final exception restoring three pre-existing values.
Observed tail boundaries retain exactly two root frames. Caller arguments,
heap allocation, output tails and stack fences are checked. Pending-effect
recursion still fails at a checked stack limit. Twenty additional checks cover
missing internal entries, allocation-free literal APPLY and escaping captures.

A separate retained composition probe rebinds V1 to the existing literal-APPLY
caller, then traverses 100,000 nested singleton lists. It executes 200,001
observed tail transfers, uses no heap for the uncaptured callable, and restores
the caller after the terminal arity condition. Four runs cover both memory
placements and observation modes. This supplemental probe uses the unchanged
compiled modules and has its own replay command; it is outside the standard
corpus/replay counts above.

Nineteen recompiled compiler mutants and two inherited development regression
controls reject. R6/R6a passes: 162 registered FASLs unchanged, two explained
registration artifacts, all 164 restored, and 21,843 native tests. The pristine
accepted baseline is reused; registered execution and restoration are fresh.
The finalized packet is replayed before commit.

Development found a real ordering defect: the first wrapper wrote context
metadata before checking its complete scratch extent. The memory-end fence
caught it. The full preflight now precedes all context writes, and a mutant
retains that omission. The other retained failures are an assembler syntax
error and corrected test expectations, disclosed in the development record.

Claude’s seventy-second audit found no defect. The user accepted this auxiliary
unit and its exact reviewed backend is now [integrated](integration-b-tail-calls.json).
No inventory slot is claimed.
Dynamic binding/cleanup, production Lisp conditions, authenticated lazy
adapters and collection remain open; neither complete LL05 slot is claimed.
The next call-path work is the condition and lazy-adapter machinery, with tail
legality revisited when dynamic scopes are admitted.

Packet: `ccl-evidence/2026-09-16-stage1-b-tail-calls-r1`.

Carry forward: revisit tail legality when dynamic extents are admitted; qualify
stack-temporary callable roots with the collector; charge the 48-byte ordinary-call
context plus padded arguments in performance measurements.
