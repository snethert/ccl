# Audit 159 stack acceptance

537 original definitions execute, 502 have non-NIL witnesses, and 2,060 of
2,231 admit. Integration adds no throughput or slot credit.

The user accepted all seven packets, explicitly including behavioural branch
WB-1. The final files are copied from the reviewed division proposal; all
runtime sources remain unchanged. The native command qualifies the final
integrated source in pristine U1. The verify command reconstructs only the
needed numeric artifacts from the bound delta chain and executes through
byte-verified production runtime imports. It needs no temporary prior replay.

```sh
python3 tests/wasm/stage1/bootstrap-stack-acceptance/run.py native --output /tmp/ccl-stack-native-replay
python3 tests/wasm/stage1/bootstrap-stack-acceptance/run.py verify --output /tmp/ccl-stack-target-replay
```

The initial artifact reconstruction visited only the first dependency and
missed two introspection artifacts; the corrected traversal follows all needed
bound ancestors. It preserves every final artifact by its reviewed hash.
Full method selection, numeric restarts, GCD, class-based condition matching
and the image/READY join remain work for later proposals.
