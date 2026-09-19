# TCR v2: persistent recovery fields

19 September 2026. [Schema](tcr.v2.json), derived and checked by the
[LL19 follow-up](../../../tests/wasm/stage1/control-followup/README.md).
The 256-byte, 48-field layout is byte-compatible with frozen [v1](tcr.v1.md).
No accepted contract binding or earlier evidence is changed.

| Offset | v2 name | Historical alias | Meaning |
| --- | --- | --- | --- |
| 180 | stack_reserve_flags | scratch0 | Bit 0 means recovery is using stack reserve; other bits are preserved. |
| 184 | debugger_depth | scratch1 | Persistent hook nesting depth, restored on return and transfer. |

Both are owner-thread raw state, never roots or reusable scratch. Existing
architecture aliases retain the same addresses; future code must honour these
names and ownership. No compiler regeneration is needed for this compatible
schema revision.

The current reserve bit suppresses soft checks on VSP, TSP and CSP together
while recovery executes. Each hard limit remains enforced. This differs from
native per-stack guard state; changing to separate reserve flags requires new
nested-exhaustion and recovery tests. Ordinary-service decline is executed by
the same follow-up, including a returning hook and a NIL hook. Interactive
debugger and host re-entry behaviour remain separate work.
