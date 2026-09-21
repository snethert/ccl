# Bootstrap execution frontier

172 original CCL definitions execute and match native, up from 137, in 7,912 comparisons across both placements and moving collection. This is a compiler proposal, not LL15 completion or integration. The final summary binds the comparison counts, compiled inventory and remaining bodies without input recipes. No C or JS implementation service is added.

Audit 146 is addressed at the head of this larger execution packet. The unsigned-byte-8 store now consumes NX1 operands in their actual order: kind, vector, index, value. A four-element vector of nines with index 3 and value 2 becomes `[9,9,9,2]`. The store's return value, mutated vector, operand effects and collection during later operands are compared with native. Restoring the old swap fails the focused control.

**Correction to the preceding library README:** its assertion that both string-copy definitions executed was false. They only compiled. Both `%COPY-U8-TO-STRING` and `%COPY-STRING-TO-U8` now execute from unchanged source, with native results and mutated arguments checked before and after movement. The report asserts their presence; an input recipe alone cannot establish execution. The original packet remains immutable, reviewed with findings and unaccepted.

CCL's ADD2, SUB2, MUL2, DIV2 and NUMCMP operators use the accepted numeric paths. CCL's own `1+` and `1-` bodies now compile and execute, and calls to those names and scalar ZEROP lower through the same arithmetic/comparison implementation. Fixnum increments with fixnum results stay in Wasm, checked by both service counters. The numeric scope remains the accepted integer/single/double subset; this does not add rational arithmetic or complex arithmetic, or a complete standalone ZEROP implementation. EQL calls use the existing reviewed EQL service and adapter. Its internal-only public entry is intentionally not used. The generated CORE-EQL wrapper and native EQL-based consumers exercise it; EQL is excluded from the count of newly compiled Lisp definitions.

The NIL dependency was also an emitter bug. A non-immediate callable left `name` as NIL, and `(symbolp name)` selected the named-call path. All four ordinary/APPLY, tail/internal sites now require an immediate callee before treating it as a symbol. Computed callables are evaluated as callables. Directed generated calls and CCL's unchanged FUNCALL/APPLY bodies execute with installed real callees. APPLY now marks computed dispatch in dependency records. Static closure propagates this flag through named callees; runtime-dispatched rows are listed separately and tested only with their declared callable inputs. No missing dependency is named NIL in this corpus.

The compiler proposal contains one `bootstrap-operator` and one `bootstrap-numeric-call`, with the library and arithmetic cases in their existing dispatch forms. It does not rename those functions and install overriding wrappers. The accepted runtime services and native Lisp source proposals are unchanged.

New native executions include list length, simple-string comparison, UTF-8/UTF-16 encoded lengths, EQL unions, association/member tests with runtime predicates, method lambda-list flattening, file-range encoding, and primitive numeric helpers. `execution-frontier.json` gives every executed definition and every admitted candidate without inputs. This remains a finite input qualification. In particular, numeric ctype and stream-ioblock bodies still need valid object/environment recipes; read-loop dispatch needs initialized stream/scheduler state. They receive no execution credit. The real worklist reports 1,522 admissions from 1,919 parsed definitions, with the same 22 reader/environment stops. The historical diagnostic is 1,864/2,492. The incomplete denominator and the remaining 25 l0-misc records are unchanged obligations.

`lowering-coverage.json` distinguishes emitters present in directly executed modules from unexecuted emitters. ADD2, SUB2, MUL2, DIV2, NUMCMP and the byte store have witnesses. The added `%IZEROP` emitter has no source witness: CCL translates the `%izerop` source probe into EQ. It is explicitly unexecuted, as is the previously owed source-emitted `%I<>` witness. Module presence does not claim all instruction branches ran.

The new proposal is rebuilt against pristine U1 for R6/R6a. All 164 native FASLs and the native snapshot equal the preceding qualified library build, so its 21,843 passing native tests are reused instead of rerun. The native-source files are identical to that packet; the existing-target reader matrix is reused by hash. Target execution, six focused controls and the ten legacy-byte comparisons run for this proposal. Original development failures are retained. No additional accepted ledger row is claimed.

```sh
python3 tests/wasm/stage1/bootstrap-execution/packet.py verify \
  --packet ../ccl-evidence/2026-09-21-stage1-bootstrap-execution-r1 \
  --output /tmp/bootstrap-execution-review
```
