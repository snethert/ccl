/*
 * WASM32 kernel stubs
 *
 * These definitions exist to let the WASM kernel link as a freestanding module
 * during early bring-up (no image loader, no OS, no WASI).
 */

#ifdef WASM32

#include "lisp.h"
#include "lisp-exceptions.h"
#include "lisp_globals.h"
#include "wasm-subprims.h"

#include <stdint.h>
#include <sys/types.h>
#include <limits.h>
#include <string.h>

/* Used by lisp-debug.c for banner/prompt printing. */
pid_t main_thread_pid = 0;

/* pmcl-kernel.c stores the address of these in lisp globals. On other
 * platforms they're code labels; for now they're placeholders.
 */
LispObj ret1valn = 0;
LispObj nvalret = 0;
LispObj popj = 0;
extern LispObj lisp_nil;

enum {
  WASM_SUBPRIM_FUNCALL_INDEX = 24,
  WASM_SUBPRIM_MKCATCH1V_INDEX = 25,
  WASM_SUBPRIM_NTHROW1VALUE_INDEX = 41,
  /* Keep in sync with scripts/wasm/make_minimal_image.py and load-image.mjs. */
  WASM_BOOT_ENTRY_INDEX = 200,
  /* Smoke-test entrypoint for the WASM calling convention. */
  WASM_TEST_ENTRY_INDEX = 201,
  /* Constant-return entrypoint for compiler IR bring-up. */
  WASM_CONST_ENTRY_INDEX = 202
};

static inline LispObj
wasm_subprim_fixnum(uint32_t index)
{
  return box_fixnum(index);
}

static uint32_t wasm_subprims_ready = 0;

__attribute__((used, visibility("default"), export_name("wasm_set_subprims_ready")))
void
wasm_set_subprims_ready(uint32_t ready)
{
  wasm_subprims_ready = ready ? 1u : 0u;
}

__attribute__((used, visibility("default"), export_name("wasm_get_subprims_ready")))
uint32_t
wasm_get_subprims_ready(void)
{
  return wasm_subprims_ready;
}

static int
wasm_toplevel_loop(TCR *tcr)
{
  for (;;) {
    LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
    if (vsp_ptr == NULL) {
      return -1;
    }
    LispObj topfn = *vsp_ptr;
    if (topfn == lisp_nil) {
      return 0;
    }

    tcr->wasm_gprs[arg_z] = nrs_TOPLCATCH.vcell;
    wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKCATCH1V_INDEX));

    tcr->wasm_gprs[nargs] = box_fixnum(0);
    tcr->wasm_gprs[nfn] = topfn;
    tcr->wasm_gprs[Rfn] = topfn;
    wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));
    if (tcr->wasm_pending_throw) {
      return 1;
    }

    tcr->wasm_gprs[arg_z] = lisp_nil;
    tcr->wasm_gprs[imm0] = box_fixnum(1);
    wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_NTHROW1VALUE_INDEX));
    if (tcr->wasm_pending_throw) {
      tcr->wasm_pending_throw = 0;
    }
  }
}

__attribute__((used, visibility("default"), export_name("wasm_boot_entry")))
void
wasm_boot_entry(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
  if (vsp_ptr != NULL) {
    *vsp_ptr = lisp_nil;
  }
  tcr->wasm_gprs[arg_z] = lisp_nil;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_test_entry")))
void
wasm_test_entry(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }

  LispObj arg = tcr->wasm_gprs[arg_z];
  if (tag_of(arg) != tag_fixnum) {
    tcr->wasm_gprs[arg_z] = lisp_nil;
  } else {
    tcr->wasm_gprs[arg_z] = arg + box_fixnum(1);
  }
  tcr->wasm_gprs[nargs] = box_fixnum(1);

  /* Allow the stub to terminate the toplevel loop if used as %toplevel-function%. */
  LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
  if (vsp_ptr != NULL) {
    *vsp_ptr = lisp_nil;
  }
}

static LispObj wasm_const_value = (LispObj)nil_value;

static inline int64_t
wasm_fixnum_min(void)
{
  return -(1LL << (nbits_in_word - fixnum_shift - 1));
}

