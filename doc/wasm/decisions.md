# Architectural Decisions (CCL→WASM)

**Status:** Living document (restarted 2026-02-15)
**Purpose:** Record major architectural and strategic decisions

**Previous decisions:** See [archive/decisions-2026-02-15-archived.md](archive/decisions-2026-02-15-archived.md) for historical ADRs

---

## ADR-0001: Two-Mode, Two-Phase Development Strategy

**Status:** Accepted
**Date:** 2026-02-15

**Decision:**

Build two distinct deployment modes sequentially:

1. **MVP-1: Library/Embedded Mode** (current focus)
   - Single WASM runner (no threading)
   - postMessage interface for external communication
   - Works in any browser context (no secure requirements)
   - Limited capabilities (stdio only, no persistence, no FFI)
   - Target: Developers embedding CCL WASM in web applications

2. **MVP-2: Full Runtime Mode** (future)
   - Multi-runner with Web Workers
   - SharedArrayBuffer + Atomics for coordination
   - Requires secure context (COOP + COEP headers)
   - Full storage backend (IndexedDB)
   - Complete IDE capabilities (web-ui/ide integration)
   - Target: Developers using CCL as primary development environment

**Rationale:**

**Why two modes:**
- Different users have fundamentally different needs
- Library users want embeddability and simplicity (no hosting requirements)
- Full runtime users want power and accept secure context constraints
- Trying to make one mode serve both use cases creates complexity
- Both are first-class targets, not fallback strategies

**Why sequential delivery (Library Mode first):**
1. **Simpler**: Validates core architecture without threading complexity
2. **Shippable**: Provides concrete deliverable (embeddable CCL WASM)
3. **User feedback**: Real users validate approach before expansion
4. **Technical**: Foundation must work before adding concurrency
5. **Risk reduction**: Avoids building complex features on broken foundation

**What this replaces:**
- Old terminology: "replacement lane" vs "legacy lane" (confusing, implied fallback)
- Old approach: Try to support both modes simultaneously
- Old priority: Threading/SAB work before basic stability

**Impact:**
- Threading/SAB work explicitly deferred to MVP-2
- Current focus: Fix regression (fasl loading), stabilize single-runner
- Success criteria: MVP-1 shippable before any MVP-2 work starts
- No silent degradation: Both modes fail explicitly when capabilities unavailable

**References:**
- [roadmap.md](roadmap.md) - Detailed phased strategy
- [README.md](README.md) - Current status and two-mode description
- [project-overview.md](project-overview.md) - Architectural vision

**Consequences:**
- Clear prioritization: Fix broken → Ship Library Mode → Build Full Runtime
- Threading/SAB deferred but intentionally, not forgotten
- web-ui/ide integration deferred to MVP-2
- Easier to explain to users: "embeddable Lisp" vs "full IDE"

---

## ADR-0002: Character/String Encoding Model (UTF-32 ↔ UTF-8 ↔ UTF-16)

**Status:** Accepted
**Date:** 2026-02-15

**Decision:**

Use a three-encoding model for character/string handling:

```
CCL (internal)  →  Wire Protocol  →  JavaScript (internal)
   UTF-32       ↔     UTF-8       ↔      UTF-16
```

**Specifics:**

1. **CCL side (UTF-32):**
   - Keep CCL's native character representation unchanged
   - Characters are 32-bit Unicode codepoints (UTF-32/UCS-4)
   - No artificial ASCII limitation
   - Full Unicode support as CCL expects

2. **Boundary (UTF-8):**
   - All strings crossing the CL↔JS boundary are UTF-8 encoded
   - Standard web encoding
   - Compact for common text (1 byte ASCII, 2-3 bytes most Unicode)
   - Can represent all Unicode codepoints
   - No surrogate pair issues

3. **JavaScript side (UTF-16):**
   - Keep JS's native string representation unchanged
   - Strings are UTF-16 encoded (standard JS)
   - Use TextEncoder/TextDecoder for UTF-8 conversion

**Implementation:**

```c
// lisp-kernel/wasm32/ exports
LispObj wasm_string_to_utf8(LispObj ccl_string, uint8_t **out_bytes, size_t *out_len);
LispObj wasm_utf8_to_string(uint8_t *utf8_bytes, size_t len);
```

```javascript
// doc/wasm/js/ microkernel
const encoder = new TextEncoder();       // JS → UTF-8
const decoder = new TextDecoder('utf-8'); // UTF-8 → JS

function sendStringToCL(jsString) {
  const utf8Bytes = encoder.encode(jsString);
  // Send bytes to CL via wasm_utf8_to_string
}

function receiveStringFromCL(clString) {
  // Call wasm_string_to_utf8, get bytes
  return decoder.decode(utf8Bytes);
}
```

**Rationale:**

**Why NOT ASCII-only:**
- Artificial limitation that CCL doesn't have
- CCL natively uses UTF-32, forcing ASCII fights the system
- Makes international text impossible
- Doesn't match real-world usage

**Why UTF-8 at boundary:**
- Standard web encoding (interoperability)
- Efficient for most text (1 byte for ASCII)
- TextEncoder/TextDecoder are standard, fast, well-tested
- Avoids surrogate pair complexity (UTF-16)
- Avoids size overhead (UTF-32 = 4 bytes always)
- Can represent all Unicode

