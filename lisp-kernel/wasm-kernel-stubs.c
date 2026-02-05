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

__attribute__((noreturn))
static void
wasm_fixnum_overflow_trap(void)
{
  static const char msg[] =
    "WASM fixnum overflow: bignum allocation not implemented\n";
  wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
  __builtin_trap();
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
  if (!wasm_fixnum_fits(sum)) {
    wasm_fixnum_overflow_trap();
  }
  tcr->wasm_gprs[arg_z] = box_fixnum((signed_natural)sum);
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
  if (!wasm_fixnum_fits(diff)) {
    wasm_fixnum_overflow_trap();
  }
  tcr->wasm_gprs[arg_z] = box_fixnum((signed_natural)diff);
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
  if (!wasm_fixnum_fits(prod)) {
    wasm_fixnum_overflow_trap();
  }
  tcr->wasm_gprs[arg_z] = box_fixnum((signed_natural)prod);
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
  signed_natural max_shift = nbits_in_word - fixnum_shift;
  if (amt >= 0) {
    if (amt >= max_shift) {
      if (val != 0) {
        wasm_fixnum_overflow_trap();
      }
      result = 0;
    } else {
      int64_t shifted = ((int64_t)val) << amt;
      if (!wasm_fixnum_fits(shifted)) {
        wasm_fixnum_overflow_trap();
      }
      result = (signed_natural)shifted;
    }
  } else {
    signed_natural shift = -amt;
    if (shift >= max_shift) {
      result = (val < 0) ? -1 : 0;
    } else {
      result = val >> shift;
    }
  }
  tcr->wasm_gprs[arg_z] = box_fixnum(result);
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
  if (!wasm_fixnum_fits(neg)) {
    wasm_fixnum_overflow_trap();
  }
  tcr->wasm_gprs[arg_z] = box_fixnum((signed_natural)neg);
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
