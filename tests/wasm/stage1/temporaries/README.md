# S1-LL06-a: temporary lifetime and evaluation order

The isolated proposal admits PROG2 through CCL's own macro expansion and adds
same-function TAGBODY/GO through the real front-end IR. The source validator
checks tag type, duplicates, lexical scope and function boundaries. Native tag
identity distinguishes nested scopes.

A TAGBODY emits a Wasm loop with ordered segments. Each GO raises the existing
addressed exit after setting an unboxed destination local. Intervening cleanup,
special-binding and temporary frames unwind before that segment starts; a plain
branch would skip their restoration. Each GO currently costs an exception and a
control-record cycle. No speed claim is made. Cross-function GO and general
DO/DOTIMES/LOOP source syntax remain refused.

Thirty cases supply literal expected values and heap effects. Native CCL must
agree before target compilation. The target runs each case below and above
2 GiB, both without collection and with legal collection at the generated GC
service entry: 120 comparisons, 300 collections. Dead allocations must be
reclaimed, and every retired semispace is poisoned. The matrix includes nested
PROG1/PROG2, LET/LET*, SETQ, conditionals, argument order, pending multiple values,
40-iteration loops, captured and special variables, nested/shadowed tags, GO
through cleanup and binding extents, replacement exits, caught errors and a fatal
exit after cleanup. The inherited observer independently checks root, result,
binding, handler, value-stack, temporary-stack and control-stack restoration.

Eight compiler mutants reach runtime and fail: reused local allocation, clobbered
PROG1 saved count, unrooted retained values, shifted retained data, wrong loop
entry, wrong GO target, lost fallthrough and skipped unwind. Eight source
refusals and six publication controls also run. Recompiling the accepted
constructor corpus yields 152 byte-identical WAT/Wasm files. Native R6/R6a runs
on the exact new compiler in disposable U1; the collector source and binary stay
byte-identical to accepted LL18-a.

```sh
python3 tests/wasm/stage1/temporaries/run.py \
  --evidence ../ccl-evidence --output /tmp/ll06-new --qualify
python3 tests/wasm/stage1/temporaries/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-temporaries-r1 \
  --output /tmp/ll06-review-new
```

The [scope](scope.json) and [coverage](coverage.json) identify each claim. This is
a proposal until independently reviewed and accepted; the shared compiler is
unchanged. The replay verifies native R6/R6a from retained builds and re-executes
all oracle compilation, target execution, mutants and admission checks.
