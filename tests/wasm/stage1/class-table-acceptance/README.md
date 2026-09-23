# Class-table integration identity check

Steve accepted audit 164 with “Accept and integrate default-off”. All three
changed source files equal the reviewed native-qualified proposal. The check
reuses final-source R6/R6a and Claude’s fresh replay; it does not execute again.
The original packet replays from a7d33401, before its shared-source pins changed.

```
python3 tests/wasm/stage1/class-table-acceptance/check.py --output /tmp/class-table-integration.json
```

Class-table growth, REMHASH, implicit condition allocation, and actual
cross-dumped image/READY installation remain explicit obligations.
