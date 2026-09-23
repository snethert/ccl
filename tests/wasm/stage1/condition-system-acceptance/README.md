# Condition-system integration identity check

Steve accepted audit 163 with “Accept and integrate default-off”. All four
changed source files equal the reviewed native-qualified proposal. The check
reuses final-source R6/R6a and Claude’s fresh replay; it does not execute again.
The original packet replays from dbd66ffe, before its shared-source pins changed.

```
python3 tests/wasm/stage1/condition-system-acceptance/check.py --output /tmp/condition-system-integration.json
```

SIGNAL placement, class-table writes, implicit condition allocation, and actual
cross-dumped image/READY installation remain explicit obligations.
