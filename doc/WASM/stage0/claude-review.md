# Claude adversarial review and disposition — 2026-09-11

Provenance: two reviews supplied by the user in this conversation. The reviewed author was Codex; the reviewer was Claude. This satisfies the requested different-model adversarial review of **r8**. It is not acceptance of r8 or automatic review of later changes. The first supplied notes are retained [verbatim](../history/claude-first-review.txt); the follow-up findings and dispositions are recorded below.

Claude reported fresh fixture execution and byte-identical rebuilt binaries, matching counts, valid r3/r6 original failures, the correct r8 archive hash, passing document/checker controls, and no tracked upstream source edits. Those are reviewer-reported observations; this record does not invent missing raw Claude execution logs. The follow-up withdrew the earlier recommendation for Codex to audit its own implementation and approved committing the isolated additions after verification.

| Finding | Disposition |
| --- | --- |
| Exceptional return left worker 0 idle in JavaScript with RUNNING/admitted state; retirement depended on it | Reproduced unchanged in [original r9 failure](../evidence/runs/2026-09-11-integrated-r9.zip). Fixed in `program.mjs` by parking after checkpoint restoration; `retire` now admits. r10 collects between exceptional exit and retirement; an omitted-park mutant reproduces the failed collector and idle RUNNING TCR. |
| D5 omitted generation-guarded final wakes and explicit active-request routing | [D5 protocol v1.1](../decisions.md) records both mechanisms, terminal-outcome ordering, and the idle-host-boundary requirement with dated rationale. |
| Missing-notification controls used self-witnessing rejection | README and case comments now identify the waiter-count witness. A host-outcome-after-final-wake mutant adds a third explicit waiter witness. |
| Unpinned LLD | Both runners explicitly select Homebrew clang/LLD 21.1.8 and verify versions; executable paths and hashes are retained. r10 passed with all three selection variables unset. |
| Stale probe/boundary inventory hashes labeled current | Old records are marked superseded. Fresh probes r5 bind the current inventory; r10 contains the freshly executed boundary prerequisites. |
| Platform mismatch | User selected macOS. Native target, bootstrap, second-Mac reproduction and external census tracing now use macOS. Fresh native r3 passes both release-era test runs with 164/164 raw-identical FASLs; the current-head diagnostic retains three failures separately. Earlier platform-specific facts are historical only. |
| Heading, sentence, typo and stale DOCX verification | Fixed in the coordinated outline 0.14 / acceptance 1.4 / decisions 1.5 package; reading copies and verification regenerated. |
| Evidence weight and missing standing rules | Superseded packs moved byte-for-byte to the external local store with locators/hashes. Current packs and original integrated failures r3/r6/r9 stay in the repository. Root AGENTS.md and CLAUDE.md record the user-supplied scope and verification rules. |

The r10 runtime result records remain **NOT_REVIEWED** because the changes following Claude's r8 audit have not received a new external review. Stage 0 remains incomplete. No shared compiler or upstream `lisp-kernel` source was edited. Same-author verification of these fixes supports a reviewable commit, not acceptance.
