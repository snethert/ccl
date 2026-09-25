# Stream constructor acceptance

Audit 175 and Steve's “accept and proceed” accept READY R13. The three product
files match its reviewed bytes, including the complete compiler/source identity
that passed native R6/R6a and the 17-profile reader proof. No further native or
target execution is claimed by this integration.

Run `python3 tests/wasm/stage1/stream-constructor-acceptance/check.py`. It binds
the audit, acceptance, proposal qualification and integrated sources at
`b2f0ad8f`. The namespace consumer integration supersedes these product bytes;
the checker therefore reads historical sources, as the R12 checker does.
It rejects the namespace sources as R13 in the successor's directed control.
Later product changes require their own qualification; this is a historical
integration identity check, not a claim about arbitrary HEADs.
R13's full replay runs at `ce5e125b`, before its derivation anchors were integrated.

Accepted: 575 original definitions executed, 535 with non-NIL witnesses. No LL15
credit. General element types and fill-pointer strings remain unqualified.
