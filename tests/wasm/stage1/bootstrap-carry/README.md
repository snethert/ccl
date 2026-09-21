# Bootstrap carry items from audit 149

301 unchanged CCL definitions still execute and match native, 290 with a
non-NIL witness. This packet adds no original-definition or slot credit.
Historical admission corrects 1,864 to 1,862 of 2,492: STANDARDIZED-TYPE-SPECIFIER
and VERIFY-DEFERRED-TYPE-WARNING contain unsupported handler classes and now
refuse before emission. The incomplete target list is 1,573/2,006, including
the new target ASSQ definition; 38/57 files read completely.

The proposal changes two files, in disposable U1 only:

* `level-0/WASM32/w32-prims.lisp` gains an ordinary DOLIST-based ASSQ. The
  backend's handwritten Wasm loop and special call dispatch are removed.
  REGISTER-ISTRUCT-CELL, ASSEQL, ADJOIN-ASSQ and the explicit callers link to
  the Lisp entry. Five direct inputs compare against the native LAP entry;
  five further callers check first-match identity and collection during both
  operands. The supported input is a proper alist of conses and NIL entries.
  The target definition is excluded from the unchanged-native-DEFUN headline.
* The bootstrap entry binds a macro-expansion hook which validates CCL's
  HANDLER-BIND and HANDLER-CASE class literals with the existing class mask
  registry. It delegates expansion to the existing hook and native macros.
  Direct, nested-macro and compound-type refusals are retained. Macro identity
  distinguishes lexical shadows, and quoted forms are untouched. No source
  walker or override dispatcher is added. Legacy entry points are unchanged.

APPLY of SIGNAL or ERROR with a spread list now has explicit source refusal
cases. The runtime limitation is unchanged. Removing the handler admission
guard admits the unsupported class; changing the generated Lisp ASSQ's EQ
sense fails its native caller. Known handler paths remain in the inherited
execution corpus.

Signed zero is a retained compatibility observation, not a new arithmetic
change: at the pinned native default policy, `(- x 0)` for `x = -0.0d0`
returns positive zero; variable zero returns negative zero. Wasm preserves
negative zero in both cases. Eight directed inputs run before/after movement
at both placements, giving 32 bit-pattern observations. Only the four literal
negative-zero executions differ, and each is asserted explicitly. There are
11,016 target comparisons, **11,012 native matches and four declared differences**.
The full run performs 5,874 collections, with 38 inherited checked refusals.

The harness is now written as `check.mjs` and `install.mjs`, starting from the
accepted integration's generated harness. It no longer builds those files
through a chain of string replacements. The compiler driver still reuses
the pinned constants and whole-file compilation machinery.

The collector is unchanged. Its 40 checks already passed in integration
`b9de543d`; this packet binds that result and requires both collector sources
and the rebuilt binary to equal the checked versions. The 20 inherited
ISTRUCT checks also run with the generated corpus. Fresh R6/R6a passes:
all 164 FASLs restore; 21,843 native tests are reused only after exact equality
of freshly rebuilt native FASLs and snapshot. Existing reader/source-location
evidence is unchanged. No C or JS runtime service is added.

```
python3 tests/wasm/stage1/bootstrap-carry/run.py /tmp/ccl-carry-new
python3 tests/wasm/stage1/bootstrap-carry/packet.py verify \
  --packet ../ccl-evidence/2026-09-21-stage1-bootstrap-carry-r1 \
  --output /tmp/ccl-carry-verify-new
```

No shared source is changed or integrated by this packet. Claude's review is
next. LL15, the missing input recipes and the POSIX-dependent source work
remain open.
