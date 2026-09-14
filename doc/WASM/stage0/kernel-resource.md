# KERNEL-PATH resource replacement — 14 September 2026

Status: executed, independent review pending. Packet
`NATIVE-KERNEL-RESOURCE-R1` supplies one explicit source replacement and its
native reference behavior. It gives no census gate credit. Stage 0 remains
**39 accepted, nine missing and zero unreviewed of 48**.

## Original source and replacement

U1's `KERNEL-PATH` reads a native kernel-global pointer, decodes a C string or
consults the executable command line, and performs platform-specific pathname
processing. Those mechanisms are outside the Wasm profile. The existing
[boundary ledger](target-descriptions.md) requires a loader-supplied bootstrap
resource identity in the virtual namespace; it does not permit dropping the
function from the census.

The fixture reads the exact original form from `lib/dumplisp.lisp`, ordinal 12,
character offsets 12716–13142, under the registered Wasm target. The original
still stops at `%GET-KERNEL-GLOBAL-PTR`. A separate fixture source defines the
replacement as one direct call to
`WASM-CENSUS-SERVICES::KERNEL-RESOURCE-IDENTITY`. The real front end captures
that function and the named call before code emission.

Both source records, the original failure and the replacement's single call
are retained. No U1 form, compiler IR or global `CCL::KERNEL-PATH` definition
is overwritten. These are separate source slices: the replacement is not
presented as an eighth successfully traversed original definition. The full
original-file result remains seven captured definitions and five stops.

The replacement's body needs no macro expansion. Its enclosing `DEFUN` does:
the capture records the native expander's U1 source position, 29147 in
`lib/macros.lisp`, and the Wasm target context. This deliberately small slice
does not rerun the source-rebuilt macro environment or qualify the original
body's expanders. The native utility driver also emits a warning about its
unused legacy `RUN` entrypoint; this fixture calls only its native compilation
helper and reaches its own explicit completion marker.

## Loader contract and reference behavior

The [contract](../../../tests/wasm/native-census/kernel-resource/contract.json)
refines the existing resource-name obligation:

- The loader supplies a nonempty Lisp string without NUL, once before lookup.
- Installation copies the input before marking it ready. Every lookup returns
  an independent string, so callers cannot change the stored identity.
- Lookup before installation, invalid input and a second installation signal
  distinct errors. Invalid input leaves the state unready and permits a retry.
- The name is opaque. Unicode, spaces and `..` segments are preserved exactly;
  native executable lookup and pathname canonicalization are absent.

The reference service bodies and replacement are compiled as lexical functions
in native CCL. Only fixture-owned special variables are dynamically bound; none
of those functions is installed globally. These variables are a reference for
future process-owned loader storage, not a Wasm implementation of that storage.

Fourteen cases check every return value, error category and message, readiness
and stored name. They include caller mutation of the input, mutation of a
returned string, a second installation, invalid number/empty/NUL inputs with
successful retries, and an opaque Unicode resource name.

Eight native source mutants independently remove the readiness guard, input
copy, output copy, reinstall guard, string test, nonempty test or NUL test, or
publish readiness before validation. The unchanged oracle rejects each at its
named first failing case. Nineteen checker controls reject source substitutions,
missing or surplus calls/cases, wrong target context, erased original gaps,
changed service bytes and false restoration or implementation claims.

## Evidence and remaining work

Two fresh normal sessions produce byte-identical captures; all eight native
mutants complete and are rejected by the semantic oracle. The retained verifier
rechecks all ten captures, the exact mutant edits, the joins, source bindings
and controls. Native source pins and the disposable copy's FASL set remain
unchanged. Input archives, bootstrap, kernel, image and registered stub FASLs
are referenced from the existing retained inputs. There is no native rebuild.

The first attempt ran successfully in CCL but its checker incorrectly expected
zero macro events. It rejected the actual enclosing `DEFUN` expansion. The
original capture, log, run record and exact fixture sources are retained in
the packet's development archive. The corrected check requires that exact
expander observation and a new control rejects a substituted backend. The
second attempt passes. No service behavior changed between attempts.

`joins.json` records the original source identity, replacement source digest,
captured prototype and one direct service edge. It is an integration witness,
not a modification to the complete exchange graph. The earlier pinned contract
ledger stays unchanged. Wasm string materialization and collector roots,
process-owned storage and publication, early/full target conditions, and the
complete LL15 integration all remain explicit obligations. The reference does
not establish cross-Worker behavior or target-runtime implementation.

Next under the alternating plan is S0-LL13-b: a late Worker must preserve
mutated shared state while initializing only its owned private regions. Then
return to the remaining startup replacements and broader source traversal.
