# S0-LL23-a structured diagnostics

Real Wasm traps, independently checked binary offsets and exact build/entry
identities. Thirteen execution cases, three build refusals, twelve reporter
mutants and ten omitted-role controls. The first failure and bounded diagnostic
surface are checked literally. Unknown top frames have unavailable attribution.

See [scope and commands](../../../../doc/WASM/stage0/diagnostics.md). This uses a
small hand-built scalar ABI on Node/V8 and does not qualify a production debugger.
