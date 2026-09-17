# Generated cleanup extents — 16 September 2026

The [isolated proposal](../../../tests/wasm/stage1/b-unwind-protect/README.md)
adds UNWIND-PROTECT through CCL's actual front-end IR. It is the first dynamic
cleanup extent in generated B code and a prerequisite for Lisp condition
handling. The user approved integration after Claude’s seventy-fourth audit. The shared
backend is byte-identical to the reviewed payload.

Normal results survive cleanup in a runtime-sized tagged root record. On a
checked exception, each extent restores its own explicit-stack cursor, roots,
VSP and result descriptor before entering cleanup. Successful cleanup rethrows
the same exception reference; a cleanup error replaces it. The catch surrounds
only the protected form, so cleanup cannot catch its own error or run twice.
Calls in the protected form and cleanup cannot tail-transfer away the pending
work. Their callees retain ordinary Wasm tail-call optimization.

There are 234 source functions, 307 generated modules and 876 native/model cases,
with 3,504 target comparisons across low and above-2-GiB placements. The added
cases cover nested cleanup order, zero/one/130 retained values, exception
replacement, defaults, closure mutation and escape, local functions, rest/APPLY,
recursive cleanup and a 3,000-step tail-recursive child under cleanup. Resource
probes check cleanup after result-capacity and heap-exhaustion failures, and
preservation of a type-error tag and datum (12 checks across both modes and placements).
An independent ABI-derived observer
checks the cleanup-entry stack cursor, VSP and retention root extent at 132
observed cleanup entries. Public
entries remain guarded against compiled-wrapper calls.

Eighteen compiler mutants are required to reject, including omitted/duplicated
cleanup, lost values/counts, wrong exception identity, illegal tail transfers,
and omitted restoration. Two restoration mutants initially escaped value-only
checks; their original passing executions are retained, and the cleanup-entry
observer addresses that gap. The first native comparison also caught a test
whose unused CAR was optimized away; its replacement is an effectful mutation.
A reporting-only omission caused an early producer interruption and is retained.

Fresh registered native execution and R6/R6a pass: 162 unchanged FASLs, two
explained registration artifacts, all 164 restored, and 21,843 native tests.
The pristine baseline is reused. The final producer and retained replay pass, including byte-identical rebuilds
of the positive corpus and all 18 mutant compilers. The
unchanged lazy-loader composition covers all 3,504 corpus comparisons and 36
long tail chains, with 3,644 cold installations per observation mode. The 12
resource/payload probes and specialized cleanup-entry observer belong to the
eager run and are not claimed for that inherited lazy harness.

Each simultaneous cleanup extent reserves `align16(8 + 4*capacity)` bytes.
A 1,024-word reservation exhausted the fixture's 32-KiB stack in one large-values
case; the original failure remains retained and the positive cases use up to
512 words. Capacity is still a checked runtime resource, with no new fixed
argument or value ceiling.

This is accepted and integrated auxiliary execution, with no LL05/LL19 gate
credit. Condition objects and signalling, CATCH/THROW, local RETURN-FROM, special
bindings and TCR handler/control-stack publication remain open. No GC or poll
is introduced; moving exception payloads and stack-temporary callable roots
still need collector treatment. Engine traps cannot stand in for Lisp errors.

Packet: `ccl-evidence/2026-09-16-stage1-b-unwind-protect-r1`.
