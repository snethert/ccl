# S0-LL22-b — actual registration R6 control, 14 September 2026

Status: executed; reviewed by Claude's forty-second audit at `23bb1455` without
defect; project acceptance pending.
Packet `R6-REGISTRATION-CONTROL-R1` contains one complete comparison and 44
quarantined damaged inputs, all refused by the same comparator.

The subject is the actual [accepted census registration](stub-registration.md)
patch, not a synthetic compiler. The runner reapplies that unchanged observation
unit in a fresh disposable U1 source archive, records the whole source inventory,
and removes the unit before returning. It reuses the accepted 12 September native
builds, tests, FASLs and evaluated snapshots. It does **not** claim another native
build or test execution, or change the implementation checkout.

| R6 category | Comparison and scope |
| --- | --- |
| Existing target source | All 872 original regular source-archive files are accounted for. The 243 files under the enumerated target/compiler/kernel directories remain identical; every other original file except the one declared shared change is also protected by exact equality. Two observation-only additions are individually bound. Removal restores the complete original manifest. No native execution claim for other targets. |
| Unchanged native inputs | Exact source, native compiler kernel, bootstrap archive, commands, options and environment are pinned. The complete 164-file native build manifest is compared; 163 files match during registration, and all 164 match after removal. The 164 baseline archive members join their recorded bytes. No normalization is allowed. |
| Intentionally changed shared artifact | Only `lib/systems.lisp` and its `bin/systems.dx64fsl` output may change. Both source literals and both complete FASLs are decoded. The only data addition is two named module entries at their exact position, with the associated list count, source-form endpoint and file length. The original 64-byte package-setup thunk and constants remain identical. All remaining raw bytes must match. Naming the file does not exempt its contents. |
| Existing native behavior and R6a | Reuse both accepted 21,843-pass native suites, with 75 upstream-disabled tests disclosed and identical retained test inventories/results. Compare the compiled ABI probe, unchanged kernel identity, backend/feature/word-size snapshot, vinsn templates, startup groups and all 279 evaluated operator records, including 12 reserved slots. Join the 199/201 evaluated module records to the decoded source/FASL lists. |

The native behavior claim remains the accepted registration run's scope. There
is no new exported-symbol census, cross-target execution or Wasm-generated-code
qualification. Unchanged kernel bytes and native executable outputs protect the
existing native ABI within that scope. This control qualifies this one patch's
comparison; later shared edits need their own artifact explanation and R6 run.

The [comparator](../tools/r6_registration.py) consumes identities validated by the
[runner](../../../tests/wasm/stage0/r6-control/run.py). It reports the first failing
comparison. Its small source reader accepts this file's literal syntax only;
it does not expand Lisp macros or execute reader forms. Eleven module names
inherit their standard Common Lisp package identities. The native FASL reader
is bounded to this retained profile and consumes the entire file. It preserves
the original package thunk as raw bytes and the source-note reconstruction form
as data; neither is executed. Unknown opcodes and unsupported structures refuse.

The source definition starts at character 823 and ends at 17,784 before the
patch, 17,985 after it. The added entries occupy bytes 6,003 through 6,197 in the
changed FASL. Source spans and decoded lists justify the component differences;
the comparator then requires exact equality of all bytes outside them. It also
compares the source-location metadata inside the permitted span, so the span
cannot conceal an unrelated change. This is accounting for an intentional
source change, not an approved normalization of unchanged inputs.

The 44 controls alter copies **after** the real input hashes have been checked.
Payload-changing FASL cases update their manifest hashes so they must reach the
semantic comparison. They cover target/shared source edits and insertions,
source/output reversal, compiler/image/options substitutions, a normalization
request, unexplained FASL differences, whole-file exemptions, changed code and
constants, module data, source locations, executable opcodes, trailing bytes,
extra no-ops, source-note calls and expression-table allocation. The R6a cases
change operator IDs, names, flags, encodings, handlers, order and reserved slots;
other cases alter features, ABI width, templates, evaluated registrations,
compiled probes, execution status and test completeness or membership.

Development evidence retains four producer failures: two source-reader joins
failed on inherited Common Lisp symbol identities; their correction also fixed
the endpoint convention. Two gate expectations used the wrong prerequisite text.
Earlier decoder refusals and their original source revisions are also retained.
These were harness development errors, not newly discovered native compiler
regressions. The final verifier freshly reapplies/removes the patch and
reproduces the summary, observations, source witness and literal source files.

The permanent results envelope lives at the evidence repository root so it can
reference already retained native inputs. The publisher verifies every new
locator, runs the production gate, and checks that inverse relocation restores
the exact original result. No disposition, execution fact or hash changes.
The original producer envelope remains in the packet as a derivation record;
its temporary reference links can be recreated by the runner. The native source
and bootstrap archives are not copied into another packet.

The current ledger is **37 accepted, ten missing, one unreviewed of 48**. Only
LL22-b's runner/status registration changes; accepted contracts and results are
preserved. Next return to census helper qualification and the five explicit
startup boundary replacements under the alternating plan. LL15 closure remains
open and this control does not authorize functional compiler changes.
