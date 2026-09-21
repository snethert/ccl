# Audit 149 acceptance and integration

301 original definitions execute and match native; 290 have a non-NIL witness.
This integration adds no throughput or slot credit.

Steve accepted the witnesses packet with “accept”. The earlier “accept as
advised” was also Steve's direct message in this conversation; the existing
audit-148 acceptance record already names him. No reviewer recommendation is
used as authorization.

`fold.py` moves the reviewed fixnum selection into the existing operator CASE,
removing the front hook and its helper. The predicates, synthesized acode and
fallback order are unchanged. `run.py target` requires every emitted module,
native answer, execution record, operator witness and summary to equal the
reviewed packet. It also runs the unchanged forty-check collector-owner suite
against the new collector and owner. The optional generated-boundary case is
not part of those forty checks; the witnesses corpus supplies generated calls.

`run.py native` rebuilds the final compiler and architecture in pristine U1.
Native tests are reused only after all newly built native FASLs and the complete
native snapshot equal the reviewed passing qualification. Unchanged CCL source
reader evidence is reused by hash under the adopted R6 allowance.

```
python3 tests/wasm/stage1/bootstrap-witnesses-acceptance/run.py target \
  --output /tmp/ccl-witnesses-integration-target-new
python3 tests/wasm/stage1/bootstrap-witnesses-acceptance/run.py native \
  --work /tmp/ccl-witnesses-integration-work-new \
  --output /tmp/ccl-witnesses-integration-native-new
```

The original proposal verifier remains reproducible at `9f5bd0cc`, before its
inputs were integrated. This integration runner takes its input from that
immutable packet and works after integration.

Carry items: Lisp ASSQ; compile-time refusal of unknown handler classes;
SIGNAL spread refusal; the signed-zero native compiler difference; remaining
input recipes; corrected Wasm module selection and target source branches for
POSIX references. The next harness extension should use a written harness
instead of another replacement layer. No new implementation is hidden in this
acceptance commit.
