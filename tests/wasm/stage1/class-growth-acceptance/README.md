# Class-growth acceptance and integration

Steve accepted the audit-165 candidate with “accept”. The backend and target
Lisp file are the exact reviewed, native-qualified bytes. Class mode remains
off by default. P4 validation tooling is unchanged and under separate review.

```
python3 tests/wasm/stage1/class-growth-acceptance/check.py --output /tmp/class-growth-integration.json
```

This checks integrated source identity and reuses final-source R6/R6a (21,843
tests) and Claude's from-scratch replay (26,048 comparisons). It does not execute
again. The original growth verifier replays from 78b187ba, before integration.

Growth stops at 16,384 entries; replacement and deletion still work there.
Arithmetic payloads and condition subclasses retain the disclosed O-28/O-29
boundaries. Legacy binary identity is by inspection (O-27), not a fresh binary
comparison. Cross-dumped class roots, READY, debugger/re-entry work and removal
of legacy mode remain open. No new original-definition or LL15 credit.
