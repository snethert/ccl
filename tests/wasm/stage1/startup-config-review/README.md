# Startup configuration review corrections

This supersedes the unaccepted configuration R1 proposal and strengthens the
accepted reset fixture's validation without changing either pinned source tree.
`derive.py` creates explicit overlays from their reviewed files; both original
packets remain immutable and replayable at HEAD. No shared compiler, runtime
or kernel file changes, no acceptance and no LL15 credit.

**CPU cache.** The ninth checked global is `*cpu-count*`. The generated spin
callback reads it, publishes the owner's count when NIL, and otherwise uses the
cached count unchanged. Both its spin choice and return identity stay native.
The 36 configurations each run twice: the first starts with a NIL cache as the
accepted literal reset leaves it; the second has a cached 1 or 2 deliberately
different from the owner input. All nine global cells and their intermediate
states, not only the final spin value, are checked.

The native oracle now reads the original `cpu-count` DEFUN from pinned U1.
It requires the exact OR/cache/SETQ shape and replaces only the foreign-acquisition
expression within that body. It retains the source cache test and its write.
The other three external reads keep their original substitutions. Source and
adapted forms are retained. In addition, the untouched registered SPIN-COUNT
callback runs in the pinned kernel/image with initial caches NIL, 1 and 2;
it must publish a positive hardware count for NIL, preserve either existing
count, set spin tries and timeouts, and return the timeout symbol. All original
globals are restored. Browser and native CPU counts need not be equal: the
browser may reduce its report. This is an explicit host substitution, not a
claim that native and browser hardware discovery are identical.

**TCR checks.** Both derived harnesses compare every word of the 256-byte TCR
except `mv_count`, whose returned value is separately required to equal the
Wasm result count. The schema binds `tsp` to 76, `csp` to 88 and `mv_count` to
116. Thus the checks cover the actual stack cursors, their bases and limits,
binding/root/handler pointers, FP policy, persistent scratch and reserved words.
These specific startup bodies allocate nothing and have no pending concurrent
owner updates. The stronger invariant is for this slice, not arbitrary runtime
execution. Memory outside the declared image, stack, binding and allocation
regions remains outside the oracle; this is not a sandbox.

Four retained controls re-execute displaced-TSP and displaced-CSP modules
against both original harnesses and reproduce their successful escapes. Against
the corrected harnesses, valid assembled faults at TSP, CSP, CSP base, debugger
depth, FP control, a reserved word and result count are all rejected. A missing
CPU-cache store and an ignored existing cache fail the generated effect oracle.
The twelve inherited execution faults and ten publication controls still run.
The reset harness uses the accepted binaries and native answers, and its
stronger replay must reproduce the retained execution record byte for byte.

The configuration run recompiles all seven modules and native source oracles,
probes the real browser Worker again and repeats execution in Node and Chromium
at both placements. It compares **360 distinct native answers** in four Workers
(1,440 comparisons), with 2,032 invocations and 120 refusals. These totals do
not imply 1,440 independently generated native answers. The reset replay adds
its previous 52 comparisons, 92 calls and 42 refusals, with no new native-answer
claim. Native R6/R6a is reused by unchanged compiler hash.

```
python3 tests/wasm/stage1/startup-config-review/run.py --evidence ../ccl-evidence --output /new/startup-config-review
python3 tests/wasm/stage1/startup-config-review/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-startup-config-r2 --output /new/startup-config-review-replay
```

The five selected configuration callbacks and thirteen accepted literal resets
remain the same bounded startup selection. Seventeen snapshot callbacks and
wider startup membership, definition effects, condition activation and image
construction remain open. The corrected spin body and strengthened harnesses
remain proposals pending Claude's review and user acceptance.
