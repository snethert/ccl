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

- Total subprims: 130
- Stub: 0
- Guarded: 121
- Indirect: 0
- Clean: 9
- Missing: 0

- behavioral gap: 44
- clean: 9
- validation only: 77

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
| `_SPbind_interrupt_level` | guarded | behavioral gap | 1 | null/invalid, tcr-null | wasm_bind_interrupt_level | bounds, null/invalid, state/unwind | `wasm_bind_interrupt_level: (unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)limit_count` - `wasm_bind_interrupt_level: tlb == NULL` | state/unwind | bounds, null/invalid, tcr-null | - | no | medium |
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
| `_SPfix_nfn_entrypoint` | guarded | validation only | 2 | null/invalid, tcr-null, type/subtag | wasm_call_lisp_function | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPfix_overflow` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | yes | high |
| `_SPfuncall` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_call_lisp_function | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | 0 | no | high |
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
| `_SPksignalerr` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_call_lisp_function | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmakes32` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | yes | high |
| `_SPmakes64` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPmakestackblock` | guarded | validation only | 2 | bounds, null/invalid, tcr-null | wasm_call_lisp_function, wasm_unbox_fixnum_or_trap | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmakestackblock0` | guarded | validation only | 2 | bounds, null/invalid, tcr-null | wasm_call_lisp_function, wasm_unbox_fixnum_or_trap | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmakestacklist` | guarded | validation only | 2 | bounds, null/invalid, tcr-null | wasm_alloc_cons_or_trap, wasm_unbox_fixnum_or_trap | alloc, fixnum, null/invalid, tcr-null, type/subtag | `wasm_alloc_cons_or_trap: tcr == NULL || tcr->save_allocptr == NULL || tcr->save_allocbase == NULL || tcr->save_allocptr == (void *` - `wasm_alloc_cons_or_trap: newptr < alloc_base` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | alloc, bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmakeu32` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_alloc_bignum_or_trap | null/invalid | `wasm_alloc_bignum_or_trap: obj == (LispObj)nil_value` | - | null/invalid, tcr-null | - | no | high |
| `_SPmakeu64` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_alloc_bignum_or_trap | null/invalid | `wasm_alloc_bignum_or_trap: obj == (LispObj)nil_value` | - | null/invalid, tcr-null | - | no | high |
| `_SPmisc_alloc` | guarded | validation only | 5 | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | - | - | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmisc_alloc_init` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_call_lisp_function | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
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
| `_SPsetqsym` | guarded | validation only | 2 | fixnum, null/invalid, tcr-null, type/subtag | wasm_call_lisp_function, wasm_symbol_or_trap | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` - `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPspecref` | guarded | behavioral gap | 4 | bounds, fixnum, null/invalid, state/unwind, tcr-null, type/subtag | wasm_symbol_or_trap | type/subtag | `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPspecrefcheck` | guarded | behavioral gap | 4 | bounds, fixnum, null/invalid, state/unwind, tcr-null, type/subtag | wasm_symbol_or_trap | type/subtag | `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPspecset` | guarded | behavioral gap | 5 | bounds, fixnum, null/invalid, state/unwind, tcr-null, type/subtag | wasm_symbol_or_trap | type/subtag | `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPspread_lexprz` | guarded | behavioral gap | 4 | bounds, null/invalid, tcr-null | wasm_unbox_fixnum_or_trap, wasm_vpop_argregs, wasm_vsp_or_trap | fixnum, null/invalid, state/unwind, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vpop_argregs: tag_of(raw) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPspreadargz` | guarded | behavioral gap | 2 | bounds, null/invalid, tcr-null | wasm_unbox_fixnum_or_trap, wasm_vpop_argregs, wasm_vsp_or_trap | fixnum, null/invalid, state/unwind, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vpop_argregs: tag_of(raw) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPstack_cons_rest_arg` | guarded | behavioral gap | 3 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPstack_misc_alloc` | guarded | validation only | 7 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPstack_misc_alloc_init` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_call_lisp_function | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
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

---

## Direct Trap Site Details

| Subprim | Trap Line | Cond Line | Condition | Tags |
| --- | --- | --- | --- | --- |
| `_SPadd_values` | 1982 | 1981 | `tcr == NULL` | null/invalid, tcr-null |
| `_SParef2` | 3896 | 3895 | `tcr == NULL` | null/invalid, tcr-null |
| `_SParef3` | 3983 | 3982 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPaset2` | 4090 | 4089 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPaset3` | 4178 | 4177 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPatomic_incf_node` | 3534 | 3533 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind` | 4928 | 4927 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind` | 4944 | 4943 | `index < 0` | bounds |
| `_SPbind` | 4950 | 4949 | `(unsigned)index >= (unsigned)limit_count` | bounds |
| `_SPbind` | 4955 | 4954 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPbind_interrupt_level` | 5142 | 5141 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_interrupt_level_0` | 5107 | 5106 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_interrupt_level_0` | 5112 | 5111 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPbind_interrupt_level_m1` | 5130 | 5129 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_nil` | 5031 | 5030 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_self` | 4977 | 4976 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_self` | 4993 | 4992 | `index < 0` | bounds |
| `_SPbind_self` | 4999 | 4998 | `(unsigned)index >= (unsigned)limit_count` | bounds |
| `_SPbind_self` | 5004 | 5003 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPbind_self_boundp_check` | 5046 | 5045 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_self_boundp_check` | 5062 | 5061 | `index < 0` | bounds |
| `_SPbind_self_boundp_check` | 5068 | 5067 | `(unsigned)index >= (unsigned)limit_count` | bounds |
| `_SPbind_self_boundp_check` | 5073 | 5072 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPbuiltin_aref1` | 3483 | 3482 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_aset1` | 3508 | 3507 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_ash` | 3396 | 3395 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_assq` | 3304 | 3303 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_div` | 3122 | 3121 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_eq` | 3134 | 3133 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_eql` | 3254 | 3253 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_ge` | 3194 | 3193 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_gt` | 3174 | 3173 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_le` | 3234 | 3233 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_length` | 3280 | 3279 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logand` | 3375 | 3374 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logbitp` | 3328 | 3327 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logior` | 3354 | 3353 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logxor` | 3462 | 3461 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_lt` | 3214 | 3213 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_memq` | 3316 | 3315 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_minus` | 3080 | 3079 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_ne` | 3154 | 3153 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_negate` | 3442 | 3441 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_plus` | 3059 | 3058 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_seqtype` | 3292 | 3291 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_times` | 3101 | 3100 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPcall_closure` | 5410 | 5409 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPcall_closure` | 5415 | 5414 | `fulltag_of(closure) != fulltag_misc || header_subtag(header_of(closure)) != subtag_function` | type/subtag |
| `_SPcall_closure` | 5420 | 5419 | `argc < 0` | bounds |
| `_SPconslist` | 3674 | 3673 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPconslist` | 3679 | 3678 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPconslist` | 3683 | 3682 | `count < 0` | bounds |
| `_SPconslist_star` | 3706 | 3705 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPconslist_star` | 3711 | 3710 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPconslist_star` | 3715 | 3714 | `count < 0` | bounds |
| `_SPdebind` | 5627 | 5626 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPdebind` | 5782 | 5781 | `fulltag_of(keyvec) != fulltag_misc` | type/subtag |
| `_SPdebind` | 5786 | 5785 | `keyvec_len < 0 || keyvec_len > 256` | bounds |
| `_SPdefault_optional_args` | 2298 | 2297 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPdefault_optional_args` | 2303 | 2302 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPdefault_optional_args` | 2308 | 2307 | `tag_of(raw_limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPdefault_optional_args` | 2314 | 2313 | `nargs_count < 0 || limit < 0` | bounds |
| `_SPdiscard_stack_object` | 4331 | 4330 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPdiscard_stack_object` | 4336 | 4335 | `sp == NULL` | null/invalid |
| `_SPeabi_callback` | 5891 | 5890 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPeabi_ff_call_simple` | 5869 | 5868 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPeabi_ff_callhf` | 5880 | 5879 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfitvals` | 2194 | 2193 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfitvals` | 2199 | 2198 | `tag_of(raw_desired) != tag_fixnum` | fixnum, type/subtag |
| `_SPfitvals` | 2204 | 2203 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPfitvals` | 2210 | 2209 | `desired_count < 0 || current_count < 0` | bounds |
| `_SPfix_nfn_entrypoint` | 2029 | 2028 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfix_nfn_entrypoint` | 2034 | 2033 | `fulltag_of(fn_value) != fulltag_misc || header_subtag(header_of(fn_value)) != subtag_function` | type/subtag |
| `_SPfix_overflow` | 5956 | 5955 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfuncall` | 2052 | 2051 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgets32` | 4518 | 4517 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgets64` | 4674 | 4673 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgetu32` | 4542 | 4541 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgetu64` | 4610 | 4609 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgvector` | 2779 | 2778 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgvector` | 2784 | 2783 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPgvector` | 2788 | 2787 | `count <= 0` | bounds |
| `_SPgvector` | 2795 | 2794 | `subtag < 0` | type/subtag |
| `_SPgvector` | 2801 | 2800 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPgvset` | 3608 | 3607 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPheap_cons_rest_arg` | 2446 | 2445 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPheap_cons_rest_arg` | 2452 | 2451 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_required) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPheap_cons_rest_arg` | 2456 | 2455 | `count < 0` | bounds |
| `_SPheap_rest_arg` | 2377 | 2376 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPheap_rest_arg` | 2382 | 2381 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPheap_rest_arg` | 2386 | 2385 | `count < 0` | bounds |
| `_SPinteger_sign` | 2004 | 2003 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPinteger_sign` | 2016 | 2015 | `!wasm_bignum_info(value, &count, &digits) || count <= 0` | bounds |
| `_SPjmpsym` | 2091 | 2090 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPkeyword_bind` | 5490 | 5489 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPkeyword_bind` | 5497 | 5496 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_prev) != tag_fixnum || tag_of(keyword_flags) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPkeyword_bind` | 5503 | 5502 | `nargs_count < 0 || prev_count < 0` | bounds |
| `_SPkeyword_bind` | 5524 | 5523 | `fulltag_of(keyvec) != fulltag_misc` | type/subtag |
| `_SPkeyword_bind` | 5528 | 5527 | `keyvec_len < 0 || keyvec_len > 256` | bounds |
| `_SPksignalerr` | 4350 | 4349 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakes32` | 4406 | 4405 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakes64` | 4499 | 4498 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestackblock` | 2929 | 2928 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestackblock` | 2935 | 2934 | `count < 0` | bounds |
| `_SPmakestackblock0` | 2956 | 2955 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestackblock0` | 2962 | 2961 | `count < 0` | bounds |
| `_SPmakestacklist` | 2882 | 2881 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestacklist` | 2888 | 2887 | `count < 0` | bounds |
| `_SPmakeu32` | 4421 | 4420 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakeu64` | 4451 | 4450 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_alloc` | 2617 | 2614 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_alloc` | 2624 | 2621 | `tag_of(subtag_val) != tag_fixnum` | fixnum, type/subtag |
| `_SPmisc_alloc` | 2630 | 2627 | `tag_of(count_val) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmisc_alloc` | 2645 | 2642 | `subtag_tag != fulltag_nodeheader && subtag_tag != fulltag_immheader` | type/subtag |
| `_SPmisc_alloc` | 2652 | 2649 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPmisc_alloc_init` | 2664 | 2663 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_ref` | 2712 | 2711 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_set` | 3013 | 3012 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkcatch1v` | 1594 | 1593 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkcatchmv` | 1620 | 1619 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkstackv` | 3851 | 3850 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkstackv` | 3856 | 3855 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmkstackv` | 3860 | 3859 | `count < 0` | bounds |
| `_SPmkstackv` | 3874 | 3873 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPmkunwind` | 1646 | 1645 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkunwind` | 1662 | 1661 | `catch_top == 0 || catch_top == (LispObj)nil_value` | null/invalid, state/unwind |
| `_SPmvpass` | 2141 | 2140 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmvpass` | 2152 | 2151 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmvpasssym` | 2601 | 2600 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmvslide` | 2566 | 2565 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmvslide` | 2571 | 2570 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmvslide` | 2576 | 2575 | `count < 0` | bounds |
| `_SPnthrow1value` | 1674 | 1673 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPnthrow1value` | 1689 | 1688 | `catch_top == 0 || catch_top == (LispObj)nil_value` | null/invalid, state/unwind |
| `_SPnthrow1value` | 1707 | 1706 | `tag_of(cleanup) != tag_fixnum` | fixnum, type/subtag |
| `_SPnthrow1value` | 1712 | 1711 | `count < 0` | bounds |
| `_SPnthrow1value` | 1721 | 1720 | `saved_vsp == NULL` | null/invalid, state/unwind |
| `_SPnthrow1value` | 1745 | 1744 | `saved_vsp == NULL` | null/invalid, state/unwind |
| `_SPnthrowvalues` | 1764 | 1763 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPnthrowvalues` | 1777 | 1776 | `catch_top == 0 || catch_top == (LispObj)nil_value` | null/invalid, state/unwind |
| `_SPnthrowvalues` | 1795 | 1794 | `tag_of(cleanup) != tag_fixnum` | fixnum, type/subtag |
| `_SPnthrowvalues` | 1800 | 1799 | `count < 0` | bounds |
| `_SPnthrowvalues` | 1809 | 1808 | `saved_vsp == NULL` | null/invalid, state/unwind |
| `_SPnthrowvalues` | 1833 | 1832 | `count < 0` | bounds |
| `_SPnthrowvalues` | 1838 | 1837 | `dest == NULL` | null/invalid |
| `_SPnthvalue` | 2259 | 2258 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPnthvalue` | 2264 | 2263 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPnthvalue` | 2269 | 2268 | `count < 0` | bounds |
| `_SPnthvalue` | 2275 | 2274 | `tag_of(raw_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPopt_supplied_p` | 2339 | 2338 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPopt_supplied_p` | 2344 | 2343 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPopt_supplied_p` | 2349 | 2348 | `tag_of(raw_opt) != tag_fixnum` | fixnum, type/subtag |
| `_SPopt_supplied_p` | 2355 | 2354 | `nargs_count < 0 || opt_count < 0` | bounds |
| `_SPpopj` | 4395 | 4394 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPprogvrestore` | 5373 | 5372 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPprogvrestore` | 5378 | 5377 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPprogvrestore` | 5388 | 5387 | `old_vsp == NULL` | null/invalid, state/unwind |
| `_SPprogvrestore` | 5401 | 5387 | `old_vsp == NULL` | null/invalid, state/unwind |
| `_SPprogvsave` | 5290 | 5289 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPprogvsave` | 5304 | 5303 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPprogvsave` | 5324 | 5323 | `tag_of(sym_list) != tag_list` | type/subtag |
| `_SPprogvsave` | 5334 | 5333 | `(unsigned)index >= (unsigned)limit_count` | bounds |
| `_SPprogvsave` | 5342 | 5341 | `tag_of(val_list) != tag_list` | type/subtag |
| `_SPrecover_values` | 1993 | 1992 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPreq_heap_rest_arg` | 2411 | 2410 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPreq_heap_rest_arg` | 2417 | 2416 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_required) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPreq_heap_rest_arg` | 2421 | 2420 | `count < 0` | bounds |
| `_SPreq_stack_rest_arg` | 2493 | 2492 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPreset` | 4363 | 4362 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPrplaca` | 3555 | 3554 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPrplaca` | 3560 | 3559 | `fulltag_of(cell) != fulltag_cons` | type/subtag |
| `_SPrplacd` | 3572 | 3571 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPrplacd` | 3577 | 3576 | `fulltag_of(cell) != fulltag_cons` | type/subtag |
| `_SPsave_values` | 1971 | 1970 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsdiv32` | 5923 | 5922 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPset_hash_key` | 3623 | 3622 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsetqsym` | 4852 | 4851 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsetqsym` | 4860 | 4859 | `tag_of(flags) != tag_fixnum` | fixnum, type/subtag |
| `_SPspecref` | 4714 | 4713 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspecref` | 4721 | 4720 | `tag_of(binding_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecref` | 4726 | 4725 | `tag_of(limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecref` | 4731 | 4730 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPspecrefcheck` | 4755 | 4754 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspecrefcheck` | 4762 | 4761 | `tag_of(binding_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecrefcheck` | 4767 | 4766 | `tag_of(limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecrefcheck` | 4772 | 4771 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPspecset` | 4804 | 4803 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspecset` | 4812 | 4811 | `tag_of(binding_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecset` | 4817 | 4816 | `tag_of(limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecset` | 4822 | 4821 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPspecset` | 4828 | 4827 | `limit_count < 0` | bounds |
| `_SPspread_lexprz` | 4286 | 4285 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspread_lexprz` | 4291 | 4290 | `lexpr == NULL` | null/invalid |
| `_SPspread_lexprz` | 4297 | 4296 | `count < 0` | bounds |
| `_SPspread_lexprz` | 4302 | 4301 | `orig_count < 0` | bounds |
| `_SPspreadargz` | 4882 | 4881 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspreadargz` | 4890 | 4889 | `orig_count < 0` | bounds |
| `_SPstack_cons_rest_arg` | 2506 | 2505 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstack_cons_rest_arg` | 2512 | 2511 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_required) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstack_cons_rest_arg` | 2516 | 2515 | `count < 0` | bounds |
| `_SPstack_misc_alloc` | 2728 | 2727 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstack_misc_alloc` | 2733 | 2732 | `tag_of(raw_count) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstack_misc_alloc` | 2737 | 2736 | `count < 0` | bounds |
| `_SPstack_misc_alloc` | 2743 | 2742 | `subtag < 0` | type/subtag |
| `_SPstack_misc_alloc` | 2751 | 2750 | `words > (SIZE_MAX / node_size)` | bounds |
| `_SPstack_misc_alloc` | 2756 | 2755 | `!wasm_ivector_total_bytes((unsigned)subtag, count, &bytes)` | type/subtag |
| `_SPstack_misc_alloc` | 2759 | 2755 | `!wasm_ivector_total_bytes((unsigned)subtag, count, &bytes)` | type/subtag |
| `_SPstack_misc_alloc_init` | 2688 | 2687 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstack_rest_arg` | 2479 | 2478 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkconslist` | 3749 | 3748 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkconslist` | 3754 | 3753 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstkconslist` | 3758 | 3757 | `count < 0` | bounds |
| `_SPstkconslist_star` | 3800 | 3799 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkconslist_star` | 3805 | 3804 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstkconslist_star` | 3809 | 3808 | `count < 0` | bounds |
| `_SPstkgvector` | 2823 | 2822 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkgvector` | 2828 | 2827 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstkgvector` | 2832 | 2831 | `count <= 0` | bounds |
| `_SPstkgvector` | 2839 | 2838 | `((unsigned)subtag & fulltagmask) != fulltag_nodeheader` | type/subtag |
| `_SPstkgvector` | 2848 | 2847 | `words > (SIZE_MAX / node_size)` | bounds |
| `_SPstkgvector` | 2859 | 2858 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPstore_node_conditional` | 3638 | 3637 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsubtag_misc_ref` | 2985 | 2984 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsubtag_misc_ref` | 2991 | 2990 | `subtag < 0` | type/subtag |
| `_SPsubtag_misc_ref` | 2996 | 2995 | `fulltag_of(obj) != fulltag_misc` | type/subtag |
| `_SPsubtag_misc_ref` | 2999 | 2998 | `header_subtag(header_of(obj)) != (unsigned)subtag` | type/subtag |
| `_SPsubtag_misc_set` | 3030 | 3029 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsubtag_misc_set` | 3036 | 3035 | `subtag < 0` | type/subtag |
| `_SPsubtag_misc_set` | 3041 | 3040 | `fulltag_of(obj) != fulltag_misc` | type/subtag |
| `_SPsubtag_misc_set` | 3044 | 3043 | `header_subtag(header_of(obj)) != (unsigned)subtag` | type/subtag |
| `_SPtcallsymgen` | 2103 | 2102 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPtcallsymslide` | 2115 | 2114 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPthrow` | 1915 | 1914 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPthrow` | 1920 | 1919 | `count < 0` | bounds |
| `_SPudiv32` | 5902 | 5901 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPudiv32` | 5907 | 5906 | `denom == 0` | null/invalid |
| `_SPudiv64by32` | 4585 | 4584 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPudiv64by32` | 4590 | 4589 | `denom == 0` | null/invalid |
| `_SPunbind` | 5190 | 5189 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPunbind` | 5196 | 5195 | `binding == NULL || tlb == NULL` | null/invalid, state/unwind |
| `_SPunbind_interrupt_level` | 5159 | 5158 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPunbind_interrupt_level` | 5165 | 5164 | `binding == NULL || tlb == NULL` | null/invalid, state/unwind |
| `_SPunbind_n` | 5241 | 5240 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPunbind_n` | 5246 | 5245 | `count < 0` | bounds |
| `_SPunbind_n` | 5255 | 5254 | `binding == NULL || tlb == NULL` | null/invalid, state/unwind |
| `_SPunbind_n` | 5260 | 5259 | `binding == NULL` | null/invalid |
| `_SPunbind_to` | 5277 | 5276 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPvalues` | 2170 | 2169 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPvalues` | 2175 | 2174 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |

