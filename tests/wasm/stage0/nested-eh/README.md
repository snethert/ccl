# Nested exception transfer

S0-LL19-a executes nonlocal exits through nested hand-built emitted frames
under the B entry shape. Each frame pushes a frame record and a root record,
binds a dynamic cell and reserves VSP; frames with cleanup use the final
`try_table catch_all_ref` / `throw_ref` encoding so the cleanup runs exactly
once and the same exception continues outward. Ten cases cover ordinary
return, exits carrying zero, one and six values, a cleanup that raises a
second exit, a missing handler that reaches the host after every frame is
restored, a recoverable check resumed by a use-value handler without
unwinding, a declined handler that becomes an error, a nested debugger exit
inside the handler after the caught values are secured, and a chain of nine
cleanup frames. After every case VSP, TSP, CSP, the binding, the root head and
the handler depth are back at their checkpoints, cleanups are counted, no
post-exit effect ran, every value is compared and the complete event order is
checked. Nine mutants are rejected by the unchanged oracle and ten production
artifact-role omissions are refused.

```sh
python3 tests/wasm/stage0/nested-eh/run.py --output /private/tmp/ccl-nested-eh-fresh
python3 tests/wasm/stage0/nested-eh/run.py --verify /private/tmp/ccl-nested-eh-fresh
```

Requires macOS with Node, WABT `wat2wasm` and `wasm-objdump` on PATH. Use a
fresh output directory outside the checkout. `abi.json` fixes the fixture
TCR, regions, records and cases; `oracle.py` derives every expectation from
it. This is not the production TCR, condition system, debugger, collector or
C boundary; the accepted S0-LL19-b fixture covers the emitted/C boundary.

See [scope and results](../../../../doc/WASM/stage0/nested-eh.md).
