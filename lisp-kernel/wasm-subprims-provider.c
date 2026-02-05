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

__attribute__((import_module("ccl"), import_name("wasm_box_signed_64")))
LispObj wasm_box_signed_64(TCR *tcr, int64_t value);

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

static inline signed_natural
wasm_unbox_fixnum_or_trap(LispObj value)
{
  if (tag_of(value) != tag_fixnum) {
    wasm_subprims_trap();
  }
  return unbox_fixnum(value);
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

static inline LispObj *
wasm_vsp_or_trap(TCR *tcr)
{
  LispObj *vsp_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (vsp_ptr == NULL) {
    wasm_subprims_trap();
  }
  return vsp_ptr;
}

static void
wasm_push_value_set(TCR *tcr)
{
  signed_natural count = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, nargs));
  if (count < 0) {
    wasm_subprims_trap();
  }

  LispObj *old_vsp = wasm_vsp_or_trap(tcr);
  LispObj *prev_frame = (LispObj *)tcr->save_tsp;

  const signed_natural header_words = 4;
  signed_natural total_words = count + header_words;
  LispObj *new_vsp = old_vsp - total_words;

  signed_natural older_offset = (prev_frame != NULL) ? (signed_natural)(prev_frame - new_vsp) : 0;
  signed_natural old_vsp_offset = (signed_natural)(old_vsp - new_vsp);

  new_vsp[0] = box_fixnum(older_offset);
  new_vsp[1] = box_fixnum(0);
  new_vsp[2] = box_fixnum(count);
  new_vsp[3] = box_fixnum(old_vsp_offset);

  if (prev_frame != NULL) {
    signed_natural younger_offset = (signed_natural)(new_vsp - prev_frame);
    prev_frame[1] = box_fixnum(younger_offset);
  }

  if (count > 0) {
    new_vsp[4] = wasm_reg(tcr, arg_z);
    if (count > 1) {
      for (signed_natural i = 1; i < count; i++) {
        new_vsp[4 + i] = old_vsp[i];
      }
    }
  }

  wasm_set_reg(tcr, vsp, (LispObj)new_vsp);
  tcr->save_vsp = new_vsp;
  tcr->save_tsp = new_vsp;
  wasm_set_reg(tcr, nargs, box_fixnum(0));
}

static void
wasm_recover_value_sets(TCR *tcr)
{
  LispObj *newest = (LispObj *)tcr->save_tsp;
  if (newest == NULL) {
    return;
  }

  LispObj *oldest = newest;
  for (;;) {
    signed_natural older = wasm_unbox_fixnum_or_trap(oldest[0]);
    if (older == 0) {
      break;
    }
    oldest = oldest + older;
  }

  signed_natural total = 0;
  for (LispObj *cur = newest; cur != NULL; ) {
    total += wasm_unbox_fixnum_or_trap(cur[2]);
    signed_natural older = wasm_unbox_fixnum_or_trap(cur[0]);
    if (older == 0) {
      break;
    }
    cur = cur + older;
  }

  if (total <= 0) {
    signed_natural old_vsp_offset = wasm_unbox_fixnum_or_trap(oldest[3]);
    LispObj *old_vsp = oldest + old_vsp_offset;
    wasm_set_reg(tcr, arg_z, (LispObj)nil_value);
    wasm_set_reg(tcr, nargs, box_fixnum(0));
    wasm_set_reg(tcr, vsp, (LispObj)old_vsp);
    tcr->save_vsp = old_vsp;
    tcr->save_tsp = NULL;
    return;
  }

  LispObj *new_vsp = newest - total;
  signed_natural out = 0;
  for (LispObj *cur = oldest; cur != NULL; ) {
    signed_natural count = wasm_unbox_fixnum_or_trap(cur[2]);
    for (signed_natural j = 0; j < count; j++) {
      new_vsp[out++] = cur[4 + j];
    }
    signed_natural younger = wasm_unbox_fixnum_or_trap(cur[1]);
    if (younger == 0) {
      break;
    }
    cur = cur + younger;
  }

  wasm_set_reg(tcr, arg_z, new_vsp[0]);
  wasm_set_reg(tcr, vsp, (LispObj)new_vsp);
  tcr->save_vsp = new_vsp;
  wasm_set_reg(tcr, nargs, box_fixnum(total));
  tcr->save_tsp = NULL;
}

