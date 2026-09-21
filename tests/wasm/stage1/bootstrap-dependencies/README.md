# Execute native bootstrap dependencies

**252 original definitions execute and match native, up from 186 (+66). Admission stays 1,864/2,492 historically and 1,522/1,919 in the incomplete target worklist.** The run has 2,472 native rows, 9,888 comparisons, 5,270 collections, 38 checked refusals and 14 rejected faults. It builds on the reviewed execution work and the integer-division proposal. It adds no C or JavaScript runtime service and changes no shared file. The retained summary and execution frontier give the final counts and per-definition input counts.

The backend lowers ASSQ, fixnum LOGAND/LOGIOR calls, unary and variadic subtraction, constant LDB fields, and constant TYPEP/REQUIRE-TYPE calls. Type tests call the existing CCL predicates; EQL/member tests use the accepted EQL implementation. Dynamic type specifiers and unsupported literal descriptors remain real Lisp dependencies. Subtraction uses the accepted numeric implementation, with every operand evaluated once in source order into roots and every accumulated result rooted before another call.

CCL's original REGISTER-ISTRUCT-CELL, SET-ISTRUCT-CELL-INFO, ADJOIN-ASSQ, LENGTH, SEQUENCE-TYPE, STRINGP, LAST, NTH, NTHCDR and array-query bodies execute unchanged. The packet expands the input recipes for existing closed definitions too. TYPECODE, FULLTAG and LISPTAG run against the native callable entries on shared fixnum representations; these three target primitive bodies are excluded from the original-definition count.

The %BADARG path preserves CCL's compact type IDs: the front end emits these IDs even when the source supplies a quoted type. The error lowering calls unchanged %TYPE-ERROR-TYPE before constructing the accepted TYPE-ERROR condition. Its owner supplies CCL's typespec vector as a rooted literal, shared by all decoder calls. Handler witnesses compare the datum and decoded expected type with native. The explicit %ERR-DISP code 157 path stages both operands before calling the decoder. It does not claim the native USE-VALUE restart protocol.

Recipe environments are explicit. The native registration oracle binds *ISTRUCT-CELLS* empty, matching the owner. Uninterned fixture symbols have zero binding indices, NIL packages and unbound value cells; the moving replay restores their initial unbound state before its second invocation. The type decoder's vector comes from the pinned native image, whose source defines it as literal data. The original definitions read it through their normal special-variable access. Structure predicates without instance recipes exercise nonmembers only. INVALID-HASH-KEY-P remains unexecuted: its standalone body lacks the lexical marker bindings supplied by its defining file. Package topology and a complete startup environment remain owed.

Limits are explicit. Logical calls and LDB currently accept fixnum operands; bignums refuse code 32. LDB requires a constant byte specifier with at most 29 result bits. Constant integer type bounds are D1 fixnums; byte type widths through 28 are admitted. Other descriptors retain their Lisp dependencies. Proper lists and simple strings, bit vectors, byte vectors and simple vectors qualify LENGTH; displaced/adjustable array instances are not supplied. Circular/improper-list error code 170 remains checked refusal 45. Exact integer division is inherited; nonintegral integer quotients and rational arithmetic still refuse. Compilation, dependency closure and execution are reported separately.

The new compiler gets a fresh native R6/R6a build; unchanged native tests and reader evidence are reused only after the established FASL and snapshot equality checks. The finalized packet is replayed unmodified before publication. Integration still requires Claude's review and the user's acceptance.

```sh
python3 tests/wasm/stage1/bootstrap-dependencies/packet.py verify \
  --packet ../ccl-evidence/2026-09-21-stage1-bootstrap-dependencies-r1 \
  --output /tmp/bootstrap-dependencies-review
```
