# ARM lessons for the Wasm port — 16 September 2026

Status: reviewer document by Claude, written after Stage 0 closed and before
Stage 1's first packet. It records what CCL's 32-bit ARM port, the closest
native analogue to a 32-bit non-x86 target without hardware traps, shows
about mechanisms the Stage 0 decisions and contracts either did not name or
named only in part, and which ARM precedents Stage 1 should take, adapt or
avoid. It changes no decision and claims no execution. Line references are
to U1 `c994217a`.

## Verdict

Nothing in the ARM code would have changed an accepted Stage 0 slot. Four
mechanisms appear in no Stage 0 decision or contract, two are named only
in part, and one Stage 1 precedent choice should be revised. Everything
else ARM does differently from x86 is either already decided in Stage 0 or
does not transfer to Wasm.

## Obligations Stage 1 inherits by name

| # | Mechanism | What ARM does | What Stage 0 records | Falls due |
| --- | --- | --- | --- | --- |
| 1 | Kernel globals block | Runtime globals (heap thresholds, subprims base, exception lock, multiple-value return addresses, static conses, float ABI) live in a NIL-relative table, `lisp-kernel/lisp_globals.h:94-134`, reached from Lisp by the `%get-kernel-global` arch macros, `compiler/ARM/arm-arch.lisp:1260-1362`. | The layout schema has nine layouts (frames, areas, TCR, locks) and no kernel-globals layout; the term appears in no decision or contract. | 1A: the wasm32 architecture file must place the block in linear memory and the arch macros must reach it. |
| 2 | Thread-local binding vector growth | `uuo-tlb-too-small` at `level-0/ARM/arm-symbol.lisp:157`; the kernel reallocates and fills new slots with `no_thread_local_binding_marker`, `lisp-kernel/arm-exceptions.c:2014-2042`. | `tlb_pointer` and `tlb_limit` are TCR fields under D5; no record says who grows the vector, how the collector treats it mid-growth, or what the empty-slot marker is. | 1C, S1-LL17-a. |
| 3 | Interrupt level as a special binding | Polls read the TLB entry at `INTERRUPT_LEVEL_BINDING_INDEX` before the pending word, `lisp-kernel/arm-macros.s:537-545`; a negative level defers delivery. | D5 names the shared pending word and the poll sites, not the per-thread interrupt level that gates delivery; `without-interrupts` has no contract. | 1C with the binding subset; the poll sequence in 1B's emitter. |
| 4 | Stack overflow as a condition | Soft limits raise a Lisp condition and the limit is re-armed after unwinding, `lisp-kernel/arm-exceptions.c:589-641`; the register that overflowed is reported to Lisp, `level-1/arm-error-signal.lisp:335-341`. | Limits and `stack_reserve_bytes` are in the TCR; the debug-frame contract says explicit-stack overflow traps; D6's lowering rule lists type, bounds, arity and unbound checks only. | 1C: a lowering class, the condition path, and the reserve-then-re-arm protocol. |
| 5 | Trap taxonomy, continuable checks | About thirty UUO classes, `compiler/ARM/arm-asm.lisp:190-314`, including continuable variants of every type check, slot-unbound, no-throw-tag, undefined-function call, unresolved foreign entry point, array rank, flags and axis bounds, integer divide by zero; decoded to conditions in `level-1/arm-error-signal.lisp:161-350`. | D6 retains the 143 x86-64 check sites as an inventory to reconcile; continuable checks appear nowhere. | 1C: use ARM's list as the checklist for the lowering-class inventory the exit-criteria review carries forward. |
| 6 | Callback slots | Trampolines are four machine words generated at runtime, then the instruction cache is flushed, `level-1/arm-callback-support.lisp:19-41`. | The seeds and the kernel-import census name the callback dispatcher; no contract says how a callback slot is allocated and installed on a target that cannot generate code. | Stage 2 host services; note in the Stage 2 inventory when it is drafted. |

## Precedents to take from ARM

- **Floating point.** Decided on 16 September as the ARM model: the enable
  mask in the TCR, checks emitted under float safety, ARM's condition
  priority, signalling comparisons. Recorded in
  [the specification](../contracts/floating-point.v1.md).
- **Subprims through a table.** ARM dispatches every subprim through a
  256-entry table inside each TCR at offset 256,
  `lisp-kernel/arm-constants.h:321`, with `ldr lr,[rcontext,#off]`; x8632
  uses absolute addresses. D4's emitted subprims reached by `call_indirect`
  are the same idea without the per-thread copy. `.SPfix-nfn-entrypoint`
  must be subprim zero on ARM; the equivalent lazy fix-up is D5's typed
  entry slot and LL21's lazy installation.
