# Callable metadata — S1-LL12-a

This proposal uses the existing arity and debug words in each 32-byte function.
A pool-owned arity record contains required/optional counts, rest/key/allow flags
and the actual keyword vector (including repeated aliases). A debug record
contains the code name and capture slot names with package identities. Closure
constructors install these records themselves; installation writes no Lisp heap
bytes and performs no global repair. Ordinary compiler entry points keep the
feature off and emit the reviewed bytes.

Sixteen generated modules exercise shared and distinct mutable cells, optional
and keyword defaults, empty key lists, repeated aliases and two named captures.
Native CCL supplies eleven signatures and the mutable closure sequence. Native
closures must be unwrapped with CCL's own `closure-function` before reading their
argument bits and key vectors. Capture names are checked against source names,
and the two-capture record is used to read the actual cells by slot.

Three fresh Workers inspect records before installing code. The latter two
restore a snapshot at 2 MiB and 2 GiB, with different keyword addresses, then call
and mutate restored closures after overwriting the former stack. The snapshot
reader admits only the exact six-word function shape in addition to its accepted
literal kinds. This remains a fixture transport, not the production image loader.

Seven recompiled compiler faults have distinct oracles. Two runtime faults lose
function-field relocation or write during installation. Six malformed snapshots
refuse before publication. The checker also rejects omitted or changed evidence.
Default-mode moving-loop/temporary corpora reproduce all 256 WAT, Wasm and
installed-binary files, with 240 comparisons and 430 collections. A new native
R6/R6a run covers the proposal.

```sh
python3 tests/wasm/stage1/callable-metadata/run.py \
  --evidence ../ccl-evidence --output /tmp/callable-metadata-new --qualify
python3 tests/wasm/stage1/callable-metadata/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-callable-metadata-r1 \
  --output /tmp/callable-metadata-review-new
```

See [scope.json](scope.json) for exclusions. The proposal is not integrated.
Debug records do not yet provide source maps or live debugger state. Production
ownership, arbitrary function kinds and general image construction are separate.
