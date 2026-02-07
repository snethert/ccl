# WASM Subprims Work Remaining (Critical Detail)

Auto-generated status map for WASM subprims based on:

- `doc/wasm/subprims-map.json` (canonical symbol list)
- `lisp-kernel/wasm-subprims-provider.c` (provider implementations)
- `lisp-kernel/wasm-kernel-stubs.c` (kernel-implemented subprims)

**Status meanings**

- `stub`: provider body is only `wasm_subprims_trap()` (always traps).
- `guarded`: provider body contains at least one direct `wasm_subprims_trap()` call.
- `indirect`: no direct trap, but calls a helper that can trap.
- `clean`: no direct trap and no helper trap calls detected.
- `missing`: no provider definition found; stand-in stub will be used.

**Work remaining (derived)**

- `unimplemented`: stub or missing.
- `behavioral gap`: traps include state/unwind, unsupported-case, unconditional, or unknown.
- `validation only`: traps appear to be input validation (type/bounds/null/alloc).
- `clean`: no trap paths detected.

**Summary**

- Total subprims: 132
- Stub: 0
- Guarded: 123
- Indirect: 0
- Clean: 9
- Missing: 0

- behavioral gap: 44
- clean: 9
- validation only: 79

**Tier markers**

- `0`: Tier-0 per `doc/wasm/subprims-provider-plan.md`
- `1`: Tier-1 per `doc/wasm/subprims-provider-plan.md`
- `-`: not listed in the tier plan

---

## Overview

