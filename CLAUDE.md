# CCL project rules

This is the clean upstream Clozure/ccl v1.13 restart at `c994217adc56b3f8a564526cee4695893ac84d86`. Current Wasm work lives in `doc/WASM` and `tests/wasm`; the sibling `ccl-attempt1` tree is archived, read-only reference. Its old instructions are not this project's rules.

- macOS is the sole reference platform for the Wasm project. The native baseline is macOS x86-64, a target supported by U1. The Wasm target runs in its engine. Historical evidence retains its original provenance.
- Codex may build isolated fixtures, supporting tooling and documentation. Codex must not edit shared compiler or upstream `lisp-kernel` source. The freestanding fixture kernel under `tests/wasm` is within the authorized scope.
- Verify changes before committing. Retain original failing evidence, exact input/toolchain hashes, explicit skips and the difference between executed and accepted results.
- Adversarial review must come from a different model/provider than the author. A same-author audit does not satisfy it. Claude's user-supplied review of Codex's r8 fixture is recorded in `doc/WASM/stage0/claude-review.md`; subsequent fixes need their own review before acceptance.
- Follow the R6 and R7 contracts in `doc/WASM/acceptance.md`. Do not weaken a test or silently waive an obligation to obtain PASS. Shared native changes require their own qualified before/after evidence and review.

These rules record the user's 2026-09-11 platform decision and supplied audit instructions. They do not import unpublished memory or rules from the archived attempt.