---

## Helper Trap Site Details

| Helper | Trap Line | Cond Line | Condition | Tags |
| --- | --- | --- | --- | --- |
| `__attribute__` | 1594 | 1593 | `tcr == NULL` | null/invalid, tcr-null |
| `wasm_alloc_bignum_or_trap` | 816 | 815 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_complex_double_float_from_bits` | 1039 | 1038 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_complex_single_float_from_bits` | 1026 | 1025 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_cons_or_trap` | 503 | 498 | `tcr == NULL || tcr->save_allocptr == NULL || tcr->save_allocbase == NULL || tcr->save_allocptr == (void *` | alloc, null/invalid, tcr-null |
| `wasm_alloc_cons_or_trap` | 510 | 509 | `newptr < alloc_base` | alloc |
| `wasm_alloc_double_float_from_bits` | 1013 | 1012 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_single_float_from_bits` | 1001 | 1000 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_arrayH_data_or_trap` | 1354 | 1353 | `fulltag_of(array) != fulltag_misc` | type/subtag |
| `wasm_arrayH_data_or_trap` | 1357 | 1356 | `header_subtag(header_of(array)) != subtag_arrayH` | type/subtag |
| `wasm_arrayH_data_or_trap` | 1363 | 1362 | `rank != expected_rank` | unknown |
| `wasm_array_data_vector_or_trap` | 1374 | 1373 | `fulltag_of(current) != fulltag_misc` | type/subtag |
| `wasm_bind_interrupt_level` | 5214 | 5213 | `(unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)limit_count` | bounds |
| `wasm_bind_interrupt_level` | 5219 | 5218 | `tlb == NULL` | null/invalid, state/unwind |
| `wasm_builtin_function` | 482 | 481 | `vec == (LispObj)nil_value` | null/invalid |
| `wasm_cached_symbol_named` | 295 | 294 | `sym == (LispObj)NULL` | null/invalid |
| `wasm_call_lisp_function` | 1872 | 1871 | `fn_value == (LispObj)nil_value` | null/invalid |
| `wasm_call_lisp_function` | 1876 | 1875 | `fulltag_of(fn_value) != fulltag_misc` | type/subtag |
| `wasm_call_lisp_function` | 1885 | 1884 | `fulltag_of(fn_value) != fulltag_misc` | type/subtag |
| `wasm_call_lisp_function` | 1892 | 1891 | `subtag != subtag_function` | type/subtag |
| `wasm_call_lisp_function` | 1900 | 1899 | `tag_of(entry) != tag_fixnum` | fixnum, type/subtag |
| `wasm_gvector_set_or_trap` | 3587 | 3586 | `index < 0 || fulltag_of(obj) != fulltag_misc` | bounds, type/subtag |
| `wasm_gvector_set_or_trap` | 3591 | 3590 | `(header_subtag(header) & fulltagmask) != fulltag_nodeheader` | type/subtag |
| `wasm_gvector_set_or_trap` | 3595 | 3594 | `index >= count` | bounds |
| `wasm_make_simple_base_string` | 188 | 187 | `tcr == NULL || bytes == NULL` | null/invalid, tcr-null |
| `wasm_make_simple_base_string` | 193 | 192 | `len > ((size_t)INT32_MAX)` | bounds |
| `wasm_make_simple_base_string` | 198 | 197 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_misc_ref_dispatch` | 1053 | 1052 | `index < 0 || fulltag_of(obj) != fulltag_misc` | bounds, type/subtag |
| `wasm_misc_ref_dispatch` | 1060 | 1059 | `index >= count` | bounds |
| `wasm_misc_ref_dispatch` | 1069 | 1068 | `(subtag & fulltagmask) != fulltag_immheader` | type/subtag |
| `wasm_misc_set_dispatch` | 1159 | 1158 | `index < 0 || fulltag_of(obj) != fulltag_misc` | bounds, type/subtag |
| `wasm_misc_set_dispatch` | 1166 | 1165 | `index >= count` | bounds |
| `wasm_misc_set_dispatch` | 1176 | 1175 | `(subtag & fulltagmask) != fulltag_immheader` | type/subtag |
| `wasm_positive_fixnum_or_trap` | 799 | 798 | `count <= 0` | bounds |
| `wasm_push_value_set` | 1430 | 1429 | `count < 0` | bounds |
| `wasm_signal_errdisp_2` | 443 | 442 | `tcr == NULL` | null/invalid, tcr-null |
| `wasm_symbol_or_trap` | 789 | 788 | `fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | type/subtag |
| `wasm_unbind_to` | 1555 | 1554 | `tlb == NULL` | null/invalid, state/unwind |
| `wasm_unbind_to` | 1560 | 1559 | `binding == NULL` | null/invalid |
| `wasm_unbox_fixnum_or_trap` | 61 | 60 | `tag_of(value) != tag_fixnum` | fixnum, type/subtag |
| `wasm_unbox_u32_or_trap` | 873 | 872 | `sval < 0` | unknown |
| `wasm_unbox_u32_or_trap` | 888 | 887 | `v & 0x80000000u` | unknown |
| `wasm_unbox_u32_or_trap` | 895 | 894 | `digits[1] != 0` | unknown |
| `wasm_unbox_u32_or_trap` | 900 | 894 | `digits[1] != 0` | unknown |
| `wasm_vpop_argregs` | 731 | 730 | `tag_of(raw) != tag_fixnum` | fixnum, type/subtag |
| `wasm_vpush_argregs` | 763 | 762 | `tag_of(raw) != tag_fixnum` | fixnum, type/subtag |
| `wasm_vsp_or_trap` | 721 | 720 | `vsp_ptr == NULL` | null/invalid, state/unwind |
