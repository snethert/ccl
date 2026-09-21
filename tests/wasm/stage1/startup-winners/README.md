# Startup EQ table reset

This implements the RESET-WINNERS callback's effect on the accepted strong EQ
backing vector: clear every entry without replacing the table. The proposal
adds operation 5 to the integrated C hash service. All table-shape and owner
range checks precede clearing. It reuses the existing initializer to remove
bucket and cache references, tombstones and the key-moved flag, preserving
capacity and object identity; result publication remains last. It neither
allocates nor polls. Operations 0–3 and the B adapter are unchanged.

The unchanged compiler emits seven modules covering the reset itself, APPLY,
multiple-value binding, direct and indirect producers, and cleanup. The native
oracle locates RESET-WINNERS exactly once in the pinned image's system-pointer
registry and asserts its U1 source at byte 8001. With a dynamically bound private
table it calls that untouched registered function, then repeats all six calling
forms natively. Ten populations from empty through 256 entries verify return
identity, value count and secondary NIL. No real compiler cache is cleared.

The target executes full, tombstone and moved tables at 4 MiB and 2 GiB: 360
scenarios, each clearing and then reusing and clearing the same table again.
All three result-delivery modes execute. The explicit cons list in this APPLY
form is optimized by U1, and these generated calls allocate zero bytes.
Complete TCR restoration is checked except the separately verified value count.
Entry objects outside the table remain byte-identical. Collections before and
after clearing poison retired space and independently verify that only the
empty table survives and every previously reachable key/value byte is reclaimed.

Nine compiled C faults cover return identity, both cache and bucket references,
the last bucket, tombstones, moved state, padding and early publication. Twelve
owner refusals preserve the table and result words. The accepted hash-table
trace, both primitive and generated with movement, reproduces exactly against
the proposed service and integrated collector.

```
python3 tests/wasm/stage1/startup-winners/run.py --evidence ../ccl-evidence --output /new/winners
python3 tests/wasm/stage1/startup-winners/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-startup-winners-r1 --output /new/replay
```

This is an auxiliary proposal awaiting review, with no LL15 credit. It adds a
concrete effect for one of the seventeen previously open snapshot callbacks;
sixteen others remain, alongside wider bootstrap membership and definition
work. It uses an owner-installed runtime leaf and a backing-vector adaptation,
not the native HASH-TABLE wrapper or production compiler-cache materialization.
The fixture is Node/V8 only. Integration must use the derived hash.c retained
here; the shared runtime is unchanged. Native R6/R6a is reused by exact compiler
hash, while generated modules and native answers are compiled afresh.
