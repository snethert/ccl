# Protocol Compatibility Report v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-17  
Scope: Executable compatibility evidence for runtime bridge and wire-protocol versioning  
Depends on: `web-ui/spec/protocol-version-negotiation-v1.md`, `web-ui/spec/runtime-bridge-envelope-v1.md`, `web-ui/spec/ui-wire-format-tree-v1.md`, `web-ui/spec/ui-wire-format-events-v1.md`, `web-ui/spec/conformance-gate-profiles-v1.md`  
Compatibility: Report format is stable for `v1.x`; incompatible report schema changes require `v2`.

## 1. Purpose

This report captures current compatibility evidence for protocol negotiation and mixed-version handling.
It complements normative contracts with executable outcomes.

## 2. Evidence Summary

| Evidence ID | Command | Observation | Result |
|---|---|---|---|
| `compat.runtime-bridge.version-check.v1` | `node --test tests/phase-5-runtime-bridge.test.mjs` | Runtime envelope accepts `version=1` and rejects unsupported versions. | pass |
| `compat.command-frame.version.v1` | `node --test tests/phase-5-runtime-command-roundtrip.test.mjs` | Runtime command frame encodes/decodes `frame_version=1`. | pass |
| `compat.microkernel.bridge-opcodes.v1` | `node --test tests/bridge-microkernel.test.mjs` | Bridge opcodes for poll/render/measure execute with stable contracts. | pass |
| `compat.runtime-output.transport.v1` | `node --test tests/phase-5-runtime-output.test.mjs` | Runtime output/event transport works in default and `sab_ring_v1` lanes. | pass |
| `compat.browser.render-kernelless.v1` | `npm run -s test:browser:render` | Browser harness validates DOM/Canvas/WebGL render path with `kernel=off`. | pass |

## 3. Claim Scope Verdicts

| Claim scope | Required protocol evidence lanes | Current verdict | Blocking lanes |
|---|---|---|---|
| `full-runtime-v1` | `compat.runtime-bridge.version-check.v1`, `compat.command-frame.version.v1`, `compat.microkernel.bridge-opcodes.v1`, `compat.runtime-output.transport.v1`, `compat.browser.render-kernelless.v1`, `compat.kernel.abi-negotiation.v1`, `compat.browser.kernel-on.v1` | blocked | `compat.kernel.abi-negotiation.v1`, `compat.browser.kernel-on.v1` |

## 4. Mixed-Version Behavior Matrix

| Surface | Producer | Consumer | Expected behavior | Evidence | Verdict |
|---|---|---|---|---|---|
| Runtime envelope | `v1` | `v1` | Accept and normalize message | `tests/phase-5-runtime-bridge.test.mjs` | pass |
| Runtime envelope | `v99` | `v1` | Reject with unsupported-version failure | `tests/phase-5-runtime-bridge.test.mjs` | pass |
| Runtime command frame | `v1` | `v1` | Poll/decode succeeds with stable header layout | `tests/phase-5-runtime-command-roundtrip.test.mjs` | pass |
| UI tree/event wire payloads | `v1` | `v1` | Decode succeeds through bridge codec paths | `tests/bridge-codec.test.mjs` | pass |
| Kernel ABI negotiation (`KERNEL_OP_CAPS`) | unknown | `v1` runtime | Must enforce strict-major gate before startup | Not executable in current environment | pending (`full-runtime-v1` blocker only) |

## 5. Known Gaps

1. Kernel-enabled negotiation evidence is blocked in the current environment and remains an open lane for `full-runtime-v1`.
2. Kernel-on browser harness (`tests/browser.test.mjs`) is required for `full-runtime-v1` and is currently blocked while kernel assets are unavailable.
3. Current asset preflight shows kernel-on browser lane is blocked by missing local artifacts:
   - `wasm-ui-modules.json` (all candidate locations missing)
   - `root.image`/`minimal.image` (all candidate locations missing)

## 6. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `compat-report.evidence-missing` | Required compatibility evidence lane not executed. | Conditional | Run the missing lane and record result. |
| `compat-report.negotiation-regression` | Observed behavior contradicts protocol negotiation contract. | No | Block release and remediate contract or implementation. |
| `compat-report.environment-blocked` | Lane cannot execute due environment constraints. | Conditional | Re-run in supported environment and update report. |
| `compat-report.scope-blocked` | Required blocker lane failed for a given claim scope. | Conditional | Resolve blocker lane(s) for the blocked scope. |

## 7. Conformance

This report is conformant only if:

1. Section 2 contains at least one passing lane for each scoped protocol surface.
2. Section 3 declares a verdict for `full-runtime-v1`.
3. Section 4 includes both acceptance and rejection behavior for version negotiation where executable.
4. Pending required rows <a id="REQ-PROTOCOL-COMPATIBILITY-REPORT-V1-0D3CDB1195"></a>MUST keep `full-runtime-v1` blocked until passing evidence is recorded.
