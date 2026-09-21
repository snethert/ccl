# Generated consumers of strong populations

Auxiliary LL15 implementation proposal. Twenty-two modules from the unchanged compiler now execute contents reads and SETF, public keyword type results, PUSH through public and internal population places, function references, APPLY, local functions/defaults, list copying, closures, cleanup and nonlocal exits. Both list and alist representations run below and above 2 GiB. This supplies consumer lowering and generated accessor entries for the approved strong representation; it is not installation at the real CCL symbols or completion of LL15.

`lower.lisp` redirects selected population operations to three private generated entries. The entries call the reviewed checked Wasm leaf through the retained B adapter. The type entry maps validated raw type codes to owner-provided :LIST/:ALIST identities. Native `population-data` uses a different layout; its selected references are explicitly redirected to the strong accessor rather than emitted with native offsets.

PUSH and population SETF are expanded by CCL itself before the accessor calls are redirected, preserving evaluation order and single evaluation of the place. In this CCL, PUSH evaluates the item before the place; SETF evaluates the place before the new value. The effect cases prepend distinct markers to an observable list so both duplication and reversal change the result. The selected compile entry remaps only its private call-link names to the compiler package and removes IGNORE declarations, unsupported by the unchanged front-end admission. Native oracle forms remain untouched.

The native oracle invokes CCL's real MAKE-POPULATION, POPULATION-CONTENTS, its SETF function, POPULATION-TYPE and POPULATION-DATA, on the pinned U1 kernel/image. Native member objects stay strongly referenced during the oracle because the approved target policy intentionally extends their lifetime. Target execution then drops independent member roots and collects with only the population and effect log rooted. Old space is poisoned. Every TCR word other than allocation state and returned count must be restored by each generated call. Closures and retained result lists also cross collections *inside* generated code.

Thirty-two native cases produce 64 comparisons and 80 moving collections across two Workers. The four freshly recompiled faults swap keyword results, discard the setter's returned value, route a data reader to the type operation, or reverse PUSH operand order. Each must fail against an unchanged native observation. The compiler, service, adapter and collector are unchanged; native R6/R6a is reused by exact compiler hash.

Scope: this is a selected-runtime transformation, not a generally admitted user-source extension. Local functions shadowing the population APIs and multi-place population SETF are explicitly refused; arbitrary lexical/dynamic bindings of API names are not claimed. Invalid-object and non-list setter failures still use the leaf's checked boundary, not public Lisp TYPE-ERROR signalling. Member payloads here are conses, not a qualification of actual lock/thread/GF layouts. The explicit GC function is an owner fixture entry; allocation retry and scheduler installation are not claimed. Real-symbol binding, production macro integration and real-image root discovery remain owed.

```
python3 tests/wasm/stage1/population-consumers/run.py --output /new/execution
python3 tests/wasm/stage1/population-consumers/packet.py verify --packet ../ccl-evidence/2026-09-21-stage1-population-consumers-r1 --output /new/replay
```

The neighboring audit-139 supplement carries the small residual refusal controls. Neither proposal changes shared runtime/compiler source or earns LL15 credit.