**Why keep UTF-32 internally (CL) and UTF-16 internally (JS):**
- No internal conversion needed
- Let each side use its native representation
- Only convert at the boundary (minimal overhead)

**Migration path:**
1. Current "ASCII" code is already valid UTF-8 (ASCII ⊂ UTF-8)
2. Add UTF-8 encoding/decoding support
3. Remove ASCII validation checks
4. Test with international text
5. Document UTF-32 (CL) ↔ UTF-8 (wire) ↔ UTF-16 (JS) flow

**Impact:**
- Full Unicode support from day one
- No artificial character limitations
- Standard web approach (TextEncoder/TextDecoder)
- ~10 lines of conversion code per side

**Replaces:**
- Old decision: "Strings start as ASCII-only with plan for UTF-8 later"
- New approach: UTF-8 wire format from the start, no migration needed

**References:**
- [Unicode Standard](https://unicode.org/)
- [MDN TextEncoder](https://developer.mozilla.org/en-US/docs/Web/API/TextEncoder)
- [MDN TextDecoder](https://developer.mozilla.org/en-US/docs/Web/API/TextDecoder)

**Consequences:**
- Full international text support
- `(format t "Hello 世界! 👋")` works without special handling
- String I/O uses UTF-8 encoding (stdio, kernel_request, etc.)
- No "upgrade to UTF-8 later" technical debt
- Matches how modern web apps handle text

---

## ADR-0003: Capability Model (Explicit Failure, No Silent Degradation)

**Status:** Accepted (retained from previous decisions)
**Date:** 2026-02-15

**Decision:**

Missing host capabilities MUST fail explicitly via `CAPABILITY-UNAVAILABLE` condition:
- Library Mode signals CAPABILITY-UNAVAILABLE for: threading, storage, FFI, networking, real filesystem
- Full Runtime Mode refuses to start without: secure context, worker capability, SharedArrayBuffer
- NO silent fallback from Full Runtime → Library Mode
- NO "try threading, fall back to single-runner" behavior

**Rationale:**
- Clear contract about what works in which mode
- Users know exactly what they're getting
- No mysterious performance degradation
- No "it works sometimes" behavior

**Impact:**
- Library Mode explicitly limited (documented)
- Full Runtime Mode strictly gated (COOP + COEP required)
- Error messages guide users to correct mode for their use case

**References:**
- [capability-matrix.md](capability-matrix.md)
- Original ADR-0009 (archived decisions)

---

## ADR-0004: Subprims as Table Indices (WASM Function Tables)

**Status:** Accepted (retained from previous decisions)
**Date:** Original; reaffirmed 2026-02-15

**Decision:**

Subprims are fixnum indices into a WASM function table, not code addresses.

**Rationale:**
- Matches WASM execution model
- Stable across memory growth
- No PC-style address arithmetic needed

**References:**
- [ABI.md](ABI.md)
- Original ADR-0003 (archived decisions)

---

## ADR-0005: No WASI Runtime (Freestanding Link)

**Status:** Accepted (retained from previous decisions)
**Date:** Original; reaffirmed 2026-02-15

**Decision:**

Compile with WASI headers (for development convenience) but link freestanding:
- No `wasi_snapshot_preview1` imports
- All host interaction via `kernel_request` ABI
- Keeps kernel portable and host-controlled

**Rationale:**
- Avoid implicit POSIX assumptions
- Explicit host boundary via microkernel
- Portable across different JS environments

**References:**
- [build.md](build.md)
- [kernel-request-abi.md](kernel-request-abi.md)
- Original ADR-0004 (archived decisions)

---

## ADR-0006: Explicit Yield/Resume (No Stack Suspension)

**Status:** Accepted (retained from previous decisions)
**Date:** Original; reaffirmed 2026-02-15

**Decision:**

Use explicit stepping (`wasm_ccl_step`) rather than stack-suspension toolchains:
- Portable and simple
- Avoids asyncify/stack-switch complexity
- `kernel_wait` deferred (Stage-3)

**Rationale:**
- Simpler implementation
- Better browser compatibility
- Easier to debug

**References:**
- [yield-resume.md](yield-resume.md)
- Original ADR-0005 (archived decisions)

---

## Decision Numbering

ADRs are numbered sequentially. When archiving old decisions and starting fresh:
- Retain numbers for decisions we're keeping (ADR-0003, 0004, 0005 → renumbered as 0004, 0005, 0006)
- New decisions get new numbers (ADR-0001, 0002, 0003 for new strategic decisions)
- Archived decisions remain in archive with original numbers for reference

This document reflects decisions as of 2026-02-15 after strategic reset to two-mode, two-phase approach.

---

## See Also

- **[roadmap.md](roadmap.md)** - How these decisions translate to phases and deliverables
- **[README.md](README.md)** - Current implementation status
- **[project-overview.md](project-overview.md)** - Architectural vision
- **[archive/decisions-2026-02-15-archived.md](archive/decisions-2026-02-15-archived.md)** - Previous ADRs
