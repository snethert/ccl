# LL10 follow-up to audit 85

This strengthens the reviewed LL10 qualification without changing its compiler,
loader, encoder or snapshot implementation. The original R1 fixture and packet
remain reproducible. This runner derives an isolated test harness from their
hash-pinned sources; the derived source files are retained alongside execution.
It reuses the reviewed native R6/R6a for the identical compiler.

The four compiler mutants now have focused positive cases and distinct failure
oracles:

| Mutation | Focused observation |
| --- | --- |
| Header used as constant slot zero | A scalar literal returns the vector header instead of the bignum; the value-tag oracle rejects it. |
| Lost child pool | The constructor's pool field differs from the child's pool before the child is called. |
| Wrong SELF root | A string literal refuses the invalid function read from the padding root. |
| Temporary environment overwrites pool | Captured literal APPLY returns a captured cons instead of its string literal. |

The native session compiles two getters over the same string, a third over a
separate equal string, and a function that calls two supplied functions and
compares their returned values with EQ. Native CCL supplies all three answers;
the target invokes the corresponding generated modules at each placement. A
control redirects one getter to the equal-but-distinct string and is rejected.

The restored expectation is built from the native graph before canonical IDs
are assigned. Only the object returned by `cycle` has its CAR changed to 11.
A separate cons with CAR 7 stays 7. The former broad rewrite is retained as a
control and fails on this unrelated cons. Mutation remains a persistence probe,
not a claim that modifying a literal is portable Common Lisp.

The complete extended corpus runs at 1 MiB, 2 MiB and 2 GiB: 91 B modules plus a
header probe, 245 native-derived comparisons, and nine additional cross-function
comparisons. The original 100,000-transfer chains, cold pool inspection and
fresh-Worker restoration also run. Four recompiled compiler mutants and two
semantic controls reject. No new gate slot, acceptance or integration is claimed.
Owner registration for quoted keywords and the two validations per literal load
remain the reviewed scope and implementation respectively.

From the repository root:

```sh
python3 tests/wasm/stage1/constants/review-followup/run.py verify \
  --packet ../ccl-evidence/2026-09-17-stage1-ll10-review-followup-r1 \
  --output /tmp/ll10-followup-review
```

`run --output NEW_DIRECTORY` produces independently. `retain --run RUN_DIRECTORY
--output PACKET_DIRECTORY` retains that run. The verifier checks the pinned
reviewed inputs, recompiles the corpus and four mutant compilers, executes the
oracles, and compares deterministic outputs with the packet. The retained
`development.tar.gz` holds the two original failed attempts and their source:
a copied-harness relative schema path, then an overly specific expected refusal
where the temporary-relocation mutant instead produced the wrong value.
