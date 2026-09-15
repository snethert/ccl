# Native generic-function registry checkpoint

`inspect.lisp` observes a fresh release bootstrap in a disposable pristine U1
archive. It copies the native GF population, reads subtype and registry slots,
and joins installed methods to actual function objects with per-session IDs.
It retains an uninitialized object explicitly. There is no cross-run identity
join to the original 465 prototypes and no callee bound or gate credit.

The private corpus runs actual CCL generic-function construction, method
addition, replacement, removal, EQL dispatch and around-method combination.
It compares twelve calls and eight changed checkpoints, exercises four field
mutations with restoration, and rejects an ordinary function with the same
dcode literal as a GF. These are sequential observations; effective-method
caches, mutable class/combination internals and concurrency are not qualified.

One call exposes an upstream defect: after removal of all methods, a direct
method dcode still executes. `removal-probe.lisp` reproduces it in a separate
process with no observer or inspector loaded. Analysis requires that negative
evidence to remain visible. A diagnostic PASS means the stated observations
and controls agree; it does not mark this behavior semantically correct.

```sh
python3 tests/wasm/native-census/dispatch-registry/run.py \
  --evidence /Users/buildsomething/Source/ccl-evidence \
  --work /tmp/ccl-dispatch-registry-work \
  --output /tmp/ccl-dispatch-registry-output
```

Both paths must be fresh, outside the checkout and evidence repository. Two
native captures must be byte-identical. The third session runs the independent
reproduction. The analyzer joins all records, checks the literal probe oracle,
and runs 23 omission/substitution/promotion controls. No shared source is edited,
no native build runs and no FASL or image is saved.

Add `--packet /path/to/retained/packet` to verify a packet against three new
native sessions and six byte-identical outputs. The runner preserves command
logs, original failures and the executed source versions. Finalization retains
one packet and references the existing source, kernel and bootstrap archives.
It does not scan the historical evidence store.