static inline int64_t
wasm_fixnum_max(void)
{
  return (1LL << (nbits_in_word - fixnum_shift - 1)) - 1;
}

static inline int
wasm_fixnum_fits(int64_t value)
{
  return (value >= wasm_fixnum_min()) && (value <= wasm_fixnum_max());
}

static inline size_t
wasm_align_dnode(size_t bytes)
{
  return (bytes + (dnode_size - 1)) & ~(size_t)(dnode_size - 1);
}

static int
wasm_reserve_heap_segment(TCR *tcr, size_t bytes_needed)
{
  ExceptionInformation xp;

  if (tcr == NULL) {
    return 0;
  }

  if (tcr->save_allocptr == (void *)VOID_ALLOCPTR ||
      tcr->save_allocbase == (void *)VOID_ALLOCPTR ||
      tcr->save_allocptr == NULL || tcr->save_allocbase == NULL) {
    memset(&xp, 0, sizeof(xp));
    if (!new_heap_segment(&xp, (natural)bytes_needed, true, tcr, NULL)) {
      return 0;
    }
  }

  BytePtr alloc_ptr = (BytePtr)tcr->save_allocptr;
  BytePtr alloc_base = (BytePtr)tcr->save_allocbase;
  if ((alloc_ptr - (signed_natural)bytes_needed) < alloc_base) {
    memset(&xp, 0, sizeof(xp));
    if (!new_heap_segment(&xp, (natural)bytes_needed, true, tcr, NULL)) {
      return 0;
    }
  }

  return 1;
}

static LispObj
wasm_alloc_bignum(TCR *tcr, unsigned digits, const uint32_t *values)
{
  if (digits == 0 || values == NULL) {
    return lisp_nil;
  }

  size_t bytes = wasm_align_dnode((size_t)(1 + digits) * node_size);
  if (!wasm_reserve_heap_segment(tcr, bytes)) {
    return lisp_nil;
  }

  BytePtr alloc_ptr = (BytePtr)tcr->save_allocptr;
  BytePtr alloc_base = (BytePtr)tcr->save_allocbase;
  BytePtr newptr = alloc_ptr - (signed_natural)bytes;
  if (newptr < alloc_base) {
    return lisp_nil;
  }

  tcr->save_allocptr = (void *)newptr;
  LispObj obj = (LispObj)(newptr + fulltag_misc);
  header_of(obj) = make_header(subtag_bignum, digits);

  uint32_t *data = (uint32_t *)((BytePtr)obj + misc_data_offset);
  for (unsigned i = 0; i < digits; i++) {
    data[i] = values[i];
  }

  return obj;
}

__attribute__((used, visibility("default"), export_name("wasm_box_signed_64")))
LispObj
wasm_box_signed_64(TCR *tcr, int64_t value)
{
  if (wasm_fixnum_fits(value)) {
    return box_fixnum((signed_natural)value);
  }

  uint32_t digits[2];
  uint64_t uval = (uint64_t)value;
  digits[0] = (uint32_t)uval;
  digits[1] = (uint32_t)(uval >> 32);

  unsigned count = (value >= (int64_t)INT32_MIN && value <= (int64_t)INT32_MAX) ? 1u : 2u;
  return wasm_alloc_bignum(tcr, count, digits);
}

static LispObj
wasm_box_shifted_fixnum(TCR *tcr, int32_t value, uint32_t shift)
{
  if (shift < 63) {
    int64_t shifted = ((int64_t)value) << shift;
    return wasm_box_signed_64(tcr, shifted);
  }

  uint32_t word_shift = shift / 32;
  uint32_t bit_shift = shift % 32;
  unsigned digits = word_shift + 1 + (bit_shift ? 1 : 0);

  uint32_t *buf = (uint32_t *)calloc(digits + 1, sizeof(uint32_t));
  if (buf == NULL) {
    return lisp_nil;
  }

  uint64_t chunk = ((uint64_t)(uint32_t)value) << bit_shift;
  buf[word_shift] = (uint32_t)chunk;
  if (bit_shift) {
    buf[word_shift + 1] = (uint32_t)(chunk >> 32);
  }

  if (value >= 0) {
    if (buf[digits - 1] & 0x80000000u) {
      buf[digits++] = 0;
    }
  } else {
    if ((buf[digits - 1] & 0x80000000u) == 0) {
      buf[digits++] = 0xFFFFFFFFu;
    }
  }

  if (value >= 0) {
    while (digits > 1 &&
           buf[digits - 1] == 0 &&
           ((buf[digits - 2] & 0x80000000u) == 0)) {
      digits--;
    }
  } else {
    while (digits > 1 &&
           buf[digits - 1] == 0xFFFFFFFFu &&
           (buf[digits - 2] & 0x80000000u)) {
      digits--;
    }
  }

  LispObj result = wasm_alloc_bignum(tcr, digits, buf);
  free(buf);
  return result;
}

