# Census stub registration — 12 September 2026

S0-LL08-a has executed and its [standalone record](../evidence/stub-registration-summary.json) is ready for independent review. It qualifies an observation-only backend-loading recipe and target-state proof. It does not claim a complete bootstrap census, a production Wasm backend or target execution. The existing 27 project acceptances are unchanged.

## Applied unit and loading recipe

The [registration unit](../../../tests/wasm/native-census/stub-backend/patch.json) modifies one shared file in a disposable pristine U1 archive: two entries in `lib/systems.lisp` register the census architecture and backend modules. It adds `compiler/WASM-CENSUS/census-arch.lisp` and `census-backend.lisp` only inside that archive. The main checkout's upstream compiler and kernel source are untouched. The patch, source identities, original failures and exact commands are retained.

Each target session starts a new native process, compiles and loads the architecture and then the backend through the actual module entries, and establishes the complete target context before reading target-dependent source. That context binds the backend, features, FASL target, foreign type data and `TARGET`/`OS` package nicknames. Source containing reader conditionals and read-time constants is read inside it. The target-dependent macro source is loaded there as well. Normal return and nonlocal escape both restore native state.

The architecture supplies the D1 subset used by this proof: 32-bit words, four-byte nodes, fixnum shift 2, cons tag 1, misc tag 6 and the specified tag-bit widths. B supplies zero argument registers. The fixture's unused U1 CPU/OS bit patterns are local identifiers, not a production ABI allocation. Other layout rows, foreign types, architecture macros and lowerings are outside this descriptor's qualified scope; it must not be treated as a complete architecture for the full upstream corpus.

The registered pass-2 entry receives a real U1 front-end function object, retains its acode/dependencies and exits through an explicit capture context. It never returns executable output or writes a target FASL. This is reversible observation under the existing exception, not authorization for a functional pass-2 implementation. Implementation still starts from pristine U1 and the pinned bootstrap.

## Verification

| Check | Result |
| --- | --- |
| Clean native suite | 21,843 / 21,843 eligible tests pass |
| Native suite with registration loaded | 21,843 / 21,843 pass |
| Unchanged native FASLs while registered | 163 / 164 byte-identical |
| Intentional shared artifact | `bin/systems.dx64fsl`: two module data entries; all existing entries unchanged |
| FASLs after removing the unit and rebuilding | 164 / 164 byte-identical to baseline |
| Native probe output and behavior | Identical / pass |
| Evaluated native operator snapshot | Unchanged: 279 slots, including 12 reserved slots |
| Fresh target sessions | 14 cases each; 28 pass; reports identical |
| Target-state controls | 8 rejected |
| Reversible-unit controls | 6 rejected; complete and partial-removal cases pass |
| Producer controls | 11 rejected against the final qualifier |

Both native suites disclose the same 75 upstream-disabled tests. There are no output normalizations. The clean image is rebuilt after removal, and a fresh startup confirms that the census package, backend and module registration are absent. The development registration was also removed.

The target cases observe read-time word width and tags, target/native reader features, a captured macro, natural-width access, the 32-bit fixnum boundary, B's actual five-stack/zero-register argument partition, and direct, lexical and unresolved function-variable dependencies. Natural access reaches the real `immediate-get-xxx` acode with the four-byte unsigned flag, rather than merely reporting a macro name. Lexical calls retain their actual child function identity. Dynamic calls remain unresolved.

Controls expose late package selection, host features/backend, dirty native target features, incorrect word width or argument registers, an actually compiled cached host macro, and a missing module registration. Unit controls reject duplicate application, changed or occupied source, unexplained edits on removal, damaged recovery data and missing ownership. Producer controls reject inconsistent native results, missing or changed FASLs, incomplete reversal, changed operators/registrations, hidden controls and fabricated dynamic-call resolution. The current producer control replay is retained alongside the original control report; an added native-summary consistency check changes one rejection explanation, with all eleven controls still rejecting.

The first full-build attempt omitted the bootstrap's interface databases. Its failure and runner are retained; the qualified run extracts the complete pinned macOS bootstrap. Earlier development reader/type/oracle failures are retained too. None is a CCL defect claim or a passing result.

## Scope and next dependency

The static records cover the fourteen source forms in this fixture, including their compiler-generated inner functions. They do not qualify all 51,342 r7 compiler bodies, narrow the 1,729 dynamic call sites or resolve the remaining 183 unmatched names. This satisfies the registration/target-state slice at its stated bounds; full module/function reachability, operator/lowering/effect joins and semantic initializer prerequisites remain LL15-b/c work. The broader implementation edit-site plan in D6 remains a proposal.

The finalized packet stores the native baseline FASLs once in an archive and retains the one changed shared FASL, the small new module FASLs and the new logs/reports. It references the pinned source/bootstrap/tests and kernel instead of copying prerequisite evidence trees. Verification covers this new packet and its direct inputs. No historical archive scan or new acceptance aggregate was produced. The LL08-a envelope has a per-test contract binding; independent review and project acceptance remain separate steps.

[Reproduction and recovery](../../../tests/wasm/native-census/stub-backend/README.md) describe the executable recipe and its bounds.
