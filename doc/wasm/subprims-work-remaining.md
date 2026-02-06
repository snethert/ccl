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

- behavioral gap: 46
- clean: 9
- validation only: 75

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
| `_SPbind` | guarded | behavioral gap | 4 | null/invalid, state/unwind, tcr-null, unknown | wasm_positive_fixnum_or_trap, wasm_symbol_or_trap, wasm_unbox_fixnum_or_trap, wasm_vsp_or_trap | fixnum, null/invalid, state/unwind, type/subtag, unknown | `wasm_positive_fixnum_or_trap: result <= 0` - `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind, unknown | fixnum, null/invalid, tcr-null, type/subtag | - | no | low: unknown conds -> `idx < 0`; `(unsigned)idx >= (unsigned)lim`; `result <= 0` |
| `_SPbind_interrupt_level` | guarded | behavioral gap | 1 | null/invalid, tcr-null | wasm_bind_interrupt_level | null/invalid, state/unwind, unknown | `wasm_bind_interrupt_level: (unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)lim` - `wasm_bind_interrupt_level: tlb == NULL` | state/unwind, unknown | null/invalid, tcr-null | - | no | low: unknown conds -> `(unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)lim` |
| `_SPbind_interrupt_level_0` | guarded | behavioral gap | 2 | null/invalid, state/unwind, tcr-null | wasm_bind_interrupt_level | null/invalid, state/unwind, unknown | `wasm_bind_interrupt_level: (unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)lim` - `wasm_bind_interrupt_level: tlb == NULL` | state/unwind, unknown | null/invalid, tcr-null | - | no | low: unknown conds -> `(unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)lim` |
| `_SPbind_interrupt_level_m1` | guarded | behavioral gap | 1 | null/invalid, tcr-null | wasm_bind_interrupt_level | null/invalid, state/unwind, unknown | `wasm_bind_interrupt_level: (unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)lim` - `wasm_bind_interrupt_level: tlb == NULL` | state/unwind, unknown | null/invalid, tcr-null | - | no | low: unknown conds -> `(unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)lim` |
| `_SPbind_nil` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbind_self` | guarded | behavioral gap | 4 | null/invalid, state/unwind, tcr-null, unknown | wasm_positive_fixnum_or_trap, wasm_symbol_or_trap, wasm_unbox_fixnum_or_trap, wasm_vsp_or_trap | fixnum, null/invalid, state/unwind, type/subtag, unknown | `wasm_positive_fixnum_or_trap: result <= 0` - `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind, unknown | fixnum, null/invalid, tcr-null, type/subtag | - | no | low: unknown conds -> `idx < 0`; `(unsigned)idx >= (unsigned)lim`; `result <= 0` |
| `_SPbind_self_boundp_check` | guarded | behavioral gap | 4 | null/invalid, state/unwind, tcr-null, unknown | wasm_positive_fixnum_or_trap, wasm_symbol_or_trap, wasm_unbox_fixnum_or_trap, wasm_vsp_or_trap | fixnum, null/invalid, state/unwind, type/subtag, unknown | `wasm_positive_fixnum_or_trap: result <= 0` - `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind, unknown | fixnum, null/invalid, tcr-null, type/subtag | - | no | low: unknown conds -> `idx < 0`; `(unsigned)idx >= (unsigned)lim`; `result <= 0` |
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
| `_SPfitvals` | guarded | behavioral gap | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag, unknown | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind, unknown | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | low: unknown conds -> `desired < 0 || current < 0` |
| `_SPfix_nfn_entrypoint` | guarded | validation only | 2 | null/invalid, tcr-null, type/subtag | wasm_call_lisp_function | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPfix_overflow` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | yes | high |
| `_SPfuncall` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_call_lisp_function | fixnum, null/invalid, type/subtag | `wasm_call_lisp_function: fn_value == (LispObj)nil_value` - `wasm_call_lisp_function: fulltag_of(fn_value) != fulltag_misc` - `wasm_call_lisp_function: subtag != subtag_function` - `wasm_call_lisp_function: tag_of(entry) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | 0 | no | high |
| `_SPgets32` | guarded | validation only | 2 | bounds, null/invalid, tcr-null | - | - | - | - | bounds, null/invalid, tcr-null | - | no | high |
| `_SPgets64` | guarded | behavioral gap | 2 | null/invalid, tcr-null, unknown | - | - | - | unknown | null/invalid, tcr-null | - | no | low: unknown conds -> `!wasm_bignum_info(value, &count, &digits)` |
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
| `_SPmisc_alloc` | guarded | behavioral gap | 5 | bounds, fixnum, null/invalid, tcr-null, type/subtag, unknown | - | - | - | unknown | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | low: unknown conds -> `tag != fulltag_nodeheader && tag != fulltag_immheader` |
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
| `_SPnthrow1value` | guarded | behavioral gap | 5 | bounds, fixnum, null/invalid, state/unwind, tcr-null, type/subtag | wasm_push_value_set, wasm_unbind_to, wasm_unbox_fixnum_or_trap | bounds, fixnum, null/invalid, state/unwind, type/subtag | `wasm_push_value_set: count < 0` - `wasm_unbind_to: tlb == NULL` - `wasm_unbind_to: binding == NULL` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | 0 | no | medium |
| `_SPnthrowvalues` | guarded | behavioral gap | 7 | bounds, fixnum, null/invalid, state/unwind, tcr-null, type/subtag | wasm_push_value_set, wasm_unbind_to, wasm_unbox_fixnum_or_trap, wasm_vsp_or_trap | bounds, fixnum, null/invalid, state/unwind, type/subtag | `wasm_push_value_set: count < 0` - `wasm_unbind_to: tlb == NULL` - `wasm_unbind_to: binding == NULL` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | 1 | no | medium |
| `_SPnthvalue` | guarded | behavioral gap | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPnvalret` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPopt_supplied_p` | guarded | behavioral gap | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vsp_or_trap | null/invalid, state/unwind | `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPpopj` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPprogvrestore` | guarded | behavioral gap | 4 | null/invalid, state/unwind, tcr-null | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | state/unwind | fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPprogvsave` | guarded | behavioral gap | 5 | null/invalid, state/unwind, tcr-null, type/subtag, unknown | wasm_positive_fixnum_or_trap, wasm_symbol_or_trap, wasm_vsp_or_trap | null/invalid, state/unwind, type/subtag, unknown | `wasm_positive_fixnum_or_trap: result <= 0` - `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind, unknown | null/invalid, tcr-null, type/subtag | - | no | low: unknown conds -> `(unsigned)idx >= (unsigned)lim`; `result <= 0` |
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
| `_SPspecset` | guarded | behavioral gap | 5 | bounds, fixnum, null/invalid, state/unwind, tcr-null, type/subtag, unknown | wasm_symbol_or_trap | type/subtag | `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | state/unwind, unknown | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | low: unknown conds -> `lim < 0` |
| `_SPspread_lexprz` | guarded | behavioral gap | 4 | bounds, null/invalid, tcr-null | wasm_unbox_fixnum_or_trap, wasm_vpop_argregs, wasm_vsp_or_trap | fixnum, null/invalid, state/unwind, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vpop_argregs: tag_of(raw) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
| `_SPspreadargz` | guarded | behavioral gap | 3 | bounds, null/invalid, tcr-null, type/subtag | wasm_unbox_fixnum_or_trap, wasm_vpop_argregs, wasm_vsp_or_trap | fixnum, null/invalid, state/unwind, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vpop_argregs: tag_of(raw) != tag_fixnum` - `wasm_vsp_or_trap: vsp_ptr == NULL` | state/unwind | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | medium |
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
| `_SPadd_values` | 1976 | 1975 | `tcr == NULL` | null/invalid, tcr-null |
| `_SParef2` | 3890 | 3889 | `tcr == NULL` | null/invalid, tcr-null |
| `_SParef3` | 3977 | 3976 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPaset2` | 4084 | 4083 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPaset3` | 4172 | 4171 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPatomic_incf_node` | 3528 | 3527 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind` | 4916 | 4915 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind` | 4932 | 4931 | `idx < 0` | unknown |
| `_SPbind` | 4938 | 4937 | `(unsigned)idx >= (unsigned)lim` | unknown |
| `_SPbind` | 4943 | 4942 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPbind_interrupt_level` | 5130 | 5129 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_interrupt_level_0` | 5095 | 5094 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_interrupt_level_0` | 5100 | 5099 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPbind_interrupt_level_m1` | 5118 | 5117 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_nil` | 5019 | 5018 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_self` | 4965 | 4964 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_self` | 4981 | 4980 | `idx < 0` | unknown |
| `_SPbind_self` | 4987 | 4986 | `(unsigned)idx >= (unsigned)lim` | unknown |
| `_SPbind_self` | 4992 | 4991 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPbind_self_boundp_check` | 5034 | 5033 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_self_boundp_check` | 5050 | 5049 | `idx < 0` | unknown |
| `_SPbind_self_boundp_check` | 5056 | 5055 | `(unsigned)idx >= (unsigned)lim` | unknown |
| `_SPbind_self_boundp_check` | 5061 | 5060 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPbuiltin_aref1` | 3477 | 3476 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_aset1` | 3502 | 3501 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_ash` | 3390 | 3389 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_assq` | 3298 | 3297 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_div` | 3116 | 3115 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_eq` | 3128 | 3127 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_eql` | 3248 | 3247 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_ge` | 3188 | 3187 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_gt` | 3168 | 3167 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_le` | 3228 | 3227 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_length` | 3274 | 3273 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logand` | 3369 | 3368 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logbitp` | 3322 | 3321 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logior` | 3348 | 3347 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logxor` | 3456 | 3455 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_lt` | 3208 | 3207 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_memq` | 3310 | 3309 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_minus` | 3074 | 3073 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_ne` | 3148 | 3147 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_negate` | 3436 | 3435 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_plus` | 3053 | 3052 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_seqtype` | 3286 | 3285 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_times` | 3095 | 3094 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPcall_closure` | 5398 | 5397 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPcall_closure` | 5403 | 5402 | `fulltag_of(closure) != fulltag_misc || header_subtag(header_of(closure)) != subtag_function` | type/subtag |
| `_SPcall_closure` | 5408 | 5407 | `argc < 0` | bounds |
| `_SPconslist` | 3668 | 3667 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPconslist` | 3673 | 3672 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPconslist` | 3677 | 3676 | `count < 0` | bounds |
| `_SPconslist_star` | 3700 | 3699 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPconslist_star` | 3705 | 3704 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPconslist_star` | 3709 | 3708 | `count < 0` | bounds |
| `_SPdebind` | 5615 | 5614 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPdebind` | 5770 | 5769 | `fulltag_of(keyvec) != fulltag_misc` | type/subtag |
| `_SPdebind` | 5774 | 5773 | `keyvec_len < 0 || keyvec_len > 256` | bounds |
| `_SPdefault_optional_args` | 2292 | 2291 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPdefault_optional_args` | 2297 | 2296 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPdefault_optional_args` | 2302 | 2301 | `tag_of(raw_limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPdefault_optional_args` | 2308 | 2307 | `nargs_count < 0 || limit < 0` | bounds |
| `_SPdiscard_stack_object` | 4325 | 4324 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPdiscard_stack_object` | 4330 | 4329 | `sp == NULL` | null/invalid |
| `_SPeabi_callback` | 5879 | 5878 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPeabi_ff_call_simple` | 5857 | 5856 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPeabi_ff_callhf` | 5868 | 5867 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfitvals` | 2188 | 2187 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfitvals` | 2193 | 2192 | `tag_of(raw_desired) != tag_fixnum` | fixnum, type/subtag |
| `_SPfitvals` | 2198 | 2197 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPfitvals` | 2204 | 2203 | `desired < 0 || current < 0` | unknown |
| `_SPfix_nfn_entrypoint` | 2023 | 2022 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfix_nfn_entrypoint` | 2028 | 2027 | `fulltag_of(fn_value) != fulltag_misc || header_subtag(header_of(fn_value)) != subtag_function` | type/subtag |
| `_SPfix_overflow` | 5944 | 5943 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfuncall` | 2046 | 2045 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgets32` | 4512 | 4511 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgets32` | 4524 | 4523 | `!wasm_bignum_info(value, &count, &digits) || count != 1` | bounds |
| `_SPgets64` | 4667 | 4666 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgets64` | 4681 | 4680 | `!wasm_bignum_info(value, &count, &digits)` | unknown |
| `_SPgetu32` | 4535 | 4534 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgetu64` | 4603 | 4602 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgvector` | 2773 | 2772 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgvector` | 2778 | 2777 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPgvector` | 2782 | 2781 | `count <= 0` | bounds |
| `_SPgvector` | 2789 | 2788 | `subtag < 0` | type/subtag |
| `_SPgvector` | 2795 | 2794 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPgvset` | 3602 | 3601 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPheap_cons_rest_arg` | 2440 | 2439 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPheap_cons_rest_arg` | 2446 | 2445 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_required) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPheap_cons_rest_arg` | 2450 | 2449 | `count < 0` | bounds |
| `_SPheap_rest_arg` | 2371 | 2370 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPheap_rest_arg` | 2376 | 2375 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPheap_rest_arg` | 2380 | 2379 | `count < 0` | bounds |
| `_SPinteger_sign` | 1998 | 1997 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPinteger_sign` | 2010 | 2009 | `!wasm_bignum_info(value, &count, &digits) || count <= 0` | bounds |
| `_SPjmpsym` | 2085 | 2084 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPkeyword_bind` | 5478 | 5477 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPkeyword_bind` | 5485 | 5484 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_prev) != tag_fixnum || tag_of(keyword_flags) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPkeyword_bind` | 5491 | 5490 | `nargs_count < 0 || prev_count < 0` | bounds |
| `_SPkeyword_bind` | 5512 | 5511 | `fulltag_of(keyvec) != fulltag_misc` | type/subtag |
| `_SPkeyword_bind` | 5516 | 5515 | `keyvec_len < 0 || keyvec_len > 256` | bounds |
| `_SPksignalerr` | 4344 | 4343 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakes32` | 4400 | 4399 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakes64` | 4493 | 4492 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestackblock` | 2923 | 2922 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestackblock` | 2929 | 2928 | `count < 0` | bounds |
| `_SPmakestackblock0` | 2950 | 2949 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestackblock0` | 2956 | 2955 | `count < 0` | bounds |
| `_SPmakestacklist` | 2876 | 2875 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestacklist` | 2882 | 2881 | `count < 0` | bounds |
| `_SPmakeu32` | 4415 | 4414 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakeu64` | 4445 | 4444 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_alloc` | 2611 | 2608 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_alloc` | 2618 | 2615 | `tag_of(subtag_val) != tag_fixnum` | fixnum, type/subtag |
| `_SPmisc_alloc` | 2624 | 2621 | `tag_of(count_val) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmisc_alloc` | 2639 | 2636 | `tag != fulltag_nodeheader && tag != fulltag_immheader` | unknown |
| `_SPmisc_alloc` | 2646 | 2643 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPmisc_alloc_init` | 2658 | 2657 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_ref` | 2706 | 2705 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_set` | 3007 | 3006 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkcatch1v` | 1593 | 1592 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkcatchmv` | 1619 | 1618 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkstackv` | 3845 | 3844 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkstackv` | 3850 | 3849 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmkstackv` | 3854 | 3853 | `count < 0` | bounds |
| `_SPmkstackv` | 3868 | 3867 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPmkunwind` | 1645 | 1644 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkunwind` | 1661 | 1660 | `catch_top == 0 || catch_top == (LispObj)nil_value` | null/invalid, state/unwind |
| `_SPmvpass` | 2135 | 2134 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmvpass` | 2146 | 2145 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmvpasssym` | 2595 | 2594 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmvslide` | 2560 | 2559 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmvslide` | 2565 | 2564 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmvslide` | 2570 | 2569 | `count < 0` | bounds |
| `_SPnthrow1value` | 1673 | 1672 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPnthrow1value` | 1688 | 1687 | `catch_top == 0 || catch_top == (LispObj)nil_value` | null/invalid, state/unwind |
| `_SPnthrow1value` | 1706 | 1705 | `tag_of(cleanup) != tag_fixnum` | fixnum, type/subtag |
| `_SPnthrow1value` | 1711 | 1710 | `count < 0` | bounds |
| `_SPnthrow1value` | 1720 | 1719 | `saved_vsp == NULL` | null/invalid, state/unwind |
| `_SPnthrowvalues` | 1758 | 1757 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPnthrowvalues` | 1771 | 1770 | `catch_top == 0 || catch_top == (LispObj)nil_value` | null/invalid, state/unwind |
| `_SPnthrowvalues` | 1789 | 1788 | `tag_of(cleanup) != tag_fixnum` | fixnum, type/subtag |
| `_SPnthrowvalues` | 1794 | 1793 | `count < 0` | bounds |
| `_SPnthrowvalues` | 1803 | 1802 | `saved_vsp == NULL` | null/invalid, state/unwind |
| `_SPnthrowvalues` | 1827 | 1826 | `count < 0` | bounds |
| `_SPnthrowvalues` | 1832 | 1831 | `dest == NULL` | null/invalid |
| `_SPnthvalue` | 2253 | 2252 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPnthvalue` | 2258 | 2257 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPnthvalue` | 2263 | 2262 | `count < 0` | bounds |
| `_SPnthvalue` | 2269 | 2268 | `tag_of(raw_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPopt_supplied_p` | 2333 | 2332 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPopt_supplied_p` | 2338 | 2337 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPopt_supplied_p` | 2343 | 2342 | `tag_of(raw_opt) != tag_fixnum` | fixnum, type/subtag |
| `_SPopt_supplied_p` | 2349 | 2348 | `nargs_count < 0 || opt_count < 0` | bounds |
| `_SPpopj` | 4389 | 4388 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPprogvrestore` | 5361 | 5360 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPprogvrestore` | 5366 | 5365 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPprogvrestore` | 5376 | 5375 | `old_vsp == NULL` | null/invalid, state/unwind |
| `_SPprogvrestore` | 5389 | 5375 | `old_vsp == NULL` | null/invalid, state/unwind |
| `_SPprogvsave` | 5278 | 5277 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPprogvsave` | 5292 | 5291 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPprogvsave` | 5312 | 5311 | `tag_of(sym_list) != tag_list` | type/subtag |
| `_SPprogvsave` | 5322 | 5321 | `(unsigned)idx >= (unsigned)lim` | unknown |
| `_SPprogvsave` | 5330 | 5329 | `tag_of(val_list) != tag_list` | type/subtag |
| `_SPrecover_values` | 1987 | 1986 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPreq_heap_rest_arg` | 2405 | 2404 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPreq_heap_rest_arg` | 2411 | 2410 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_required) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPreq_heap_rest_arg` | 2415 | 2414 | `count < 0` | bounds |
| `_SPreq_stack_rest_arg` | 2487 | 2486 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPreset` | 4357 | 4356 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPrplaca` | 3549 | 3548 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPrplaca` | 3554 | 3553 | `fulltag_of(cell) != fulltag_cons` | type/subtag |
| `_SPrplacd` | 3566 | 3565 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPrplacd` | 3571 | 3570 | `fulltag_of(cell) != fulltag_cons` | type/subtag |
| `_SPsave_values` | 1965 | 1964 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsdiv32` | 5911 | 5910 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPset_hash_key` | 3617 | 3616 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsetqsym` | 4844 | 4843 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsetqsym` | 4852 | 4851 | `tag_of(flags) != tag_fixnum` | fixnum, type/subtag |
| `_SPspecref` | 4706 | 4705 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspecref` | 4713 | 4712 | `tag_of(binding_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecref` | 4718 | 4717 | `tag_of(limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecref` | 4723 | 4722 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPspecrefcheck` | 4747 | 4746 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspecrefcheck` | 4754 | 4753 | `tag_of(binding_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecrefcheck` | 4759 | 4758 | `tag_of(limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecrefcheck` | 4764 | 4763 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPspecset` | 4796 | 4795 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspecset` | 4804 | 4803 | `tag_of(binding_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecset` | 4809 | 4808 | `tag_of(limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecset` | 4814 | 4813 | `tlb == NULL` | null/invalid, state/unwind |
| `_SPspecset` | 4820 | 4819 | `lim < 0` | unknown |
| `_SPspread_lexprz` | 4280 | 4279 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspread_lexprz` | 4285 | 4284 | `lexpr == NULL` | null/invalid |
| `_SPspread_lexprz` | 4291 | 4290 | `count < 0` | bounds |
| `_SPspread_lexprz` | 4296 | 4295 | `orig_count < 0` | bounds |
| `_SPspreadargz` | 4874 | 4873 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspreadargz` | 4881 | 4880 | `orig_count < 0` | bounds |
| `_SPspreadargz` | 4892 | 4888 | `tag_of(list) != tag_list` | type/subtag |
| `_SPstack_cons_rest_arg` | 2500 | 2499 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstack_cons_rest_arg` | 2506 | 2505 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_required) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstack_cons_rest_arg` | 2510 | 2509 | `count < 0` | bounds |
| `_SPstack_misc_alloc` | 2722 | 2721 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstack_misc_alloc` | 2727 | 2726 | `tag_of(raw_count) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstack_misc_alloc` | 2731 | 2730 | `count < 0` | bounds |
| `_SPstack_misc_alloc` | 2737 | 2736 | `subtag < 0` | type/subtag |
| `_SPstack_misc_alloc` | 2745 | 2744 | `words > (SIZE_MAX / node_size)` | bounds |
| `_SPstack_misc_alloc` | 2750 | 2749 | `!wasm_ivector_total_bytes((unsigned)subtag, count, &bytes)` | type/subtag |
| `_SPstack_misc_alloc` | 2753 | 2749 | `!wasm_ivector_total_bytes((unsigned)subtag, count, &bytes)` | type/subtag |
| `_SPstack_misc_alloc_init` | 2682 | 2681 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstack_rest_arg` | 2473 | 2472 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkconslist` | 3743 | 3742 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkconslist` | 3748 | 3747 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstkconslist` | 3752 | 3751 | `count < 0` | bounds |
| `_SPstkconslist_star` | 3794 | 3793 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkconslist_star` | 3799 | 3798 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstkconslist_star` | 3803 | 3802 | `count < 0` | bounds |
| `_SPstkgvector` | 2817 | 2816 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkgvector` | 2822 | 2821 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstkgvector` | 2826 | 2825 | `count <= 0` | bounds |
| `_SPstkgvector` | 2833 | 2832 | `((unsigned)subtag & fulltagmask) != fulltag_nodeheader` | type/subtag |
| `_SPstkgvector` | 2842 | 2841 | `words > (SIZE_MAX / node_size)` | bounds |
| `_SPstkgvector` | 2853 | 2852 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPstore_node_conditional` | 3632 | 3631 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsubtag_misc_ref` | 2979 | 2978 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsubtag_misc_ref` | 2985 | 2984 | `subtag < 0` | type/subtag |
| `_SPsubtag_misc_ref` | 2990 | 2989 | `fulltag_of(obj) != fulltag_misc` | type/subtag |
| `_SPsubtag_misc_ref` | 2993 | 2992 | `header_subtag(header_of(obj)) != (unsigned)subtag` | type/subtag |
| `_SPsubtag_misc_set` | 3024 | 3023 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsubtag_misc_set` | 3030 | 3029 | `subtag < 0` | type/subtag |
| `_SPsubtag_misc_set` | 3035 | 3034 | `fulltag_of(obj) != fulltag_misc` | type/subtag |
| `_SPsubtag_misc_set` | 3038 | 3037 | `header_subtag(header_of(obj)) != (unsigned)subtag` | type/subtag |
| `_SPtcallsymgen` | 2097 | 2096 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPtcallsymslide` | 2109 | 2108 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPthrow` | 1909 | 1908 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPthrow` | 1914 | 1913 | `count < 0` | bounds |
| `_SPudiv32` | 5890 | 5889 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPudiv32` | 5895 | 5894 | `denom == 0` | null/invalid |
| `_SPudiv64by32` | 4578 | 4577 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPudiv64by32` | 4583 | 4582 | `denom == 0` | null/invalid |
| `_SPunbind` | 5178 | 5177 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPunbind` | 5184 | 5183 | `binding == NULL || tlb == NULL` | null/invalid, state/unwind |
| `_SPunbind_interrupt_level` | 5147 | 5146 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPunbind_interrupt_level` | 5153 | 5152 | `binding == NULL || tlb == NULL` | null/invalid, state/unwind |
| `_SPunbind_n` | 5229 | 5228 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPunbind_n` | 5234 | 5233 | `count < 0` | bounds |
| `_SPunbind_n` | 5243 | 5242 | `binding == NULL || tlb == NULL` | null/invalid, state/unwind |
| `_SPunbind_n` | 5248 | 5247 | `binding == NULL` | null/invalid |
| `_SPunbind_to` | 5265 | 5264 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPvalues` | 2164 | 2163 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPvalues` | 2169 | 2168 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |

---

## Helper Trap Site Details

| Helper | Trap Line | Cond Line | Condition | Tags |
| --- | --- | --- | --- | --- |
| `__attribute__` | 1593 | 1592 | `tcr == NULL` | null/invalid, tcr-null |
| `wasm_alloc_bignum_or_trap` | 815 | 814 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_complex_double_float_from_bits` | 1038 | 1037 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_complex_single_float_from_bits` | 1025 | 1024 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_cons_or_trap` | 502 | 497 | `tcr == NULL || tcr->save_allocptr == NULL || tcr->save_allocbase == NULL || tcr->save_allocptr == (void *` | alloc, null/invalid, tcr-null |
| `wasm_alloc_cons_or_trap` | 509 | 508 | `newptr < alloc_base` | alloc |
| `wasm_alloc_double_float_from_bits` | 1012 | 1011 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_single_float_from_bits` | 1000 | 999 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_arrayH_data_or_trap` | 1353 | 1352 | `fulltag_of(array) != fulltag_misc` | type/subtag |
| `wasm_arrayH_data_or_trap` | 1356 | 1355 | `header_subtag(header_of(array)) != subtag_arrayH` | type/subtag |
| `wasm_arrayH_data_or_trap` | 1362 | 1361 | `rank != expected_rank` | unknown |
| `wasm_array_data_vector_or_trap` | 1373 | 1372 | `fulltag_of(current) != fulltag_misc` | type/subtag |
| `wasm_bind_interrupt_level` | 5202 | 5201 | `(unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)lim` | unknown |
| `wasm_bind_interrupt_level` | 5207 | 5206 | `tlb == NULL` | null/invalid, state/unwind |
| `wasm_builtin_function` | 481 | 480 | `vec == (LispObj)nil_value` | null/invalid |
| `wasm_cached_symbol_named` | 294 | 293 | `sym == (LispObj)NULL` | null/invalid |
| `wasm_call_lisp_function` | 1866 | 1865 | `fn_value == (LispObj)nil_value` | null/invalid |
| `wasm_call_lisp_function` | 1870 | 1869 | `fulltag_of(fn_value) != fulltag_misc` | type/subtag |
| `wasm_call_lisp_function` | 1879 | 1878 | `fulltag_of(fn_value) != fulltag_misc` | type/subtag |
| `wasm_call_lisp_function` | 1886 | 1885 | `subtag != subtag_function` | type/subtag |
| `wasm_call_lisp_function` | 1894 | 1893 | `tag_of(entry) != tag_fixnum` | fixnum, type/subtag |
| `wasm_gvector_set_or_trap` | 3581 | 3580 | `index < 0 || fulltag_of(obj) != fulltag_misc` | bounds, type/subtag |
| `wasm_gvector_set_or_trap` | 3585 | 3584 | `(header_subtag(header) & fulltagmask) != fulltag_nodeheader` | type/subtag |
| `wasm_gvector_set_or_trap` | 3589 | 3588 | `index >= count` | bounds |
| `wasm_make_simple_base_string` | 187 | 186 | `tcr == NULL || bytes == NULL` | null/invalid, tcr-null |
| `wasm_make_simple_base_string` | 192 | 191 | `len > ((size_t)INT32_MAX)` | bounds |
| `wasm_make_simple_base_string` | 197 | 196 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_misc_ref_dispatch` | 1052 | 1051 | `index < 0 || fulltag_of(obj) != fulltag_misc` | bounds, type/subtag |
| `wasm_misc_ref_dispatch` | 1059 | 1058 | `index >= count` | bounds |
| `wasm_misc_ref_dispatch` | 1068 | 1067 | `(subtag & fulltagmask) != fulltag_immheader` | type/subtag |
| `wasm_misc_set_dispatch` | 1158 | 1157 | `index < 0 || fulltag_of(obj) != fulltag_misc` | bounds, type/subtag |
| `wasm_misc_set_dispatch` | 1165 | 1164 | `index >= count` | bounds |
| `wasm_misc_set_dispatch` | 1175 | 1174 | `(subtag & fulltagmask) != fulltag_immheader` | type/subtag |
| `wasm_positive_fixnum_or_trap` | 798 | 797 | `result <= 0` | unknown |
| `wasm_push_value_set` | 1429 | 1428 | `count < 0` | bounds |
| `wasm_signal_errdisp_2` | 442 | 441 | `tcr == NULL` | null/invalid, tcr-null |
| `wasm_symbol_or_trap` | 788 | 787 | `fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | type/subtag |
| `wasm_unbind_to` | 1554 | 1553 | `tlb == NULL` | null/invalid, state/unwind |
| `wasm_unbind_to` | 1559 | 1558 | `binding == NULL` | null/invalid |
| `wasm_unbox_fixnum_or_trap` | 61 | 60 | `tag_of(value) != tag_fixnum` | fixnum, type/subtag |
| `wasm_unbox_u32_or_trap` | 872 | 871 | `sval < 0` | unknown |
| `wasm_unbox_u32_or_trap` | 887 | 886 | `v & 0x80000000u` | unknown |
| `wasm_unbox_u32_or_trap` | 894 | 893 | `digits[1] != 0` | unknown |
| `wasm_unbox_u32_or_trap` | 899 | 893 | `digits[1] != 0` | unknown |
| `wasm_vpop_argregs` | 730 | 729 | `tag_of(raw) != tag_fixnum` | fixnum, type/subtag |
| `wasm_vpush_argregs` | 762 | 761 | `tag_of(raw) != tag_fixnum` | fixnum, type/subtag |
| `wasm_vsp_or_trap` | 720 | 719 | `vsp_ptr == NULL` | null/invalid, state/unwind |
