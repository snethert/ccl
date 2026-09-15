# Kernel-import census — 15 September 2026

Status: diagnostic EXECUTED and PASSING at its stated scope; awaiting Codex's
review under the 15 September role switch. Packet `KERNEL-IMPORTS-R1` in the
evidence repository. No inventory slot changes and no gate credit; Stage 0
stays at 40 accepted, two missing and six unreviewed of 48.

Authorship: Claude Fable 5.1 wrote this fixture and the generated
[census](../contracts/kernel-imports.v1.md) on branch `wasm2-claude`; Codex
reviews them. No shared compiler or upstream kernel source changed: the
derivation reads the pinned U1 files. It touches none of the census
fixtures Codex is working in; its census-shaped nodes are offered as the
content of the working graph's unresolved `gap:imports` placeholder.

## What executes

A control execution over pinned U1 sources. The C `defimport` table and the
x8632 `KERNEL-IMPORT-` enumeration are joined by index with offset and name
agreement checked; the Lisp sources are scanned for every caller site with
its form and x8632 applicability; `lisp-kernel` is scanned for every C or
assembly definition and C call-site count; and a closed disposition ledger
supplies each import's D6 group, per-profile disposition, closure phase,
replacement, regression obligations and expected caller counts. The
committed [kernel-imports.v1.json](../contracts/kernel-imports.v1.json)
must equal the regeneration byte for byte.

| Fact | Value |
| --- | --- |
| Imports | 65, all with a located C or assembly definition |
| With x8632 Lisp callers | 42 over 63 sites |
| Required in the bootstrap closure | 57 (10 loader, 3 definitions, 36 runtime, 16 none) |
| Full profile | 10 Wasm runtime, 24 host services, 15 atomics, 16 unsupported |
| Single-thread JSPI | 6, 26, 10, 23 |
| Precompiled callback | 6, 6, 10, 43 |

## Findings for the reviewer

Shared-library revival in `l0-cfm-support` reaches `GetSharedLibrary` and
`FindSymbol` at startup on native macOS; both are unsupported in every
profile, so the evaluated closure has to carry those callers through the
unsupported disposition explicitly. Twenty-three imports have no Lisp caller by
name and are reached only from C, subprimitives or the GC trap; the C-side
rendezvous entries among them are replaced by the D5 protocol, not removed.
The four FP-context and vector-register entries are assembly-defined,
uncalled from Lisp, and unsupported pending the D6 floating-point policy.

## Controls

Seven refusals of mutated copies: a ledger entry removed, the C table
shortened, the Lisp table reordered (caught by name agreement, not by
counts), a wrong expected caller count, a disposition outside the
vocabulary, a census node outside the census schema, and an unsupported
import placed in a closure phase.

## Evidence and reproduction

The packet holds the regenerated census, observations, environment with U1
pins, the seven control records and source snapshots; the verifier
regenerates the census and compares the deterministic files byte for byte in
about two seconds. A change to either U1 source, the ledger or the committed
census makes the producer refuse.

Limits. Source inspection cannot see target conditionals, macro-mediated
calls or reachability; those are S0-LL15-b's job. Dispositions are proposals
under D6's decided vocabulary, not decisions about hosting; the floating-point
policy and the writable store remain later decisions.
