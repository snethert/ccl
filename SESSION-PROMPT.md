# CCL WASM Port - Session Start Prompt

Copy everything below the line into a new Claude Code session.

---

## Context

You are continuing work on the CCL (Clozure Common Lisp) WASM port. The repository is at `/Users/buildsomething/Source/ccl` on branch `wasm-port`.

**Read these files first** (in parallel):
1. `/Users/buildsomething/Source/ccl/TODO.md` — Current task tracker with priorities, blockers, and decisions
2. `/Users/buildsomething/Source/ccl/doc/wasm/README.md` — Project status overview

**Then** suggest the highest-priority unblocked task from TODO.md and ask which task I'd like to work on.

## Project State Summary

**What this is:** Porting Clozure Common Lisp to WebAssembly. Two-mode strategy: MVP-1 (Library/Embedded, single-runner, current focus) then MVP-2 (Full Runtime, multi-runner, deferred).

## Key Files

| Purpose | Path |
|---------|------|
| Task tracker | `TODO.md` |
| C kernel stubs | `lisp-kernel/wasm-kernel-stubs.c` (~4960 lines) |
| C subprims | `lisp-kernel/wasm-subprims-provider.c` (~6580 lines) |
| WASM Makefile | `lisp-kernel/wasm32/Makefile` |
| JS microkernel | `scripts/wasm/lib/microkernel.mjs` |
| JS image builder | `scripts/wasm/lib/make-real-image.mjs` |
| JS image loader | `scripts/wasm/lib/load-image.mjs` |
| JS WASM loader | `scripts/wasm/lib/ccl-loader.mjs` |
| JS bootstrap contract | `scripts/wasm/lib/bootstrap-contract.mjs` |
| JS persistence | `scripts/wasm/lib/persist-service.mjs` |
| Smoke tests | `scripts/wasm/tests/smoke-test.mjs`, `gc-forwarding-smoke.mjs`, `kernel-request-smoke.mjs` |
| Build script | `scripts/wasm/rebuild-everything.sh` |
| Repro pipeline | `scripts/wasm/repro-startup-pipeline.sh` |
| Docs root | `doc/wasm/README.md` |
| Porting status | `doc/wasm/porting-status.md` |

## Standing Rules

1. **Read TODO.md at session start.** Use TodoWrite for micro-tracking within the session. Update TODO.md when tasks complete or new blockers are discovered.
2. **Time-box investigations.** Set time limits, then decide fix vs workaround vs defer.
3. **No "replacement" or "deprecation" language.** Use MVP-1 / MVP-2 mode names.
4. **Professional tone.** No informal phrases like "core bet", "the hard question".
5. **Build and test after changes.** `make -C lisp-kernel/wasm32` then run the 3 smoke tests.
6. **Doc conformance.** When editing `doc/wasm/` specs, check Doc Version field against STYLE-GUIDE.md v1.0.0.
