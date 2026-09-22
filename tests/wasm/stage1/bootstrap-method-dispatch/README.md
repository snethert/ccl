# Cached method dispatch through callable generic functions

Execution rises from **547 to 549 originals**, with **514 non-NIL witnesses**.
All **23,916 comparisons** pass; **608** are the new dispatch/error cases.
The final proposed backend passes 21,843 native tests and restores 164 FASLs.

This proposal executes CCL's original `%%ASSQ-COMBINED-METHOD-DCODE` and
`%%ASSOC-COMBINED-METHOD-DCODE`, compiled in their real file environment.
The first selects by EQ; the second calls CCL's ASSOC with its default EQL
comparison. Neither selection algorithm is reimplemented.

The owner fixture supplies the cached method functions and default function.
Witnesses cover first-match ordering, misses, argument positions zero and one,
distinct EQL bignums and doubles, list and CCL `&LEXPR` delivery, the accepted
funcallable trampoline, dcode rebinding, and collection in the selected function.
Native CCL runs the same untouched dispatch definitions. All earlier executions
remain in the corpus. The execution totals are in the retained summary; this
unit does not rerun or claim an increased admission count.

The backend directs two-argument ASSOC to CCL's existing ASSEQL;
keyword-bearing ASSOC calls stay ordinary calls. It also handles
SIGNAL-PROGRAM-ERROR with a literal string. It evaluates and roots the original operands in order, then uses the
existing condition constructor and signal dispatcher. No synthetic symbols
are added to an already-built literal pool. A witness checks format arguments,
operand effects, cleanup and a PROGRAM-ERROR handler across collection.
Numeric resource identifiers and dynamic format controls keep ordinary calls.

This is cached EQ/EQL dispatch, not the full generic-function implementation.
Class applicability, specificity ordering, ADD-METHOD, cache construction and
invalidation remain owed. The fixture's cache is owner-supplied. Native dcode's
malformed-cache and too-few-argument paths are not newly qualified here.
No source rewriter, new C/JS service, shared-source integration or LL15 credit.
The proposal builds on the unintegrated GCD packet and must be reviewed with it.

Run from the checkout root:

```
python3 tests/wasm/stage1/bootstrap-method-dispatch/packet.py verify \
  --packet ../ccl-evidence/2026-09-22-stage1-method-dispatch-r1 \
  --output /tmp/ccl-method-dispatch-replay
```

Replay reuses the native qualification only after matching every final proposed
source by hash. Unchanged artifacts reference the GCD packet. The worklist is
not recounted; no admission increase is inferred from these executions.
