# Bootstrap conditions, characters and symbols

137 original CCL definitions execute against native (previously 129), in 7,236 comparisons. The historical diagnostic census rises from 1,539 to 1,862 admissions, but its 2,492 denominator remains invalid. The new reader follows the actual 57-file target worklist: 1,520 of 1,919 recovered definitions compile; 22 files stop at a missing compile-time definition or foreign interface. These are lower bounds, not a complete denominator or LL15 completion.

The proposal lowers ERROR and SIGNAL arguments through the existing rooted condition constructor and dispatcher. String designators preserve format controls, argument order and complete argument lists. Literal SIMPLE-CONDITION, SIMPLE-ERROR, SIMPLE-PROGRAM-ERROR, TYPE-ERROR, ARITHMETIC-ERROR and DIVISION-BY-ZERO designators accept their two declared payload initargs, with first-keyword precedence and native default/unbound slots. Existing condition objects without extra arguments retain the existing dispatch path. Simple-condition and type-error readers expose the slots. Dynamic class names, other classes/initargs, spread calls and unbound-slot signalling are not implemented; unbound reader slots refuse at the checked boundary instead of publishing a marker. The existing debugger/declined-error boundary is unchanged. This is not the complete CLOS MAKE-CONDITION protocol.

Character/code conversion, simple-string reads and writes, raw character-code access, and unsigned-byte-8 vector reads/writes are emitted in Wasm. The two unchanged CCL string-copy functions now execute. Invalid primitive operands remain checked refusals. CODE-CHAR returns NIL for surrogates and refuses out-of-range integers. No C or JS implementation service is added.

The symbol pointer conversions and missing native symbol cell-index constants allow all 28 `l0-symbol.lisp` file-compiler records to compile, including its 27 named functions. SYMBOL-NAME gains a Wasm reader branch. GET, PUT, SYMBOL-PLIST and SYMBOL-NAME execute at their real CCL names. The owner fixture now publishes print names and the real NIL symbol object, and inventories all tagged symbol fields, including a mutated plist, as roots. This starts replacing the C service; it does not retire it or claim complete namespace installation.

`l0-misc.lisp` passes through CCL's whole-file compiler too, retaining its remaining refusals rather than fabricating implementations of kernel globals, pointers or thread operations. File-local macros use CCL's own compile-time environment. The new WASM32 source directory is registered with the cross-loader. The safer census uses normal target reading and stops on read errors; notably it finds zero definitions in l0-bignum64. Its lack of complete compile-time/foreign environments is explicit. The old census remains only for selecting the inherited execution corpus and reporting a historical proxy.

Audit-145 carries addressed here: an emitted `%ILOGNOT` witness, a fixnum operand refusal, a mis-tagged but otherwise valid node-vector refusal, and zero padding for even-length node vectors. The signed comparison witness tests the call lowering; its recorded IR is CALL, not `%I<>`. A source-emitted `%I<>` witness remains owed. Four focused faults exercise the new payload, character decoding, signed comparison and plist-root observations. They run only their named native rows; there is no repeated sweep of the accepted core.

Native qualification rebuilt the proposal and restored all 164 FASLs. The native tests ran once (21,843 passed); subsequent Wasm-only additions reused that execution only after all 164 freshly rebuilt native FASLs and the complete native snapshot matched exactly. The new l0-symbol branch reads identically under all 17 existing targets; the 51 unchanged reader joins are reused. No shared compiler/runtime source is changed by this proposal.

```sh
python3 tests/wasm/stage1/bootstrap-library/packet.py verify \
  --packet ../ccl-evidence/2026-09-21-stage1-bootstrap-library-r1 \
  --output /tmp/library-review
```

The packet retains implementation failures and focused reproductions. Routine verification covers the new proposal and its direct inputs; unchanged qualification is reused by digest. Acceptance and integration await Claude's review.
