/*
 * Auto-generated from lisp-kernel/arm-spentry.s, with
 * WASM-only stub entries appended at the end.
 *
 * Keep this in sync with the ARM sptab order; WASM subprim indices must match.
 */

#ifndef __ccl_wasm_subprims_map_h__
#define __ccl_wasm_subprims_map_h__

#define WASM_SUBPRIMS_COUNT 132

#define FOR_EACH_WASM_SUBPRIM(X) \
  X(_SPfix_nfn_entrypoint) \
  X(_SPbuiltin_plus) \
  X(_SPbuiltin_minus) \
  X(_SPbuiltin_times) \
  X(_SPbuiltin_div) \
  X(_SPbuiltin_eq) \
  X(_SPbuiltin_ne) \
  X(_SPbuiltin_gt) \
  X(_SPbuiltin_ge) \
  X(_SPbuiltin_lt) \
  X(_SPbuiltin_le) \
  X(_SPbuiltin_eql) \
  X(_SPbuiltin_length) \
  X(_SPbuiltin_seqtype) \
  X(_SPbuiltin_assq) \
  X(_SPbuiltin_memq) \
  X(_SPbuiltin_logbitp) \
  X(_SPbuiltin_logior) \
  X(_SPbuiltin_logand) \
  X(_SPbuiltin_ash) \
  X(_SPbuiltin_negate) \
  X(_SPbuiltin_logxor) \
  X(_SPbuiltin_aref1) \
  X(_SPbuiltin_aset1) \
  X(_SPfuncall) \
  X(_SPmkcatch1v) \
  X(_SPmkcatchmv) \
  X(_SPmkunwind) \
  X(_SPbind) \
  X(_SPconslist) \
  X(_SPconslist_star) \
  X(_SPmakes32) \
  X(_SPmakeu32) \
  X(_SPfix_overflow) \
  X(_SPmakeu64) \
  X(_SPmakes64) \
  X(_SPmvpass) \
  X(_SPvalues) \
  X(_SPnvalret) \
  X(_SPthrow) \
  X(_SPnthrowvalues) \
  X(_SPnthrow1value) \
  X(_SPbind_self) \
  X(_SPbind_nil) \
  X(_SPbind_self_boundp_check) \
  X(_SPrplaca) \
  X(_SPrplacd) \
  X(_SPgvset) \
  X(_SPset_hash_key) \
  X(_SPstore_node_conditional) \
  X(_SPset_hash_key_conditional) \
  X(_SPstkconslist) \
  X(_SPstkconslist_star) \
  X(_SPmkstackv) \
  X(_SPsetqsym) \
  X(_SPprogvsave) \
  X(_SPstack_misc_alloc) \
  X(_SPgvector) \
  X(_SPfitvals) \
  X(_SPnthvalue) \
  X(_SPdefault_optional_args) \
  X(_SPopt_supplied_p) \
  X(_SPheap_rest_arg) \
  X(_SPreq_heap_rest_arg) \
  X(_SPheap_cons_rest_arg) \
  X(_SPcheck_fpu_exception) \
  X(_SPdiscard_stack_object) \
  X(_SPksignalerr) \
  X(_SPstack_rest_arg) \
  X(_SPreq_stack_rest_arg) \
  X(_SPstack_cons_rest_arg) \
  X(_SPcall_closure) \
  X(_SPspreadargz) \
  X(_SPtfuncallgen) \
  X(_SPtfuncallslide) \
  X(_SPjmpsym) \
  X(_SPtcallsymgen) \
  X(_SPtcallsymslide) \
  X(_SPtcallnfngen) \
  X(_SPtcallnfnslide) \
  X(_SPmisc_ref) \
  X(_SPsubtag_misc_ref) \
  X(_SPmakestackblock) \
  X(_SPmakestackblock0) \
  X(_SPmakestacklist) \
  X(_SPstkgvector) \
  X(_SPmisc_alloc) \
  X(_SPatomic_incf_node) \
  X(_SPunused1) \
  X(_SPunused2) \
  X(_SPrecover_values) \
  X(_SPinteger_sign) \
  X(_SPsubtag_misc_set) \
  X(_SPmisc_set) \
  X(_SPspread_lexprz) \
  X(_SPreset) \
  X(_SPmvslide) \
  X(_SPsave_values) \
  X(_SPadd_values) \
  X(_SPmisc_alloc_init) \
  X(_SPstack_misc_alloc_init) \
  X(_SPpopj) \
  X(_SPudiv64by32) \
  X(_SPgetu64) \
  X(_SPgets64) \
  X(_SPspecref) \
  X(_SPspecrefcheck) \
  X(_SPspecset) \
  X(_SPgets32) \
  X(_SPgetu32) \
  X(_SPmvpasssym) \
  X(_SPunbind) \
  X(_SPunbind_n) \
  X(_SPunbind_to) \
  X(_SPprogvrestore) \
  X(_SPbind_interrupt_level_0) \
  X(_SPbind_interrupt_level_m1) \
  X(_SPbind_interrupt_level) \
  X(_SPunbind_interrupt_level) \
  X(_SParef2) \
  X(_SParef3) \
  X(_SPaset2) \
  X(_SPaset3) \
  X(_SPkeyword_bind) \
  X(_SPudiv32) \
  X(_SPsdiv32) \
  X(_SPeabi_ff_call_simple) \
  X(_SPdebind) \
  X(_SPeabi_callback) \
  X(_SPeabi_ff_callhf) \
  X(_SPwasm_macro_apply_stub) \
  X(_SPwasm_udf_stub)

#endif
