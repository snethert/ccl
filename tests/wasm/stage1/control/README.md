# Generated LL19 control and recovery

This completes the generated LL19 qualification at the bounded scope in
[scope.json](scope.json). It is a compiler proposal for Claude review, not an
integration or an acceptance. The shared compiler and kernel are untouched.

The proposal extends the accepted B compiler with condition instances and slot
readers, active restarts, the generated debugger-hook boundary, checked cons and
vector operations, unbound specials and improper APPLY handling. Control records
also have a separate CSP entry. Soft VSP/TSP/CSP exhaustion enters Lisp with an
emergency reserve and re-arms after transfer. Explicit interrupt polls preserve
masking, unwind and re-enable semantics without suppressing the collector service.

The 46 new native cases generate 107 modules and run in four placement/observation
combinations (184 comparisons). Native CCL must first reproduce every literal
expectation, including effects, values and restored special values. Eight target
resource/protocol cases add 32 comparisons; native stack byte budgets are not the
oracle for these. Thirteen recompiled mutants, five source refusals and six
publication controls must fail. The inherited 587-module B corpus, 62-module
condition corpus and 46-module call-error corpus, cold installation and the full
installation mutant set are re-executed. An independent cleanup observer derives
expected VSP, TSP, CSP, root and binding state from source and ABI sizes, not saved
checkpoint fields. Early fatal diagnostics are checked as structured records.

Condition instances use D1's standard-instance and owner-linked slot-vector
layouts. Each native compilation exports the twelve native classes' effective
slot order/defaults; the owner installs an explicitly sealed bootstrap registry.
The former private condition-mask vectors are gone. Full CLOS metaobjects and
class mutation remain LL11. General restart options/association, interactive
debugger UI, moving collection, symbol installation and host re-entry are not
silently claimed here; see the scope record. Successful compiled calls keep the
accepted direct-continuation path and no extra public-wrapper dispatch.

## Reproduce

From the source repository root, with Node/WABT at the retained toolchain versions:

```sh
python3 tests/wasm/stage1/control/native.py --evidence ../ccl-evidence \
  --work /tmp/ll19-native-work-new --output /tmp/ll19-native-new
python3 tests/wasm/stage1/control/qualify.py --evidence ../ccl-evidence \
  --native /tmp/ll19-native-new --work /tmp/ll19-execution-new \
  --output /tmp/ll19-packet-new
```

The native driver references the accepted unchanged baseline, rebuilds the exact
proposal in pristine U1, tests it, removes it and rebuilds from the original
bootstrap. Qualification also checks native operators and all existing target
module profiles. A retained packet can be verified without another full build:

```sh
python3 tests/wasm/stage1/control/packet.py verify --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-control-r1 \
  --output /tmp/ll19-review-new
```

That command checks every packet/source pin, reconstructs the native evidence
from its archive and accepted baseline references, reruns native qualification,
recompiles positive and mutant compilers, executes all new and inherited tests,
and compares deterministic outputs. Original failed inputs/logs are retained in
`development.tar.gz`; successful intermediate native runs do not substitute for
the final exact-compiler R6. The APPLY prerequisite's source is under
`../b-apply-errors`; this final qualification supersedes its auxiliary scope.
