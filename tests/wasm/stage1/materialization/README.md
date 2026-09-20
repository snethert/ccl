# Generated template materialization — S1-LL21-a

This proposal adds an opt-in canonical-template switch to the three existing
compiler emitters and a portable synchronous D2 materializer. The shared runtime
and compiler are unchanged until review and acceptance.

Eighteen generated modules cover leaf, typed primitive and B entries, including
closure children. Canonical templates import unshared memory with explicit limits
1–32769 pages. Shared output changes precisely the independently located flag
byte from 1 to 3; it equals the ordinary compiler output. Unshared output keeps
the bytes. Forty default-mode outputs equal a separate compilation with the
integrated compiler.

Each record binds the template, materializer, actual import offset, limits,
imports/exports, features, engine pins and final binary. Installation re-derives
the expected output using trusted build inputs rather than trusting the offered
record. In the unshared case the two roles necessarily have identical hashes;
the installed record still names its profile and final-byte identity.

The existing callable-metadata oracle runs unchanged apart from host plumbing:
native signatures, keyword binding, mutable escaping closures and snapshot
restoration execute in six fresh Workers at 1 MiB, 2 MiB and 2 GiB. Both profiles
give identical observations: 58 calls and 162 metadata checks. Ten more
leaf/primitive calls and eleven engine link cases cover limits and sharedness.
Thirty-six refusals, eleven faults and seven publication omissions qualify the
boundary. The compiler fault is compiled by real CCL. Native R6/R6a passed with
21,843 tests, 162 unchanged registered FASLs and all 164 restored.

```sh
python3 tests/wasm/stage1/materialization/run.py \
  --evidence ../ccl-evidence --output /tmp/materialization-new
python3 tests/wasm/stage1/materialization/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-20-stage1-materialization-r1 \
  --output /tmp/materialization-review-new
```

The retained verifier replays the compiler, both execution profiles, native
qualification, faults and publication checks. Commands, input hashes and
toolchain identities are retained. The engine/tool pins match the accepted
Stage 0 Node/V8 matrix exactly. WABT instruction classification is a trusted
build input tied to the template digest, not a runtime disassembler.

[Scope](scope.json) matters: this is generated **code** materialization, not a
complete unshared runtime or a browser qualification. The fixture owner installs
exports eagerly after D2 validation; no unshared lazy-loader profile is added.
Services retain their own profile-specific builds. JSPI remains deferred.
Module granularity and the coordinated image loader are subsequent units.
