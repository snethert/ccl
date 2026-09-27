# Claude review of MCP-P6/P7 (9ae6bfd8, c9f259a4) — 27 September 2026

```
REVIEWER      Claude (Fable 5.1), at the user's request ("review the updated plan")
SCOPE         the P6 and P7 amendments to module-consolidation-plan.md and their two
              decisions.md entries; documentation only, no implementation reviewed
VERIFIED      F-14's native values against level-1/l1-lisp-threads.lisp and
              lisp-kernel/pmcl-kernel.c; A-14's scratch formula and the growth policy
              against runtime/wasm32/collector-owner.mjs; the root representation
              against runtime/wasm32/collector.c; F-15's retention paths against
              tests/wasm/stage1/loader-target/boot0.mjs and target-load-session.mjs
DISPOSITION   AGREE on every amended item except the four AMENDs below; none blocks
              adoption of the amendments; one AMEND (P-1 scope) changes how the
              work is packaged
```

## Per ID

- U-6, U-7, F-13, F-15, D-4, A-11, P-2, P-3, P-4, R-9, both decisions.md
  entries: AGREE.
- F-14: AGREE on the 32-bit stacks (`(ash 1 20)`, `(ash 1 20)`, `(ash 1 19)`
  at `l1-lisp-threads.lisp:283-291`), on `DEFAULT_LISP_HEAP_GC_THRESHOLD`
  (16<<20) for 32-bit and on the growth policy (`ensure` collects first and
  relocates only when the collected space still cannot hold the request,
  `collector-owner.mjs:320-330`). UNVERIFIED: the 256 KiB bootstrap
  temporary stack; the kernel's `DEFAULT_INITIAL_STACK_SIZE` is 1<<20.
  Add the fact that today's Wasm `temp` and `control` areas are 16 KiB each
  (`boot0.mjs:96`, regions 196608–212992 and 212992–229376) against the
  native 512 KiB and 1 MiB; that gap, not only the heap pair, is what A-14
  corrects.
- A-14: AGREE on the values and the headroom policy. AMEND the expectation
  it carries. Per collection the host builds a JavaScript array of every
  registered root, currently 125,203 cells plus image slots, and writes it
  into the root list before calling the collector (`#validate` and
  `#copyInto`, `collector-owner.mjs:178-184, 291-303`); the C collector
  then visits each entry (`collector.c:308`). That cost is fixed per
  collection and independent of space size. The C inventory and object
  map are proportional to the used from-space (`96 + used/8*20 +
  logCapacity*12`). Larger spaces therefore cut the total of the fixed
  part and leave the total of the proportional part roughly constant. The
  16/32/64 MiB comparison will only be interpretable if P-1 splits the
  present `collector.copy` timer into host preparation and C collection,
  and records per-collection root count and used bytes. State that
  expectation in A-14 so a flat result is not read as "sizing does not
  matter" and a good result is not credited to copying.
- A-15: AGREE on direct unit slices and no rescan. AMEND to separate the
  two costs it bundles, because they live in different places. The 115 s
  of F-13 is host-side: `rootCells` re-enumerates all roots through
  `#validate` and then scans the external region cell by cell against a
  `Set` of occupied slots, for every unit (`collector-owner.mjs:186-196`).
  Direct slices remove that without touching the C collector. The
  per-collection cost above is different: it comes from listing 125k
  individual cells on every collection, and a "collector range path" that
  removes it is a change to `collector.c`, which is accepted evidence with
  its own qualification (59 checks and 17 killed mutants in audit 185).
  Recommend: P-1 does the host-side slice fix and measures; the C range
  path is its own packet with collector re-qualification, justified by the
  split timer of A-14, not assumed in P-1.
- A-16: AGREE. One clarification: the main thread is the file host
  (`serviceRequest` answers the Worker's read requests from the main-thread
  namespace, `boot0.mjs:45-48`), so the FASL bytes, about 5.8 MB, stay
  main-thread resident unless the file host moves; the archive binary and
  validation manifest are Worker-only. Say so, since "the main thread
  needs file-service data" otherwise reads as optional.
- R-8: AGREE, with the fixed/proportional split above as its measurement.
- P-1: AMEND, the substantive finding. P-1 now carries four independent
  changes: (1) the archive, generations and root slices (A-1..A-12, A-15
  host part), (2) heap and stack sizing with the new growth policy (A-14),
  (3) input ownership and release (A-16), and (4) a three-configuration
  sizing comparison. Each has its own gates, and the plan's own rule
  (A-15, R-8: measure separately) cannot be met if they land together,
  because the before/after against F-13 then attributes nothing. A defect
  in any one also blocks the adopted decision, which is (1) alone.
  Recommend three packets in this order, each measured against F-13 with
  P-0's instrumentation: P-1a archive + generations + root slices (the
  adopted consolidation, the largest measured cost); P-1b sizing and
  growth policy with the 16/32/64 comparison (a configuration change that
  could equally be measured on v1 first, in one short run each); P-1c
  ownership and release. P-2 follows P-1a for the boot tier. Gates stay as
  written, distributed by packet.

## Not findings

The instrumentation commit `0675ba83` was read: the runtime edits are
`measure` hooks with identity defaults and a read-only `storage` getter;
no behaviour changes. The P-0 counters reconcile: 5,189,058,560 bytes =
4.833 GiB, 5,033,697,280 = 4.688 GiB, 125,566,976 = 119.75 MiB, and the
exclusive Worker phases sum to 324.8 s inside the 341.1 s launch.
