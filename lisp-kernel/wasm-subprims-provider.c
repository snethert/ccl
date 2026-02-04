#ifdef WASM32
#include <stdint.h>
#include <string.h>

#include "lisp.h"
#include "lisp-exceptions.h"

__attribute__((import_module("ccl"), import_name("wasm_get_current_tcr")))
TCR *wasm_get_current_tcr(void);

__attribute__((import_module("ccl"), import_name("wasm_get_cstack_pointer")))
void *wasm_get_cstack_pointer(void);

__attribute__((import_module("ccl"), import_name("wasm_set_cstack_pointer")))
void wasm_set_cstack_pointer(void *stack_ptr);

static void
wasm_subprims_trap(void)
{
  __builtin_trap();
  __builtin_unreachable();
}

static inline LispObj
wasm_reg(TCR *tcr, int reg)
{
  return tcr->wasm_gprs[reg];
}

static inline void
wasm_set_reg(TCR *tcr, int reg, LispObj value)
{
  tcr->wasm_gprs[reg] = value;
}

static inline void
wasm_set_pending_throw(TCR *tcr, LispObj flag)
{
  tcr->wasm_pending_throw = flag;
}

static inline int
wasm_pending_throw_p(TCR *tcr)
{
  return tcr->wasm_pending_throw != 0;
}

static void
wasm_sync_arg_regs_from_vsp(TCR *tcr)
{
  LispObj nargs_val = wasm_reg(tcr, nargs);
  if (tag_of(nargs_val) != tag_fixnum) {
    wasm_subprims_trap();
  }
  signed_natural count = unbox_fixnum(nargs_val);
  if (count <= 0) {
    return;
  }

  LispObj *vsp_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (vsp_ptr == NULL) {
    wasm_subprims_trap();
  }

  if (count >= 1) {
    wasm_set_reg(tcr, arg_z, vsp_ptr[0]);
  }
  if (count >= 2) {
    wasm_set_reg(tcr, arg_y, vsp_ptr[1]);
  }
  if (count >= 3) {
    wasm_set_reg(tcr, arg_x, vsp_ptr[2]);
  }
}

static void
wasm_unbind_to(TCR *tcr, special_binding *target)
{
  special_binding *binding = tcr->db_link;
  LispObj *tlb = tcr->tlb_pointer;

  if (binding == NULL || tlb == NULL) {
    wasm_subprims_trap();
  }

  while (binding != target) {
    LispObj symidx = (LispObj)binding->sym;
    LispObj value = binding->value;
    binding = binding->link;
    tlb[unbox_fixnum(symidx)] = value;
    if (binding == NULL) {
      wasm_subprims_trap();
    }
  }
  tcr->db_link = target;
}

static inline catch_frame *
wasm_alloc_catch_frame(void)
{
  BytePtr stack_ptr = (BytePtr)wasm_get_cstack_pointer();
  size_t bytes = sizeof(catch_frame);
  stack_ptr -= bytes;
  wasm_set_cstack_pointer(stack_ptr);
  return (catch_frame *)stack_ptr;
}

static inline void
wasm_free_catch_frame(catch_frame *cf)
{
  BytePtr stack_ptr = (BytePtr)cf;
  stack_ptr += sizeof(catch_frame);
  wasm_set_cstack_pointer(stack_ptr);
}

__attribute__((used, visibility("default"), export_name("_SPmkcatch1v")))
void
_SPmkcatch1v(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  catch_frame *cf = wasm_alloc_catch_frame();
  memset(cf, 0, sizeof(*cf));

  cf->header = catch_frame_header;
  cf->link = tcr->catch_top;
  cf->mvflag = 0;
  cf->catch_tag = wasm_reg(tcr, arg_z);
  cf->db_link = (LispObj)tcr->db_link;
  cf->xframe = (LispObj)tcr->xframe;
  cf->last_lisp_frame = (LispObj)tcr->last_lisp_frame;
  cf->nfp = (LispObj)tcr->nfp;
  cf->save_vsp = wasm_reg(tcr, vsp);

  tcr->catch_top = ptr_to_lispobj((BytePtr)cf + fulltag_misc);
}

__attribute__((used, visibility("default"), export_name("_SPnthrow1value")))
void
_SPnthrow1value(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  signed_natural frame_count = unbox_fixnum(wasm_reg(tcr, imm0));
  if (frame_count <= 0) {
    return;
  }

  tcr->unwinding = 1;
  wasm_set_reg(tcr, nargs, box_fixnum(1));

  while (frame_count-- > 0) {
    LispObj catch_top = tcr->catch_top;
    if (catch_top == 0 || catch_top == (LispObj)nil_value) {
      wasm_subprims_trap();
    }

    catch_frame *cf = (catch_frame *)ptr_from_lispobj(untag(catch_top));
    special_binding *target_db = (special_binding *)cf->db_link;

    tcr->catch_top = cf->link;
    tcr->xframe = (xframe_list *)cf->xframe;
    tcr->last_lisp_frame = (natural)cf->last_lisp_frame;
    tcr->nfp = (void *)cf->nfp;

    if (tcr->db_link != target_db) {
      wasm_unbind_to(tcr, target_db);
    }

    if (cf->catch_tag == (LispObj)unbound_marker) {
      /* Unwind-protect frames are Tier-1; trap for now. */
      wasm_subprims_trap();
    }

    if (frame_count == 0) {
      wasm_set_reg(tcr, vsp, cf->save_vsp);
    }

    wasm_free_catch_frame(cf);
  }

  tcr->unwinding = 0;
  wasm_set_pending_throw(tcr, box_fixnum(1));
}

typedef void (*wasm_lisp_fn)(void);

static inline void
wasm_call_entry_index(uint32_t index)
{
  ((wasm_lisp_fn)(uintptr_t)index)();
}

__attribute__((used, visibility("default"), export_name("_SPfuncall")))
void
_SPfuncall(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  wasm_sync_arg_regs_from_vsp(tcr);

  LispObj fn_value = wasm_reg(tcr, nfn);
  if (fn_value == (LispObj)nil_value) {
    wasm_subprims_trap();
  }

  if (fulltag_of(fn_value) != fulltag_misc) {
    wasm_subprims_trap();
  }

  LispObj header = header_of(fn_value);
  int subtag = header_subtag(header);
  if (subtag == subtag_symbol) {
    lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(fn_value));
    fn_value = sym->fcell;
    if (fulltag_of(fn_value) != fulltag_misc) {
      wasm_subprims_trap();
    }
    header = header_of(fn_value);
    subtag = header_subtag(header);
  }

  if (subtag != subtag_function) {
    wasm_subprims_trap();
  }

  wasm_set_reg(tcr, nfn, fn_value);
  wasm_set_reg(tcr, Rfn, fn_value);

  LispObj entry = deref(fn_value, 1);
  if (tag_of(entry) != tag_fixnum) {
    wasm_subprims_trap();
  }

  wasm_call_entry_index((uint32_t)unbox_fixnum(entry));

  if (wasm_pending_throw_p(tcr)) {
    return;
  }
}
#endif
