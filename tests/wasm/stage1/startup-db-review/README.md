# Database reset admission follow-up

Auxiliary response to audit 130 F1; no acceptance, integration or slot credit.
The service, compiler, adapter, generated modules and native oracle are reused
unchanged from STAGE1-STARTUP-DB-R1. Its fixture remains unmodified.

The derived harness adds three consistent malformed-owner cases at 4 MiB and
2 GiB. A correctly linked forged directory replaces an arena member; a correctly
linked shorter list omits an arena member; and both structure roles use one
descriptor. The service refuses with status 3, 3 and 2 respectively. Each case
checks the arena, a guarded outside object, all four poisoned publication words
and all 64 TCR words remain byte-identical.

Removing membership, exact visit count or descriptor distinctness independently
passes the full original harness. Each compiled mutant now fails its own directed
case. The four earlier mutants still fail. The original positive execution record
remains byte-identical, with the six added refusals recorded separately. No native
or compiler rebuild is needed for this harness correction.

```
python3 tests/wasm/stage1/startup-db-review/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-20-stage1-startup-db-review-r1 \
  --output /private/tmp/ccl-startup-db-review-replay
```
