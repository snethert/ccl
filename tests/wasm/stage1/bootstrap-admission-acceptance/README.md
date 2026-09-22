# Audit 153 acceptance and integration

No new execution credit: 382 original definitions remain matched, 355 with non-NIL return witnesses. Steve authorized “accept and integrate.” This integration includes the compiler, architecture and re-cut CCL source, and keeps the OS routing prototype out of the shared tree.

The two reviewed architecture macros move from the backend tail into `wasm32-arch.lisp`, in the same package and with identical forms. All other reviewed files are installed byte for byte. The runner first asserts that every installed byte is the declared final byte, then uses those current files in the disposable build. Runtime files are unchanged.

From the project root:

```sh
python3 tests/wasm/stage1/bootstrap-admission-acceptance/run.py target --output /tmp/admission-integration-replay
python3 tests/wasm/stage1/bootstrap-admission-acceptance/run.py native --output /tmp/admission-native-replay --work /tmp/admission-native-work
```

The retained native run passes 21,843 tests, with 146 identical FASLs and all 164 restored. The target replay reproduces 1,152 reviewed files. The earlier existing-target reader matrix is reused by exact CCL source identity; macro relocation does not change those source branches. Records are retained under `accepted-integration` in the combined bootstrap-math packet. No LL15 or other slot credit.