| Subprim | Status | Work Remaining | Direct Trap Count | Direct Tags | Helper Trap Calls | Helper Tags | Helper Trap Conditions | Gap Types | Validation Types | Tier | Kernel Impl | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `_SPadd_values` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_push_value_set | bounds | `wasm_push_value_set: count < 0` | - | bounds, null/invalid, tcr-null | - | no | high |
| `_SParef2` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_array_data_vector_or_trap, wasm_misc_ref_dispatch, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_array_data_vector_or_trap: fulltag_of(current) != fulltag_misc` - `wasm_misc_ref_dispatch: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_misc_ref_dispatch: index >= count` - `wasm_misc_ref_dispatch: (subtag & fulltagmask) != fulltag_immheader` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SParef3` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_array_data_vector_or_trap, wasm_misc_ref_dispatch, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_array_data_vector_or_trap: fulltag_of(current) != fulltag_misc` - `wasm_misc_ref_dispatch: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_misc_ref_dispatch: index >= count` - `wasm_misc_ref_dispatch: (subtag & fulltagmask) != fulltag_immheader` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPaset2` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_array_data_vector_or_trap, wasm_misc_set_dispatch, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_array_data_vector_or_trap: fulltag_of(current) != fulltag_misc` - `wasm_misc_set_dispatch: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_misc_set_dispatch: index >= count` - `wasm_misc_set_dispatch: (subtag & fulltagmask) != fulltag_immheader` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPaset3` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_array_data_vector_or_trap, wasm_misc_set_dispatch, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_array_data_vector_or_trap: fulltag_of(current) != fulltag_misc` - `wasm_misc_set_dispatch: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_misc_set_dispatch: index >= count` - `wasm_misc_set_dispatch: (subtag & fulltagmask) != fulltag_immheader` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPatomic_incf_node` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPbind` | guarded | behavioral gap | 4 | bounds, null/invalid, state/unwind, tcr-null | wasm_positive_fixnum_or_trap, wasm_symbol_or_trap, wasm_unbox_fixnum_or_trap, wasm_vsp_or_trap | bounds, fixnum, null/invalid, state/unwind, type/subtag | `wasm_positive_fixnum_or_trap: count <= 0` - `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPbind_interrupt_level` | guarded | behavioral gap | 2 | null/invalid, state/unwind, tcr-null | wasm_bind_interrupt_level | bounds, null/invalid, state/unwind | `wasm_bind_interrupt_level: (unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)limit_count` - `wasm_bind_interrupt_level: tlb == NULL` | state/unwind | bounds, null/invalid, tcr-null | - | no | medium |
| `_SPbind_interrupt_level_0` | guarded | behavioral gap | 2 | null/invalid, state/unwind, tcr-null | wasm_bind_interrupt_level | bounds, null/invalid, state/unwind | `wasm_bind_interrupt_level: (unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)limit_count` - `wasm_bind_interrupt_level: tlb == NULL` | state/unwind | bounds, null/invalid, tcr-null | - | no | medium |
| `_SPbind_interrupt_level_m1` | guarded | behavioral gap | 1 | null/invalid, tcr-null | wasm_bind_interrupt_level | bounds, null/invalid, state/unwind | `wasm_bind_interrupt_level: (unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)limit_count` - `wasm_bind_interrupt_level: tlb == NULL` | state/unwind | bounds, null/invalid, tcr-null | - | no | medium |
| `_SPbind_nil` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbind_self` | guarded | behavioral gap | 4 | bounds, null/invalid, state/unwind, tcr-null | wasm_positive_fixnum_or_trap, wasm_symbol_or_trap, wasm_unbox_fixnum_or_trap, wasm_vsp_or_trap | bounds, fixnum, null/invalid, state/unwind, type/subtag | `wasm_positive_fixnum_or_trap: count <= 0` - `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPbind_self_boundp_check` | guarded | behavioral gap | 4 | bounds, null/invalid, state/unwind, tcr-null | wasm_positive_fixnum_or_trap, wasm_symbol_or_trap, wasm_unbox_fixnum_or_trap, wasm_vsp_or_trap | bounds, fixnum, null/invalid, state/unwind, type/subtag | `wasm_positive_fixnum_or_trap: count <= 0` - `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPbuiltin_aref1` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_misc_ref_dispatch | bounds, type/subtag | `wasm_misc_ref_dispatch: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_misc_ref_dispatch: index >= count` - `wasm_misc_ref_dispatch: (subtag & fulltagmask) != fulltag_immheader` | - | bounds, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPbuiltin_aset1` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_misc_set_dispatch | bounds, type/subtag | `wasm_misc_set_dispatch: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_misc_set_dispatch: index >= count` - `wasm_misc_set_dispatch: (subtag & fulltagmask) != fulltag_immheader` | - | bounds, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPbuiltin_ash` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_assq` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_div` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_eq` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_eql` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_ge` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_gt` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_le` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_length` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_logand` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_logbitp` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_logior` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_logxor` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_lt` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_memq` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_minus` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_ne` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_negate` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_plus` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_seqtype` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbuiltin_times` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPcall_closure` | guarded | behavioral gap | 3 | bounds, null/invalid, tcr-null, type/subtag | wasm_unbox_fixnum_or_trap, wasm_vpush_argregs, wasm_vsp_or_trap | fixnum, null/invalid, state/unwind, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vpush_argregs: tag_of(raw) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPcheck_fpu_exception` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPconslist` | guarded | behavioral gap | 3 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_alloc_cons_or_trap, wasm_vsp_or_trap | alloc, null/invalid, state/unwind, tcr-null | `wasm_alloc_cons_or_trap: tcr == NULL || tcr->save_allocptr == NULL || tcr->save_allocbase == NULL || tcr->save_allocptr == (void *` - `wasm_alloc_cons_or_trap: newptr < alloc_base` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | alloc, bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPconslist_star` | guarded | behavioral gap | 3 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_alloc_cons_or_trap, wasm_vsp_or_trap | alloc, null/invalid, state/unwind, tcr-null | `wasm_alloc_cons_or_trap: tcr == NULL || tcr->save_allocptr == NULL || tcr->save_allocbase == NULL || tcr->save_allocptr == (void *` - `wasm_alloc_cons_or_trap: newptr < alloc_base` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | alloc, bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPdebind` | guarded | behavioral gap | 3 | bounds, null/invalid, tcr-null, type/subtag | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPdefault_optional_args` | guarded | behavioral gap | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vpush_argregs, wasm_vsp_or_trap | fixnum, null/invalid, state/unwind, type/subtag | `wasm_vpush_argregs: tag_of(raw) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPdiscard_stack_object` | guarded | validation only | 2 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPeabi_callback` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPeabi_ff_call_simple` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPeabi_ff_callhf` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPfitvals` | guarded | behavioral gap | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPfix_nfn_entrypoint` | guarded | validation only | 2 | null/invalid, tcr-null, type/subtag | wasm_call_lisp_function | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function && subtag != subtag_pseudofunction` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPfix_overflow` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | yes | high |
| `_SPfuncall` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_call_lisp_function | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function && subtag != subtag_pseudofunction` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | 0 | no | high |
| `_SPgets32` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPgets64` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPgetu32` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPgetu64` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPgvector` | guarded | behavioral gap | 5 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_unbox_fixnum_or_trap, wasm_vsp_or_trap | fixnum, null/invalid, state/unwind, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPgvset` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_gvector_set_or_trap, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_gvector_set_or_trap: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_gvector_set_or_trap: (header_subtag(header) & fulltagmask) != fulltag_nodeheader` - `wasm_gvector_set_or_trap: index >= count` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPheap_cons_rest_arg` | guarded | behavioral gap | 3 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_alloc_cons_or_trap, wasm_vsp_or_trap | alloc, null/invalid, state/unwind, tcr-null | `wasm_alloc_cons_or_trap: tcr == NULL || tcr->save_allocptr == NULL || tcr->save_allocbase == NULL || tcr->save_allocptr == (void *` - `wasm_alloc_cons_or_trap: newptr < alloc_base` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | alloc, bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPheap_rest_arg` | guarded | behavioral gap | 3 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_alloc_cons_or_trap, wasm_vpush_argregs, wasm_vsp_or_trap | alloc, fixnum, null/invalid, state/unwind, tcr-null, type/subtag | `wasm_alloc_cons_or_trap: tcr == NULL || tcr->save_allocptr == NULL || tcr->save_allocbase == NULL || tcr->save_allocptr == (void *` - `wasm_alloc_cons_or_trap: newptr < alloc_base` - `wasm_vpush_argregs: tag_of(raw) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | alloc, bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPinteger_sign` | guarded | validation only | 2 | bounds, null/invalid, tcr-null | - | - | - | - | bounds, null/invalid, tcr-null | - | no | high |
| `_SPjmpsym` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPkeyword_bind` | guarded | behavioral gap | 5 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPksignalerr` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_call_lisp_function | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function && subtag != subtag_pseudofunction` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmakes32` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | yes | high |
| `_SPmakes64` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPmakestackblock` | guarded | validation only | 2 | bounds, null/invalid, tcr-null | wasm_call_lisp_function, wasm_unbox_fixnum_or_trap | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function && subtag != subtag_pseudofunction` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmakestackblock0` | guarded | validation only | 2 | bounds, null/invalid, tcr-null | wasm_call_lisp_function, wasm_unbox_fixnum_or_trap | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function && subtag != subtag_pseudofunction` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmakestacklist` | guarded | validation only | 2 | bounds, null/invalid, tcr-null | wasm_alloc_cons_or_trap, wasm_unbox_fixnum_or_trap | alloc, fixnum, null/invalid, tcr-null, type/subtag | `wasm_alloc_cons_or_trap: tcr == NULL || tcr->save_allocptr == NULL || tcr->save_allocbase == NULL || tcr->save_allocptr == (void *` - `wasm_alloc_cons_or_trap: newptr < alloc_base` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | alloc, bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmakeu32` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_alloc_bignum_or_trap | null/invalid | `wasm_alloc_bignum_or_trap: obj == (LispObj)nil_value` | - | null/invalid, tcr-null | - | no | high |
| `_SPmakeu64` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_alloc_bignum_or_trap | null/invalid | `wasm_alloc_bignum_or_trap: obj == (LispObj)nil_value` | - | null/invalid, tcr-null | - | no | high |
| `_SPmisc_alloc` | guarded | validation only | 5 | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | - | - | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmisc_alloc_init` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_call_lisp_function | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function && subtag != subtag_pseudofunction` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmisc_ref` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_misc_ref_dispatch, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_misc_ref_dispatch: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_misc_ref_dispatch: index >= count` - `wasm_misc_ref_dispatch: (subtag & fulltagmask) != fulltag_immheader` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmisc_set` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_misc_set_dispatch, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_misc_set_dispatch: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_misc_set_dispatch: index >= count` - `wasm_misc_set_dispatch: (subtag & fulltagmask) != fulltag_immheader` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmkcatch1v` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | 1 | no | high |
| `_SPmkcatchmv` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | 1 | no | high |
| `_SPmkstackv` | guarded | behavioral gap | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPmkunwind` | guarded | behavioral gap | 2 | null/invalid, state/unwind, tcr-null | - | - | - | state/unwind | null/invalid, tcr-null | - | no | medium |
| `_SPmvpass` | guarded | behavioral gap | 2 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPmvpasssym` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPmvslide` | guarded | behavioral gap | 3 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPnthrow1value` | guarded | behavioral gap | 6 | bounds, fixnum, null/invalid, state/unwind, tcr-null, type/subtag | wasm_push_value_set, wasm_unbind_to, wasm_unbox_fixnum_or_trap | bounds, fixnum, null/invalid, state/unwind, type/subtag | `wasm_push_value_set: count < 0` - `wasm_unbind_to: tlb == NULL` - `wasm_unbind_to: binding == NULL` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | 0 | no | medium |
| `_SPnthrowvalues` | guarded | behavioral gap | 7 | bounds, fixnum, null/invalid, state/unwind, tcr-null, type/subtag | wasm_push_value_set, wasm_unbind_to, wasm_unbox_fixnum_or_trap, wasm_vsp_or_trap | bounds, fixnum, null/invalid, state/unwind, type/subtag | `wasm_push_value_set: count < 0` - `wasm_unbind_to: tlb == NULL` - `wasm_unbind_to: binding == NULL` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | 1 | no | medium |
| `_SPnthvalue` | guarded | behavioral gap | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPnvalret` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPopt_supplied_p` | guarded | behavioral gap | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPpopj` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPprogvrestore` | guarded | behavioral gap | 4 | null/invalid, state/unwind, tcr-null | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | state/unwind | fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPprogvsave` | guarded | behavioral gap | 5 | bounds, null/invalid, state/unwind, tcr-null, type/subtag | wasm_positive_fixnum_or_trap, wasm_symbol_or_trap, wasm_vsp_or_trap | bounds, null/invalid, state/unwind, type/subtag | `wasm_positive_fixnum_or_trap: count <= 0` - `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPrecover_values` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPreq_heap_rest_arg` | guarded | behavioral gap | 3 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_alloc_cons_or_trap, wasm_vpush_argregs, wasm_vsp_or_trap | alloc, fixnum, null/invalid, state/unwind, tcr-null, type/subtag | `wasm_alloc_cons_or_trap: tcr == NULL || tcr->save_allocptr == NULL || tcr->save_allocbase == NULL || tcr->save_allocptr == (void *` - `wasm_alloc_cons_or_trap: newptr < alloc_base` - `wasm_vpush_argregs: tag_of(raw) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | alloc, bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPreq_stack_rest_arg` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_vpush_argregs | fixnum, type/subtag | `wasm_vpush_argregs: tag_of(raw) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPreset` | guarded | behavioral gap | 1 | null/invalid, tcr-null | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | null/invalid, tcr-null | - | no | medium |
| `_SPrplaca` | guarded | validation only | 2 | null/invalid, tcr-null, type/subtag | - | - | - | - | null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPrplacd` | guarded | validation only | 2 | null/invalid, tcr-null, type/subtag | - | - | - | - | null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPsave_values` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_push_value_set | bounds | `wasm_push_value_set: count < 0` | - | bounds, null/invalid, tcr-null | - | no | high |
| `_SPsdiv32` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPset_hash_key` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_gvector_set_or_trap, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_gvector_set_or_trap: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_gvector_set_or_trap: (header_subtag(header) & fulltagmask) != fulltag_nodeheader` - `wasm_gvector_set_or_trap: index >= count` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPset_hash_key_conditional` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPsetqsym` | guarded | validation only | 2 | fixnum, null/invalid, tcr-null, type/subtag | wasm_call_lisp_function, wasm_symbol_or_trap | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function && subtag != subtag_pseudofunction` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` - `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPspecref` | guarded | behavioral gap | 4 | bounds, fixnum, null/invalid, state/unwind, tcr-null, type/subtag | wasm_symbol_or_trap | type/subtag | `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPspecrefcheck` | guarded | behavioral gap | 4 | bounds, fixnum, null/invalid, state/unwind, tcr-null, type/subtag | wasm_symbol_or_trap | type/subtag | `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPspecset` | guarded | behavioral gap | 5 | bounds, fixnum, null/invalid, state/unwind, tcr-null, type/subtag | wasm_symbol_or_trap | type/subtag | `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPspread_lexprz` | guarded | behavioral gap | 4 | bounds, null/invalid, tcr-null | wasm_unbox_fixnum_or_trap, wasm_vpop_argregs, wasm_vsp_or_trap | fixnum, null/invalid, state/unwind, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vpop_argregs: tag_of(raw) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPspreadargz` | guarded | behavioral gap | 2 | bounds, null/invalid, tcr-null | wasm_unbox_fixnum_or_trap, wasm_vpop_argregs, wasm_vsp_or_trap | fixnum, null/invalid, state/unwind, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vpop_argregs: tag_of(raw) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPstack_cons_rest_arg` | guarded | behavioral gap | 3 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPstack_misc_alloc` | guarded | validation only | 7 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPstack_misc_alloc_init` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_call_lisp_function | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function && subtag != subtag_pseudofunction` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPstack_rest_arg` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_vpush_argregs | fixnum, type/subtag | `wasm_vpush_argregs: tag_of(raw) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPstkconslist` | guarded | behavioral gap | 3 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPstkconslist_star` | guarded | behavioral gap | 3 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPstkgvector` | guarded | behavioral gap | 6 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_unbox_fixnum_or_trap, wasm_vsp_or_trap | fixnum, null/invalid, state/unwind, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPstore_node_conditional` | guarded | behavioral gap | 1 | null/invalid, tcr-null | wasm_unbox_fixnum_or_trap, wasm_vsp_or_trap | fixnum, null/invalid, state/unwind, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPsubtag_misc_ref` | guarded | validation only | 4 | null/invalid, tcr-null, type/subtag | wasm_misc_ref_dispatch, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_misc_ref_dispatch: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_misc_ref_dispatch: index >= count` - `wasm_misc_ref_dispatch: (subtag & fulltagmask) != fulltag_immheader` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPsubtag_misc_set` | guarded | validation only | 4 | null/invalid, tcr-null, type/subtag | wasm_misc_set_dispatch, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_misc_set_dispatch: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_misc_set_dispatch: index >= count` - `wasm_misc_set_dispatch: (subtag & fulltagmask) != fulltag_immheader` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPtcallnfngen` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPtcallnfnslide` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPtcallsymgen` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPtcallsymslide` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPtfuncallgen` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPtfuncallslide` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPthrow` | guarded | behavioral gap | 2 | bounds, null/invalid, tcr-null | wasm_unbox_fixnum_or_trap, wasm_vsp_or_trap | fixnum, null/invalid, state/unwind, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | 1 | no | medium |
| `_SPudiv32` | guarded | validation only | 2 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPudiv64by32` | guarded | validation only | 2 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPunbind` | guarded | behavioral gap | 2 | null/invalid, state/unwind, tcr-null | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | state/unwind | fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPunbind_interrupt_level` | guarded | behavioral gap | 2 | null/invalid, state/unwind, tcr-null | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | state/unwind | fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPunbind_n` | guarded | behavioral gap | 4 | bounds, null/invalid, state/unwind, tcr-null | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPunbind_to` | guarded | behavioral gap | 1 | null/invalid, tcr-null | wasm_unbind_to | null/invalid, state/unwind | `wasm_unbind_to: tlb == NULL` - `wasm_unbind_to: binding == NULL` | state/unwind | null/invalid, tcr-null | - | no | medium |
| `_SPunused1` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPunused2` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPvalues` | guarded | behavioral gap | 2 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPwasm_macro_apply_stub` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPwasm_udf_stub` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |

---

## Direct Trap Site Details

| Subprim | Trap Line | Cond Line | Condition | Tags |
| --- | --- | --- | --- | --- |
| `_SPadd_values` | 1992 | 1991 | `tcr == NULL` | null/invalid, tcr-null |
| `_SParef2` | 3906 | 3905 | `tcr == NULL` | null/invalid, tcr-null |
| `_SParef3` | 3993 | 3992 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPaset2` | 4100 | 4099 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPaset3` | 4188 | 4187 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPatomic_incf_node` | 3544 | 3543 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind` | 4981 | 4980 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind` | 4997 | 4996 | `index < 0` | bounds |
| `_SPbind` | 5003 | 5002 | `(unsigned)index >= (unsigned)limit_count` | bounds |
| `_SPbind` | 5008 | 5007 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPbind_interrupt_level` | 5194 | 5193 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_interrupt_level` | 5204 | 5203 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPbind_interrupt_level_0` | 5160 | 5159 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_interrupt_level_0` | 5165 | 5164 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPbind_interrupt_level_m1` | 5182 | 5181 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_nil` | 5084 | 5083 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_self` | 5030 | 5029 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_self` | 5046 | 5045 | `index < 0` | bounds |
| `_SPbind_self` | 5052 | 5051 | `(unsigned)index >= (unsigned)limit_count` | bounds |
| `_SPbind_self` | 5057 | 5056 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPbind_self_boundp_check` | 5099 | 5098 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_self_boundp_check` | 5115 | 5114 | `index < 0` | bounds |
| `_SPbind_self_boundp_check` | 5121 | 5120 | `(unsigned)index >= (unsigned)limit_count` | bounds |
| `_SPbind_self_boundp_check` | 5126 | 5125 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPbuiltin_aref1` | 3493 | 3492 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_aset1` | 3518 | 3517 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_ash` | 3406 | 3405 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_assq` | 3314 | 3313 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_div` | 3132 | 3131 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_eq` | 3144 | 3143 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_eql` | 3264 | 3263 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_ge` | 3204 | 3203 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_gt` | 3184 | 3183 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_le` | 3244 | 3243 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_length` | 3290 | 3289 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logand` | 3385 | 3384 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logbitp` | 3338 | 3337 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logior` | 3364 | 3363 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logxor` | 3472 | 3471 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_lt` | 3224 | 3223 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_memq` | 3326 | 3325 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_minus` | 3090 | 3089 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_ne` | 3164 | 3163 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_negate` | 3452 | 3451 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_plus` | 3069 | 3068 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_seqtype` | 3302 | 3301 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_times` | 3111 | 3110 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPcall_closure` | 5495 | 5494 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPcall_closure` | 5500 | 5499 | `fulltag_of(closure) != fulltag_misc || header_subtag(header_of(closure)) != subtag_function` | type/subtag |
| `_SPcall_closure` | 5505 | 5504 | `argc < 0` | bounds |
| `_SPconslist` | 3684 | 3683 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPconslist` | 3689 | 3688 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPconslist` | 3693 | 3692 | `count < 0` | bounds |
| `_SPconslist_star` | 3716 | 3715 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPconslist_star` | 3721 | 3720 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPconslist_star` | 3725 | 3724 | `count < 0` | bounds |
| `_SPdebind` | 5712 | 5711 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPdebind` | 5867 | 5866 | `fulltag_of(keyvec) != fulltag_misc` | type/subtag |
| `_SPdebind` | 5871 | 5870 | `keyvec_len < 0 || keyvec_len > 256` | bounds |
| `_SPdefault_optional_args` | 2308 | 2307 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPdefault_optional_args` | 2313 | 2312 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPdefault_optional_args` | 2318 | 2317 | `tag_of(raw_limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPdefault_optional_args` | 2324 | 2323 | `nargs_count < 0 || limit < 0` | bounds |
| `_SPdiscard_stack_object` | 4341 | 4340 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPdiscard_stack_object` | 4346 | 4345 | `sp == NULL` | null/invalid |
| `_SPeabi_callback` | 5976 | 5975 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPeabi_ff_call_simple` | 5954 | 5953 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPeabi_ff_callhf` | 5965 | 5964 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfitvals` | 2204 | 2203 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfitvals` | 2209 | 2208 | `tag_of(raw_desired) != tag_fixnum` | fixnum, type/subtag |
| `_SPfitvals` | 2214 | 2213 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPfitvals` | 2220 | 2219 | `desired_count < 0 || current_count < 0` | bounds |
| `_SPfix_nfn_entrypoint` | 2039 | 2038 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfix_nfn_entrypoint` | 2044 | 2043 | `fulltag_of(fn_value) != fulltag_misc || header_subtag(header_of(fn_value)) != subtag_function` | type/subtag |
| `_SPfix_overflow` | 6041 | 6040 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfuncall` | 2062 | 2061 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgets32` | 4571 | 4570 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgets64` | 4727 | 4726 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgetu32` | 4595 | 4594 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgetu64` | 4663 | 4662 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgvector` | 2789 | 2788 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgvector` | 2794 | 2793 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPgvector` | 2798 | 2797 | `count <= 0` | bounds |
| `_SPgvector` | 2805 | 2804 | `subtag < 0` | type/subtag |
| `_SPgvector` | 2811 | 2810 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPgvset` | 3618 | 3617 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPheap_cons_rest_arg` | 2456 | 2455 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPheap_cons_rest_arg` | 2462 | 2461 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_required) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPheap_cons_rest_arg` | 2466 | 2465 | `count < 0` | bounds |
| `_SPheap_rest_arg` | 2387 | 2386 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPheap_rest_arg` | 2392 | 2391 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPheap_rest_arg` | 2396 | 2395 | `count < 0` | bounds |
| `_SPinteger_sign` | 2014 | 2013 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPinteger_sign` | 2026 | 2025 | `!wasm_bignum_info(value, &count, &digits) || count <= 0` | bounds |
| `_SPjmpsym` | 2101 | 2100 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPkeyword_bind` | 5575 | 5574 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPkeyword_bind` | 5582 | 5581 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_prev) != tag_fixnum || tag_of(keyword_flags) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPkeyword_bind` | 5588 | 5587 | `nargs_count < 0 || prev_count < 0` | bounds |
| `_SPkeyword_bind` | 5609 | 5608 | `fulltag_of(keyvec) != fulltag_misc` | type/subtag |
| `_SPkeyword_bind` | 5613 | 5612 | `keyvec_len < 0 || keyvec_len > 256` | bounds |
| `_SPksignalerr` | 4360 | 4359 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakes32` | 4459 | 4458 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakes64` | 4552 | 4551 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestackblock` | 2939 | 2938 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestackblock` | 2945 | 2944 | `count < 0` | bounds |
| `_SPmakestackblock0` | 2966 | 2965 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestackblock0` | 2972 | 2971 | `count < 0` | bounds |
| `_SPmakestacklist` | 2892 | 2891 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestacklist` | 2898 | 2897 | `count < 0` | bounds |
| `_SPmakeu32` | 4474 | 4473 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakeu64` | 4504 | 4503 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_alloc` | 2627 | 2624 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_alloc` | 2634 | 2631 | `tag_of(subtag_val) != tag_fixnum` | fixnum, type/subtag |
| `_SPmisc_alloc` | 2640 | 2637 | `tag_of(count_val) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmisc_alloc` | 2655 | 2652 | `subtag_tag != fulltag_nodeheader && subtag_tag != fulltag_immheader` | type/subtag |
| `_SPmisc_alloc` | 2662 | 2659 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPmisc_alloc_init` | 2674 | 2673 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_ref` | 2722 | 2721 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_set` | 3023 | 3022 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkcatch1v` | 1604 | 1603 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkcatchmv` | 1630 | 1629 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkstackv` | 3861 | 3860 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkstackv` | 3866 | 3865 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmkstackv` | 3870 | 3869 | `count < 0` | bounds |
| `_SPmkstackv` | 3884 | 3883 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPmkunwind` | 1656 | 1655 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkunwind` | 1672 | 1671 | `catch_top == 0 || catch_top == (LispObj)nil_value` | null/invalid, state/unwind |
| `_SPmvpass` | 2151 | 2150 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmvpass` | 2162 | 2161 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmvpasssym` | 2611 | 2610 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmvslide` | 2576 | 2575 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmvslide` | 2581 | 2580 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmvslide` | 2586 | 2585 | `count < 0` | bounds |
| `_SPnthrow1value` | 1684 | 1683 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPnthrow1value` | 1699 | 1698 | `catch_top == 0 || catch_top == (LispObj)nil_value` | null/invalid, state/unwind |
| `_SPnthrow1value` | 1717 | 1716 | `tag_of(cleanup) != tag_fixnum` | fixnum, type/subtag |
| `_SPnthrow1value` | 1722 | 1721 | `count < 0` | bounds |
| `_SPnthrow1value` | 1731 | 1730 | `saved_vsp == NULL` | null/invalid, state/unwind |
| `_SPnthrow1value` | 1755 | 1754 | `saved_vsp == NULL` | null/invalid, state/unwind |
| `_SPnthrowvalues` | 1774 | 1773 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPnthrowvalues` | 1787 | 1786 | `catch_top == 0 || catch_top == (LispObj)nil_value` | null/invalid, state/unwind |
| `_SPnthrowvalues` | 1805 | 1804 | `tag_of(cleanup) != tag_fixnum` | fixnum, type/subtag |
| `_SPnthrowvalues` | 1810 | 1809 | `count < 0` | bounds |
| `_SPnthrowvalues` | 1819 | 1818 | `saved_vsp == NULL` | null/invalid, state/unwind |
| `_SPnthrowvalues` | 1843 | 1842 | `count < 0` | bounds |
| `_SPnthrowvalues` | 1848 | 1847 | `dest == NULL` | null/invalid |
| `_SPnthvalue` | 2269 | 2268 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPnthvalue` | 2274 | 2273 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPnthvalue` | 2279 | 2278 | `count < 0` | bounds |
| `_SPnthvalue` | 2285 | 2284 | `tag_of(raw_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPopt_supplied_p` | 2349 | 2348 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPopt_supplied_p` | 2354 | 2353 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPopt_supplied_p` | 2359 | 2358 | `tag_of(raw_opt) != tag_fixnum` | fixnum, type/subtag |
| `_SPopt_supplied_p` | 2365 | 2364 | `nargs_count < 0 || opt_count < 0` | bounds |
| `_SPpopj` | 4448 | 4447 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPprogvrestore` | 5458 | 5457 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPprogvrestore` | 5463 | 5462 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPprogvrestore` | 5473 | 5472 | `old_vsp == NULL` | null/invalid, state/unwind |
| `_SPprogvrestore` | 5486 | 5472 | `old_vsp == NULL` | null/invalid, state/unwind |
| `_SPprogvsave` | 5375 | 5374 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPprogvsave` | 5389 | 5388 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPprogvsave` | 5409 | 5408 | `tag_of(sym_list) != tag_list` | type/subtag |
| `_SPprogvsave` | 5419 | 5418 | `(unsigned)index >= (unsigned)limit_count` | bounds |
| `_SPprogvsave` | 5427 | 5426 | `tag_of(val_list) != tag_list` | type/subtag |
| `_SPrecover_values` | 2003 | 2002 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPreq_heap_rest_arg` | 2421 | 2420 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPreq_heap_rest_arg` | 2427 | 2426 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_required) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPreq_heap_rest_arg` | 2431 | 2430 | `count < 0` | bounds |
| `_SPreq_stack_rest_arg` | 2503 | 2502 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPreset` | 4416 | 4415 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPrplaca` | 3565 | 3564 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPrplaca` | 3570 | 3569 | `fulltag_of(cell) != fulltag_cons` | type/subtag |
| `_SPrplacd` | 3582 | 3581 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPrplacd` | 3587 | 3586 | `fulltag_of(cell) != fulltag_cons` | type/subtag |
| `_SPsave_values` | 1981 | 1980 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsdiv32` | 6008 | 6007 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPset_hash_key` | 3633 | 3632 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsetqsym` | 4905 | 4904 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsetqsym` | 4913 | 4912 | `tag_of(flags) != tag_fixnum` | fixnum, type/subtag |
| `_SPspecref` | 4767 | 4766 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspecref` | 4774 | 4773 | `tag_of(binding_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecref` | 4779 | 4778 | `tag_of(limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecref` | 4784 | 4783 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPspecrefcheck` | 4808 | 4807 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspecrefcheck` | 4815 | 4814 | `tag_of(binding_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecrefcheck` | 4820 | 4819 | `tag_of(limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecrefcheck` | 4825 | 4824 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPspecset` | 4857 | 4856 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspecset` | 4865 | 4864 | `tag_of(binding_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecset` | 4870 | 4869 | `tag_of(limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecset` | 4875 | 4874 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPspecset` | 4881 | 4880 | `limit_count < 0` | bounds |
| `_SPspread_lexprz` | 4296 | 4295 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspread_lexprz` | 4301 | 4300 | `lexpr == NULL` | null/invalid |
| `_SPspread_lexprz` | 4307 | 4306 | `count < 0` | bounds |
| `_SPspread_lexprz` | 4312 | 4311 | `orig_count < 0` | bounds |
| `_SPspreadargz` | 4935 | 4934 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspreadargz` | 4943 | 4942 | `orig_count < 0` | bounds |
| `_SPstack_cons_rest_arg` | 2516 | 2515 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstack_cons_rest_arg` | 2522 | 2521 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_required) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstack_cons_rest_arg` | 2526 | 2525 | `count < 0` | bounds |
| `_SPstack_misc_alloc` | 2738 | 2737 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstack_misc_alloc` | 2743 | 2742 | `tag_of(raw_count) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstack_misc_alloc` | 2747 | 2746 | `count < 0` | bounds |
| `_SPstack_misc_alloc` | 2753 | 2752 | `subtag < 0` | type/subtag |
| `_SPstack_misc_alloc` | 2761 | 2760 | `words > (SIZE_MAX / node_size)` | bounds |
| `_SPstack_misc_alloc` | 2766 | 2765 | `!wasm_ivector_total_bytes((unsigned)subtag, count, &bytes)` | type/subtag |
| `_SPstack_misc_alloc` | 2769 | 2765 | `!wasm_ivector_total_bytes((unsigned)subtag, count, &bytes)` | type/subtag |
| `_SPstack_misc_alloc_init` | 2698 | 2697 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstack_rest_arg` | 2489 | 2488 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkconslist` | 3759 | 3758 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkconslist` | 3764 | 3763 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstkconslist` | 3768 | 3767 | `count < 0` | bounds |
| `_SPstkconslist_star` | 3810 | 3809 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkconslist_star` | 3815 | 3814 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstkconslist_star` | 3819 | 3818 | `count < 0` | bounds |
| `_SPstkgvector` | 2833 | 2832 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkgvector` | 2838 | 2837 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstkgvector` | 2842 | 2841 | `count <= 0` | bounds |
| `_SPstkgvector` | 2849 | 2848 | `((unsigned)subtag & fulltagmask) != fulltag_nodeheader` | type/subtag |
| `_SPstkgvector` | 2858 | 2857 | `words > (SIZE_MAX / node_size)` | bounds |
| `_SPstkgvector` | 2869 | 2868 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPstore_node_conditional` | 3648 | 3647 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsubtag_misc_ref` | 2995 | 2994 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsubtag_misc_ref` | 3001 | 3000 | `subtag < 0` | type/subtag |
| `_SPsubtag_misc_ref` | 3006 | 3005 | `fulltag_of(obj) != fulltag_misc` | type/subtag |
| `_SPsubtag_misc_ref` | 3009 | 3008 | `header_subtag(header_of(obj)) != (unsigned)subtag` | type/subtag |
| `_SPsubtag_misc_set` | 3040 | 3039 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsubtag_misc_set` | 3046 | 3045 | `subtag < 0` | type/subtag |
| `_SPsubtag_misc_set` | 3051 | 3050 | `fulltag_of(obj) != fulltag_misc` | type/subtag |
| `_SPsubtag_misc_set` | 3054 | 3053 | `header_subtag(header_of(obj)) != (unsigned)subtag` | type/subtag |
| `_SPtcallsymgen` | 2113 | 2112 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPtcallsymslide` | 2125 | 2124 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPthrow` | 1925 | 1924 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPthrow` | 1930 | 1929 | `count < 0` | bounds |
| `_SPudiv32` | 5987 | 5986 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPudiv32` | 5992 | 5991 | `denom == 0` | null/invalid |
| `_SPudiv64by32` | 4638 | 4637 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPudiv64by32` | 4643 | 4642 | `denom == 0` | null/invalid |
| `_SPunbind` | 5251 | 5250 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPunbind` | 5257 | 5256 | `binding == NULL || tlb == NULL` | null/invalid, state/unwind |
| `_SPunbind_interrupt_level` | 5221 | 5220 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPunbind_interrupt_level` | 5227 | 5226 | `binding == NULL || tlb == NULL` | null/invalid, state/unwind |
| `_SPunbind_n` | 5326 | 5325 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPunbind_n` | 5331 | 5330 | `count < 0` | bounds |
| `_SPunbind_n` | 5340 | 5339 | `binding == NULL || tlb == NULL` | null/invalid, state/unwind |
| `_SPunbind_n` | 5345 | 5344 | `binding == NULL` | null/invalid |
| `_SPunbind_to` | 5362 | 5361 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPvalues` | 2180 | 2179 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPvalues` | 2185 | 2184 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPwasm_macro_apply_stub` | 4384 | 4383 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPwasm_udf_stub` | 4400 | 4399 | `tcr == NULL` | null/invalid, tcr-null |

---

## Helper Trap Site Details

| Helper | Trap Line | Cond Line | Condition | Tags |
| --- | --- | --- | --- | --- |
| `__attribute__` | 1604 | 1603 | `tcr == NULL` | null/invalid, tcr-null |
| `wasm_alloc_bignum_or_trap` | 826 | 825 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_complex_double_float_from_bits` | 1049 | 1048 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_complex_single_float_from_bits` | 1036 | 1035 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_cons_or_trap` | 513 | 508 | `tcr == NULL || tcr->save_allocptr == NULL || tcr->save_allocbase == NULL || tcr->save_allocptr == (void *` | alloc, null/invalid, tcr-null |
| `wasm_alloc_cons_or_trap` | 520 | 519 | `newptr < alloc_base` | alloc |
| `wasm_alloc_double_float_from_bits` | 1023 | 1022 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_single_float_from_bits` | 1011 | 1010 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_arrayH_data_or_trap` | 1364 | 1363 | `fulltag_of(array) != fulltag_misc` | type/subtag |
| `wasm_arrayH_data_or_trap` | 1367 | 1366 | `header_subtag(header_of(array)) != subtag_arrayH` | type/subtag |
| `wasm_arrayH_data_or_trap` | 1373 | 1372 | `rank != expected_rank` | unknown |
| `wasm_array_data_vector_or_trap` | 1384 | 1383 | `fulltag_of(current) != fulltag_misc` | type/subtag |
| `wasm_bind_interrupt_level` | 5275 | 5274 | `(unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)limit_count` | bounds |
| `wasm_bind_interrupt_level` | 5280 | 5279 | `tlb == NULL` | null/invalid, state/unwind |
| `wasm_builtin_function` | 492 | 491 | `vec == (LispObj)nil_value` | null/invalid |
| `wasm_cached_symbol_named` | 305 | 304 | `sym == (LispObj)NULL` | null/invalid |
| `wasm_call_lisp_function` | 1882 | 1881 | `fn_value == (LispObj)nil_value` | null/invalid |
| `wasm_call_lisp_function` | 1886 | 1885 | `fulltag_of(fn_value) != fulltag_misc` | type/subtag |
| `wasm_call_lisp_function` | 1895 | 1894 | `fulltag_of(fn_value) != fulltag_misc` | type/subtag |
| `wasm_call_lisp_function` | 1902 | 1901 | `subtag != subtag_function && subtag != subtag_pseudofunction` | type/subtag |
| `wasm_call_lisp_function` | 1910 | 1909 | `tag_of(entry) != tag_fixnum` | fixnum, type/subtag |
| `wasm_gvector_set_or_trap` | 3597 | 3596 | `index < 0 || fulltag_of(obj) != fulltag_misc` | bounds, type/subtag |
| `wasm_gvector_set_or_trap` | 3601 | 3600 | `(header_subtag(header) & fulltagmask) != fulltag_nodeheader` | type/subtag |
| `wasm_gvector_set_or_trap` | 3605 | 3604 | `index >= count` | bounds |
| `wasm_make_simple_base_string` | 198 | 197 | `tcr == NULL || bytes == NULL` | null/invalid, tcr-null |
| `wasm_make_simple_base_string` | 203 | 202 | `len > ((size_t)INT32_MAX)` | bounds |
| `wasm_make_simple_base_string` | 208 | 207 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_misc_ref_dispatch` | 1063 | 1062 | `index < 0 || fulltag_of(obj) != fulltag_misc` | bounds, type/subtag |
| `wasm_misc_ref_dispatch` | 1070 | 1069 | `index >= count` | bounds |
| `wasm_misc_ref_dispatch` | 1079 | 1078 | `(subtag & fulltagmask) != fulltag_immheader` | type/subtag |
| `wasm_misc_set_dispatch` | 1169 | 1168 | `index < 0 || fulltag_of(obj) != fulltag_misc` | bounds, type/subtag |
| `wasm_misc_set_dispatch` | 1176 | 1175 | `index >= count` | bounds |
| `wasm_misc_set_dispatch` | 1186 | 1185 | `(subtag & fulltagmask) != fulltag_immheader` | type/subtag |
| `wasm_positive_fixnum_or_trap` | 809 | 808 | `count <= 0` | bounds |
| `wasm_push_value_set` | 1440 | 1439 | `count < 0` | bounds |
| `wasm_signal_errdisp_2` | 453 | 452 | `tcr == NULL` | null/invalid, tcr-null |
| `wasm_symbol_or_trap` | 799 | 798 | `fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | type/subtag |
| `wasm_unbind_to` | 1565 | 1564 | `tlb == NULL` | null/invalid, state/unwind |
| `wasm_unbind_to` | 1570 | 1569 | `binding == NULL` | null/invalid |
| `wasm_unbox_fixnum_or_trap` | 68 | 67 | `tag_of(value) != tag_fixnum` | fixnum, type/subtag |
| `wasm_unbox_u32_or_trap` | 883 | 882 | `sval < 0` | unknown |
| `wasm_unbox_u32_or_trap` | 898 | 897 | `v & 0x80000000u` | unknown |
| `wasm_unbox_u32_or_trap` | 905 | 904 | `digits[1] != 0` | unknown |
| `wasm_unbox_u32_or_trap` | 910 | 904 | `digits[1] != 0` | unknown |
| `wasm_vpop_argregs` | 741 | 740 | `tag_of(raw) != tag_fixnum` | fixnum, type/subtag |
| `wasm_vpush_argregs` | 773 | 772 | `tag_of(raw) != tag_fixnum` | fixnum, type/subtag |
| `wasm_vsp_or_trap` | 731 | 730 | `vsp_ptr == NULL` | null/invalid, state/unwind |
