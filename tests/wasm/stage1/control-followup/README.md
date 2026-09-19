# LL19 review follow-up

Audit 88's three observations, without changing the accepted compiler or loader.
The original LL19 fixture and its pins remain unchanged; its R6/R6a applies to
these identical implementation bytes. This auxiliary packet claims no new slot.

`tcr.v2.json` names the persistent recovery/depth words at offsets 180 and 184.
`schema.py` derives it from frozen v1 and checks all 48 fields' layout, ownership
and root classifications. Three corruptions must fail. Existing generated v1
scratch aliases remain compatible; new code must respect the named ownership.
The reserve-in-use bit suppresses the soft checks for all three stacks together.
Every hard limit stays active. Native CCL's separate guards are not claimed.

Four native cases exercise ordinary error-service decline: a hook returning
zero values, one returning 130, no hook, and a declining handler before a
returning hook. Effects prove the hook/handler ran and the interrupted form did
not resume. All four run at both placements, with and without the state observer
(16 comparisons). Fatal records must identify ordinary-error-service, code 5
and the Wasm tag. Relabelled, missing and engine-trap records are refused.

Native observation intercepts `%break-message` in a fresh disposable image,
**after** U1 calls the real debugger hook. It then invokes the fixture's captured
status observer instead of opening an interactive terminal debugger. With the
observer inactive it forwards unchanged. No source or FASL is patched; the
process is discarded. `l1-readloop-lds.lisp` is pinned as the boundary authority.
This is a post-hook boundary witness, not an interactive native debugger test.
The target harness labels fatal code 5 TYPE for this focused non-function
TYPE-ERROR corpus; it does not alter the emitted exception or diagnostic.

```sh
python3 tests/wasm/stage1/control-followup/run.py --output /tmp/ll19-followup-new
python3 tests/wasm/stage1/control-followup/packet.py verify \
  --packet ../ccl-evidence/2026-09-19-stage1-control-followup-r1 \
  --output /tmp/ll19-followup-review-new
```

Replay checks the accepted packet identity, its 152 executed-source pins, the
unchanged integrated compiler, native expectations, Wasm execution and every
retained deterministic binary and observation. Original two failures are kept
in development.tar.gz. A later compiler change needs its own qualification.
