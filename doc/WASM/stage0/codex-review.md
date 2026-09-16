# Codex review of Claude's Stage 0 branch — 15 September 2026

Latest disposition: the [R3 follow-up](#r3-follow-up--16-september-2026)
closes both remaining findings. Branch merged; all six pending Stage 0 slots
are recommended for acceptance at their recorded scopes. Earlier findings
below remain historical records.

Reviewed `wasm2-claude` at `b62ef7ac`, nine commits from `79e34a90` onward.
**Two defects found; branch merge withheld.** No acceptance or criterion changes.
The branch's ledger reproduces 40 accepted, two missing and six unreviewed;
`wasm2` remains at 40 accepted and eight missing until integration.

## Blocking findings

**1. Nested EH leaves the departed frame active during cleanup (`488325aa`).**
In `tests/wasm/stage0/nested-eh/frames.wat`, `$f4` calls `$pop_frame` only
on ordinary return (line 153). Its exceptional exits jump to `$f3`, which
calls `$cleanup` before restoring the skipped frame (lines 168–170).
An observation-only probe at cleanup entry records `special = 104` where
the depth-3 cleanup must see its own binding, 103. Root head and TSP are
12032, the departed depth-4 record, instead of 12096. Seven existing cases
show this, including exits with zero/one/six values, cleanup throwing again,
the missing handler, nested debugger and declined handler. Ordinary return
and the deep cleanup chain provide passing comparisons.

The final outer pop hides the error, so the supplied oracle passes. This
affects what cleanup code can observe, even without collection. Restore
each unwound frame before executing an outer cleanup, and assert binding,
root and stack state *inside* cleanups as well as after the whole call.
S0-LL19-a is not ready for acceptance.

**2. Floating-point exactness fails near the largest finite double
(`bbcdd377`).** The unmodified module returns status 5 (inexact), rather
than 0, for `MAX * 1`, `MAX * 0.5` and `MAX / 1`, although each result is
exact and its returned bits are correct. In `checked.wat` lines 44–49,
scaling protects the splitter multiplication but scaling the high part
back up can overflow. The error calculation then contains infinities/NaNs
and incorrectly reports a nonzero residual. The retained 1,882-case corpus
and all eight mutants still pass.

Correct the witness scaling and add exact operations near both signs of
the maximum exponent. The claim that general detection is proved, and
ready for cost measurement, is premature. These counterexamples affect
the optional inexact classification; they do not demonstrate a failure
of the default-mode overflow/invalid/zero-divide checks. No Stage 0 slot
is attached to this auxiliary result.

## Commit dispositions

| Commit | Review |
| --- | --- |
| `79e34a90`, engine matrix | No implementation defect found at the retained versions; current-machine replay has the version change below. |
| `e9ff6347`, both materialization variants | No blocking finding; fresh verifier passes, 370 deterministic files identical. |
| `488325aa`, nested EH | DEFECT_FOUND, finding 1; retained verifier nevertheless reproduces 92 files. |
| `0e5d2756`, contracts join | No blocking finding; regeneration reproduces 15 files. This joins the accepted fixtures' contracts, not a production runtime. |
| `8d852303`, initializer binding | No blocking finding; fresh verifier reproduces 812 files, including whole-memory expectations and the no-load mutant. |
| `a1471709`, kernel imports | No blocking finding at source-inspection scope; regeneration reproduces 11 files. Caller-name scanning is not evaluated reachability. |
| `993831b0`, TCR schema | No blocking finding as an unexecuted build target; regeneration reproduces 12 files. Clarify the count wording below. |
| `bbcdd377`, floating-point detection | DEFECT_FOUND, finding 2; retained verifier nevertheless reproduces 66 files. |
| `b62ef7ac`, Stage 1 draft | Structurally valid: unchanged gate reports exactly 31 missing variants, no malformed-inventory errors. Remains unadopted; refresh its inputs below. |

## Engine change and follow-ups

Firefox changed from the retained 147.0.4 executable to 156.0. The retained
engine verifier refuses with `JSPI unavailable` because Firefox 156 now
successfully executes the suspending import and promising export. Its
current isolated and plain pages both yield 105 and 50 with the live local
intact. The failure is preserved, not presented as a byte-identical replay.
Node and both Chrome pages reproduce their observations; supplementary
runs pass both Safari pages and all seven Node mutants. Firefox's changed
profile was checked with JSPI expected true in the review process only;
no source expectation or retained envelope was changed. Refresh the engine
record before treating its table as the current Mac's capability matrix.
The old Firefox result remains evidence about that old binary.

Two wording/integration notes:

- `tcr-schema/tcr.json:355` calls `mv_count` the number of "extra values"
  while mapping it to the accepted fixture's `nvalues`. The accepted B
  contract copies the **complete ordered sequence**, including value0,
  into the owned region and scans using that count. Specify that convention
  explicitly before implementing the production scanner.
- The Stage 1 draft predates the approved on-demand LL15 policy on `wasm2`.
  Refresh its exhaustive-closure assumptions, its Firefox statement, and
  its claim that floating-point detection is proved before adoption. Author,
  inventory and floating-point policy decisions remain the user's.

## Retained review evidence

Packet `CODEX-CLAUDE-BRANCH-REVIEW-R1` contains the seven passing verifier
logs, original engine verification failure and supplementary observations,
the two portable independent reproducers and their actual outputs, the
draft assessment, ledger result and scoped packet checks. All 1,921 files
listed by the eight new packet manifests match their recorded sizes and
hashes. Document checks pass; the branch changes no shared compiler or
kernel source from U1. No old evidence-store payloads were rescanned.

Reproduce the two defects against the reviewed checkout:

```sh
python3 /path/to/ccl-evidence/2026-09-15-codex-branch-review-r1/repro/run.py \
  --source /path/to/ccl-claude --output /new/output
```

The EH probe adds only observation stores into unused memory; the float
module is assembled unchanged. Their assertions establish the defects,
not acceptance of the implementations. Fixes need new fixture cases,
retained executions and follow-up review; existing PASS envelopes remain
immutable and unaccepted.

## R2 follow-up — 16 September 2026

Reviewed `wasm2-claude` at `2bdcbd24`, including the five R2 packets and
the Stage 1 draft refresh. **Two findings remain; do not accept LL19-a or
the floating-point auxiliary result yet.** No acceptance changes or merge.

**1. High: unwind-to-handler invents a cleanup record.**
`tests/wasm/stage0/nested-eh/frames.wat:84` always restores CSP to
`saved_csp - 8`. That is the state of a frame that pushed its own cleanup.
`$outer` pushes a frame but never calls `$push_cleanup`, then calls this
same restoration helper before entering its handler (line 276).
The handler therefore sees CSP 16376 instead of its saved 16384. A probe
adding only four observation stores before event 63 reproduces this in
the ordinary nonlocal-exit case (mode 1) and nested debugger case (mode 5).
The final pop restores 16384 and hides the error. The debugger also saves
the incorrect incoming CSP; its cleanup oracle checks against that saved
value, so the new assertions pass.

Restore the actual cleanup state belonging to the destination frame,
distinguishing handler-only frames from cleanup-owning frames. Assert the
handler's state before delivering values or entering the debugger, with an
independent expected CSP. The original departed-frame binding/root defect
is corrected, and all 101 deterministic R2 files reproduce, but the claimed
restoration before handler code runs is still false.

**2. Medium: floating-point implementation and rational oracle disagree at
the normal/subnormal boundary.** The unmodified R2 module evaluates
`2^-1022 * (1 - 2^-53)` to `2^-1022` with status 5 (inexact).
Its own `ieee.expected` returns the same bits with status 4 (underflow).
`checked.wat:68` tests tininess of the final result; `ieee.py:46–56` tests
the magnitude rounded with an unbounded exponent range. The exact product
is `2^-1022 - 2^-1075`, so this case distinguishes those definitions.
The prose contract currently describes the module's final-result test.

Resolve this policy/oracle/implementation inconsistency explicitly and add
the boundary case to the corpus, including signs and adjacent values.
This finding establishes a disagreement with the project's oracle, not a
claim here about which underflow policy the project must adopt. It does
not affect the three default-mode conditions. The original `MAX * 1`,
`MAX * 0.5` and `MAX / 1` counterexamples now correctly report exact; all
66 deterministic R2 files and eight mutants reproduce.

The other updates have no new finding:

- Engine matrix: all four engines replay; 361 deterministic files match,
  including Firefox 156's JSPI execution.
- Materialization: 370 deterministic files match, with Safari providing
  the profile-not-admitted control.
- TCR schema: 12 deterministic files match; `mv_count` now explicitly
  includes value0 in the complete ordered sequence.
- Stage 1 draft: on-demand census and current-machine JSPI wording are
  refreshed, and corpus execution no longer claims general proof. The
  draft remains unadopted.
- Integration: all 288 index records from current `wasm2` are preserved
  as complete objects, including historical records. LL15 inventory entries
  are unchanged. Shared upstream source is untouched. The branch's ledger
  and document checks pass at 40 accepted, 2 missing, 6 unreviewed.

Packet `CODEX-CLAUDE-BRANCH-REVIEW-R2` retains verifier logs, scoped checks
of all 1,022 files in the five R2 manifests, and the independent probes.
No old evidence payloads were rescanned. Run the probes against the
reviewed checkout with:

```sh
python3 /path/to/ccl-evidence/2026-09-16-codex-branch-review-r2/repro/reproduce.py \
  --source /path/to/ccl-claude --output /new/output
```

The assertions expect these review counterexamples. They are not acceptance
tests; their outputs show both the fixed max-exponent cases and the two
remaining findings.


## R3 follow-up — 16 September 2026

Reviewed `wasm2-claude` at `6c78877d`, including `bca2d4e9`, `e6ffc921`
and the integration records. **No new defect found. Both R2 findings are
closed.** The branch was fast-forwarded into `wasm2` after review.

The EH frame now saves its own CSP separately and updates it when acquiring
a cleanup record. The unwind helper restores that actual owned state.
The oracle derives all cleanup and handler addresses from a model over its
literal expected events, region bases and record sizes; it does not borrow
saved addresses from observed frames. This catches the circular expectation
that previously hid the debugger's wrong incoming CSP. Fresh verification
reproduces 128 deterministic files and rejects all thirteen mutants.
Our observation-only probe independently sees CSP 16384 at both handler
entries (ordinary exit and nested debugger), equal to the required base.

The float correction distinguishes the smallest-normal result using its
scaled exact residual, including the strict quarter-unit boundary and signs.
The division path tests the corresponding scaled numerator/divisor relation.
Fresh verification reproduces 89 deterministic files: all 2,069 corpus cases
and eleven rejected mutants, plus all 1,646 f64 cases checked against native
scalar SSE status and result bits. The native witness clears MXCSR and uses
masked exceptions with DAZ/FTZ off. Our original large-exponent probes remain
exact, and our minimum-normal boundary now returns underflow, agreeing with
the rational oracle. This is reviewed corpus evidence, not proof over every
floating-point operand or approval of a production condition policy.

The contract discloses the separate unmasked-underflow behavior, including
tiny exact results. This review and the user's six-slot acceptance do not
choose that optional policy. FLOAT-DETECTION-R3 is auxiliary evidence and
not one of the six Stage 0 slots.

The passing prior reviews of ENGINE-MATRIX-R2, MATERIALIZATION-R2,
CONTRACTS-R1 and INITIALIZER-BINDING-R1 still apply: their executed sources
are unchanged by this correction. The six eligible records are ENGINE-a,
LL21-c/shared-template, LL21-c/unshared-template, LL19-a/full, CONTRACTS-a
and LL15-a/full. Their hand-built/engine/desk-review scope stays unchanged;
none establishes generated-code execution or census qualification.

The branch ledger and document checks pass at 40 accepted, two missing and
six unreviewed before project acceptance. The R3 packet checks cover 250
listed files; no historical evidence rescan or new native CCL build was
needed. `CODEX-CLAUDE-BRANCH-REVIEW-R3` retains logs and independent probe
outputs. The probe observation code is unchanged from R2; only its assertions
now require corrected results.


## D6 policy and TCR extension — 16 September 2026

Reviewed `wasm2-claude` at `9b6b4605`, including the five D6 commits
`cd6851eb`, `c799c08f`, `54e66575`, `bcbe7249` and `fe1c79d7`.
**No defect found at the recorded scopes.** The branch, including Claude's
sixtieth acceptance audit, was fast-forwarded into `wasm2`.

Fresh verification reproduces all 110 deterministic FLOAT-DETECTION-R4 files
and all 12 TCR-SCHEMA-R3 files. The float corpus has 2,135 cases, including
1,656 native SSE arithmetic/comparison witnesses; all fourteen mutants reject.
The TCR regeneration and eight controls pass. Both direct packet manifests
were checked, without rescanning the historical evidence store.

An independent probe imports no fixture oracle. Literal condition lists check
all 256 combinations of 32 enable masks and eight status codes, including the
secondary inexact flag for overflow and underflow. Another 224 combinations
feed real arithmetic results into the policy, including tiny exact results,
and 256 exercise comparison status and mask selection. New instances start
at mask 7 and remain independent; four high-bit inputs normalize as specified
by the fixture. All pass. This probes separate fixture instances, not a
production per-Worker TCR implementation.

Independent schema comparison preserves all 47 old field records exactly.
The sole new field is thread-owned bounded `fp_control`, four bytes at offset
200 with alignment 4. The reserved tail starts at 204; total size remains 256.
This is a schema proof, not execution of thread creation or `set-fpu-mode`.

U1 source supports the stated model: `thread_manager.c` initializes ARM's
invalid/division-by-zero/overflow enables; `arm-float.lisp` keeps logical
control in the TCR and chooses invalid, division-by-zero, overflow, underflow,
inexact in that order; `trap-if-fpu-exception` masks the status before trapping.
The arithmetic pass-2 paths clear pending flags before a checked operation,
which supports using per-operation derived flags here. `nx-float-safety`
selects safety 3 or the named policy hook. The source comparison instruction
is signalling, matching the added explicit NaN check and native witness.

Limits remain explicit: the policy fixture stores its mask in an instance
global, produces condition codes rather than Lisp condition objects, and does
not exercise production TCR initialization, API keyword errors or emission.
Single-float underflow/inexact, host-math limitations, non-nearest rounding
refusal and generated-code cost remain later implementation obligations.
The recorded user decision is imported as a project decision; this review
adds no policy choice or Stage 0 acceptance. The live ledger remains PASS
with all 48 records accepted and unchanged.

`CODEX-D6-POLICY-REVIEW-R1` retains the replay driver, literal probe, logs,
source identities and direct packet checks. Reproduce with its `reproduce.py`
using `--source`, `--evidence` and a new `--output` directory.
