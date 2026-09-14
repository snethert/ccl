# S0-LL22-a artifact identity control

Runs the unchanged production gate against quarantined synthetic records and
files. No compiler, image restore, materializer or Wasm execution is claimed.

```sh
python3 tests/wasm/stage0/artifact-identity-control/run.py \
  --output /private/tmp/ccl-artifact-identity
python3 tests/wasm/stage0/artifact-identity-control/run.py \
  --verify /private/tmp/ccl-artifact-identity
```

Use a fresh output directory outside the checkout. The two synthetic builds have
separate source, implementation, test, ABI, template, installed-binary, image,
host-compiler, options and log files. Their templates are identical while their
hand-encoded module bytes differ. Those modules are never instantiated.

The synthetic inventory explicitly requires all ten artifact roles. Two complete
reports pass. For each role, a mixed/stale file, a missing file and an omitted
role fail. Six additional cases cover a duplicate masking the absent ABI role,
a template hash offered for installed bytes, a wrong source revision, a changed
test contract, a stale inventory snapshot and an unreviewed record. The 38 cases
have literal expected statuses, exit codes and diagnostics in `cases.json`.

The verifier rebuilds the synthetic files, bounds the retained file set, compares
each mutation with its declaration, and re-executes the real gate on every case.
The outer result is a CONTROL EXECUTION record for S0-LL22-a and stays unreviewed
until independent review and explicit project acceptance.

The gate checks declared identities against bytes and configured mandatory
roles. It does not authenticate a producer or infer that a newly rehashed set
is semantically consistent. A template-to-binary materialization relationship,
Lisp behavior and the actual R6 patch comparisons remain separate obligations.
