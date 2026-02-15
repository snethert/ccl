# WASM Subprims Work Remaining (Critical Detail)

Auto-generated status map for WASM subprims based on:

- `build/wasm32/subprims-map.json` (canonical symbol list)
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

- clean: 9
- validation only: 123

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
| `_SPbind` | guarded | validation only | 5 | bounds, null/invalid, tcr-null | wasm_positive_fixnum_or_trap, wasm_symbol_or_trap, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_positive_fixnum_or_trap: count <= 0` - `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPbind_interrupt_level` | guarded | validation only | 2 | null/invalid, tcr-null | wasm_bind_interrupt_level | bounds, null/invalid | `wasm_bind_interrupt_level: (unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)limit_count` - `wasm_bind_interrupt_level: binding_slots == NULL` - `wasm_bind_interrupt_level: stack_ptr == NULL` | - | bounds, null/invalid, tcr-null | - | no | high |
| `_SPbind_interrupt_level_0` | guarded | validation only | 2 | null/invalid, tcr-null | wasm_bind_interrupt_level | bounds, null/invalid | `wasm_bind_interrupt_level: (unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)limit_count` - `wasm_bind_interrupt_level: binding_slots == NULL` - `wasm_bind_interrupt_level: stack_ptr == NULL` | - | bounds, null/invalid, tcr-null | - | no | high |
| `_SPbind_interrupt_level_m1` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_bind_interrupt_level | bounds, null/invalid | `wasm_bind_interrupt_level: (unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)limit_count` - `wasm_bind_interrupt_level: binding_slots == NULL` - `wasm_bind_interrupt_level: stack_ptr == NULL` | - | bounds, null/invalid, tcr-null | - | no | high |
| `_SPbind_nil` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPbind_self` | guarded | validation only | 5 | bounds, null/invalid, tcr-null | wasm_positive_fixnum_or_trap, wasm_symbol_or_trap, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_positive_fixnum_or_trap: count <= 0` - `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPbind_self_boundp_check` | guarded | validation only | 5 | bounds, null/invalid, tcr-null | wasm_positive_fixnum_or_trap, wasm_symbol_or_trap, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_positive_fixnum_or_trap: count <= 0` - `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
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
| `_SPcall_closure` | guarded | validation only | 5 | bounds, null/invalid, tcr-null, type/subtag | wasm_unbox_fixnum_or_trap, wasm_vpush_argregs | fixnum, null/invalid, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vpush_argregs: tag_of(raw) != tag_fixnum` - `wasm_vpush_argregs: stack_ptr == NULL` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPcheck_fpu_exception` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPconslist` | guarded | validation only | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_alloc_cons_or_trap | null/invalid, tcr-null | `wasm_alloc_cons_or_trap: tcr == NULL` - `wasm_alloc_cons_or_trap: obj == (LispObj)nil_value` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPconslist_star` | guarded | validation only | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_alloc_cons_or_trap | null/invalid, tcr-null | `wasm_alloc_cons_or_trap: tcr == NULL` - `wasm_alloc_cons_or_trap: obj == (LispObj)nil_value` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPdebind` | guarded | validation only | 4 | bounds, null/invalid, tcr-null, type/subtag | - | - | - | - | bounds, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPdefault_optional_args` | guarded | validation only | 5 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_vpush_argregs | fixnum, null/invalid, type/subtag | `wasm_vpush_argregs: tag_of(raw) != tag_fixnum` - `wasm_vpush_argregs: stack_ptr == NULL` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPdiscard_stack_object` | guarded | validation only | 2 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPeabi_callback` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_signal_capability_unavailable | null/invalid | `wasm_signal_capability_unavailable: stack_ptr == NULL` | - | null/invalid, tcr-null | - | no | high |
| `_SPeabi_ff_call_simple` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_signal_capability_unavailable | null/invalid | `wasm_signal_capability_unavailable: stack_ptr == NULL` | - | null/invalid, tcr-null | - | no | high |
| `_SPeabi_ff_callhf` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_signal_capability_unavailable | null/invalid | `wasm_signal_capability_unavailable: stack_ptr == NULL` | - | null/invalid, tcr-null | - | no | high |
| `_SPfitvals` | guarded | validation only | 5 | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | - | - | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPfix_nfn_entrypoint` | guarded | validation only | 2 | null/invalid, tcr-null, type/subtag | - | - | - | - | null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPfix_overflow` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | yes | high |
| `_SPfuncall` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_sync_arg_regs_from_vsp | null/invalid | `wasm_sync_arg_regs_from_vsp: stack_ptr == NULL` | - | null/invalid, tcr-null | 0 | no | high |
| `_SPgets32` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPgets64` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPgetu32` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPgetu64` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPgvector` | guarded | validation only | 6 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPgvset` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_gvector_set_or_trap, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_gvector_set_or_trap: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_gvector_set_or_trap: (header_subtag(header) & fulltagmask) != fulltag_nodeheader` - `wasm_gvector_set_or_trap: index >= count` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPheap_cons_rest_arg` | guarded | validation only | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_alloc_cons_or_trap | null/invalid, tcr-null | `wasm_alloc_cons_or_trap: tcr == NULL` - `wasm_alloc_cons_or_trap: obj == (LispObj)nil_value` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPheap_rest_arg` | guarded | validation only | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_alloc_cons_or_trap, wasm_vpush_argregs | fixnum, null/invalid, tcr-null, type/subtag | `wasm_alloc_cons_or_trap: tcr == NULL` - `wasm_alloc_cons_or_trap: obj == (LispObj)nil_value` - `wasm_vpush_argregs: tag_of(raw) != tag_fixnum` - `wasm_vpush_argregs: stack_ptr == NULL` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPinteger_sign` | guarded | validation only | 2 | bounds, null/invalid, tcr-null | - | - | - | - | bounds, null/invalid, tcr-null | - | no | high |
| `_SPjmpsym` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPkeyword_bind` | guarded | validation only | 6 | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | - | - | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPksignalerr` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPmakes32` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | yes | high |
| `_SPmakes64` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPmakestackblock` | guarded | validation only | 2 | bounds, null/invalid, tcr-null | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmakestackblock0` | guarded | validation only | 2 | bounds, null/invalid, tcr-null | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmakestacklist` | guarded | validation only | 2 | bounds, null/invalid, tcr-null | wasm_alloc_cons_or_trap, wasm_unbox_fixnum_or_trap | fixnum, null/invalid, tcr-null, type/subtag | `wasm_alloc_cons_or_trap: tcr == NULL` - `wasm_alloc_cons_or_trap: obj == (LispObj)nil_value` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmakeu32` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_alloc_bignum_or_trap | null/invalid | `wasm_alloc_bignum_or_trap: obj == (LispObj)nil_value` | - | null/invalid, tcr-null | - | no | high |
| `_SPmakeu64` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_alloc_bignum_or_trap | null/invalid | `wasm_alloc_bignum_or_trap: obj == (LispObj)nil_value` | - | null/invalid, tcr-null | - | no | high |
| `_SPmisc_alloc` | guarded | validation only | 5 | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | - | - | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmisc_alloc_init` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPmisc_ref` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_misc_ref_dispatch, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_misc_ref_dispatch: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_misc_ref_dispatch: index >= count` - `wasm_misc_ref_dispatch: (subtag & fulltagmask) != fulltag_immheader` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmisc_set` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_misc_set_dispatch, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_misc_set_dispatch: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_misc_set_dispatch: index >= count` - `wasm_misc_set_dispatch: (subtag & fulltagmask) != fulltag_immheader` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmkcatch1v` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | 1 | no | high |
| `_SPmkcatchmv` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | 1 | no | high |
| `_SPmkstackv` | guarded | validation only | 5 | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | - | - | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmkunwind` | guarded | validation only | 2 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPmvpass` | guarded | validation only | 3 | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | - | - | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPmvpasssym` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPmvslide` | guarded | validation only | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | - | - | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPnthrow1value` | guarded | validation only | 6 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_push_value_set, wasm_unbind_to, wasm_unbox_fixnum_or_trap | bounds, fixnum, null/invalid, type/subtag | `wasm_push_value_set: count < 0` - `wasm_unbind_to: binding_slots == NULL` - `wasm_unbind_to: current_binding == NULL` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | 0 | no | high |
| `_SPnthrowvalues` | guarded | validation only | 8 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_push_value_set, wasm_sync_arg_regs_from_vsp, wasm_unbind_to, wasm_unbox_fixnum_or_trap | bounds, fixnum, null/invalid, type/subtag | `wasm_push_value_set: count < 0` - `wasm_sync_arg_regs_from_vsp: stack_ptr == NULL` - `wasm_unbind_to: binding_slots == NULL` - `wasm_unbind_to: current_binding == NULL` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | 1 | no | high |
| `_SPnthvalue` | guarded | validation only | 5 | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | - | - | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPnvalret` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPopt_supplied_p` | guarded | validation only | 5 | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | - | - | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPpopj` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPprogvrestore` | guarded | validation only | 4 | null/invalid, tcr-null | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPprogvsave` | guarded | validation only | 6 | bounds, null/invalid, tcr-null, type/subtag | wasm_positive_fixnum_or_trap, wasm_symbol_or_trap | bounds, type/subtag | `wasm_positive_fixnum_or_trap: count <= 0` - `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | - | bounds, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPrecover_values` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPreq_heap_rest_arg` | guarded | validation only | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_alloc_cons_or_trap, wasm_vpush_argregs | fixnum, null/invalid, tcr-null, type/subtag | `wasm_alloc_cons_or_trap: tcr == NULL` - `wasm_alloc_cons_or_trap: obj == (LispObj)nil_value` - `wasm_vpush_argregs: tag_of(raw) != tag_fixnum` - `wasm_vpush_argregs: stack_ptr == NULL` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPreq_stack_rest_arg` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_vpush_argregs | fixnum, null/invalid, type/subtag | `wasm_vpush_argregs: tag_of(raw) != tag_fixnum` - `wasm_vpush_argregs: stack_ptr == NULL` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPreset` | guarded | validation only | 2 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPrplaca` | guarded | validation only | 2 | null/invalid, tcr-null, type/subtag | - | - | - | - | null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPrplacd` | guarded | validation only | 2 | null/invalid, tcr-null, type/subtag | - | - | - | - | null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPsave_values` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_push_value_set | bounds | `wasm_push_value_set: count < 0` | - | bounds, null/invalid, tcr-null | - | no | high |
| `_SPsdiv32` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPset_hash_key` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_gvector_set_or_trap, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_gvector_set_or_trap: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_gvector_set_or_trap: (header_subtag(header) & fulltagmask) != fulltag_nodeheader` - `wasm_gvector_set_or_trap: index >= count` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPset_hash_key_conditional` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPsetqsym` | guarded | validation only | 2 | fixnum, null/invalid, tcr-null, type/subtag | wasm_symbol_or_trap | type/subtag | `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPspecref` | guarded | validation only | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_symbol_or_trap | type/subtag | `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPspecrefcheck` | guarded | validation only | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_symbol_or_trap | type/subtag | `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPspecset` | guarded | validation only | 5 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_symbol_or_trap | type/subtag | `wasm_symbol_or_trap: fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPspread_lexprz` | guarded | validation only | 5 | bounds, null/invalid, tcr-null | wasm_unbox_fixnum_or_trap, wasm_vpop_argregs | fixnum, null/invalid, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vpop_argregs: tag_of(raw) != tag_fixnum` - `wasm_vpop_argregs: stack_ptr == NULL` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPspreadargz` | guarded | validation only | 3 | bounds, null/invalid, tcr-null | wasm_unbox_fixnum_or_trap, wasm_vpop_argregs | fixnum, null/invalid, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` - `wasm_vpop_argregs: tag_of(raw) != tag_fixnum` - `wasm_vpop_argregs: stack_ptr == NULL` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPstack_cons_rest_arg` | guarded | validation only | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | - | - | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPstack_misc_alloc` | guarded | validation only | 7 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPstack_misc_alloc_init` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPstack_rest_arg` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_vpush_argregs | fixnum, null/invalid, type/subtag | `wasm_vpush_argregs: tag_of(raw) != tag_fixnum` - `wasm_vpush_argregs: stack_ptr == NULL` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPstkconslist` | guarded | validation only | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | - | - | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPstkconslist_star` | guarded | validation only | 4 | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | - | - | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPstkgvector` | guarded | validation only | 7 | bounds, fixnum, null/invalid, tcr-null, type/subtag | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPstore_node_conditional` | guarded | validation only | 2 | null/invalid, tcr-null | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPsubtag_misc_ref` | guarded | validation only | 4 | null/invalid, tcr-null, type/subtag | wasm_misc_ref_dispatch, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_misc_ref_dispatch: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_misc_ref_dispatch: index >= count` - `wasm_misc_ref_dispatch: (subtag & fulltagmask) != fulltag_immheader` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPsubtag_misc_set` | guarded | validation only | 4 | null/invalid, tcr-null, type/subtag | wasm_misc_set_dispatch, wasm_unbox_fixnum_or_trap | bounds, fixnum, type/subtag | `wasm_misc_set_dispatch: index < 0 || fulltag_of(obj) != fulltag_misc` - `wasm_misc_set_dispatch: index >= count` - `wasm_misc_set_dispatch: (subtag & fulltagmask) != fulltag_immheader` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPtcallnfngen` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPtcallnfnslide` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPtcallsymgen` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPtcallsymslide` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPtfuncallgen` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPtfuncallslide` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPthrow` | guarded | validation only | 3 | bounds, null/invalid, tcr-null | wasm_sync_arg_regs_from_vsp, wasm_unbox_fixnum_or_trap | fixnum, null/invalid, type/subtag | `wasm_sync_arg_regs_from_vsp: stack_ptr == NULL` - `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | 1 | no | high |
| `_SPudiv32` | guarded | validation only | 2 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPudiv64by32` | guarded | validation only | 2 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPunbind` | guarded | validation only | 2 | null/invalid, tcr-null | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPunbind_interrupt_level` | guarded | validation only | 2 | null/invalid, tcr-null | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPunbind_n` | guarded | validation only | 4 | bounds, null/invalid, tcr-null | wasm_unbox_fixnum_or_trap | fixnum, type/subtag | `wasm_unbox_fixnum_or_trap: tag_of(value) != tag_fixnum` | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPunbind_to` | guarded | validation only | 1 | null/invalid, tcr-null | wasm_unbind_to | null/invalid | `wasm_unbind_to: binding_slots == NULL` - `wasm_unbind_to: current_binding == NULL` | - | null/invalid, tcr-null | - | no | high |
| `_SPunused1` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPunused2` | clean | clean | 0 | - | - | - | - | - | - | - | no | high |
| `_SPvalues` | guarded | validation only | 3 | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | - | - | - | bounds, fixnum, null/invalid, tcr-null, type/subtag | - | no | high |
| `_SPwasm_macro_apply_stub` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |
| `_SPwasm_udf_stub` | guarded | validation only | 1 | null/invalid, tcr-null | - | - | - | - | null/invalid, tcr-null | - | no | high |

---

## Direct Trap Site Details

| Subprim | Trap Line | Cond Line | Condition | Tags |
| --- | --- | --- | --- | --- |
| `_SPadd_values` | 2024 | 2023 | `tcr == NULL` | null/invalid, tcr-null |
| `_SParef2` | 4011 | 4010 | `tcr == NULL` | null/invalid, tcr-null |
| `_SParef3` | 4098 | 4097 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPaset2` | 4205 | 4204 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPaset3` | 4293 | 4292 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPatomic_incf_node` | 3625 | 3624 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind` | 5123 | 5122 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind` | 5139 | 5138 | `index < 0` | bounds |
| `_SPbind` | 5145 | 5144 | `(unsigned)index >= (unsigned)limit_count` | bounds |
| `_SPbind` | 5150 | 5149 | `binding_slots == NULL` | null/invalid |
| `_SPbind` | 5156 | 5155 | `stack_ptr == NULL` | null/invalid |
| `_SPbind_interrupt_level` | 5345 | 5344 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_interrupt_level` | 5355 | 5354 | `binding_slots == NULL` | null/invalid |
| `_SPbind_interrupt_level_0` | 5311 | 5310 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_interrupt_level_0` | 5316 | 5315 | `binding_slots == NULL` | null/invalid |
| `_SPbind_interrupt_level_m1` | 5333 | 5332 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_nil` | 5232 | 5231 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_self` | 5175 | 5174 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_self` | 5191 | 5190 | `index < 0` | bounds |
| `_SPbind_self` | 5197 | 5196 | `(unsigned)index >= (unsigned)limit_count` | bounds |
| `_SPbind_self` | 5202 | 5201 | `binding_slots == NULL` | null/invalid |
| `_SPbind_self` | 5213 | 5212 | `stack_ptr == NULL` | null/invalid |
| `_SPbind_self_boundp_check` | 5247 | 5246 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbind_self_boundp_check` | 5263 | 5262 | `index < 0` | bounds |
| `_SPbind_self_boundp_check` | 5269 | 5268 | `(unsigned)index >= (unsigned)limit_count` | bounds |
| `_SPbind_self_boundp_check` | 5274 | 5273 | `binding_slots == NULL` | null/invalid |
| `_SPbind_self_boundp_check` | 5292 | 5291 | `stack_ptr == NULL` | null/invalid |
| `_SPbuiltin_aref1` | 3574 | 3573 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_aset1` | 3599 | 3598 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_ash` | 3487 | 3486 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_assq` | 3395 | 3394 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_div` | 3213 | 3212 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_eq` | 3225 | 3224 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_eql` | 3345 | 3344 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_ge` | 3285 | 3284 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_gt` | 3265 | 3264 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_le` | 3325 | 3324 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_length` | 3371 | 3370 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logand` | 3466 | 3465 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logbitp` | 3419 | 3418 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logior` | 3445 | 3444 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_logxor` | 3553 | 3552 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_lt` | 3305 | 3304 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_memq` | 3407 | 3406 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_minus` | 3171 | 3170 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_ne` | 3245 | 3244 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_negate` | 3533 | 3532 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_plus` | 3150 | 3149 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_seqtype` | 3383 | 3382 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPbuiltin_times` | 3192 | 3191 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPcall_closure` | 5653 | 5652 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPcall_closure` | 5658 | 5657 | `fulltag_of(closure) != fulltag_misc || header_subtag(header_of(closure)) != subtag_function` | type/subtag |
| `_SPcall_closure` | 5663 | 5662 | `argc < 0` | bounds |
| `_SPcall_closure` | 5668 | 5667 | `stack_ptr == NULL` | null/invalid |
| `_SPcall_closure` | 5686 | 5685 | `stack_ptr == NULL` | null/invalid |
| `_SPconslist` | 3769 | 3768 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPconslist` | 3774 | 3773 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPconslist` | 3778 | 3777 | `count < 0` | bounds |
| `_SPconslist` | 3783 | 3782 | `stack_ptr == NULL` | null/invalid |
| `_SPconslist_star` | 3805 | 3804 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPconslist_star` | 3810 | 3809 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPconslist_star` | 3814 | 3813 | `count < 0` | bounds |
| `_SPconslist_star` | 3819 | 3818 | `stack_ptr == NULL` | null/invalid |
| `_SPdebind` | 5882 | 5881 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPdebind` | 5888 | 5887 | `stack_ptr == NULL` | null/invalid |
| `_SPdebind` | 6041 | 6040 | `fulltag_of(keyvec) != fulltag_misc` | type/subtag |
| `_SPdebind` | 6045 | 6044 | `keyvec_len < 0 || keyvec_len > 256` | bounds |
| `_SPdefault_optional_args` | 2354 | 2353 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPdefault_optional_args` | 2359 | 2358 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPdefault_optional_args` | 2364 | 2363 | `tag_of(raw_limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPdefault_optional_args` | 2370 | 2369 | `nargs_count < 0 || limit < 0` | bounds |
| `_SPdefault_optional_args` | 2382 | 2381 | `stack_ptr == NULL` | null/invalid |
| `_SPdiscard_stack_object` | 4450 | 4449 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPdiscard_stack_object` | 4455 | 4454 | `sp == NULL` | null/invalid |
| `_SPeabi_callback` | 6150 | 6149 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPeabi_ff_call_simple` | 6128 | 6127 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPeabi_ff_callhf` | 6139 | 6138 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfitvals` | 2242 | 2241 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfitvals` | 2247 | 2246 | `tag_of(raw_desired) != tag_fixnum` | fixnum, type/subtag |
| `_SPfitvals` | 2252 | 2251 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPfitvals` | 2258 | 2257 | `desired_count < 0 || current_count < 0` | bounds |
| `_SPfitvals` | 2263 | 2262 | `stack_ptr == NULL` | null/invalid |
| `_SPfix_nfn_entrypoint` | 2071 | 2070 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfix_nfn_entrypoint` | 2076 | 2075 | `fulltag_of(fn_value) != fulltag_misc || header_subtag(header_of(fn_value)) != subtag_function` | type/subtag |
| `_SPfix_overflow` | 6215 | 6214 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPfuncall` | 2094 | 2093 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgets32` | 4709 | 4708 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgets64` | 4865 | 4864 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgetu32` | 4733 | 4732 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgetu64` | 4801 | 4800 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgvector` | 2862 | 2861 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPgvector` | 2867 | 2866 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPgvector` | 2871 | 2870 | `count <= 0` | bounds |
| `_SPgvector` | 2876 | 2875 | `stack_ptr == NULL` | null/invalid |
| `_SPgvector` | 2882 | 2881 | `subtag < 0` | type/subtag |
| `_SPgvector` | 2888 | 2887 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPgvset` | 3699 | 3698 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPheap_cons_rest_arg` | 2518 | 2517 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPheap_cons_rest_arg` | 2524 | 2523 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_required) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPheap_cons_rest_arg` | 2528 | 2527 | `count < 0` | bounds |
| `_SPheap_cons_rest_arg` | 2533 | 2532 | `stack_ptr == NULL` | null/invalid |
| `_SPheap_rest_arg` | 2441 | 2440 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPheap_rest_arg` | 2446 | 2445 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPheap_rest_arg` | 2450 | 2449 | `count < 0` | bounds |
| `_SPheap_rest_arg` | 2457 | 2456 | `stack_ptr == NULL` | null/invalid |
| `_SPinteger_sign` | 2046 | 2045 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPinteger_sign` | 2058 | 2057 | `!wasm_bignum_info(value, &count, &digits) || count <= 0` | bounds |
| `_SPjmpsym` | 2133 | 2132 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPkeyword_bind` | 5741 | 5740 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPkeyword_bind` | 5748 | 5747 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_prev) != tag_fixnum || tag_of(keyword_flags) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPkeyword_bind` | 5754 | 5753 | `nargs_count < 0 || prev_count < 0` | bounds |
| `_SPkeyword_bind` | 5775 | 5774 | `fulltag_of(keyvec) != fulltag_misc` | type/subtag |
| `_SPkeyword_bind` | 5779 | 5778 | `keyvec_len < 0 || keyvec_len > 256` | bounds |
| `_SPkeyword_bind` | 5792 | 5791 | `stack_ptr == NULL` | null/invalid |
| `_SPksignalerr` | 4469 | 4468 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakes32` | 4597 | 4596 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakes64` | 4690 | 4689 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestackblock` | 3020 | 3019 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestackblock` | 3026 | 3025 | `count < 0` | bounds |
| `_SPmakestackblock0` | 3047 | 3046 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestackblock0` | 3053 | 3052 | `count < 0` | bounds |
| `_SPmakestacklist` | 2973 | 2972 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakestacklist` | 2979 | 2978 | `count < 0` | bounds |
| `_SPmakeu32` | 4612 | 4611 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmakeu64` | 4642 | 4641 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_alloc` | 2700 | 2697 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_alloc` | 2707 | 2704 | `tag_of(subtag_val) != tag_fixnum` | fixnum, type/subtag |
| `_SPmisc_alloc` | 2713 | 2710 | `tag_of(count_val) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmisc_alloc` | 2728 | 2725 | `subtag_tag != fulltag_nodeheader && subtag_tag != fulltag_immheader` | type/subtag |
| `_SPmisc_alloc` | 2735 | 2732 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPmisc_alloc_init` | 2747 | 2746 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_ref` | 2795 | 2794 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmisc_set` | 3104 | 3103 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkcatch1v` | 1614 | 1613 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkcatchmv` | 1640 | 1639 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkstackv` | 3962 | 3961 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkstackv` | 3967 | 3966 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmkstackv` | 3971 | 3970 | `count < 0` | bounds |
| `_SPmkstackv` | 3976 | 3975 | `stack_ptr == NULL` | null/invalid |
| `_SPmkstackv` | 3989 | 3988 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPmkunwind` | 1666 | 1665 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmkunwind` | 1682 | 1681 | `target_link == 0 || target_link == (LispObj)nil_value` | null/invalid |
| `_SPmvpass` | 2183 | 2182 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmvpass` | 2194 | 2193 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmvpass` | 2204 | 2203 | `stack_ptr == NULL` | null/invalid |
| `_SPmvpasssym` | 2684 | 2683 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmvslide` | 2646 | 2645 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPmvslide` | 2651 | 2650 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPmvslide` | 2656 | 2655 | `count < 0` | bounds |
| `_SPmvslide` | 2661 | 2660 | `stack_ptr == NULL` | null/invalid |
| `_SPnthrow1value` | 1694 | 1693 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPnthrow1value` | 1709 | 1708 | `target_link == 0 || target_link == (LispObj)nil_value` | null/invalid |
| `_SPnthrow1value` | 1727 | 1726 | `tag_of(cleanup) != tag_fixnum` | fixnum, type/subtag |
| `_SPnthrow1value` | 1732 | 1731 | `count < 0` | bounds |
| `_SPnthrow1value` | 1741 | 1740 | `saved_stack_ptr == NULL` | null/invalid |
| `_SPnthrow1value` | 1765 | 1764 | `saved_stack_ptr == NULL` | null/invalid |
| `_SPnthrowvalues` | 1784 | 1783 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPnthrowvalues` | 1797 | 1796 | `target_link == 0 || target_link == (LispObj)nil_value` | null/invalid |
| `_SPnthrowvalues` | 1815 | 1814 | `tag_of(cleanup) != tag_fixnum` | fixnum, type/subtag |
| `_SPnthrowvalues` | 1820 | 1819 | `count < 0` | bounds |
| `_SPnthrowvalues` | 1829 | 1828 | `saved_stack_ptr == NULL` | null/invalid |
| `_SPnthrowvalues` | 1853 | 1852 | `count < 0` | bounds |
| `_SPnthrowvalues` | 1857 | 1856 | `stack_ptr == NULL` | null/invalid |
| `_SPnthrowvalues` | 1862 | 1861 | `dest == NULL` | null/invalid |
| `_SPnthvalue` | 2311 | 2310 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPnthvalue` | 2316 | 2315 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPnthvalue` | 2321 | 2320 | `count < 0` | bounds |
| `_SPnthvalue` | 2326 | 2325 | `stack_ptr == NULL` | null/invalid |
| `_SPnthvalue` | 2331 | 2330 | `tag_of(raw_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPopt_supplied_p` | 2399 | 2398 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPopt_supplied_p` | 2404 | 2403 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPopt_supplied_p` | 2409 | 2408 | `tag_of(raw_opt) != tag_fixnum` | fixnum, type/subtag |
| `_SPopt_supplied_p` | 2415 | 2414 | `nargs_count < 0 || opt_count < 0` | bounds |
| `_SPopt_supplied_p` | 2420 | 2419 | `stack_ptr == NULL` | null/invalid |
| `_SPpopj` | 4586 | 4585 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPprogvrestore` | 5616 | 5615 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPprogvrestore` | 5621 | 5620 | `binding_slots == NULL` | null/invalid |
| `_SPprogvrestore` | 5631 | 5630 | `saved_stack_ptr == NULL` | null/invalid |
| `_SPprogvrestore` | 5644 | 5630 | `saved_stack_ptr == NULL` | null/invalid |
| `_SPprogvsave` | 5529 | 5528 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPprogvsave` | 5543 | 5542 | `binding_slots == NULL` | null/invalid |
| `_SPprogvsave` | 5550 | 5549 | `stack_ptr == NULL` | null/invalid |
| `_SPprogvsave` | 5567 | 5566 | `tag_of(sym_list) != tag_list` | type/subtag |
| `_SPprogvsave` | 5577 | 5576 | `(unsigned)index >= (unsigned)limit_count` | bounds |
| `_SPprogvsave` | 5585 | 5584 | `tag_of(val_list) != tag_list` | type/subtag |
| `_SPrecover_values` | 2035 | 2034 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPreq_heap_rest_arg` | 2479 | 2478 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPreq_heap_rest_arg` | 2485 | 2484 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_required) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPreq_heap_rest_arg` | 2489 | 2488 | `count < 0` | bounds |
| `_SPreq_heap_rest_arg` | 2496 | 2495 | `stack_ptr == NULL` | null/invalid |
| `_SPreq_stack_rest_arg` | 2569 | 2568 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPreset` | 4550 | 4549 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPreset` | 4555 | 4554 | `stack_ptr == NULL` | null/invalid |
| `_SPrplaca` | 3646 | 3645 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPrplaca` | 3651 | 3650 | `fulltag_of(cell) != fulltag_cons` | type/subtag |
| `_SPrplacd` | 3663 | 3662 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPrplacd` | 3668 | 3667 | `fulltag_of(cell) != fulltag_cons` | type/subtag |
| `_SPsave_values` | 2013 | 2012 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsdiv32` | 6182 | 6181 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPset_hash_key` | 3714 | 3713 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsetqsym` | 5043 | 5042 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsetqsym` | 5051 | 5050 | `tag_of(flags) != tag_fixnum` | fixnum, type/subtag |
| `_SPspecref` | 4905 | 4904 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspecref` | 4912 | 4911 | `tag_of(binding_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecref` | 4917 | 4916 | `tag_of(limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecref` | 4922 | 4921 | `binding_slots == NULL` | null/invalid |
| `_SPspecrefcheck` | 4946 | 4945 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspecrefcheck` | 4953 | 4952 | `tag_of(binding_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecrefcheck` | 4958 | 4957 | `tag_of(limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecrefcheck` | 4963 | 4962 | `binding_slots == NULL` | null/invalid |
| `_SPspecset` | 4995 | 4994 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspecset` | 5003 | 5002 | `tag_of(binding_index) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecset` | 5008 | 5007 | `tag_of(limit) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPspecset` | 5013 | 5012 | `binding_slots == NULL` | null/invalid |
| `_SPspecset` | 5019 | 5018 | `limit_count < 0` | bounds |
| `_SPspread_lexprz` | 4401 | 4400 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspread_lexprz` | 4406 | 4405 | `lexpr == NULL` | null/invalid |
| `_SPspread_lexprz` | 4412 | 4411 | `count < 0` | bounds |
| `_SPspread_lexprz` | 4417 | 4416 | `orig_count < 0` | bounds |
| `_SPspread_lexprz` | 4422 | 4421 | `stack_ptr == NULL` | null/invalid |
| `_SPspreadargz` | 5073 | 5072 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPspreadargz` | 5080 | 5079 | `stack_ptr == NULL` | null/invalid |
| `_SPspreadargz` | 5085 | 5084 | `orig_count < 0` | bounds |
| `_SPstack_cons_rest_arg` | 2582 | 2581 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstack_cons_rest_arg` | 2588 | 2587 | `tag_of(raw_nargs) != tag_fixnum || tag_of(raw_required) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstack_cons_rest_arg` | 2592 | 2591 | `count < 0` | bounds |
| `_SPstack_cons_rest_arg` | 2597 | 2596 | `stack_ptr == NULL` | null/invalid |
| `_SPstack_misc_alloc` | 2811 | 2810 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstack_misc_alloc` | 2816 | 2815 | `tag_of(raw_count) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstack_misc_alloc` | 2820 | 2819 | `count < 0` | bounds |
| `_SPstack_misc_alloc` | 2826 | 2825 | `subtag < 0` | type/subtag |
| `_SPstack_misc_alloc` | 2834 | 2833 | `words > (SIZE_MAX / node_size)` | bounds |
| `_SPstack_misc_alloc` | 2839 | 2838 | `!wasm_ivector_total_bytes((unsigned)subtag, count, &bytes)` | type/subtag |
| `_SPstack_misc_alloc` | 2842 | 2838 | `!wasm_ivector_total_bytes((unsigned)subtag, count, &bytes)` | type/subtag |
| `_SPstack_misc_alloc_init` | 2771 | 2770 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstack_rest_arg` | 2555 | 2554 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkconslist` | 3852 | 3851 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkconslist` | 3857 | 3856 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstkconslist` | 3861 | 3860 | `count < 0` | bounds |
| `_SPstkconslist` | 3880 | 3879 | `stack_ptr == NULL` | null/invalid |
| `_SPstkconslist_star` | 3907 | 3906 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkconslist_star` | 3912 | 3911 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstkconslist_star` | 3916 | 3915 | `count < 0` | bounds |
| `_SPstkconslist_star` | 3936 | 3935 | `stack_ptr == NULL` | null/invalid |
| `_SPstkgvector` | 2910 | 2909 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstkgvector` | 2915 | 2914 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPstkgvector` | 2919 | 2918 | `count <= 0` | bounds |
| `_SPstkgvector` | 2924 | 2923 | `stack_ptr == NULL` | null/invalid |
| `_SPstkgvector` | 2930 | 2929 | `((unsigned)subtag & fulltagmask) != fulltag_nodeheader` | type/subtag |
| `_SPstkgvector` | 2939 | 2938 | `words > (SIZE_MAX / node_size)` | bounds |
| `_SPstkgvector` | 2950 | 2949 | `obj == (LispObj)nil_value` | null/invalid |
| `_SPstore_node_conditional` | 3729 | 3728 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPstore_node_conditional` | 3734 | 3733 | `stack_ptr == NULL` | null/invalid |
| `_SPsubtag_misc_ref` | 3076 | 3075 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsubtag_misc_ref` | 3082 | 3081 | `subtag < 0` | type/subtag |
| `_SPsubtag_misc_ref` | 3087 | 3086 | `fulltag_of(obj) != fulltag_misc` | type/subtag |
| `_SPsubtag_misc_ref` | 3090 | 3089 | `header_subtag(header_of(obj)) != (unsigned)subtag` | type/subtag |
| `_SPsubtag_misc_set` | 3121 | 3120 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPsubtag_misc_set` | 3127 | 3126 | `subtag < 0` | type/subtag |
| `_SPsubtag_misc_set` | 3132 | 3131 | `fulltag_of(obj) != fulltag_misc` | type/subtag |
| `_SPsubtag_misc_set` | 3135 | 3134 | `header_subtag(header_of(obj)) != (unsigned)subtag` | type/subtag |
| `_SPtcallsymgen` | 2145 | 2144 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPtcallsymslide` | 2157 | 2156 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPthrow` | 1953 | 1952 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPthrow` | 1958 | 1957 | `count < 0` | bounds |
| `_SPthrow` | 1963 | 1962 | `stack_ptr == NULL` | null/invalid |
| `_SPudiv32` | 6161 | 6160 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPudiv32` | 6166 | 6165 | `denom == 0` | null/invalid |
| `_SPudiv64by32` | 4776 | 4775 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPudiv64by32` | 4781 | 4780 | `denom == 0` | null/invalid |
| `_SPunbind` | 5402 | 5401 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPunbind` | 5408 | 5407 | `current_binding == NULL || binding_slots == NULL` | null/invalid |
| `_SPunbind_interrupt_level` | 5372 | 5371 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPunbind_interrupt_level` | 5378 | 5377 | `current_binding == NULL || binding_slots == NULL` | null/invalid |
| `_SPunbind_n` | 5480 | 5479 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPunbind_n` | 5485 | 5484 | `count < 0` | bounds |
| `_SPunbind_n` | 5494 | 5493 | `current_binding == NULL || binding_slots == NULL` | null/invalid |
| `_SPunbind_n` | 5499 | 5498 | `current_binding == NULL` | null/invalid |
| `_SPunbind_to` | 5516 | 5515 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPvalues` | 2215 | 2214 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPvalues` | 2220 | 2219 | `tag_of(raw_nargs) != tag_fixnum` | bounds, fixnum, type/subtag |
| `_SPvalues` | 2231 | 2230 | `stack_ptr == NULL` | null/invalid |
| `_SPwasm_macro_apply_stub` | 4518 | 4517 | `tcr == NULL` | null/invalid, tcr-null |
| `_SPwasm_udf_stub` | 4534 | 4533 | `tcr == NULL` | null/invalid, tcr-null |

---

## Helper Trap Site Details

| Helper | Trap Line | Cond Line | Condition | Tags |
| --- | --- | --- | --- | --- |
| `__attribute__` | 1614 | 1613 | `tcr == NULL` | null/invalid, tcr-null |
| `wasm_alloc_bignum_or_trap` | 832 | 831 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_complex_double_float_from_bits` | 1055 | 1054 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_complex_single_float_from_bits` | 1042 | 1041 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_cons_or_trap` | 521 | 520 | `tcr == NULL` | null/invalid, tcr-null |
| `wasm_alloc_cons_or_trap` | 525 | 524 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_double_float_from_bits` | 1029 | 1028 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_alloc_single_float_from_bits` | 1017 | 1016 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_arrayH_data_or_trap` | 1370 | 1369 | `fulltag_of(array) != fulltag_misc` | type/subtag |
| `wasm_arrayH_data_or_trap` | 1373 | 1372 | `header_subtag(header_of(array)) != subtag_arrayH` | type/subtag |
| `wasm_arrayH_data_or_trap` | 1379 | 1378 | `rank != expected_rank` | unknown |
| `wasm_array_data_vector_or_trap` | 1390 | 1389 | `fulltag_of(current) != fulltag_misc` | type/subtag |
| `wasm_bind_interrupt_level` | 5426 | 5425 | `(unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)limit_count` | bounds |
| `wasm_bind_interrupt_level` | 5431 | 5430 | `binding_slots == NULL` | null/invalid |
| `wasm_bind_interrupt_level` | 5436 | 5435 | `stack_ptr == NULL` | null/invalid |
| `wasm_builtin_function` | 504 | 503 | `vec == (LispObj)nil_value` | null/invalid |
| `wasm_cached_symbol_named` | 313 | 312 | `sym == (LispObj)NULL` | null/invalid |
| `wasm_gvector_set_or_trap` | 3678 | 3677 | `index < 0 || fulltag_of(obj) != fulltag_misc` | bounds, type/subtag |
| `wasm_gvector_set_or_trap` | 3682 | 3681 | `(header_subtag(header) & fulltagmask) != fulltag_nodeheader` | type/subtag |
| `wasm_gvector_set_or_trap` | 3686 | 3685 | `index >= count` | bounds |
| `wasm_make_simple_base_string` | 201 | 200 | `tcr == NULL || bytes == NULL` | null/invalid, tcr-null |
| `wasm_make_simple_base_string` | 206 | 205 | `len > ((size_t)INT32_MAX)` | bounds |
| `wasm_make_simple_base_string` | 211 | 210 | `obj == (LispObj)nil_value` | null/invalid |
| `wasm_misc_ref_dispatch` | 1069 | 1068 | `index < 0 || fulltag_of(obj) != fulltag_misc` | bounds, type/subtag |
| `wasm_misc_ref_dispatch` | 1076 | 1075 | `index >= count` | bounds |
| `wasm_misc_ref_dispatch` | 1085 | 1084 | `(subtag & fulltagmask) != fulltag_immheader` | type/subtag |
| `wasm_misc_set_dispatch` | 1175 | 1174 | `index < 0 || fulltag_of(obj) != fulltag_misc` | bounds, type/subtag |
| `wasm_misc_set_dispatch` | 1182 | 1181 | `index >= count` | bounds |
| `wasm_misc_set_dispatch` | 1192 | 1191 | `(subtag & fulltagmask) != fulltag_immheader` | type/subtag |
| `wasm_positive_fixnum_or_trap` | 815 | 814 | `count <= 0` | bounds |
| `wasm_push_value_set` | 1446 | 1445 | `count < 0` | bounds |
| `wasm_signal_capability_unavailable` | 360 | 359 | `stack_ptr == NULL` | null/invalid |
| `wasm_signal_errdisp_2` | 465 | 464 | `tcr == NULL` | null/invalid, tcr-null |
| `wasm_symbol_or_trap` | 805 | 804 | `fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol` | type/subtag |
| `wasm_sync_arg_regs_from_vsp` | 1553 | 1552 | `stack_ptr == NULL` | null/invalid |
| `wasm_unbind_to` | 1575 | 1574 | `binding_slots == NULL` | null/invalid |
| `wasm_unbind_to` | 1580 | 1579 | `current_binding == NULL` | null/invalid |
| `wasm_unbox_fixnum_or_trap` | 71 | 70 | `tag_of(value) != tag_fixnum` | fixnum, type/subtag |
| `wasm_unbox_u32_or_trap` | 889 | 888 | `sval < 0` | unknown |
| `wasm_unbox_u32_or_trap` | 904 | 903 | `v & 0x80000000u` | unknown |
| `wasm_unbox_u32_or_trap` | 911 | 910 | `digits[1] != 0` | unknown |
| `wasm_unbox_u32_or_trap` | 916 | 910 | `digits[1] != 0` | unknown |
| `wasm_vpop_argregs` | 739 | 738 | `tag_of(raw) != tag_fixnum` | fixnum, type/subtag |
| `wasm_vpop_argregs` | 749 | 748 | `stack_ptr == NULL` | null/invalid |
| `wasm_vpush_argregs` | 775 | 774 | `tag_of(raw) != tag_fixnum` | fixnum, type/subtag |
| `wasm_vpush_argregs` | 785 | 784 | `stack_ptr == NULL` | null/invalid |
| `wasm_vsp_or_trap` | 729 | 728 | `vsp_ptr == NULL` | null/invalid, state/unwind |
