# LL09 review follow-up

Answers audit 120 without changing the reviewed R1 packet or shared source.
Every R1 source is pinned; the compiler and all thirteen generated modules,
B adapter and image transport stay byte-identical. The derived C service adds
one check: symbol names reject surrogate code points U+D800–U+DFFF. Pinned native
CCL returns NIL from CODE-CHAR for those values. Unicode scalar boundaries
U+D7FF, U+E000 and U+10FFFF remain admitted; U+110000 remains refused. This is
symbol-name admission, not a claim about every future string interface.

The inherited qualification runs against the corrected service, including all
twelve implementation faults and eight publication controls. A supplemental
native run compiles the six MAKE-SYMBOL calling forms and checks the existing
ALLOW-OTHER-KEYS keyword before INTERN, plus the character boundaries. The
derived harness explicitly drives each MAKE-SYMBOL form twice, checks fresh
identity, name, package, exact result count and NIL fills, and records the
operation's fixed/direct/indirect delivery counters. It repeats these checks
before and after relocation, with the original trace and bindings still running.

Both primitive and generated 4 MiB runs load into 2 GiB, poison the old region,
re-admit, and continue against native answers. The other placements load into
4 MiB. ALLOW-OTHER-KEYS is materialized from known pre-existing native membership;
FIND-SYMBOL precedes INTERN, which must neither allocate nor change its identity.
Its relocated identity and self-value are checked after loading.

Four execution controls reject the original surrogate guard, omission of the
existing keyword, a zero-count dynamic MAKE-SYMBOL result and omission of the
high-address load. Six independent report controls reject missing forms,
delivery, keyword, character, after-load or high-load evidence. The original
failed control implementation is retained: it used bitwise AND with an aligned
descriptor address, so its injected fault never executed; the corrected control
compares that address with zero first.

```
python3 tests/wasm/stage1/symbols/review-followup/run.py \
  --evidence ../ccl-evidence --output /tmp/symbols-followup-new
python3 tests/wasm/stage1/symbols/review-followup/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-20-stage1-symbols-review-r1 \
  --output /tmp/symbols-followup-replay-new
```

This auxiliary proposal adds no slot credit. R1's sealed topology, fixed capacity,
pinned objects and checked refusals remain in force. Both packets need acceptance;
integration should take the corrected C service from this follow-up.
