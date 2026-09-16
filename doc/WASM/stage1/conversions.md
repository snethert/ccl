# Generated typed conversions — 16 September 2026

S1-LL07-a is reviewed by Claude and [accepted by the user](acceptance-ll07.json). The [exact reviewed backend](integration-ll07.json) is integrated; its
reversible proposal remains under `tests/wasm/stage1/conversions`. The verifier checks that the inherited LL04 emitter is
unchanged apart from dispatch to the new primitive mode.

| Check | Result |
| --- | --- |
| Real front-end/pass-2 generated functions | 17 |
| Native mathematical / Python / target comparisons | 349: 129 returns, 220 checked refusals |
| Static representation and source refusals | 14 |
| One-site compiler mutants | 20 rejected |
| Real target memory | 32,769 pages, including header reads above 2 GiB |
| Registered native suite | 21,843 passed; 75 upstream-disabled |
| R6 / R6a | 162/164 unchanged while registered, two explained registration changes; 164/164 after removal; five architecture tables and seventeen module profiles preserved |

The new entry is explicitly a **typed internal primitive ABI**, not a Lisp B
entry. Raw parameters and results stay outside the tagged root stack. The
compiler checks representation kinds on actual front-end IR; an address
cannot feed signed boxing, and an unvalidated integer cannot feed code-ID
or slot extraction. General Lisp calls and primitive-call integration remain
LL05. The accepted B decision is retained as the separate Lisp ABI authority.

Fixnum boxing/unboxing checks the signed 30-bit limits and sign extension.
Pointer tagging and checked displacement retain high bits; real header reads
use displacement -6 below and above 2 GiB. Near-4-GiB values are converted
without dereference. Array payload arithmetic derives the exclusive limit
2^(32-8) from U1 and tests 2^24-1 versus 2^24, with separate multiplication
overflow checks and no at-limit allocation.

The ID registry is monotonic, single-owner and bounded; validation proves
issuance, and a shared-memory sequence reaches exhaustion without a failed
write. Slot handles carry an explicit kind and are checked against actual
table capacity/presence, reserved prefix and owner-supplied signature/role
metadata. A generated identity function supplies the callable table entries.
This is not the full installation registry: its owner must maintain truthful
metadata and stability during validation and use. Concurrency, reclamation,
allocation, object construction and Lisp condition objects remain later work.

The native reference evaluates the same lambdas using mathematical word
operations and sparse memory; it does not present native pointers as Wasm
addresses. Target execution additionally checks physical memory effects and
refusal preservation. The accepted pristine 1A native baseline is reused;
the registered build/test and removal build are fresh.

Development retained two failed compiler/reference sessions and the mutation
run that exposed the missing exact-2^32 address-overflow test. The test was
added; the production overflow check already refused that value correctly.

[Commands, ABI and verifier](../../../tests/wasm/stage1/conversions/README.md).
Packet: `ccl-evidence/2026-09-16-stage1-conversions-r1`.