__attribute__((used, visibility("default"), export_name("wasm_set_const_value")))
void
wasm_set_const_value(LispObj value)
{
  wasm_const_value = value;
}

__attribute__((used, visibility("default"), export_name("wasm_const_entry")))
void
wasm_const_entry(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj value = wasm_const_value;
  LispObj fn_value = tcr->wasm_gprs[nfn];
  if (fulltag_of(fn_value) == fulltag_misc) {
    LispObj header = header_of(fn_value);
    if (header_subtag(header) == subtag_function &&
        header_element_count(header) >= 4) {
      value = deref(fn_value, 3);
    }
  }
  tcr->wasm_gprs[arg_z] = value;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_constant")))
void
wasm_return_constant(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_gprs[arg_z] = value;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_add")))
void
wasm_return_fixnum_add(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  int64_t a = (int64_t)unbox_fixnum(tcr->wasm_gprs[arg_z]);
  int64_t b = (int64_t)unbox_fixnum(tcr->wasm_gprs[arg_y]);
  int64_t sum = a + b;
  tcr->wasm_gprs[arg_z] = wasm_box_signed_64(tcr, sum);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_sub")))
void
wasm_return_fixnum_sub(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  int64_t a = (int64_t)unbox_fixnum(tcr->wasm_gprs[arg_z]);
  int64_t b = (int64_t)unbox_fixnum(tcr->wasm_gprs[arg_y]);
  int64_t diff = a - b;
  tcr->wasm_gprs[arg_z] = wasm_box_signed_64(tcr, diff);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_mul")))
void
wasm_return_fixnum_mul(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  signed_natural a = unbox_fixnum(tcr->wasm_gprs[arg_z]);
  signed_natural b = unbox_fixnum(tcr->wasm_gprs[arg_y]);
  int64_t prod = (int64_t)a * (int64_t)b;
  tcr->wasm_gprs[arg_z] = wasm_box_signed_64(tcr, prod);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_ash")))
void
wasm_return_fixnum_ash(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  signed_natural val = unbox_fixnum(tcr->wasm_gprs[arg_z]);
  signed_natural amt = unbox_fixnum(tcr->wasm_gprs[arg_y]);
  signed_natural result = 0;
  if (amt >= 0) {
    tcr->wasm_gprs[arg_z] = wasm_box_shifted_fixnum(tcr, (int32_t)val, (uint32_t)amt);
    tcr->wasm_gprs[nargs] = box_fixnum(1);
    return;
  } else {
    signed_natural shift = -amt;
    result = (shift >= (signed_natural)(nbits_in_word - 1)) ? ((val < 0) ? -1 : 0) : (val >> shift);
  }
  tcr->wasm_gprs[arg_z] = wasm_box_signed_64(tcr, result);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_neg")))
void
wasm_return_fixnum_neg(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  int64_t val = (int64_t)unbox_fixnum(tcr->wasm_gprs[arg_z]);
  int64_t neg = -val;
  tcr->wasm_gprs[arg_z] = wasm_box_signed_64(tcr, neg);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("_SPmakes32")))
void
_SPmakes32(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj raw = tcr->wasm_gprs[imm0];
  int32_t val = (tag_of(raw) == tag_fixnum) ? (int32_t)unbox_fixnum(raw) : (int32_t)raw;
  tcr->wasm_gprs[arg_z] = wasm_box_signed_64(tcr, (int64_t)val);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("_SPfix_overflow")))
void
_SPfix_overflow(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  int32_t val = (int32_t)unbox_fixnum(tcr->wasm_gprs[arg_z]);
  int32_t adjust = (int32_t)(3u << (nbits_in_word - 2));
  val ^= adjust;
  tcr->wasm_gprs[arg_z] = wasm_box_signed_64(tcr, (int64_t)val);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_logand")))
void
wasm_return_fixnum_logand(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj a = tcr->wasm_gprs[arg_z];
  LispObj b = tcr->wasm_gprs[arg_y];
  tcr->wasm_gprs[arg_z] = a & b;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_logior")))
void
wasm_return_fixnum_logior(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj a = tcr->wasm_gprs[arg_z];
  LispObj b = tcr->wasm_gprs[arg_y];
  tcr->wasm_gprs[arg_z] = a | b;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_logxor")))
void
wasm_return_fixnum_logxor(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj a = tcr->wasm_gprs[arg_z];
  LispObj b = tcr->wasm_gprs[arg_y];
  tcr->wasm_gprs[arg_z] = a ^ b;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_lognot")))
void
wasm_return_fixnum_lognot(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  signed_natural val = unbox_fixnum(tcr->wasm_gprs[arg_z]);
  tcr->wasm_gprs[arg_z] = box_fixnum(~val);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

LispObj
start_lisp(TCR *tcr, LispObj arg)
{
  (void)arg;
  if (tcr != NULL) {
    tcr->valence = TCR_STATE_LISP;
  }

  if (!wasm_subprims_ready) {
    static const char msg[] =
      "WASM start_lisp: subprims not ready; returning to host\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    goto done;
  }

  if (tcr != NULL) {
    LispObj topfn = nrs_TOPLFUNC.vcell;
    if (topfn == lisp_nil) {
      static const char msg[] =
        "WASM start_lisp: toplevel function is NIL; returning to host\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      goto done;
    }

    tcr->wasm_pending_throw = 0;
    tcr->wasm_gprs[vsp] = (LispObj)tcr->save_vsp;
    LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
    if (vsp_ptr == NULL) {
      static const char msg[] =
        "WASM start_lisp: VSP not initialized; returning to host\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      goto done;
    }
    *--vsp_ptr = topfn;
    tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;

    (void)wasm_toplevel_loop(tcr);

    tcr->save_vsp = (LispObj *)tcr->wasm_gprs[vsp];
    if (tcr->wasm_pending_throw) {
      tcr->wasm_pending_throw = 0;
    }
  }

done:
  if (tcr != NULL) {
    tcr->valence = TCR_STATE_FOREIGN;
  }

  return lisp_nil;
}

__attribute__((used, visibility("default"), export_name("wasm_run_toplevel")))
int
wasm_run_toplevel(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return -1;
  }
  if (!wasm_subprims_ready) {
    return -2;
  }

  LispObj topfn = nrs_TOPLFUNC.vcell;
  if (topfn == lisp_nil) {
    return -3;
  }

  natural old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)tcr->save_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[vsp] = (LispObj)tcr->save_vsp;
  LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
  if (vsp_ptr == NULL) {
    tcr->valence = TCR_STATE_FOREIGN;
    wasm_exit_lisp_frame(tcr, old_last_lisp_frame);
    return -4;
  }
  *--vsp_ptr = topfn;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;

  int rc = wasm_toplevel_loop(tcr);

  tcr->save_vsp = (LispObj *)tcr->wasm_gprs[vsp];
  if (tcr->wasm_pending_throw) {
    tcr->wasm_pending_throw = 0;
  }
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old_last_lisp_frame);
  return rc;
}

__attribute__((used, visibility("default"), export_name("wasm_test_funcall")))
LispObj
wasm_test_funcall(uint32_t raw_arg)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  if (!wasm_subprims_ready) {
    return lisp_nil;
  }

  LispObj fn_obj[3] __attribute__((aligned(8)));
  LispObj entry_fixnum = box_fixnum(WASM_TEST_ENTRY_INDEX);
  fn_obj[0] = make_header(subtag_function, 2);
  fn_obj[1] = entry_fixnum;
  fn_obj[2] = entry_fixnum;
  LispObj fn_value = (LispObj)((BytePtr)fn_obj + fulltag_misc);

  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }

  natural old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)saved_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;

  LispObj *vsp_ptr = saved_vsp;
  *--vsp_ptr = box_fixnum((signed_natural)raw_arg);

  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
  tcr->wasm_gprs[nfn] = fn_value;
  tcr->wasm_gprs[Rfn] = fn_value;

  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  LispObj result = tcr->wasm_gprs[arg_z];
  tcr->save_vsp = saved_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old_last_lisp_frame);

  return result;
}

__attribute__((used, visibility("default"), export_name("wasm_test_const_funcall")))
LispObj
wasm_test_const_funcall(uint32_t raw_value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  if (!wasm_subprims_ready) {
    return lisp_nil;
  }

  LispObj fn_obj[4] __attribute__((aligned(8)));
  LispObj entry_fixnum = box_fixnum(WASM_CONST_ENTRY_INDEX);
  fn_obj[0] = make_header(subtag_function, 4);
  fn_obj[1] = entry_fixnum;
  fn_obj[2] = entry_fixnum;
  fn_obj[3] = box_fixnum((signed_natural)raw_value);
  LispObj fn_value = (LispObj)((BytePtr)fn_obj + fulltag_misc);

  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }

  natural old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)saved_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;

  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->wasm_gprs[nargs] = box_fixnum(0);
  tcr->wasm_gprs[nfn] = fn_value;
  tcr->wasm_gprs[Rfn] = fn_value;

  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  LispObj result = tcr->wasm_gprs[arg_z];
  tcr->save_vsp = saved_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old_last_lisp_frame);

  return result;
}