- **Function objects with a separate code vector.** ARM functions are a
  node vector whose slot 0 is the entry point and slot 1 the code vector,
  `compiler/ARM/arm-arch.lisp:761-764`; constants start at slot 2 and
  `nth-immediate` is offset by one. Wasm code is never in linear memory, so
  this shape, not x8632's inline code with a boundary marker, is the
  precedent for the function object under D5's logical code identity.
  Choose the constant index base once, in 1A, and state it.
- **The cross-fasloader.** The Stage 1 plan derives it from x8632.
  `xdump/xarmfasload.lisp` is the closer precedent for function objects: it
  handles targets whose code is not inline, sets the entry point from the
  code vector, and registers its backend with `make-backend-xload-info`.
  Derive tags and NIL from x8632 and function handling from ARM.
- **Explicit allocation slow path.** ARM resumes an interrupted allocation
  by decoding the instruction stream backwards,
  `lisp-kernel/arm-exceptions.c:101-207` and `1625-1813`. D5's explicit
  protocol replaces that; do not attempt anything like it.
- **Thread control by request.** ARM's kernel-service UUO carries
  interrupt, suspend, resume and kill through the trap handler; D5's
  lifecycle mailbox is the Wasm form.

## Facts that do not transfer

- ARM has no temp stack; dynamic-extent objects live on the control stack
  behind `stack_alloc_marker`. Keeping the TSP as D5 does is a choice, not
  a requirement.
- ARM keeps no callee-saved node registers and spills unboxed values
  through a number frame pointer; Wasm locals remove both concerns.
- ARM's constant-index limits are derived from the 12-bit `ldr`
  displacement; use x8632's large limits.
- The instruction-cache flush syscall, the runtime feature probe by
  deliberate illegal instruction, the hard-float versus soft-float ABI
  kernel global, and the per-OS signal-context layouts have no Wasm
  counterpart. The engine matrix is the feature probe.
- ARM emits no inline interrupt poll: `arm2-%interrupt-poll` references an
  `event-poll` vinsn that `compiler/ARM/arm-vinsns.lisp` never defines, so
  ARM interrupts work only through signals. Wasm has no signals; D5's
  inline polling policy stands and x8632's `event-poll` vinsn is the
  precedent.

## Confirmed covered by Stage 0

The kernel-import table is content-identical between ARM and x86-64, so
the 65-import census stands. The safe-reference fault recovery
(`%safe-get-ptr`) is used only by the Objective-C bridge, so its
unsupported disposition in the layout is right. The register-context walkers,
signal-stack copying and condition-code re-evaluation in ARM's handlers
belong to a signal-delivery model that D5 replaced.

## Do not treat as precedent

- ARM64 is not a live target in U1: `arm64-exceptions.h` is a license
  header, there is no `arm64-exceptions.c` or GC, and the compiler files
  are registered nowhere.
- The Darwin ARM kernel build is abandoned: it names an iPhone 3.2 SDK, an
  ARMv6 architecture below the kernel's own minimum, and an object file
  that does not exist.
- In `lisp-kernel/arm-exceptions.c`, `handle_trap` has no body,
  `handle_fpux_binop` still describes PowerPC opcodes, and the FP context
  save and restore imports are debug-trap stubs.
- `compiler/ARM/arm2.lisp:9591-9597` dispatches on backend names that do
  not exist, so `with-c-frame` cannot compile on any ARM target.

## Backend registration checklist for subgate 1A, from the ARM shape

A backend fills about sixty slots of `arch::target-arch`
(`compiler/arch.lisp:255-312`), supplies about twenty arch macros, a
`nx1-<arch>-lap-function` special operator (`compiler/nx1.lisp:2014-2019`
and `level-1/l1-utils.lisp:175`), its own `defarch2` dispatch vector, vinsn
definer and emit macrolet, a `platform-cpu-*` code in the three-bit field at
`compiler/backend.lisp:21-37`, a fasl version and image ABI version, module
lists in `lib/compile-ccl.lisp` and `lib/systems.lisp`, and an xload
registration. ARM's `armenv.lisp`, `arm-backtrace.lisp` and
`arm-trap-support.lisp` show the runtime-side files that accompany a
backend; their Wasm counterparts are the logical-frame and trap-attribution
contracts already accepted.
