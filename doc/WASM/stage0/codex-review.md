# Codex review of Claude's Stage 0 branch — 15 September 2026

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