__attribute__((used, visibility("default"), export_name("wasm_test_entry_funcall")))
LispObj
wasm_test_entry_funcall(uint32_t entry_index, uint32_t raw_value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  if (!wasm_subprims_ready) {
    return lisp_nil;
  }

  LispObj fn_obj[4] __attribute__((aligned(8)));
  LispObj entry_fixnum = box_fixnum((signed_natural)entry_index);
  fn_obj[0] = make_header(subtag_function, 4);
  fn_obj[1] = entry_fixnum;
  fn_obj[2] = entry_fixnum;
  fn_obj[3] = box_fixnum((signed_natural)raw_value);
  LispObj fn_value = (LispObj)((BytePtr)fn_obj + fulltag_misc);

  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }

  natural old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)saved_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;

  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->wasm_gprs[nargs] = box_fixnum(0);
  tcr->wasm_gprs[nfn] = fn_value;
  tcr->wasm_gprs[Rfn] = fn_value;

  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  LispObj result = tcr->wasm_gprs[arg_z];
  tcr->save_vsp = saved_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old_last_lisp_frame);

  return result;
}

__attribute__((used, visibility("default"), export_name("wasm_test_entry_funcall2")))
LispObj
wasm_test_entry_funcall2(uint32_t entry_index, uint32_t raw_a, uint32_t raw_b)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  if (!wasm_subprims_ready) {
    return lisp_nil;
  }

  LispObj fn_obj[4] __attribute__((aligned(8)));
  LispObj entry_fixnum = box_fixnum((signed_natural)entry_index);
  fn_obj[0] = make_header(subtag_function, 4);
  fn_obj[1] = entry_fixnum;
  fn_obj[2] = entry_fixnum;
  fn_obj[3] = 0;
  LispObj fn_value = (LispObj)((BytePtr)fn_obj + fulltag_misc);

  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }

  natural old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)saved_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;

  LispObj *vsp_ptr = saved_vsp;
  *--vsp_ptr = box_fixnum((signed_natural)raw_b);
  *--vsp_ptr = box_fixnum((signed_natural)raw_a);

  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->wasm_gprs[nargs] = box_fixnum(2);
  tcr->wasm_gprs[nfn] = fn_value;
  tcr->wasm_gprs[Rfn] = fn_value;

  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  LispObj result = tcr->wasm_gprs[arg_z];
  tcr->save_vsp = saved_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old_last_lisp_frame);

  return result;
}

__attribute__((used, visibility("default"), export_name("wasm_get_lisp_nil")))
LispObj
wasm_get_lisp_nil(void)
{
  extern LispObj lisp_nil;
  return lisp_nil;
}

#endif /* WASM32 */
