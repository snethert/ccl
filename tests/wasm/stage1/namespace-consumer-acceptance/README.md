# Namespace consumer integration and audit 177 follow-up

Files cross-compiled / cross-loaded / target-loaded: **0 / 0 / 0**.
This unit integrates the fifteen product files reviewed in audit 177, byte for
byte. It adds no original-definition credit and does not accept S1-NAMESPACE-a:
that criterion still needs LOAD of source and precompiled bundles in NSL-3.

O-73 is repaired without changing product code. `controls.mjs` builds the
qualified LL09 sealed package image. Eight configuration cases keep every
symbol inside the package arena, so an invalid linked range cannot accidentally
fail a per-symbol check. Four symbol cases call the public SYMBOL-NAME service
with an otherwise valid linked symbol; positive controls establish admission.
All twelve refusals preserve package data, descriptor, result, canonical symbols
and the linked symbol storage. Scratch remains explicitly expendable.
`refusals.py` removes each named clause separately and requires that its exact
malformed input succeeds through the complete public operation. A trap, another
refusal or merely a different error does not count as isolation.

The thirteenth clause, the inner `!span(p,32)` in `symbase`, is equivalent under
the admitted contract. Config establishes `lo <= hi <= memory size`; the other
symbol guards establish `lo <= p` and `(uint64)p + 32 <= hi`. Thus the entire
symbol is backed. Independently, `symbase` repeats `span(p,32)` in its final
return expression before reading the header. The single-deletion mutant is
retained as an intentional survivor with identical refusal results. The
redundant product check remains exactly as reviewed.

O-75: **the `home:` logical host is absent on wasm32**. No user-home environment
lookup or home-directory default is provided. The namespace uses only the
manifest's `ccl:` root and current directory. NSL-2/3's planned loader inputs use
those roots; loading user init files is outside the adopted READY profile.
Any future loader dependency on `home:` must be resolved explicitly, rather
than inventing a home path or silently mapping it to `ccl:`.

The five native weak registries use strong tables for the image lifetime:
`%setf-function-names%`, `%setf-function-name-inverses%`,
`eql-specializers-hash`, the foreign ordinal table and `%documentation`.
Steve explicitly chose “Retain the documented substitution” after audit 177.
This retains objects until image disposal and supplies no weak-table semantics;
LL15's broader weak-table dependency remains open.

O-74 (unexercised FIND-SYMBOL replacement), O-76 (fixnum-vector dispatch row),
and O-77 (cold-replay provenance/default-key hygiene) remain next-packet work.
The earlier eleven package controls are historical non-isolating controls; they
are not the proof for O-73. The new twelve cases and equivalence are that proof.

```sh
# Historical replay at namespace integration commit 1a076ca4: identities,
# native qualification, fresh four-Worker
# replay and isolated admission controls, with single-clause mutants.
python3 tests/wasm/stage1/namespace-consumer-acceptance/run.py \
  /private/tmp/ccl-work/codex/namespace-integration
```

Unchanged R6/R6a and reader evidence is reused by exact source identity from
`2026-09-24-namespace-consumers-r1`, independently replayed by Claude. The fresh
runtime replay recompiles integrated C, requires the reviewed Wasm bytes, and
uses the integrated runtime sources. The original cold qualification command
belongs to proposal commit `053ebf56`; it reconstructs the proposal from its
then-current parent sources. This command is the historical namespace integration check at `1a076ca4`.
The loader integration supersedes its compiler identity; the current product
check is [loader-acceptance/check.py](../loader-acceptance/check.py), which binds
the complete 42-file compiler source set and the reviewed loader runtime.
