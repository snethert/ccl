# CLR publication overwrite check

Audit 129 found that the successful SET before the direct CLR check left three
expected publication words in place. The guard now poisons **all four words**
with the bitwise complement of `[table, NIL, 1, 0]` immediately before CLR.
Every bit must be replaced to satisfy the same publication assertion.

Six compiled faults omit each individual word, omit all three trailing words,
or explicitly rewrite their stale contents using volatile stores. Five escape
the previous guard; the omitted primary word was already rejected. All six
fail the poisoned guard. The twelve earlier faults remain rejected, and the
positive generated execution record is byte-identical to the original packet.
The service, compiler, adapter, generated modules and native oracle are unchanged.
This sibling overlay preserves both earlier fixtures and their source pins.

Audit 129 closed registry ordering. Its pinned Node/Chromium comparison is reused
without rerunning an unchanged ordering test. No native rebuild is needed.
No acceptance, integration or LL15 credit is claimed. Future validation must use
this poisoned harness and the previously reviewed registry-order overlay.

```
python3 tests/wasm/stage1/startup-winners-publication/run.py --evidence ../ccl-evidence --output /new/publication
python3 tests/wasm/stage1/startup-winners-publication/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-startup-winners-publication-r1 --output /new/replay
```