static void
wasm_sync_arg_regs_from_vsp(TCR *tcr)
{
  signed_natural count = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, nargs));
  if (count <= 0) {
    return;
  }

  LispObj *vsp_ptr = wasm_vsp_or_trap(tcr);

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

__attribute__((used, visibility("default"), export_name("_SPmkcatchmv")))
void
_SPmkcatchmv(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  catch_frame *cf = wasm_alloc_catch_frame();
  memset(cf, 0, sizeof(*cf));

  cf->header = catch_frame_header;
  cf->link = tcr->catch_top;
  cf->mvflag = box_fixnum(1);
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

  signed_natural frame_count = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, imm0));
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

__attribute__((used, visibility("default"), export_name("_SPnthrowvalues")))
void
_SPnthrowvalues(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  signed_natural frame_count = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, imm0));
  if (frame_count <= 0) {
    return;
  }

  tcr->unwinding = 1;

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
      signed_natural count = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, nargs));
      if (count < 0) {
        wasm_subprims_trap();
      }
      LispObj *src = wasm_vsp_or_trap(tcr);
      LispObj *dest = (LispObj *)cf->save_vsp;
      if (dest == NULL) {
        wasm_subprims_trap();
      }
      LispObj *cursor = src + count;
      while (count-- > 0) {
        LispObj value = *--cursor;
        *--dest = value;
      }
      wasm_set_reg(tcr, vsp, (LispObj)dest);
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

__attribute__((used, visibility("default"), export_name("_SPthrow")))
void
_SPthrow(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  signed_natural count = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, nargs));
  if (count < 0) {
    wasm_subprims_trap();
  }

  LispObj *vsp_ptr = wasm_vsp_or_trap(tcr);
  LispObj throw_tag = vsp_ptr[count];

  LispObj catch_top = tcr->catch_top;
  signed_natural frame_count = 0;
  catch_frame *target = NULL;
  while (catch_top != 0 && catch_top != (LispObj)nil_value) {
    catch_frame *cf = (catch_frame *)ptr_from_lispobj(untag(catch_top));
    if (cf->catch_tag == throw_tag) {
      target = cf;
      break;
    }
    catch_top = cf->link;
    frame_count++;
  }

  if (target == NULL) {
    wasm_subprims_trap();
  }

  if (target->mvflag == 0) {
    if (count == 0) {
      *--vsp_ptr = (LispObj)nil_value;
      wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
    } else {
      vsp_ptr = vsp_ptr + (count - 1);
      wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
    }
    wasm_set_reg(tcr, nargs, box_fixnum(1));
  }

  wasm_set_reg(tcr, imm0, box_fixnum(frame_count + 1));
  _SPnthrowvalues();
}

__attribute__((used, visibility("default"), export_name("_SPsave_values")))
void
_SPsave_values(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  wasm_push_value_set(tcr);
}

__attribute__((used, visibility("default"), export_name("_SPadd_values")))
void
_SPadd_values(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  wasm_push_value_set(tcr);
}

__attribute__((used, visibility("default"), export_name("_SPrecover_values")))
void
_SPrecover_values(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  wasm_recover_value_sets(tcr);
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

__attribute__((used, visibility("default"), export_name("_SPmakes32")))
void
_SPmakes32(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw = wasm_reg(tcr, imm0);
  int32_t val = (tag_of(raw) == tag_fixnum) ? (int32_t)unbox_fixnum(raw) : (int32_t)raw;
  wasm_set_reg(tcr, arg_z, wasm_box_signed_64(tcr, (int64_t)val));
  wasm_set_reg(tcr, nargs, box_fixnum(1));
}

__attribute__((used, visibility("default"), export_name("_SPfix_overflow")))
void
_SPfix_overflow(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  int32_t val = (int32_t)unbox_fixnum(wasm_reg(tcr, arg_z));
  int32_t adjust = (int32_t)(3u << (nbits_in_word - 2));
  val ^= adjust;
  wasm_set_reg(tcr, arg_z, wasm_box_signed_64(tcr, (int64_t)val));
  wasm_set_reg(tcr, nargs, box_fixnum(1));
}
#endif
