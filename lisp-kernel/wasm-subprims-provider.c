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
void wasm_set_cstack_pointer(void *sp);

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

static inline catch_frame *
wasm_alloc_catch_frame(void)
{
  BytePtr sp = (BytePtr)wasm_get_cstack_pointer();
  size_t bytes = sizeof(catch_frame);
  sp -= bytes;
  wasm_set_cstack_pointer(sp);
  return (catch_frame *)sp;
}

static inline void
wasm_free_catch_frame(catch_frame *cf)
{
  BytePtr sp = (BytePtr)cf;
  sp += sizeof(catch_frame);
  wasm_set_cstack_pointer(sp);
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

  LispObj catch_top = tcr->catch_top;
  if (catch_top == 0 || catch_top == (LispObj)nil_value) {
    wasm_subprims_trap();
  }

  catch_frame *cf = (catch_frame *)ptr_from_lispobj(untag(catch_top));

  tcr->catch_top = cf->link;
  tcr->db_link = (special_binding *)cf->db_link;
  tcr->xframe = (xframe_list *)cf->xframe;
  tcr->last_lisp_frame = (natural)cf->last_lisp_frame;
  tcr->nfp = (void *)cf->nfp;

  wasm_free_catch_frame(cf);

  /* TODO: implement non-local transfer to the catch target. */
}

__attribute__((used, visibility("default"), export_name("_SPfuncall")))
void
_SPfuncall(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj nfn = wasm_reg(tcr, Rfn);
  if (nfn == (LispObj)nil_value) {
    return;
  }

  /* TODO: implement WASM codegen calling convention for Lisp functions. */
  wasm_subprims_trap();
}
#endif
