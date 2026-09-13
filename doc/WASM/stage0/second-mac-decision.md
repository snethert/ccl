# Second-Mac requirement retired — 13 September 2026

Decision: remove S0-LL08-c from the required Stage 0 inventory and execution plan. The user explicitly directed: “Also, please remove the ‘run on second Mac’ step. I dont care about that.” This is a project scope decision; the test was NOT_RUN and has not been passed or accepted.

Rationale: the user does not require qualification on a second physical Mac. The project's native reference remains macOS x86-64 at clean U1. Native behavior, same-host repeatability, reversible observation, target-state isolation, independent review and the Wasm engine matrix remain required. No cross-host reproducibility claim follows from the retained same-host evidence.

The inventory now contains 48 required variants, with the same 28 accepted records and 20 missing. No remaining test depends on S0-LL08-c. All remaining per-test contract digests and the accepted envelope are unchanged. Historical inventories, gate results and acceptance scopes retain their original meaning.

Verification is limited to the inventory change, unchanged contract bindings and accepted-envelope identity, documentation projections and the gate's existing controls. The current gate status is a scoped update of the previously verified result, removing exactly the retired missing reason. It does not rerun native tests or rehash the accepted envelope's 104,363 artifact references. See the [verification record](../evidence/second-mac-retirement.json) and [current status](../STATUS.md).
