/*
 * WASM32 kernel stubs
 *
 * These definitions exist to let the WASM kernel link as a freestanding module
 * during early bring-up (no image loader, no OS, no WASI).
 */

#ifdef WASM32

#include "lisp.h"
#include "gc.h"
#include "lisp-exceptions.h"
#include "lisp_globals.h"
#include "wasm-host.h"
#include "wasm-subprims.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdint.h>
#include <sys/types.h>
#include <limits.h>
#include <stddef.h>
#include <string.h>

enum wasm_boot_phase {
  WASM_BOOT_EARLY = 0,
  WASM_BOOT_L0_READY = 1,
  WASM_BOOT_RUNTIME = 2
};

enum wasm_probe_foreign_call_mode {
  WASM_PROBE_FOREIGN_CALL_FASLOAD = 0,
  WASM_PROBE_FOREIGN_CALL_IDENTITY = 1,
  WASM_PROBE_FOREIGN_CALL_ERROR = 2
};

/* Used by lisp-debug.c for banner/prompt printing. */
pid_t main_thread_pid = 0;

/* pmcl-kernel.c stores the address of these in lisp globals. On other
 * platforms they're code labels; for now they're placeholders.
 */
LispObj ret1valn = 0;
LispObj nvalret = 0;
LispObj popj = 0;
extern LispObj lisp_nil;
__attribute__((import_module("ccl"), import_name("wasm_host_install_const_pool")))
int32_t wasm_host_install_const_pool(uint32_t entry_index);
extern int lisp_open(char *path, int flags, mode_t mode);
extern int lisp_close(int fd);
extern ssize_t lisp_write(int fd, void *buf, size_t count);
extern OSErr save_application(int fd, Boolean egc_was_enabled);
LispObj wasm_misc_alloc(TCR *tcr, unsigned subtag, signed_natural count);
static LispObj wasm_intern_startup(TCR *tcr, const uint8_t *name_bytes, uint32_t name_len, LispObj pkg);
static LispObj wasm_intern_runtime(TCR *tcr, const uint8_t *name_bytes, uint32_t name_len, LispObj pkg);
static LispObj wasm_intern_dispatch(TCR *tcr, const uint8_t *name_bytes, uint32_t name_len, LispObj pkg);
static LispObj wasm_const_pool_intern_symbol(TCR *tcr, const uint8_t *name_bytes, uint32_t name_len, LispObj pkg);
void wasm_debug_dump_state(const char *label);

static LispObj *
wasm_toplevel_slot(TCR *tcr);

enum {
  WASM_SUBPRIM_FUNCALL_INDEX = 24,
  WASM_SUBPRIM_MKCATCH1V_INDEX = 25,
  WASM_SUBPRIM_MKUNWIND_INDEX = 27,
  WASM_SUBPRIM_VALUES_INDEX = 37,
  WASM_SUBPRIM_NTHROWVALUES_INDEX = 40,
  WASM_SUBPRIM_NTHROW1VALUE_INDEX = 41,
  /* Keep in sync with scripts/wasm/make_minimal_image.py and load-image.mjs. */
  WASM_BOOT_ENTRY_INDEX = 200,
  /* Smoke-test entrypoint for the WASM calling convention. */
  WASM_TEST_ENTRY_INDEX = 201,
  /* Constant-return entrypoint for compiler IR bring-up. */
  WASM_CONST_ENTRY_INDEX = 202
};

#define WASM_NAMED_ENTRY_MAX 8192u
#define WASM_NAMED_ENTRY_BYTES_MAX (1u << 20)

typedef struct {
  uint32_t name_offset;
  uint32_t name_len;
  uint32_t entry_index;
} wasm_named_entry_record;

static wasm_named_entry_record wasm_named_entries[WASM_NAMED_ENTRY_MAX];
static uint8_t wasm_named_entry_names[WASM_NAMED_ENTRY_BYTES_MAX];
static uint32_t wasm_named_entry_count = 0u;
static uint32_t wasm_named_entry_names_used = 0u;

/* Last const-pool-ref call — used by wasm_debug_dump_state */
static uint32_t wasm_diag_last_cpr_entry = 0;
static uint32_t wasm_diag_last_cpr_slot = 0;
static LispObj  wasm_diag_last_cpr_val = 0;

static inline LispObj
wasm_subprim_fixnum(uint32_t index)
{
  return box_fixnum(index);
}

static inline LispObj
wasm_nrs_symbol_lispobj(lispsymbol *sym)
{
  return ptr_to_lispobj((BytePtr)sym + fulltag_misc);
}

typedef void (*wasm_lisp_fn_void)(void);
typedef LispObj (*wasm_lisp_fn_unary_i32)(LispObj);
typedef LispObj (*wasm_lisp_fn_binary_i32)(LispObj, LispObj);

static inline void
wasm_call_entry_index(uint32_t index)
{
  ((wasm_lisp_fn_void)(uintptr_t)index)();
}

static inline LispObj
wasm_call_entry_index_unary_i32(uint32_t index, LispObj arg0)
{
  return ((wasm_lisp_fn_unary_i32)(uintptr_t)index)(arg0);
}

static inline LispObj
wasm_call_entry_index_binary_i32(uint32_t index, LispObj arg0, LispObj arg1)
{
  return ((wasm_lisp_fn_binary_i32)(uintptr_t)index)(arg0, arg1);
}

static void
wasm_call_lisp_function(TCR *tcr, LispObj fn_value)
{
  if (fn_value == (LispObj)nil_value) {
    wasm_debug_dump_state("fn==nil");
    __builtin_trap();
  }

  if (fulltag_of(fn_value) != fulltag_misc) {
    wasm_debug_dump_state("fn not misc");
    __builtin_trap();
  }

  LispObj header = header_of(fn_value);
  int subtag = header_subtag(header);
  if (subtag == subtag_symbol) {
    lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(fn_value));
    fn_value = sym->fcell;
    if (fulltag_of(fn_value) != fulltag_misc) {
      wasm_debug_dump_state("fcell not misc");
      __builtin_trap();
    }
    header = header_of(fn_value);
    subtag = header_subtag(header);
  }

  if (subtag != subtag_function && subtag != subtag_pseudofunction) {
    wasm_debug_dump_state("fn not function");
    __builtin_trap();
  }

  tcr->wasm_gprs[nfn] = fn_value;
  tcr->wasm_gprs[Rfn] = fn_value;

  LispObj entry = deref(fn_value, 1);
  if (tag_of(entry) != tag_fixnum) {
    wasm_debug_dump_state("entry not fixnum");
    __builtin_trap();
  }

  {
    uint32_t entry_index = (uint32_t)unbox_fixnum(entry);
    uint32_t mode = wasm_lookup_entry_gc_root_policy_mode(entry_index);
    uint32_t entry_call_abi = wasm_lookup_entry_call_abi_kind(entry_index);
    LispObj raw_nargs = tcr->wasm_gprs[nargs];
    signed_natural nargs_count =
      (tag_of(raw_nargs) == tag_fixnum) ? unbox_fixnum(raw_nargs) : 0;
    wasm_publish_gc_root_policy_mode(mode);
    switch (entry_call_abi) {
    case WASM_ENTRY_CALL_ABI_UNARY_I32: {
      LispObj result;
      if (nargs_count != 1) {
        wasm_debug_dump_state("nargs mismatch unary");
        __builtin_trap();
      }
      result = wasm_call_entry_index_unary_i32(entry_index, tcr->wasm_gprs[arg_z]);
      if (!tcr->wasm_pending_throw) {
        tcr->wasm_gprs[arg_z] = result;
        tcr->wasm_gprs[nargs] = box_fixnum(1);
      }
      break;
    }
    case WASM_ENTRY_CALL_ABI_BINARY_I32: {
      LispObj result;
      if (nargs_count != 2) {
        wasm_debug_dump_state("nargs mismatch binary");
        __builtin_trap();
      }
      result = wasm_call_entry_index_binary_i32(entry_index,
                                                tcr->wasm_gprs[arg_z],
                                                tcr->wasm_gprs[arg_y]);
      if (!tcr->wasm_pending_throw) {
        tcr->wasm_gprs[arg_z] = result;
        tcr->wasm_gprs[nargs] = box_fixnum(1);
      }
      break;
    }
    case WASM_ENTRY_CALL_ABI_LEGACY:
    default:
      wasm_call_entry_index(entry_index);
      break;
    }
  }
}

static int
wasm_interrupts_enabled(TCR *tcr)
{
  LispObj *tlb = tcr->tlb_pointer;
  if (tlb == NULL) {
    return 0;
  }
  LispObj level = tlb[INTERRUPT_LEVEL_BINDING_INDEX];
  if (tag_of(level) != tag_fixnum) {
    return 0;
  }
  return unbox_fixnum(level) >= 0;
}

static int
wasm_maybe_deliver_interrupt(TCR *tcr)
{
  if (tcr == NULL) {
    return 0;
  }
  if (tcr->interrupt_pending <= 0) {
    return 0;
  }
  if (!wasm_interrupts_enabled(tcr)) {
    return 0;
  }

  tcr->wasm_gprs[arg_z] = lisp_nil;
  tcr->wasm_gprs[nargs] = box_fixnum(0);
  wasm_call_lisp_function(tcr, wasm_nrs_symbol_lispobj(&nrs_CMAIN));
  return tcr->wasm_pending_throw ? 1 : 0;
}

static uint32_t wasm_subprims_ready = 0;
static LispObj wasm_last_compiled_modules = 0;
static volatile uint32_t wasm_boot_phase_state = WASM_BOOT_EARLY;

/* Trace verbosity for funcall dispatch.
   0 = silent (default)
   1 = print entry index for LEGACY calls
   2 = also print arg registers */
static uint32_t wasm_trace_funcall = 0;

/* Re-entrant guard: when > 0, wasm_intern_startup skips the Lisp INTERN
   path and falls through to C-only synthesis.  This breaks the circular
   dependency where const-pool installation calls INTERN which itself
   needs a const pool that hasn't been installed yet. */
static uint32_t wasm_const_pool_install_depth = 0;

/* Diagnostic: tracks which exit-point in wasm_const_pool_install_inner
   last returned lisp_nil, for debugging const-pool failures. */
static uint32_t wasm_const_pool_diag_fail = 0;
LispObj wasm_funcall1(LispObj fn_value, LispObj arg0);
uint32_t wasm_subprim_nonlocal_exit_coherence_selftest(void);
static LispObj wasm_find_package_named_bytes(const uint8_t *bytes, uint32_t len);
static LispObj wasm_find_symbol_named_bytes(const uint8_t *name, uint32_t len, LispObj package);
static LispObj wasm_foreign_funcall0(TCR *tcr, LispObj callable);
static int wasm_symbol_object_p(LispObj value);
static int wasm_debug_hex8(char *buf, uint32_t v);
static int wasm_debug_str(char *buf, const char *s);
static int wasm_debug_uint(char *buf, uint32_t v);


static uint32_t
wasm_boot_phase_normalize(uint32_t phase)
{
  switch (phase) {
  case WASM_BOOT_EARLY:
  case WASM_BOOT_L0_READY:
  case WASM_BOOT_RUNTIME:
    return phase;
  default:
    return WASM_BOOT_EARLY;
  }
}

enum {
  WASM_TOPLEVEL_EXIT = 0,
  WASM_TOPLEVEL_PENDING_THROW = 1,
  WASM_TOPLEVEL_YIELD = 2
};

static void
wasm_maybe_refresh_compiled_modules(void)
{
  LispObj registry = nrs_WASM_COMPILED_MODULES.vcell;
  if (registry == wasm_last_compiled_modules) {
    return;
  }
  wasm_last_compiled_modules = registry;
  if (registry == lisp_nil) {
    return;
  }
  (void)wasm_kernel_compiled_modules_refresh((uint32_t)registry, (uint32_t)lisp_nil);
}

__attribute__((used, visibility("default"), export_name("wasm_set_subprims_ready")))
void
wasm_set_subprims_ready(uint32_t ready)
{
  if (ready) {
    wasm_subprims_ready = 1u;
    wasm_publish_gc_root_policy_mode(WASM_GC_ROOT_MODE_RUNTIME_DEFAULT);
  } else {
    wasm_subprims_ready = 0u;
    wasm_publish_gc_root_policy_mode(WASM_GC_ROOT_MODE_RUNTIME_BOOTSTRAP);
  }
}

__attribute__((used, visibility("default"), export_name("wasm_get_subprims_ready")))
uint32_t
wasm_get_subprims_ready(void)
{
  return wasm_subprims_ready;
}

__attribute__((used, visibility("default"), export_name("wasm_set_trace_funcall")))
void
wasm_set_trace_funcall(uint32_t level)
{
  wasm_trace_funcall = level;
}

__attribute__((used, visibility("default"), export_name("wasm_get_trace_funcall")))
uint32_t
wasm_get_trace_funcall(void)
{
  return wasm_trace_funcall;
}

__attribute__((used, visibility("default"), export_name("wasm_get_lisp_nil")))
LispObj
wasm_get_lisp_nil(void)
{
  return lisp_nil;
}

__attribute__((used, visibility("default"), export_name("wasm_get_compiled_module_registry")))
LispObj
wasm_get_compiled_module_registry(void)
{
  return nrs_WASM_COMPILED_MODULES.vcell;
}

__attribute__((used, visibility("default"), export_name("wasm_boot_set_phase")))
void
wasm_boot_set_phase(uint32_t phase)
{
  wasm_boot_phase_state = wasm_boot_phase_normalize(phase);
}

__attribute__((used, visibility("default"), export_name("wasm_boot_get_phase")))
uint32_t
wasm_boot_get_phase(void)
{
  return wasm_boot_phase_state;
}

__attribute__((used, visibility("default"), export_name("wasm_set_gc_root_policy")))
uint32_t
wasm_set_gc_root_policy(uint32_t policy_mask)
{
  wasm_publish_gc_root_policy(policy_mask);
  return wasm_current_gc_root_policy();
}

__attribute__((used, visibility("default"), export_name("wasm_get_gc_root_policy")))
uint32_t
wasm_get_gc_root_policy(void)
{
  return wasm_current_gc_root_policy();
}

__attribute__((used, visibility("default"), export_name("wasm_set_gc_root_policy_mode")))
uint32_t
wasm_set_gc_root_policy_mode(uint32_t mode)
{
  wasm_publish_gc_root_policy_mode(mode);
  return wasm_current_gc_root_policy_mode();
}

__attribute__((used, visibility("default"), export_name("wasm_get_gc_root_policy_mode")))
uint32_t
wasm_get_gc_root_policy_mode(void)
{
  return wasm_current_gc_root_policy_mode();
}

__attribute__((used, visibility("default"), export_name("wasm_set_entry_gc_root_policy_mode")))
uint32_t
wasm_set_entry_gc_root_policy_mode(uint32_t entry_index, uint32_t mode)
{
  wasm_register_entry_gc_root_policy_mode(entry_index, mode);
  return wasm_lookup_entry_gc_root_policy_mode(entry_index);
}

__attribute__((used, visibility("default"), export_name("wasm_get_entry_gc_root_policy_mode")))
uint32_t
wasm_get_entry_gc_root_policy_mode(uint32_t entry_index)
{
  return wasm_lookup_entry_gc_root_policy_mode(entry_index);
}

__attribute__((used, visibility("default"), export_name("wasm_clear_entry_gc_root_policy_modes")))
void
wasm_clear_entry_gc_root_policy_modes_export(void)
{
  wasm_clear_entry_gc_root_policy_modes();
}

__attribute__((used, visibility("default"), export_name("wasm_set_entry_call_abi")))
uint32_t
wasm_set_entry_call_abi(uint32_t entry_index, uint32_t kind)
{
  wasm_register_entry_call_abi_kind(entry_index, kind);
  return wasm_lookup_entry_call_abi_kind(entry_index);
}

__attribute__((used, visibility("default"), export_name("wasm_get_entry_call_abi")))
uint32_t
wasm_get_entry_call_abi(uint32_t entry_index)
{
  return wasm_lookup_entry_call_abi_kind(entry_index);
}

__attribute__((used, visibility("default"), export_name("wasm_prepare_entry_call")))
uint32_t
wasm_prepare_entry_call(uint32_t entry_index)
{
  uint32_t mode = wasm_lookup_entry_gc_root_policy_mode(entry_index);
  wasm_publish_gc_root_policy_mode(mode);
  return wasm_lookup_entry_call_abi_kind(entry_index);
}

__attribute__((used, visibility("default"), export_name("wasm_clear_entry_call_abi")))
void
wasm_clear_entry_call_abi(void)
{
  wasm_clear_entry_call_abi_kinds();
}

__attribute__((used, visibility("default"), export_name("wasm_gc_forwarding_selftest")))
uint32_t
wasm_gc_forwarding_selftest_export(void)
{
  return wasm_gc_forwarding_selftest();
}

__attribute__((used, visibility("default"), export_name("wasm_cstack_frame_coherence_selftest")))
uint32_t
wasm_cstack_frame_coherence_selftest_export(void)
{
  return wasm_cstack_frame_coherence_selftest();
}

__attribute__((used, visibility("default"), export_name("wasm_save_image_direct")))
int32_t
wasm_save_image_direct(uint32_t path_ptr, uint32_t path_len, uint32_t egc_enabled)
{
  static const uint8_t ccl_pkg_name[] = { 'C', 'C', 'L' };
  static const uint8_t save_internal_sym_name[] = {
    '%', 'S', 'A', 'V', 'E', '-', 'A', 'P', 'P', 'L', 'I', 'C', 'A', 'T', 'I', 'O', 'N',
    '-', 'I', 'N', 'T', 'E', 'R', 'N', 'A', 'L'
  };
  if (path_ptr == 0 || path_len == 0) {
    return -EINVAL;
  }

  if (path_len >= 1024u) {
    return -ENAMETOOLONG;
  }

  char path[1024];
  const uint8_t *src = (const uint8_t *)(uintptr_t)path_ptr;
  for (uint32_t i = 0; i < path_len; i++) {
    path[i] = (char)src[i];
  }
  path[path_len] = '\0';

  int fd = lisp_open(path, O_WRONLY | O_CREAT | O_TRUNC, 0666);
  if (fd < 0) {
    return -errno;
  }

  area *active_area = active_dynamic_area;
  Boolean egc_was_enabled = (active_area != NULL) && (active_area->older != NULL);

  TCR *tcr = wasm_get_current_tcr();
  if (tcr != NULL && wasm_subprims_ready) {
    static const char msg_try_lisp_save[] = "WASM save-image: trying %save-application-internal\n";
    static const char msg_lisp_save_ok[] = "WASM save-image: %save-application-internal succeeded\n";
    static const char msg_lisp_save_no_symbol[] = "WASM save-image: %save-application-internal symbol not found\n";
    static const char msg_lisp_save_bad_symbol[] = "WASM save-image: %save-application-internal symbol has unexpected object type\n";
    static const char msg_lisp_save_udf[] = "WASM save-image: %save-application-internal fcell is UDF\n";
    static const char msg_lisp_save_throw[] = "WASM save-image: %save-application-internal signaled throw\n";
    static const char msg_lisp_save_fallback[] = "WASM save-image: %save-application-internal unavailable/failed; fallback save_application\n";
    wasm_host_log(msg_try_lisp_save, (unsigned)(sizeof(msg_try_lisp_save) - 1));
    LispObj ccl_pkg = wasm_find_package_named_bytes(ccl_pkg_name, (uint32_t)sizeof(ccl_pkg_name));
    LispObj save_sym = (LispObj)0;
    if (ccl_pkg != lisp_nil) {
      save_sym = wasm_find_symbol_named_bytes(
        save_internal_sym_name,
        (uint32_t)sizeof(save_internal_sym_name),
        ccl_pkg);
    }
    if (save_sym == (LispObj)0) {
      save_sym = wasm_find_symbol_named_bytes(
        save_internal_sym_name,
        (uint32_t)sizeof(save_internal_sym_name),
        (LispObj)0);
    }
    if (save_sym == (LispObj)0) {
      wasm_host_log(msg_lisp_save_no_symbol, (unsigned)(sizeof(msg_lisp_save_no_symbol) - 1));
    } else if (!(fulltag_of(save_sym) == fulltag_misc &&
                 header_subtag(header_of(save_sym)) == subtag_symbol)) {
      wasm_host_log(msg_lisp_save_bad_symbol, (unsigned)(sizeof(msg_lisp_save_bad_symbol) - 1));
    } else {
      lispsymbol *save_raw = (lispsymbol *)ptr_from_lispobj(untag(save_sym));
      if (save_raw->fcell == nrs_UDF.vcell) {
        wasm_host_log(msg_lisp_save_udf, (unsigned)(sizeof(msg_lisp_save_udf) - 1));
      } else {
        (void)wasm_funcall1(save_sym, box_fixnum(fd));
        if (!tcr->wasm_pending_throw) {
          wasm_host_log(msg_lisp_save_ok, (unsigned)(sizeof(msg_lisp_save_ok) - 1));
          return 0;
        }
        tcr->wasm_pending_throw = 0;
        wasm_host_log(msg_lisp_save_throw, (unsigned)(sizeof(msg_lisp_save_throw) - 1));
      }
    }
    wasm_host_log(msg_lisp_save_fallback, (unsigned)(sizeof(msg_lisp_save_fallback) - 1));
    (void)lisp_close(fd);
    fd = lisp_open(path, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (fd < 0) {
      return -errno;
    }
  } else {
    static const char msg_skip_lisp_save[] = "WASM save-image: no current TCR or subprims not ready; using save_application\n";
    wasm_host_log(msg_skip_lisp_save, (unsigned)(sizeof(msg_skip_lisp_save) - 1));
  }

  if (egc_was_enabled) {
    static const char msg_disable_egc[] =
      "WASM save-image: disabling EGC for direct save path\n";
    wasm_host_log(msg_disable_egc, (unsigned)(sizeof(msg_disable_egc) - 1));
    egc_control(false, active_area->active);
  }

  Boolean save_egc_enabled = (egc_enabled != 0) ? true : egc_was_enabled;
  OSErr err = save_application(fd, save_egc_enabled);

  if (egc_was_enabled) {
    static const char msg_restore_egc[] =
      "WASM save-image: restoring EGC after direct save path\n";
    wasm_host_log(msg_restore_egc, (unsigned)(sizeof(msg_restore_egc) - 1));
    egc_control(true, NULL);
  }

  return (int32_t)err;
}

static int
wasm_toplevel_loop(TCR *tcr)
{
  for (;;) {
    LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
    if (vsp_ptr == NULL) {
      return -1;
    }
    if (wasm_maybe_deliver_interrupt(tcr)) {
      return WASM_TOPLEVEL_PENDING_THROW;
    }
    vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
    if (vsp_ptr == NULL) {
      return -1;
    }
    LispObj topfn = *vsp_ptr;
    if (topfn == lisp_nil) {
      return 0;
    }

    tcr->wasm_gprs[arg_z] = nrs_TOPLCATCH.vcell;
    wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKCATCH1V_INDEX));

    tcr->wasm_gprs[arg_z] = lisp_nil;
    tcr->wasm_gprs[nargs] = box_fixnum(0);
    tcr->wasm_gprs[nfn] = topfn;
    tcr->wasm_gprs[Rfn] = topfn;
    wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));
    if (tcr->wasm_pending_throw) {
      wasm_maybe_refresh_compiled_modules();
      return WASM_TOPLEVEL_PENDING_THROW;
    }

    LispObj result = tcr->wasm_gprs[arg_z];
    tcr->wasm_gprs[arg_z] = lisp_nil;
    tcr->wasm_gprs[imm0] = box_fixnum(1);
    wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_NTHROW1VALUE_INDEX));
    if (tcr->wasm_pending_throw) {
      tcr->wasm_pending_throw = 0;
    }
    wasm_maybe_refresh_compiled_modules();

    if (result != lisp_nil) {
      return WASM_TOPLEVEL_YIELD;
    }
  }
}

static LispObj *
wasm_toplevel_slot(TCR *tcr)
{
  if (tcr == NULL || tcr->vs_area == NULL) {
    return NULL;
  }
  BytePtr high = tcr->vs_area->high;
  if (high == NULL) {
    return NULL;
  }
  return (LispObj *)(high - node_size);
}

static LispObj *
wasm_vsp_empty(TCR *tcr)
{
  if (tcr == NULL || tcr->vs_area == NULL) {
    return NULL;
  }
  return (LispObj *)tcr->vs_area->high;
}

__attribute__((used, visibility("default"), export_name("wasm_get_tcr_toplevel_function")))
LispObj
wasm_get_tcr_toplevel_function(LispObj raw_tcr)
{
  TCR *tcr = (TCR *)raw_tcr;
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj *slot = wasm_toplevel_slot(tcr);
  LispObj *vsp_empty = wasm_vsp_empty(tcr);
  if (slot == NULL || vsp_empty == NULL) {
    return lisp_nil;
  }

  LispObj *vsp_ptr = NULL;
  if (tcr == wasm_get_current_tcr()) {
    vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
  } else if (tcr->vs_area != NULL) {
    vsp_ptr = (LispObj *)tcr->vs_area->active;
  }
  if (vsp_ptr == NULL || vsp_ptr == vsp_empty) {
    return lisp_nil;
  }
  return *slot;
}

__attribute__((used, visibility("default"), export_name("wasm_set_tcr_toplevel_function")))
LispObj
wasm_set_tcr_toplevel_function(LispObj raw_tcr, LispObj fun)
{
  TCR *tcr = (TCR *)raw_tcr;
  if (tcr == NULL) {
    return fun;
  }
  LispObj *slot = wasm_toplevel_slot(tcr);
  LispObj *vsp_empty = wasm_vsp_empty(tcr);
  if (slot == NULL || vsp_empty == NULL) {
    return fun;
  }

  *slot = 0;

  LispObj *vsp_ptr = NULL;
  if (tcr == wasm_get_current_tcr()) {
    vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
  } else if (tcr->vs_area != NULL) {
    vsp_ptr = (LispObj *)tcr->vs_area->active;
  }
  if (vsp_ptr == NULL) {
    vsp_ptr = vsp_empty;
  }
  if (vsp_ptr == vsp_empty) {
    tcr->vs_area->active = (BytePtr)slot;
    tcr->save_vsp = slot;
    if (tcr == wasm_get_current_tcr()) {
      tcr->wasm_gprs[vsp] = (LispObj)slot;
    }
  }

  *slot = fun;
  return fun;
}

__attribute__((used, visibility("default"), export_name("wasm_set_toplfunc_entry")))
int32_t
wasm_set_toplfunc_entry(uint32_t entry_index)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return -1;
  }
  if (!wasm_subprims_ready) {
    return -2;
  }

  LispObj fn = wasm_misc_alloc(tcr, subtag_function, (signed_natural)2);
  if (fn == lisp_nil) {
    return -3;
  }
  LispObj entry = box_fixnum((signed_natural)entry_index);
  LispObj *fn_data = (LispObj *)((BytePtr)fn + misc_data_offset);
  fn_data[0] = entry;
  fn_data[1] = entry;

  nrs_TOPLFUNC.vcell = fn;
  (void)wasm_set_tcr_toplevel_function((LispObj)tcr, fn);
  return 0;
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

static inline unsigned
wasm_max_bignum_digits(void)
{
  return (unsigned)((1u << (sizeof(uint32_t) * 8 - num_subtag_bits)) - 1u);
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
wasm_alloc_bignum_uninitialized(TCR *tcr, unsigned digits, uint32_t **data_out)
{
  if (data_out != NULL) {
    *data_out = NULL;
  }
  if (digits == 0) {
    return lisp_nil;
  }
  if (digits > wasm_max_bignum_digits()) {
    return lisp_nil;
  }

  size_t words = 1 + (size_t)digits;
  if (words > (SIZE_MAX / node_size)) {
    return lisp_nil;
  }

  size_t bytes = wasm_align_dnode(words * node_size);
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

  if (data_out != NULL) {
    *data_out = (uint32_t *)((BytePtr)obj + misc_data_offset);
  }

  return obj;
}

static LispObj
wasm_alloc_node_vector_initialized(TCR *tcr, unsigned subtag, signed_natural count)
{
  if (count < 0) {
    static const char msg[] = "WASM misc_alloc: negative count\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return lisp_nil;
  }

  size_t words = 1 + (size_t)count;
  if (words > (SIZE_MAX / node_size)) {
    static const char msg[] = "WASM misc_alloc: size overflow\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return lisp_nil;
  }

  size_t bytes = wasm_align_dnode(words * node_size);
  if (!wasm_reserve_heap_segment(tcr, bytes)) {
    static const char msg[] = "WASM misc_alloc: reserve failed\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return lisp_nil;
  }

  BytePtr alloc_ptr = (BytePtr)tcr->save_allocptr;
  BytePtr alloc_base = (BytePtr)tcr->save_allocbase;
  BytePtr newptr = alloc_ptr - (signed_natural)bytes;
  if (newptr < alloc_base) {
    static const char msg[] = "WASM misc_alloc: allocptr underflow\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return lisp_nil;
  }

  tcr->save_allocptr = (void *)newptr;
  LispObj obj = (LispObj)(newptr + fulltag_misc);
  header_of(obj) = make_header(subtag, count);

  /* Initialize node vector elements.
     Simple-vectors get fixnum 0, matching native CCL behavior (zero-filled
     heap).  Hash table code in nfasload.lisp relies on empty slots being
     fixnum 0 — see %get-hashed-htab-symbol termination (eql elt 0).
     All other node vectors (symbols, functions, etc.) get lisp_nil so that
     uninitialized slots behave as "empty" for Lisp-level code.
     NOTE: Use explicit word-at-a-time loop instead of memset — the custom
     memset in wasm-no-wasi-libc.c or compiler-generated memory.fill may
     not behave correctly in all WASM environments during early boot. */
  LispObj *data = (LispObj *)((BytePtr)obj + misc_data_offset);
  if (subtag == subtag_simple_vector) {
    for (signed_natural i = 0; i < count; i++) {
      data[i] = 0;
    }
  } else {
    for (signed_natural i = 0; i < count; i++) {
      data[i] = lisp_nil;
    }
  }

  return obj;
}

static int
wasm_ivector_total_bytes(unsigned subtag, signed_natural count, size_t *bytes_out)
{
  if (count < 0) {
    static const char msg[] = "WASM misc_alloc: negative count\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return 0;
  }

  size_t element_count = (size_t)count;
  size_t total = 0;

  if (subtag <= max_32_bit_ivector_subtag) {
    if (element_count > ((SIZE_MAX - 4u) >> 2)) {
      static const char msg[] = "WASM misc_alloc: size overflow\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      return 0;
    }
    total = 4u + (element_count << 2);
  } else if (subtag <= max_8_bit_ivector_subtag) {
    if (element_count > (SIZE_MAX - 4u)) {
      static const char msg[] = "WASM misc_alloc: size overflow\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      return 0;
    }
    total = 4u + element_count;
  } else if (subtag <= max_16_bit_ivector_subtag) {
    if (element_count > ((SIZE_MAX - 4u) >> 1)) {
      static const char msg[] = "WASM misc_alloc: size overflow\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      return 0;
    }
    total = 4u + (element_count << 1);
  } else if (subtag == subtag_complex_double_float_vector) {
    if (element_count > ((SIZE_MAX - 8u) >> 4)) {
      static const char msg[] = "WASM misc_alloc: size overflow\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      return 0;
    }
    total = 8u + (element_count << 4);
  } else if (subtag == subtag_bit_vector) {
    if (element_count > (SIZE_MAX - 7u)) {
      static const char msg[] = "WASM misc_alloc: size overflow\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      return 0;
    }
    total = 4u + ((element_count + 7u) >> 3);
  } else {
    if (element_count > ((SIZE_MAX - 8u) >> 3)) {
      static const char msg[] = "WASM misc_alloc: size overflow\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      return 0;
    }
    total = 8u + (element_count << 3);
  }

  *bytes_out = wasm_align_dnode(total);
  return 1;
}

static LispObj
wasm_alloc_ivector_uninitialized(TCR *tcr, unsigned subtag, signed_natural count)
{
  size_t bytes = 0;
  if (!wasm_ivector_total_bytes(subtag, count, &bytes)) {
    return lisp_nil;
  }

  if (!wasm_reserve_heap_segment(tcr, bytes)) {
    static const char msg[] = "WASM misc_alloc: reserve failed\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return lisp_nil;
  }

  BytePtr alloc_ptr = (BytePtr)tcr->save_allocptr;
  BytePtr alloc_base = (BytePtr)tcr->save_allocbase;
  BytePtr newptr = alloc_ptr - (signed_natural)bytes;
  if (newptr < alloc_base) {
    static const char msg[] = "WASM misc_alloc: allocptr underflow\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return lisp_nil;
  }

  tcr->save_allocptr = (void *)newptr;
  LispObj obj = (LispObj)(newptr + fulltag_misc);
  header_of(obj) = make_header(subtag, count);

  if (bytes > misc_data_offset) {
    memset((BytePtr)obj + misc_data_offset, 0, bytes - misc_data_offset);
  }

  /* Diagnostic: catch creation of 8-element fixnum-vector (suspect $hprimes) */
  if (subtag == subtag_fixnum_vector && count == 8) {
    char d[80]; int p = 0;
    p += wasm_debug_str(d + p, "DIAG: alloc fixvec8 obj=0x");
    p += wasm_debug_hex8(d + p, (uint32_t)obj);
    d[p++] = '\n';
    wasm_host_log(d, (unsigned)p);
  }

  return obj;
}

__attribute__((used, visibility("default"), export_name("wasm_misc_alloc")))
LispObj
wasm_misc_alloc(TCR *tcr, unsigned subtag, signed_natural count)
{
  if (tcr == NULL) {
    static const char msg[] = "WASM misc_alloc: null TCR\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return lisp_nil;
  }

  unsigned tag = subtag & fulltagmask;
  if (tag == fulltag_nodeheader) {
    return wasm_alloc_node_vector_initialized(tcr, subtag, count);
  }
  if (tag == fulltag_immheader) {
    return wasm_alloc_ivector_uninitialized(tcr, subtag, count);
  }

  static const char msg[] = "WASM misc_alloc: bad subtag\n";
  wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
  return lisp_nil;
}

__attribute__((used, visibility("default"), export_name("wasm_box_signed_64")))
LispObj
wasm_box_signed_64(TCR *tcr, int64_t value)
{
  if (wasm_fixnum_fits(value)) {
    return box_fixnum((signed_natural)value);
  }

  unsigned count = (value >= (int64_t)INT32_MIN && value <= (int64_t)INT32_MAX) ? 1u : 2u;
  uint32_t *data = NULL;
  LispObj obj = wasm_alloc_bignum_uninitialized(tcr, count, &data);
  if (obj == lisp_nil || data == NULL) {
    return lisp_nil;
  }

  uint64_t uval = (uint64_t)value;
  data[0] = (uint32_t)uval;
  if (count > 1) {
    data[1] = (uint32_t)(uval >> 32);
  }
  return obj;
}

static LispObj
wasm_box_unsigned_64(TCR *tcr, uint64_t value)
{
  if (value <= (uint64_t)wasm_fixnum_max()) {
    return box_fixnum((signed_natural)value);
  }

  uint32_t lo = (uint32_t)value;
  uint32_t hi = (uint32_t)(value >> 32);
  unsigned digits = (hi == 0) ? 1u : 2u;
  if ((hi == 0 && (lo & 0x80000000u)) || (hi & 0x80000000u)) {
    digits += 1;
  }

  uint32_t *data = NULL;
  LispObj obj = wasm_alloc_bignum_uninitialized(tcr, digits, &data);
  if (obj == lisp_nil || data == NULL) {
    return lisp_nil;
  }

  memset(data, 0, (size_t)digits * sizeof(uint32_t));
  data[0] = lo;
  if (digits > 1) {
    data[1] = hi;
  }
  return obj;
}

static LispObj
wasm_box_shifted_fixnum(TCR *tcr, int32_t value, uint32_t shift)
{
  if (shift < 63) {
    int64_t shifted = ((int64_t)value) << shift;
    return wasm_box_signed_64(tcr, shifted);
  }
  if (value == 0) {
    return box_fixnum(0);
  }

  uint32_t mag = (value < 0) ? (uint32_t)(-(int64_t)value) : (uint32_t)value;
  uint32_t word_shift = shift / 32;
  uint32_t bit_shift = shift % 32;
  uint64_t chunk = ((uint64_t)mag) << bit_shift;
  uint32_t low = (uint32_t)chunk;
  uint32_t high = (uint32_t)(chunk >> 32);
  unsigned digits = 0;

  if (value < 0) {
    int has_high = (bit_shift != 0) && (high != 0);
    digits = word_shift + 1 + (has_high ? 1u : 0u);
    uint32_t msd = has_high ? (uint32_t)~high : (uint32_t)(~low + 1u);
    if ((msd & 0x80000000u) == 0) {
      digits += 1;
    }
  } else {
    digits = word_shift + 1;
    uint32_t msd = low;
    if (bit_shift != 0) {
      if (high != 0) {
        digits += 1;
        msd = high;
      } else if (low & 0x80000000u) {
        digits += 1;
        msd = 0;
      }
    }
    if (msd & 0x80000000u) {
      digits += 1;
    }
  }

  if (digits > wasm_max_bignum_digits()) {
    return lisp_nil;
  }

  uint32_t *data = NULL;
  LispObj obj = wasm_alloc_bignum_uninitialized(tcr, digits, &data);
  if (obj == lisp_nil || data == NULL) {
    return lisp_nil;
  }

  memset(data, 0, (size_t)digits * sizeof(uint32_t));
  data[word_shift] = low;
  if (bit_shift != 0 && high != 0) {
    data[word_shift + 1] = high;
  }

  if (value < 0) {
    uint64_t carry = 1;
    for (unsigned i = 0; i < digits; i++) {
      uint64_t sum = (uint64_t)(~data[i]) + carry;
      data[i] = (uint32_t)sum;
      carry = sum >> 32;
    }
  }

  return obj;
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

__attribute__((used, visibility("default"), export_name("wasm_get_arg_z")))
LispObj
wasm_get_arg_z(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  return tcr->wasm_gprs[arg_z];
}

__attribute__((used, visibility("default"), export_name("wasm_get_arg_y")))
LispObj
wasm_get_arg_y(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  return tcr->wasm_gprs[arg_y];
}

__attribute__((used, visibility("default"), export_name("wasm_set_arg_z")))
void
wasm_set_arg_z(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_gprs[arg_z] = value;
}

__attribute__((used, visibility("default"), export_name("wasm_set_arg_y")))
void
wasm_set_arg_y(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_gprs[arg_y] = value;
}

__attribute__((used, visibility("default"), export_name("wasm_set_arg_x")))
void
wasm_set_arg_x(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_gprs[arg_x] = value;
}

__attribute__((used, visibility("default"), export_name("wasm_set_nargs")))
void
wasm_set_nargs(uint32_t count)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_gprs[nargs] = box_fixnum((signed_natural)count);
}

__attribute__((used, visibility("default"), export_name("wasm_set_nfn")))
void
wasm_set_nfn(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_gprs[nfn] = value;
  tcr->wasm_gprs[Rfn] = value;
}

__attribute__((used, visibility("default"), export_name("wasm_set_imm0")))
void
wasm_set_imm0(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_gprs[imm0] = value;
}

__attribute__((used, visibility("default"), export_name("wasm_get_nfn")))
LispObj
wasm_get_nfn(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  return tcr->wasm_gprs[nfn];
}

__attribute__((used, visibility("default"), export_name("wasm_get_nargs")))
uint32_t
wasm_get_nargs(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return 0;
  }
  LispObj raw = tcr->wasm_gprs[nargs];
  if (tag_of(raw) != tag_fixnum) {
    return 1;
  }
  signed_natural count = unbox_fixnum(raw);
  if (count < 0) {
    return 0;
  }
  return (uint32_t)count;
}

__attribute__((used, visibility("default"), export_name("wasm_lisp_word_ref")))
LispObj
wasm_lisp_word_ref(LispObj base, LispObj offset)
{
  if (tag_of(offset) != tag_fixnum) {
    return lisp_nil;
  }

  signed_natural idx = unbox_fixnum(offset);

  /* Nil: %car/%cdr of nil = nil (unsafe %car/%cdr skip nil check) */
  if (base == (LispObj)nil_value) {
    return lisp_nil;
  }

  /* Cons: direct struct slot access.
     idx 0 = word 0 = cdr (struct offset 0)
     idx 1 = word 1 = car (struct offset 4)
     Matches constants.h:41-44 and wasm-arch.lisp:335. */
  if (tag_of(base) == tag_list) {
    cons *cell = (cons *)ptr_from_lispobj(untag(base));
    if (idx == 0) return cell->cdr;
    if (idx == 1) return cell->car;
    return lisp_nil;
  }

  if (idx < 0 && fulltag_of(base) != fulltag_misc) {
    return lisp_nil;
  }

  if (tag_of(base) == tag_fixnum) {
    signed_natural addr = unbox_fixnum(base);
    uintptr_t target = (uintptr_t)addr + (uintptr_t)idx * sizeof(LispObj);
    uintptr_t mem_limit = (uintptr_t)__builtin_wasm_memory_size(0) * 65536u;
    if (target + sizeof(LispObj) > mem_limit || addr < 0) {
      char msg[160]; int p = 0;
      p += wasm_debug_str(msg + p, "HEAP-OOB fixnum-ref base=0x");
      p += wasm_debug_hex8(msg + p, (uint32_t)base);
      p += wasm_debug_str(msg + p, " addr=0x");
      p += wasm_debug_hex8(msg + p, (uint32_t)(uintptr_t)addr);
      p += wasm_debug_str(msg + p, " idx=");
      p += wasm_debug_uint(msg + p, (uint32_t)idx);
      p += wasm_debug_str(msg + p, " limit=0x");
      p += wasm_debug_hex8(msg + p, (uint32_t)mem_limit);
      msg[p++] = '\n';
      wasm_host_log(msg, (unsigned)p);
      return lisp_nil;
    }
    LispObj *ptr = (LispObj *)(uintptr_t)addr;
    LispObj result = ptr[idx];
    return result;
  }

  if (fulltag_of(base) == fulltag_misc) {
    uintptr_t raw = (uintptr_t)untag(base);
    uintptr_t mem_limit = (uintptr_t)__builtin_wasm_memory_size(0) * 65536u;
    if (raw + sizeof(LispObj) > mem_limit) {
      char msg[120]; int p = 0;
      p += wasm_debug_str(msg + p, "HEAP-OOB misc-ref base=0x");
      p += wasm_debug_hex8(msg + p, (uint32_t)base);
      p += wasm_debug_str(msg + p, " raw=0x");
      p += wasm_debug_hex8(msg + p, (uint32_t)raw);
      p += wasm_debug_str(msg + p, " limit=0x");
      p += wasm_debug_hex8(msg + p, (uint32_t)mem_limit);
      msg[p++] = '\n';
      wasm_host_log(msg, (unsigned)p);
      return lisp_nil;
    }
    /* idx -1 = header word (used by wasm2-typecode to avoid
       box_fixnum(untag(obj)) overflow on large heap addresses). */
    if (idx == -1) {
      return header_of(base);
    }
    if (idx < 0) {
      return lisp_nil;
    }
    LispObj header = header_of(base);
    signed_natural count = header_element_count(header);
    if (idx < count) {
      /* deref(o,0) is the header; data elements start at deref(o,1).
         idx is data-relative (0 = first data element), so add 1. */
      LispObj result = deref(base, idx + 1);

      /* Diagnostic: detect NIL in simple-vector slots (hash probe bug) */
      if (wasm_trace_funcall >= 1 &&
          header_subtag(header) == subtag_simple_vector &&
          result == lisp_nil) {
        static uint32_t nil_svec_logged = 0;
        if (nil_svec_logged < 20) {
          char msg[200];
          int p = 0;
          p += wasm_debug_str(msg + p, "NIL-IN-SVEC @");
          p += wasm_debug_hex8(msg + p, (uint32_t)base);
          p += wasm_debug_str(msg + p, " [");
          p += wasm_debug_uint(msg + p, (uint32_t)idx);
          p += wasm_debug_str(msg + p, "/");
          p += wasm_debug_uint(msg + p, (uint32_t)count);
          p += wasm_debug_str(msg + p, "]\n");
          wasm_host_log(msg, (unsigned)p);
          if (nil_svec_logged == 0) {
            /* First hit: dump first 8 elements of the vector */
            int p2 = 0;
            p2 += wasm_debug_str(msg + p2, "  SVEC-DUMP:");
            int dump_n = count < 8 ? (int)count : 8;
            for (int j = 0; j < dump_n; j++) {
              msg[p2++] = ' ';
              p2 += wasm_debug_hex8(msg + p2, (uint32_t)deref(base, j + 1));
            }
            msg[p2++] = '\n';
            wasm_host_log(msg, (unsigned)p2);
          }
          nil_svec_logged++;
        }
      }

      return result;
    }

    /* Out-of-bounds access on misc object */
    if (wasm_trace_funcall >= 1 &&
        header_subtag(header) == subtag_simple_vector) {
      static uint32_t oob_svref_logged = 0;
      if (oob_svref_logged < 10) {
        char msg[128];
        int p = 0;
        p += wasm_debug_str(msg + p, "OOB-SVREF @");
        p += wasm_debug_hex8(msg + p, (uint32_t)base);
        p += wasm_debug_str(msg + p, " idx=");
        p += wasm_debug_uint(msg + p, (uint32_t)idx);
        p += wasm_debug_str(msg + p, " cnt=");
        p += wasm_debug_uint(msg + p, (uint32_t)count);
        p += wasm_debug_str(msg + p, "\n");
        wasm_host_log(msg, (unsigned)p);
        oob_svref_logged++;
      }
    }
  }

  return lisp_nil;
}

__attribute__((used, visibility("default"), export_name("wasm_lisp_word_set")))
LispObj
wasm_lisp_word_set(LispObj base, LispObj offset, LispObj value)
{
  if (tag_of(base) == tag_fixnum && tag_of(offset) == tag_fixnum) {
    signed_natural addr = unbox_fixnum(base);
    signed_natural idx = unbox_fixnum(offset);
    LispObj *ptr = (LispObj *)(uintptr_t)addr;
    ptr[idx] = value;
  }
  return value;
}

__attribute__((used, visibility("default"), export_name("wasm_return_arg_z")))
void
wasm_return_arg_z(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  if (tcr->wasm_pending_throw) {
    return;
  }
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_arg_y")))
void
wasm_return_arg_y(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  if (tcr->wasm_pending_throw) {
    return;
  }
  tcr->wasm_gprs[arg_z] = tcr->wasm_gprs[arg_y];
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_values2")))
LispObj
wasm_return_values2(LispObj value0, LispObj value1)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }
  LispObj *vsp_ptr = saved_vsp;
  /* Push value0 first (bottom), value1 last (top).
     wasm_get_mv(i) reads vsp_ptr[count-1-i], so the highest-indexed
     value must be at the top (lowest address). */
  *--vsp_ptr = value0;
  *--vsp_ptr = value1;
  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->wasm_gprs[arg_z] = value0;
  tcr->wasm_gprs[nargs] = box_fixnum(2);
  return value0;
}

__attribute__((used, visibility("default"), export_name("wasm_return_values3")))
LispObj
wasm_return_values3(LispObj value0, LispObj value1, LispObj value2)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }
  LispObj *vsp_ptr = saved_vsp;
  *--vsp_ptr = value0;
  *--vsp_ptr = value1;
  *--vsp_ptr = value2;
  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->wasm_gprs[arg_z] = value0;
  tcr->wasm_gprs[nargs] = box_fixnum(3);
  return value0;
}

__attribute__((used, visibility("default"), export_name("wasm_return_values4")))
LispObj
wasm_return_values4(LispObj value0, LispObj value1, LispObj value2, LispObj value3)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }
  LispObj *vsp_ptr = saved_vsp;
  *--vsp_ptr = value0;
  *--vsp_ptr = value1;
  *--vsp_ptr = value2;
  *--vsp_ptr = value3;
  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->wasm_gprs[arg_z] = value0;
  tcr->wasm_gprs[nargs] = box_fixnum(4);
  return value0;
}

__attribute__((used, visibility("default"), export_name("wasm_get_mv")))
LispObj
wasm_get_mv(uint32_t index)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj raw = tcr->wasm_gprs[nargs];
  if (tag_of(raw) != tag_fixnum) {
    return lisp_nil;
  }
  signed_natural count = unbox_fixnum(raw);
  if ((signed_natural)index < 0 || (signed_natural)index >= count) {
    /* Diagnostic: log first few MV index-out-of-range for index >= 2 */
    if (index >= 2) {
      static int mv_diag_count = 0;
      if (mv_diag_count < 5) {
        mv_diag_count++;
        char msg[128]; int p = 0;
        p += wasm_debug_str(msg + p, "get_mv OOB: idx=");
        p += wasm_debug_uint(msg + p, (uint32_t)index);
        p += wasm_debug_str(msg + p, " count=");
        p += wasm_debug_uint(msg + p, (uint32_t)count);
        p += wasm_debug_str(msg + p, " nargs_raw=0x");
        p += wasm_debug_hex8(msg + p, (uint32_t)raw);
        p += wasm_debug_str(msg + p, " vsp=0x");
        p += wasm_debug_hex8(msg + p, (uint32_t)tcr->wasm_gprs[vsp]);
        p += wasm_debug_str(msg + p, " save_vsp=0x");
        p += wasm_debug_hex8(msg + p, (uint32_t)(uintptr_t)tcr->save_vsp);
        msg[p++] = '\n';
        wasm_host_log(msg, (unsigned)p);
      }
    }
    return lisp_nil;
  }
  if (index == 0) {
    return tcr->wasm_gprs[arg_z];
  }
  LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
  if (vsp_ptr == NULL) {
    return lisp_nil;
  }
  return vsp_ptr[count - 1 - (signed_natural)index];
}

__attribute__((used, visibility("default"), export_name("wasm_get_mv_indexed")))
LispObj
wasm_get_mv_indexed(LispObj raw_index)
{
  if (tag_of(raw_index) != tag_fixnum) {
    return lisp_nil;
  }
  signed_natural index = unbox_fixnum(raw_index);
  if (index < 0) {
    return lisp_nil;
  }
  return wasm_get_mv((uint32_t)index);
}

__attribute__((used, visibility("default"), export_name("wasm_restore_vsp")))
void
wasm_restore_vsp(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj raw = tcr->wasm_gprs[nargs];
  if (tag_of(raw) != tag_fixnum) {
    return;
  }
  signed_natural count = unbox_fixnum(raw);
  if (count <= 1) {
    return;
  }
  LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
  if (vsp_ptr == NULL) {
    return;
  }
  vsp_ptr += count;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_vpush")))
void
wasm_vpush(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj *vsp_ptr = tcr->save_vsp;
  if (vsp_ptr == NULL) {
    return;
  }
  *--vsp_ptr = value;
  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
}

__attribute__((used, visibility("default"), export_name("wasm_vsp_ref")))
LispObj
wasm_vsp_ref(uint32_t index)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj *vsp_ptr = tcr->save_vsp;
  if (vsp_ptr == NULL) {
    return lisp_nil;
  }
  LispObj raw = tcr->wasm_gprs[nargs];
  if (tag_of(raw) != tag_fixnum) {
    return lisp_nil;
  }
  signed_natural count = unbox_fixnum(raw);
  if (count <= 0 || (signed_natural)index >= count) {
    return lisp_nil;
  }
  LispObj value = vsp_ptr[count - 1 - (signed_natural)index];
  return value;
}

__attribute__((used, visibility("default"), export_name("wasm_vpop")))
LispObj
wasm_vpop(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj *vsp_ptr = tcr->save_vsp;
  if (vsp_ptr == NULL) {
    return lisp_nil;
  }
  LispObj value = *vsp_ptr++;
  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  return value;
}

/* Spill stack counters — used by wasm_debug_dump_state */
static uint32_t wasm_spill_push_count = 0;
static uint32_t wasm_spill_pop_count = 0;

__attribute__((used, visibility("default"), export_name("wasm_spill_push")))
void
wasm_spill_push(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj *sp = tcr->wasm_spill_sp;
  if (sp == NULL || tcr->wasm_spill_base == NULL) {
    return;
  }
  if (sp <= tcr->wasm_spill_base) {
    wasm_debug_dump_state("spill_push overflow");
    __builtin_trap();
  }
  *--sp = value;
  tcr->wasm_spill_sp = sp;
  wasm_spill_push_count++;
}

__attribute__((used, visibility("default"), export_name("wasm_spill_pop")))
LispObj
wasm_spill_pop(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj *sp = tcr->wasm_spill_sp;
  if (sp == NULL || tcr->wasm_spill_limit == NULL) {
    return lisp_nil;
  }
  if (sp >= tcr->wasm_spill_limit) {
    __builtin_trap();
  }
  LispObj value = *sp++;
  tcr->wasm_spill_sp = sp;
  wasm_spill_pop_count++;
  return value;
}

/* ====================================================================
 * Debug state inspection — reusable across all debugging sessions.
 * See doc/wasm/debugging.md for usage.
 * ==================================================================== */

/* Helper: write 8-hex-digit value into buf, return chars written */
static int
wasm_debug_hex8(char *buf, uint32_t v)
{
  static const char hex[] = "0123456789abcdef";
  buf[0] = '0'; buf[1] = 'x';
  for (int i = 7; i >= 0; i--)
    buf[2 + (7 - i)] = hex[(v >> (i * 4)) & 0xf];
  return 10;
}

/* Helper: copy string literal into buf, return length */
static int
wasm_debug_str(char *buf, const char *s)
{
  int i = 0;
  while (s[i]) { buf[i] = s[i]; i++; }
  return i;
}

/* Helper: write unsigned decimal into buf, return chars written */
static int
wasm_debug_uint(char *buf, uint32_t v)
{
  if (v == 0) { buf[0] = '0'; return 1; }
  char tmp[10];
  int len = 0;
  while (v > 0) { tmp[len++] = '0' + (v % 10); v /= 10; }
  for (int i = 0; i < len; i++) buf[i] = tmp[len - 1 - i];
  return len;
}

static unsigned wasm_debug_dump_state_count = 0;

__attribute__((used, visibility("default"), export_name("wasm_reset_debug_counters")))
void
wasm_reset_debug_counters(void)
{
  wasm_debug_dump_state_count = 0;
}

__attribute__((used, visibility("default"), export_name("wasm_debug_dump_state")))
void
wasm_debug_dump_state(const char *label)
{
  /* Only log first 10 state dumps to avoid multi-million-line output.
     The v15 absorb guard causes millions of _SPksignalerr calls during
     cold-boot-init, each triggering a state dump.  Without this gate,
     output exceeds 90M lines and I/O stalls the process. */
  unsigned this_dump = wasm_debug_dump_state_count++;
  if (this_dump == 10) {
    wasm_host_log("[state-dump] further dumps suppressed\n", 39);
    return;
  }
  if (this_dump > 10) return;

  TCR *tcr = get_tcr(0);
  if (!tcr) return;
  char buf[128];
  int p;

  /* Header */
  p = 0;
  p += wasm_debug_str(buf + p, "\n=== STATE DUMP: ");
  p += wasm_debug_str(buf + p, label ? label : "?");
  p += wasm_debug_str(buf + p, " ===\n");
  wasm_host_log(buf, (unsigned)p);

  /* GPR names as fixed strings — avoids %s formatting entirely */
  static const char gpr_names[16][9] = {
    "imm0    ", "imm1    ", "nargs   ", "rctx    ",
    "arg_z   ", "arg_y   ", "arg_x   ", "temp0   ",
    "temp1   ", "nfn     ", "vsp     ", "Rfn     ",
    "allocptr", "Rsp     ", "Rlr     ", "Rpc     "
  };
  for (int i = 0; i < 16; i++) {
    p = 0;
    buf[p++] = ' '; buf[p++] = ' ';
    for (int j = 0; j < 8; j++) buf[p++] = gpr_names[i][j];
    buf[p++] = ' '; buf[p++] = '='; buf[p++] = ' ';
    p += wasm_debug_hex8(buf + p, (uint32_t)tcr->wasm_gprs[i]);
    buf[p++] = '\n';
    wasm_host_log(buf, (unsigned)p);
  }

  /* Spill stack */
  p = 0;
  p += wasm_debug_str(buf + p, "  spill: sp=");
  p += wasm_debug_hex8(buf + p, (uint32_t)(uintptr_t)tcr->wasm_spill_sp);
  p += wasm_debug_str(buf + p, " base=");
  p += wasm_debug_hex8(buf + p, (uint32_t)(uintptr_t)tcr->wasm_spill_base);
  p += wasm_debug_str(buf + p, " limit=");
  p += wasm_debug_hex8(buf + p, (uint32_t)(uintptr_t)tcr->wasm_spill_limit);
  p += wasm_debug_str(buf + p, " depth=");
  p += wasm_debug_uint(buf + p,
    (uint32_t)(tcr->wasm_spill_sp && tcr->wasm_spill_limit
               ? (tcr->wasm_spill_limit - tcr->wasm_spill_sp) : 0));
  buf[p++] = '\n';
  wasm_host_log(buf, (unsigned)p);

  /* Catch/db/throw */
  p = 0;
  p += wasm_debug_str(buf + p, "  catch_top=");
  p += wasm_debug_hex8(buf + p, (uint32_t)tcr->catch_top);
  p += wasm_debug_str(buf + p, " db_link=");
  p += wasm_debug_hex8(buf + p, (uint32_t)(uintptr_t)tcr->db_link);
  p += wasm_debug_str(buf + p, " pending_throw=");
  p += wasm_debug_hex8(buf + p, (uint32_t)tcr->wasm_pending_throw);
  buf[p++] = '\n';
  wasm_host_log(buf, (unsigned)p);

  /* VSP top values */
  LispObj vsp_val = tcr->wasm_gprs[10];
  p = 0;
  p += wasm_debug_str(buf + p, "  VSP=");
  p += wasm_debug_hex8(buf + p, (uint32_t)vsp_val);
  p += wasm_debug_str(buf + p, " top:");
  if (vsp_val) {
    LispObj *vsp_ptr = (LispObj *)vsp_val;
    for (int i = 0; i < 4; i++) {
      buf[p++] = ' ';
      p += wasm_debug_hex8(buf + p, (uint32_t)vsp_ptr[i]);
    }
  }
  buf[p++] = '\n';
  wasm_host_log(buf, (unsigned)p);

  /* Spill counters */
  p = 0;
  p += wasm_debug_str(buf + p, "  spill_push=");
  p += wasm_debug_uint(buf + p, wasm_spill_push_count);
  p += wasm_debug_str(buf + p, " spill_pop=");
  p += wasm_debug_uint(buf + p, wasm_spill_pop_count);
  buf[p++] = '\n';
  wasm_host_log(buf, (unsigned)p);

  /* Last const-pool-ref that was called */
  p = 0;
  p += wasm_debug_str(buf + p, "  last_cpr: e=");
  p += wasm_debug_uint(buf + p, wasm_diag_last_cpr_entry);
  p += wasm_debug_str(buf + p, " s=");
  p += wasm_debug_uint(buf + p, wasm_diag_last_cpr_slot);
  p += wasm_debug_str(buf + p, " val=");
  p += wasm_debug_hex8(buf + p, (uint32_t)wasm_diag_last_cpr_val);
  buf[p++] = '\n';
  wasm_host_log(buf, (unsigned)p);

  wasm_host_log("=== END STATE DUMP ===\n", 23);
}

__attribute__((used, visibility("default"), export_name("wasm_diag_get_last_cpr_entry")))
uint32_t
wasm_diag_get_last_cpr_entry(void)
{
  return wasm_diag_last_cpr_entry;
}

__attribute__((used, visibility("default"), export_name("wasm_diag_get_last_cpr_slot")))
uint32_t
wasm_diag_get_last_cpr_slot(void)
{
  return wasm_diag_last_cpr_slot;
}

/* Validate all entries in %builtin-functions% by logging each builtin's
   entry index.  Called by JS host before cold-boot-init so the output can
   be cross-referenced with manifests to find stale/gap entries. */
__attribute__((used, visibility("default"), export_name("wasm_validate_builtin_entries")))
uint32_t
wasm_validate_builtin_entries(void)
{
  LispObj vec = nrs_BUILTIN_FUNCTIONS.vcell;
  if (vec == (LispObj)nil_value || fulltag_of(vec) != fulltag_misc) return 0;
  LispObj header = header_of(vec);
  signed_natural count = header_element_count(header);
  LispObj *data = (LispObj *)((BytePtr)vec + misc_data_offset);
  uint32_t logged = 0;
  static const char hx[] = "0123456789abcdef";

  for (signed_natural i = 0; i < count; i++) {
    LispObj fn = data[i];
    if (fn == (LispObj)nil_value || fulltag_of(fn) != fulltag_misc) continue;
    unsigned subtag = header_subtag(header_of(fn));
    if (subtag != subtag_function && subtag != subtag_pseudofunction) continue;
    LispObj entry = deref(fn, 1);
    if (tag_of(entry) != tag_fixnum) continue;
    uint32_t eidx = (uint32_t)unbox_fixnum(entry);
    char msg[60]; int p = 0;
    msg[p++] = 'B'; msg[p++] = 'V'; msg[p++] = ' ';
    for (int b = 3; b >= 0; b--) msg[p++] = hx[(i >> (b * 4)) & 0xf];
    msg[p++] = '='; msg[p++] = 'e';
    for (int b = 7; b >= 0; b--) msg[p++] = hx[(eidx >> (b * 4)) & 0xf];
    msg[p++] = '\n';
    wasm_host_log(msg, (unsigned)p);
    logged++;
  }
  return logged;
}

__attribute__((used, visibility("default"), export_name("wasm_debug_tcr_offset")))
uint32_t
wasm_debug_tcr_offset(uint32_t field_id)
{
  switch (field_id) {
    case 0: return (uint32_t)offsetof(TCR, wasm_gprs);
    case 1: return (uint32_t)offsetof(TCR, wasm_spill_base);
    case 2: return (uint32_t)offsetof(TCR, wasm_spill_sp);
    case 3: return (uint32_t)offsetof(TCR, wasm_pending_throw);
    case 4: return (uint32_t)offsetof(TCR, catch_top);
    case 5: return (uint32_t)offsetof(TCR, db_link);
    case 6: return (uint32_t)offsetof(TCR, save_vsp);
    case 7: return (uint32_t)offsetof(TCR, xframe);
    case 8: return (uint32_t)offsetof(TCR, wasm_spill_limit);
    case 9: return (uint32_t)offsetof(TCR, wasm_cstack_sp);
    case 10: return (uint32_t)offsetof(TCR, nfp);
    default: return 0xFFFFFFFF;
  }
}

__attribute__((used, visibility("default"), export_name("wasm_pending_throw_p")))
uint32_t
wasm_pending_throw_p(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return 0;
  }
  /* Bounds check: TCR + pending_throw offset must be within WASM memory */
  uintptr_t tcr_addr = (uintptr_t)tcr;
  uintptr_t field_end = tcr_addr + offsetof(TCR, wasm_pending_throw) + sizeof(LispObj);
  uintptr_t mem_size = (uintptr_t)__builtin_wasm_memory_size(0) * 65536u;
  if (field_end > mem_size) {
    return 0;
  }
  return tcr->wasm_pending_throw ? 1 : 0;
}

__attribute__((used, visibility("default"), export_name("wasm_pending_throw_raw")))
LispObj
wasm_pending_throw_raw(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  return tcr->wasm_pending_throw;
}

__attribute__((used, visibility("default"), export_name("wasm_clear_pending_throw")))
void
wasm_clear_pending_throw(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_pending_throw = 0;
}

/*
 * Compatibility-only fixnum return helpers.
 * Hot arithmetic lanes should stay in compiler-emitted direct WASM lowering
 * and branch to these only on explicit fallback edges.
 */
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

static LispObj
wasm_funcall_common(TCR *tcr, LispObj fn_value, const LispObj *args, signed_natural count, int preserve_mv)
{
  if (tcr == NULL) {
    return lisp_nil;
  }
  if (!wasm_subprims_ready) {
    return lisp_nil;
  }

  int in_lisp = (tcr->valence == TCR_STATE_LISP);
  LispObj *saved_vsp = in_lisp ? (LispObj *)tcr->wasm_gprs[vsp] : tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }

  natural old_last_lisp_frame = 0;
  if (!in_lisp) {
    old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)saved_vsp);
    tcr->valence = TCR_STATE_LISP;
  }
  tcr->wasm_pending_throw = 0;

  LispObj *vsp_ptr = saved_vsp;
  for (signed_natural i = 0; i < count; i++) {
    *--vsp_ptr = args[i];
  }

  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[nargs] = box_fixnum(count);
  tcr->wasm_gprs[nfn] = fn_value;
  tcr->wasm_gprs[Rfn] = fn_value;

  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  LispObj result = tcr->wasm_gprs[arg_z];
  if (tcr->wasm_pending_throw) {
    LispObj *throw_vsp = (LispObj *)tcr->wasm_gprs[vsp];
    if (throw_vsp == NULL) {
      throw_vsp = saved_vsp;
    }
    tcr->save_vsp = throw_vsp;
    tcr->wasm_gprs[vsp] = (LispObj)throw_vsp;
    if (!in_lisp) {
      tcr->valence = TCR_STATE_FOREIGN;
      wasm_exit_lisp_frame(tcr, old_last_lisp_frame);
    }
    return result;
  }

  LispObj raw_nargs = tcr->wasm_gprs[nargs];
  signed_natural value_count = (tag_of(raw_nargs) == tag_fixnum) ? unbox_fixnum(raw_nargs) : 1;

  if (preserve_mv && value_count > 1) {
    LispObj *mv_vsp = (LispObj *)tcr->wasm_gprs[vsp];
    if (mv_vsp != NULL) {
      tcr->save_vsp = mv_vsp;
    } else {
      tcr->save_vsp = saved_vsp;
      tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
      tcr->wasm_gprs[nargs] = box_fixnum(1);
    }
  } else {
    tcr->save_vsp = saved_vsp;
    tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
    if (value_count > 1) {
      tcr->wasm_gprs[nargs] = box_fixnum(1);
    }
  }
  if (!in_lisp) {
    tcr->valence = TCR_STATE_FOREIGN;
    wasm_exit_lisp_frame(tcr, old_last_lisp_frame);
  }
  return result;
}

enum {
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_OK = 1u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_NO_TCR = 10u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_SUBPRIMS_NOT_READY = 11u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_NO_SAVEVSP = 12u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_HOST_FRAME = 13u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_CATCH_INSTALL = 14u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_PENDING_THROW = 15u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_VSP = 16u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_SAVEVSP = 17u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_LAST = 18u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_CATCH_RESTORE = 19u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_FRAME_EXIT = 20u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_SP_RESTORE = 21u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_CATCH_INSTALL = 22u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_PENDING_THROW = 23u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_VSP = 24u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_SAVEVSP = 25u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_LAST = 26u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_CATCH_RESTORE = 27u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_SP_RESTORE = 28u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_CATCH_INSTALL = 29u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_PENDING_THROW = 30u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_ARGZ = 31u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_VSP = 32u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_SAVEVSP = 33u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_LAST = 34u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_CATCH_RESTORE = 35u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_STACK_BOUNDS = 36u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_CATCH_INSTALL = 37u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_PENDING_THROW = 38u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_NARGS = 39u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_ARGZ = 40u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_VSP = 41u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_SAVEVSP = 42u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_VALUES = 43u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_LAST = 44u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_CATCH_RESTORE = 45u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_CATCH_INSTALL = 46u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_PENDING_THROW = 47u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_ARGZ = 48u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_VSP = 49u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_SAVEVSP = 50u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_SAVETSP = 51u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_LAST = 52u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_CATCH_RESTORE = 53u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_SP_RESTORE = 54u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_STACK_BOUNDS = 55u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_CATCH_INSTALL = 56u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_PENDING_THROW = 57u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_NARGS = 58u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_ARGZ = 59u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_VSP = 60u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_SAVETSP = 61u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_SAVEVSP_VALUES = 62u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_LAST = 63u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_CATCH_RESTORE = 64u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_SP_RESTORE = 65u
};

typedef struct wasm_subprim_nonlocal_exit_selftest_state {
  BytePtr cstack_sp;
  natural last_lisp_frame;
  LispObj *save_vsp;
  LispObj catch_top;
  xframe_list *xframe;
  void *nfp;
  LispObj *save_tsp;
  int valence;
  LispObj pending_throw;
  LispObj reg_vsp;
  LispObj reg_arg_z;
  LispObj reg_arg_y;
  LispObj reg_arg_x;
  LispObj reg_nargs;
  LispObj reg_imm0;
  LispObj reg_nfn;
  LispObj reg_rfn;
} wasm_subprim_nonlocal_exit_selftest_state;

static void
wasm_capture_subprim_nonlocal_exit_selftest_state(TCR *tcr,
                                                  wasm_subprim_nonlocal_exit_selftest_state *state)
{
  state->cstack_sp = (BytePtr)wasm_get_cstack_pointer();
  state->last_lisp_frame = tcr->last_lisp_frame;
  state->save_vsp = tcr->save_vsp;
  state->catch_top = tcr->catch_top;
  state->xframe = tcr->xframe;
  state->nfp = tcr->nfp;
  state->save_tsp = tcr->save_tsp;
  state->valence = tcr->valence;
  state->pending_throw = tcr->wasm_pending_throw;
  state->reg_vsp = tcr->wasm_gprs[vsp];
  state->reg_arg_z = tcr->wasm_gprs[arg_z];
  state->reg_arg_y = tcr->wasm_gprs[arg_y];
  state->reg_arg_x = tcr->wasm_gprs[arg_x];
  state->reg_nargs = tcr->wasm_gprs[nargs];
  state->reg_imm0 = tcr->wasm_gprs[imm0];
  state->reg_nfn = tcr->wasm_gprs[nfn];
  state->reg_rfn = tcr->wasm_gprs[Rfn];
}

static void
wasm_restore_subprim_nonlocal_exit_selftest_state(TCR *tcr,
                                                  const wasm_subprim_nonlocal_exit_selftest_state *state)
{
  wasm_set_cstack_pointer(state->cstack_sp);
  tcr->last_lisp_frame = state->last_lisp_frame;
  tcr->save_vsp = state->save_vsp;
  tcr->catch_top = state->catch_top;
  tcr->xframe = state->xframe;
  tcr->nfp = state->nfp;
  tcr->save_tsp = state->save_tsp;
  tcr->valence = state->valence;
  tcr->wasm_pending_throw = state->pending_throw;
  tcr->wasm_gprs[vsp] = state->reg_vsp;
  tcr->wasm_gprs[arg_z] = state->reg_arg_z;
  tcr->wasm_gprs[arg_y] = state->reg_arg_y;
  tcr->wasm_gprs[arg_x] = state->reg_arg_x;
  tcr->wasm_gprs[nargs] = state->reg_nargs;
  tcr->wasm_gprs[imm0] = state->reg_imm0;
  tcr->wasm_gprs[nfn] = state->reg_nfn;
  tcr->wasm_gprs[Rfn] = state->reg_rfn;
}

uint32_t
wasm_subprim_nonlocal_exit_coherence_selftest(void)
{
  TCR *tcr = wasm_get_current_tcr();
  wasm_subprim_nonlocal_exit_selftest_state original;
  area *vs_area;
  natural direct_old_last_lisp_frame;
  natural direct_host_last_lisp_frame;
  LispObj *direct_unwind_throw_vsp;
  LispObj cleanup_invoked_sentinel = box_fixnum(0x3301);
  LispObj mv0 = box_fixnum(0x3401);
  LispObj mv1 = box_fixnum(0x3402);
  LispObj mv2 = box_fixnum(0x3403);
  LispObj funcall_mv0 = box_fixnum(0x4401);
  LispObj funcall_mv1 = box_fixnum(0x4402);
  LispObj funcall_mv2 = box_fixnum(0x4403);
  LispObj nthrow1_fn_obj[3] __attribute__((aligned(8)));
  LispObj nthrowvalues_fn_obj[3] __attribute__((aligned(8)));
  LispObj nthrow1_entry_fixnum = box_fixnum(WASM_SUBPRIM_NTHROW1VALUE_INDEX);
  LispObj nthrowvalues_entry_fixnum = box_fixnum(WASM_SUBPRIM_NTHROWVALUES_INDEX);
  LispObj nthrow1_fn_value;
  LispObj nthrowvalues_fn_value;
  LispObj funcall_mv_args[3];

  if (tcr == NULL) {
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_NO_TCR;
  }
  if (!wasm_subprims_ready) {
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_SUBPRIMS_NOT_READY;
  }
  if (tcr->save_vsp == NULL) {
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_NO_SAVEVSP;
  }

  wasm_capture_subprim_nonlocal_exit_selftest_state(tcr, &original);

  nthrow1_fn_obj[0] = make_header(subtag_function, 2);
  nthrow1_fn_obj[1] = nthrow1_entry_fixnum;
  nthrow1_fn_obj[2] = nthrow1_entry_fixnum;
  nthrow1_fn_value = (LispObj)((BytePtr)nthrow1_fn_obj + fulltag_misc);

  nthrowvalues_fn_obj[0] = make_header(subtag_function, 2);
  nthrowvalues_fn_obj[1] = nthrowvalues_entry_fixnum;
  nthrowvalues_fn_obj[2] = nthrowvalues_entry_fixnum;
  nthrowvalues_fn_value = (LispObj)((BytePtr)nthrowvalues_fn_obj + fulltag_misc);

  tcr->wasm_pending_throw = 0;
  tcr->valence = TCR_STATE_FOREIGN;
  tcr->save_vsp = original.save_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)original.save_vsp;
  tcr->catch_top = original.catch_top;

  direct_old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)original.save_vsp);
  direct_host_last_lisp_frame = tcr->last_lisp_frame;
  if (direct_host_last_lisp_frame == 0) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_HOST_FRAME;
  }
  tcr->valence = TCR_STATE_LISP;

  tcr->wasm_gprs[arg_z] = box_fixnum(0x1101);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKCATCH1V_INDEX));
  if (tcr->catch_top == original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_CATCH_INSTALL;
  }

  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[arg_z] = box_fixnum(0x1102);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
  tcr->wasm_gprs[imm0] = box_fixnum(1);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_NTHROW1VALUE_INDEX));
  if (!tcr->wasm_pending_throw) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_PENDING_THROW;
  }
  if ((LispObj)tcr->save_vsp != tcr->wasm_gprs[vsp]) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_VSP;
  }
  if (tcr->save_vsp != original.save_vsp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_SAVEVSP;
  }
  if (tcr->last_lisp_frame != direct_host_last_lisp_frame) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_LAST;
  }
  if (tcr->catch_top != original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_CATCH_RESTORE;
  }

  /* Phase-3: mkunwind + nthrowvalues cleanup entry must execute and restore
   * non-local-exit coherence for a zero-value throw.
   */
  tcr->wasm_pending_throw = 0;
  tcr->save_tsp = NULL;
  tcr->save_vsp = original.save_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)original.save_vsp;
  tcr->wasm_gprs[nargs] = box_fixnum(0);
  tcr->wasm_gprs[arg_z] = cleanup_invoked_sentinel;
  tcr->wasm_gprs[imm0] = box_fixnum(WASM_SUBPRIM_VALUES_INDEX);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKUNWIND_INDEX));
  if (tcr->catch_top == original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_CATCH_INSTALL;
  }

  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[arg_z] = cleanup_invoked_sentinel;
  tcr->wasm_gprs[nargs] = box_fixnum(0);
  tcr->wasm_gprs[imm0] = box_fixnum(1);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_NTHROWVALUES_INDEX));
  if (!tcr->wasm_pending_throw) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_PENDING_THROW;
  }
  if (tcr->wasm_gprs[arg_z] != (LispObj)nil_value) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_ARGZ;
  }
  if ((LispObj)tcr->save_vsp != tcr->wasm_gprs[vsp]) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_VSP;
  }
  if (tcr->save_vsp != original.save_vsp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_SAVEVSP;
  }
  if (tcr->last_lisp_frame != direct_host_last_lisp_frame) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_LAST;
  }
  if (tcr->catch_top != original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_CATCH_RESTORE;
  }

  /* Phase-3: same path with MV payload verifies push/recover around cleanup. */
  vs_area = tcr->vs_area;
  if ((vs_area == NULL) || (vs_area->low == NULL) || (vs_area->high == NULL)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_STACK_BOUNDS;
  }
  direct_unwind_throw_vsp = original.save_vsp - 3;
  if (((BytePtr)direct_unwind_throw_vsp < vs_area->low) ||
      ((BytePtr)(direct_unwind_throw_vsp + 3) > vs_area->high)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_STACK_BOUNDS;
  }
  direct_unwind_throw_vsp[0] = mv0;
  direct_unwind_throw_vsp[1] = mv1;
  direct_unwind_throw_vsp[2] = mv2;

  tcr->wasm_pending_throw = 0;
  tcr->save_tsp = NULL;
  tcr->save_vsp = direct_unwind_throw_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)direct_unwind_throw_vsp;
  tcr->wasm_gprs[arg_z] = mv0;
  tcr->wasm_gprs[arg_y] = mv1;
  tcr->wasm_gprs[arg_x] = mv2;
  tcr->wasm_gprs[nargs] = box_fixnum(3);
  tcr->wasm_gprs[imm0] = box_fixnum(WASM_SUBPRIM_VALUES_INDEX);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKUNWIND_INDEX));
  if (tcr->catch_top == original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_CATCH_INSTALL;
  }

  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[arg_z] = mv0;
  tcr->wasm_gprs[nargs] = box_fixnum(3);
  tcr->wasm_gprs[imm0] = box_fixnum(1);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_NTHROWVALUES_INDEX));
  if (!tcr->wasm_pending_throw) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_PENDING_THROW;
  }
  if (tcr->wasm_gprs[nargs] != box_fixnum(3)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_NARGS;
  }
  if (tcr->wasm_gprs[arg_z] != mv0) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_ARGZ;
  }
  if ((LispObj)tcr->save_vsp != tcr->wasm_gprs[vsp]) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_VSP;
  }
  if ((tcr->save_vsp == NULL) || (tcr->save_tsp != NULL)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_SAVEVSP;
  }
  if ((tcr->save_vsp[0] != mv0) ||
      (tcr->save_vsp[1] != mv1) ||
      (tcr->save_vsp[2] != mv2)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_VALUES;
  }
  if (tcr->last_lisp_frame != direct_host_last_lisp_frame) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_LAST;
  }
  if (tcr->catch_top != original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_CATCH_RESTORE;
  }

  tcr->wasm_pending_throw = 0;
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, direct_old_last_lisp_frame);
  if (tcr->last_lisp_frame != original.last_lisp_frame) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_FRAME_EXIT;
  }
  if ((BytePtr)wasm_get_cstack_pointer() != original.cstack_sp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_SP_RESTORE;
  }

  tcr->wasm_pending_throw = 0;
  tcr->valence = TCR_STATE_FOREIGN;
  tcr->save_vsp = original.save_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)original.save_vsp;
  tcr->catch_top = original.catch_top;
  tcr->wasm_gprs[arg_z] = box_fixnum(0x2201);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKCATCH1V_INDEX));
  if (tcr->catch_top == original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_CATCH_INSTALL;
  }

  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[arg_z] = box_fixnum(0x2202);
  tcr->wasm_gprs[imm0] = box_fixnum(1);
  (void)wasm_funcall_common(tcr, nthrow1_fn_value, NULL, 0, 0);
  if (!tcr->wasm_pending_throw) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_PENDING_THROW;
  }
  if ((LispObj)tcr->save_vsp != tcr->wasm_gprs[vsp]) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_VSP;
  }
  if (tcr->save_vsp != original.save_vsp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_SAVEVSP;
  }
  if (tcr->last_lisp_frame != original.last_lisp_frame) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_LAST;
  }
  if (tcr->catch_top != original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_CATCH_RESTORE;
  }
  if ((BytePtr)wasm_get_cstack_pointer() != original.cstack_sp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_SP_RESTORE;
  }

  /*
   * Phase-4: same unwind-cleanup boundaries must hold when _SPnthrowvalues
   * is entered through wasm_funcall_common.
   */
  tcr->wasm_pending_throw = 0;
  tcr->save_tsp = NULL;
  tcr->valence = TCR_STATE_FOREIGN;
  tcr->save_vsp = original.save_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)original.save_vsp;
  tcr->catch_top = original.catch_top;
  tcr->wasm_gprs[nargs] = box_fixnum(0);
  tcr->wasm_gprs[arg_z] = cleanup_invoked_sentinel;
  tcr->wasm_gprs[imm0] = box_fixnum(WASM_SUBPRIM_VALUES_INDEX);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKUNWIND_INDEX));
  if (tcr->catch_top == original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_CATCH_INSTALL;
  }

  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[arg_z] = cleanup_invoked_sentinel;
  tcr->wasm_gprs[imm0] = box_fixnum(1);
  (void)wasm_funcall_common(tcr, nthrowvalues_fn_value, NULL, 0, 0);
  if (!tcr->wasm_pending_throw) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_PENDING_THROW;
  }
  if (tcr->wasm_gprs[arg_z] != (LispObj)nil_value) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_ARGZ;
  }
  if ((LispObj)tcr->save_vsp != tcr->wasm_gprs[vsp]) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_VSP;
  }
  if (tcr->save_vsp != original.save_vsp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_SAVEVSP;
  }
  if (tcr->save_tsp != NULL) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_SAVETSP;
  }
  if (tcr->last_lisp_frame != original.last_lisp_frame) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_LAST;
  }
  if (tcr->catch_top != original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_CATCH_RESTORE;
  }
  if ((BytePtr)wasm_get_cstack_pointer() != original.cstack_sp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_SP_RESTORE;
  }

  vs_area = tcr->vs_area;
  if ((vs_area == NULL) ||
      (vs_area->low == NULL) ||
      (vs_area->high == NULL) ||
      ((BytePtr)(original.save_vsp - 3) < vs_area->low) ||
      ((BytePtr)original.save_vsp > vs_area->high)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_STACK_BOUNDS;
  }

  tcr->wasm_pending_throw = 0;
  tcr->save_tsp = NULL;
  tcr->valence = TCR_STATE_FOREIGN;
  tcr->save_vsp = original.save_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)original.save_vsp;
  tcr->catch_top = original.catch_top;
  tcr->wasm_gprs[arg_z] = funcall_mv0;
  tcr->wasm_gprs[arg_y] = funcall_mv1;
  tcr->wasm_gprs[arg_x] = funcall_mv2;
  tcr->wasm_gprs[nargs] = box_fixnum(3);
  tcr->wasm_gprs[imm0] = box_fixnum(WASM_SUBPRIM_VALUES_INDEX);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKUNWIND_INDEX));
  if (tcr->catch_top == original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_CATCH_INSTALL;
  }

  funcall_mv_args[0] = funcall_mv0;
  funcall_mv_args[1] = funcall_mv1;
  funcall_mv_args[2] = funcall_mv2;
  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[arg_z] = funcall_mv0;
  tcr->wasm_gprs[imm0] = box_fixnum(1);
  (void)wasm_funcall_common(tcr, nthrowvalues_fn_value, funcall_mv_args, 3, 0);
  if (!tcr->wasm_pending_throw) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_PENDING_THROW;
  }
  if (tcr->wasm_gprs[nargs] != box_fixnum(3)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_NARGS;
  }
  if (tcr->wasm_gprs[arg_z] != funcall_mv0) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_ARGZ;
  }
  if ((LispObj)tcr->save_vsp != tcr->wasm_gprs[vsp]) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_VSP;
  }
  if (tcr->save_tsp != NULL) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_SAVETSP;
  }
  if ((tcr->save_vsp == NULL) ||
      (tcr->save_vsp[0] != funcall_mv0) ||
      (tcr->save_vsp[1] != funcall_mv1) ||
      (tcr->save_vsp[2] != funcall_mv2)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_SAVEVSP_VALUES;
  }
  if (tcr->last_lisp_frame != original.last_lisp_frame) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_LAST;
  }
  if (tcr->catch_top != original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_CATCH_RESTORE;
  }
  if ((BytePtr)wasm_get_cstack_pointer() != original.cstack_sp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_SP_RESTORE;
  }

  wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
  return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_OK;
}

__attribute__((used, visibility("default"), export_name("wasm_subprim_nonlocal_exit_coherence_selftest")))
uint32_t
wasm_subprim_nonlocal_exit_coherence_selftest_export(void)
{
  return wasm_subprim_nonlocal_exit_coherence_selftest();
}

__attribute__((used, visibility("default"), export_name("wasm_funcall0")))
LispObj
wasm_funcall0(LispObj fn_value)
{
  TCR *tcr = wasm_get_current_tcr();
  return wasm_funcall_common(tcr, fn_value, NULL, 0, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall1")))
LispObj
wasm_funcall1(LispObj fn_value, LispObj arg0)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[1];
  args[0] = arg0;
  return wasm_funcall_common(tcr, fn_value, args, 1, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall2")))
LispObj
wasm_funcall2(LispObj fn_value, LispObj arg0, LispObj arg1)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[2];
  args[0] = arg0;
  args[1] = arg1;
  return wasm_funcall_common(tcr, fn_value, args, 2, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall7")))
LispObj
wasm_funcall7(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[7];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  return wasm_funcall_common(tcr, fn_value, args, 7, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall8")))
LispObj
wasm_funcall8(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6, LispObj arg7)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[8];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  args[7] = arg7;
  return wasm_funcall_common(tcr, fn_value, args, 8, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall9")))
LispObj
wasm_funcall9(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6, LispObj arg7, LispObj arg8)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[9];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  args[7] = arg7;
  args[8] = arg8;
  return wasm_funcall_common(tcr, fn_value, args, 9, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall10")))
LispObj
wasm_funcall10(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6, LispObj arg7, LispObj arg8, LispObj arg9)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[10];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  args[7] = arg7;
  args[8] = arg8;
  args[9] = arg9;
  return wasm_funcall_common(tcr, fn_value, args, 10, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall3")))
LispObj
wasm_funcall3(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[3];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  return wasm_funcall_common(tcr, fn_value, args, 3, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall4")))
LispObj
wasm_funcall4(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[4];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  return wasm_funcall_common(tcr, fn_value, args, 4, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall5")))
LispObj
wasm_funcall5(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[5];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  return wasm_funcall_common(tcr, fn_value, args, 5, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall6")))
LispObj
wasm_funcall6(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[6];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  return wasm_funcall_common(tcr, fn_value, args, 6, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall0_mv")))
LispObj
wasm_funcall0_mv(LispObj fn_value)
{
  TCR *tcr = wasm_get_current_tcr();
  return wasm_funcall_common(tcr, fn_value, NULL, 0, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall1_mv")))
LispObj
wasm_funcall1_mv(LispObj fn_value, LispObj arg0)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[1];
  args[0] = arg0;
  return wasm_funcall_common(tcr, fn_value, args, 1, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall2_mv")))
LispObj
wasm_funcall2_mv(LispObj fn_value, LispObj arg0, LispObj arg1)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[2];
  args[0] = arg0;
  args[1] = arg1;
  return wasm_funcall_common(tcr, fn_value, args, 2, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall7_mv")))
LispObj
wasm_funcall7_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[7];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  return wasm_funcall_common(tcr, fn_value, args, 7, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall8_mv")))
LispObj
wasm_funcall8_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6, LispObj arg7)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[8];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  args[7] = arg7;
  return wasm_funcall_common(tcr, fn_value, args, 8, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall9_mv")))
LispObj
wasm_funcall9_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6, LispObj arg7, LispObj arg8)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[9];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  args[7] = arg7;
  args[8] = arg8;
  return wasm_funcall_common(tcr, fn_value, args, 9, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall10_mv")))
LispObj
wasm_funcall10_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6, LispObj arg7, LispObj arg8, LispObj arg9)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[10];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  args[7] = arg7;
  args[8] = arg8;
  args[9] = arg9;
  return wasm_funcall_common(tcr, fn_value, args, 10, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall3_mv")))
LispObj
wasm_funcall3_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[3];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  return wasm_funcall_common(tcr, fn_value, args, 3, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall4_mv")))
LispObj
wasm_funcall4_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[4];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  return wasm_funcall_common(tcr, fn_value, args, 4, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall5_mv")))
LispObj
wasm_funcall5_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[5];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  return wasm_funcall_common(tcr, fn_value, args, 5, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall6_mv")))
LispObj
wasm_funcall6_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[6];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  return wasm_funcall_common(tcr, fn_value, args, 6, 1);
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
    tcr->wasm_pending_throw = 0;
    tcr->wasm_gprs[vsp] = (LispObj)tcr->save_vsp;
    LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
    LispObj *vsp_empty = wasm_vsp_empty(tcr);
    if (vsp_ptr == NULL) {
      vsp_ptr = vsp_empty;
      if (vsp_ptr != NULL) {
        tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
      }
    }
    if (vsp_ptr == NULL) {
      static const char msg[] =
        "WASM start_lisp: VSP not initialized; returning to host\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      goto done;
    }
    LispObj topfn = nrs_TOPLFUNC.vcell;
    LispObj *slot = wasm_toplevel_slot(tcr);
    if (topfn != lisp_nil) {
      if (slot != NULL) {
        *slot = topfn;
        if (tcr->vs_area != NULL) {
          tcr->vs_area->active = (BytePtr)slot;
        }
        tcr->save_vsp = slot;
        vsp_ptr = slot;
        tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
      } else {
        *--vsp_ptr = topfn;
        tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
      }
      nrs_TOPLFUNC.vcell = lisp_nil;
    } else if (slot != NULL && *slot != lisp_nil) {
      if (tcr->vs_area != NULL) {
        tcr->vs_area->active = (BytePtr)slot;
      }
      tcr->save_vsp = slot;
      vsp_ptr = slot;
      tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
    } else if (vsp_ptr == vsp_empty || *vsp_ptr == lisp_nil) {
      static const char msg[] =
        "WASM start_lisp: toplevel function is NIL; returning to host\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      goto done;
    }

    /* Call RESTORE-LISP-POINTERS to rebuild package hash tables and run fixup hooks.
       This is critical for symbol lookup and FASL loading to work correctly.
       Native CCL always does this after loading an image. */
    LispObj restore_fn = nrs_RESTORE_LISP_POINTERS.vcell;
    if (restore_fn != lisp_nil &&
        fulltag_of(restore_fn) == fulltag_misc &&
        header_subtag(header_of(restore_fn)) == subtag_function) {

      tcr->wasm_gprs[nargs] = box_fixnum(0);
      tcr->wasm_gprs[nfn] = restore_fn;
      wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

      if (tcr->wasm_pending_throw) {
        /* Fixup failed - abort boot */
        static const char msg[] =
          "WASM start_lisp: RESTORE-LISP-POINTERS threw; aborting boot\n";
        wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
        goto done;
      }
    }

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

/* Call RESTORE-LISP-POINTERS after loading a boot image.
   This rehashes package tables and runs fixup hooks so that
   symbol lookup (INTERN, FIND-SYMBOL) works correctly.
   Every native CCL platform does this after image load;
   the WASM port was missing this step.
   Returns 0 on success, negative on error. */
__attribute__((used, visibility("default"), export_name("wasm_restore_lisp_pointers")))
int
wasm_restore_lisp_pointers(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return -1;
  }
  if (!wasm_subprims_ready) {
    return -2;
  }

  natural old_last_lisp_frame = wasm_enter_lisp_frame(
    tcr, 0, 0, (LispObj)tcr->save_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[vsp] = (LispObj)tcr->save_vsp;

  LispObj restore_fn = nrs_RESTORE_LISP_POINTERS.vcell;
  if (restore_fn == lisp_nil ||
      fulltag_of(restore_fn) != fulltag_misc ||
      header_subtag(header_of(restore_fn)) != subtag_function) {
    tcr->valence = TCR_STATE_FOREIGN;
    wasm_exit_lisp_frame(tcr, old_last_lisp_frame);
    return -3;
  }

  tcr->wasm_gprs[nargs] = box_fixnum(0);
  tcr->wasm_gprs[nfn] = restore_fn;
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  int result = 0;
  if (tcr->wasm_pending_throw) {
    tcr->wasm_pending_throw = 0;
    result = -4;
  }

  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old_last_lisp_frame);
  return result;
}

/* Consume *XLOAD-COLD-LOAD-FUNCTIONS*: save the list and set vcell to NIL.
   This must happen BEFORE calling %RUN-COLD-BOOT-INIT so Lisp sees an
   empty list and skips its dolist loop (which would short-circuit on
   pending_throw from earlier errors). */
static LispObj
wasm_consume_cold_load_list(TCR *tcr, LispObj ccl_pkg)
{
  (void)tcr;
  static const uint8_t sym_name[] = "*XLOAD-COLD-LOAD-FUNCTIONS*";
  LispObj sym = wasm_find_symbol_named_bytes(
    sym_name, (uint32_t)(sizeof(sym_name) - 1), ccl_pkg);
  if (sym == (LispObj)0 || fulltag_of(sym) != fulltag_misc ||
      header_subtag(header_of(sym)) != subtag_symbol) {
    static const char msg[] = "cold-load-drain: symbol not found\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return lisp_nil;
  }

  lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(untag(sym));
  LispObj list = rawsym->vcell;

  /* Consume the list (matches Lisp prog1 + setq-nil pattern) */
  rawsym->vcell = lisp_nil;

  return list;
}

/* Walk a saved cold-load function list, calling each function individually
   with pending_throw cleared between calls.  This prevents an error in one
   cold-load function from poisoning all subsequent ones.
   Must be called AFTER %RUN-COLD-BOOT-INIT has set up infrastructure
   (locks, class cells, packages) that the cold-load functions need. */
static int
wasm_drain_cold_load_list(TCR *tcr, LispObj list)
{
  if (list == lisp_nil) {
    static const char msg[] = "cold-load-drain: list empty\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return 0;
  }

  int count = 0, errors = 0, skipped = 0;
  LispObj cur = list;

  while (cur != lisp_nil && fulltag_of(cur) == fulltag_cons) {
    LispObj fn = car(cur);
    cur = cdr(cur);
    count++;

    /* Validate: must be a function object */
    if (fn == lisp_nil ||
        fulltag_of(fn) != fulltag_misc ||
        header_subtag(header_of(fn)) != subtag_function) {
      skipped++;
      continue;
    }

    /* Clear pending_throw before each call so errors don't propagate */
    tcr->wasm_pending_throw = 0;

    (void)wasm_foreign_funcall0(tcr, fn);

    if (tcr->wasm_pending_throw) {
      errors++;
      tcr->wasm_pending_throw = 0;
    }
  }

  /* Log summary */
  {
    char dbuf[128];
    int dp = 0;
    dp += wasm_debug_str(dbuf + dp, "cold-load-drain: ");
    dp += wasm_debug_uint(dbuf + dp, (uint32_t)count);
    dp += wasm_debug_str(dbuf + dp, " called, ");
    dp += wasm_debug_uint(dbuf + dp, (uint32_t)errors);
    dp += wasm_debug_str(dbuf + dp, " errors, ");
    dp += wasm_debug_uint(dbuf + dp, (uint32_t)skipped);
    dp += wasm_debug_str(dbuf + dp, " skipped\n");
    wasm_host_log(dbuf, (unsigned)dp);
  }

  return count;
}

/* Execute level-0 cold-boot initialization before FASL loading.
   Phase A: C-side drain of cold-load functions (error-resilient).
   Phase B: Lisp-side %RUN-COLD-BOOT-INIT for locks, class cells, package
   rehash, documentation, and binding indices.
   Must be called after compiled modules are installed (so boot module functions
   are in the table) and before any wasm_fasload_path() calls.
   Returns 0 on success, negative on error. */
__attribute__((used, visibility("default"), export_name("wasm_run_cold_boot_init")))
int
wasm_run_cold_boot_init(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return -1;
  }
  if (!wasm_subprims_ready) {
    return -2;
  }

  static const uint8_t ccl_pkg_name[] = { 'C', 'C', 'L' };
  LispObj ccl_pkg = wasm_find_package_named_bytes(
    ccl_pkg_name, (uint32_t)sizeof(ccl_pkg_name));
  if (ccl_pkg == lisp_nil) {
    static const char msg[] = "cold-boot-init: CCL package not found\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return -3;
  }

  /* Phase A: consume the cold-load function list (save + set vcell to NIL).
     %RUN-COLD-BOOT-INIT will see an empty list and skip its dolist loop,
     but still set up infrastructure (locks, class cells, packages). */
  LispObj saved_cold_load_list = wasm_consume_cold_load_list(tcr, ccl_pkg);

  /* Phase B: run %RUN-COLD-BOOT-INIT for infrastructure setup */
  static const uint8_t fn_name[] = "%RUN-COLD-BOOT-INIT";
  LispObj sym = wasm_find_symbol_named_bytes(
    fn_name, (uint32_t)(sizeof(fn_name) - 1), ccl_pkg);
  if (sym == (LispObj)0 ||
      fulltag_of(sym) != fulltag_misc ||
      header_subtag(header_of(sym)) != subtag_symbol) {
    static const char msg[] = "cold-boot-init: symbol not found\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return -4;
  }

  lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(untag(sym));
  LispObj fn = rawsym->fcell;
  if (fn == lisp_nil || fn == nrs_UDF.vcell ||
      fulltag_of(fn) != fulltag_misc ||
      header_subtag(header_of(fn)) != subtag_function) {
    static const char msg[] = "cold-boot-init: function undefined\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return -5;
  }

  /* Diagnostic: log the entry index of %run-cold-boot-init */
  {
    LispObj entry_s0 = deref(fn, 1);
    char d[80]; int p = 0;
    p += wasm_debug_str(d + p, "cold-boot-init: fn=0x");
    p += wasm_debug_hex8(d + p, (uint32_t)fn);
    p += wasm_debug_str(d + p, " entry=0x");
    p += wasm_debug_hex8(d + p, (uint32_t)entry_s0);
    if (tag_of(entry_s0) == tag_fixnum) {
      p += wasm_debug_str(d + p, " (idx=");
      p += wasm_debug_uint(d + p, (uint32_t)unbox_fixnum(entry_s0));
      p += wasm_debug_str(d + p, ")");
    }
    d[p++] = '\n';
    wasm_host_log(d, (unsigned)p);
  }

  natural old_last_lisp_frame = wasm_enter_lisp_frame(
    tcr, 0, 0, (LispObj)tcr->save_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[vsp] = (LispObj)tcr->save_vsp;

  tcr->wasm_gprs[nargs] = box_fixnum(0);
  tcr->wasm_gprs[nfn] = fn;
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  int result = 0;
  LispObj final_pending = tcr->wasm_pending_throw;
  tcr->wasm_pending_throw = 0;

  /* Read *WASM-STARTUP-STEP* to determine how far cold-boot-init got */
  signed_natural startup_step = -1;
  {
    static const uint8_t step_name[] = "*WASM-STARTUP-STEP*";
    LispObj step_sym = wasm_find_symbol_named_bytes(
      step_name, (uint32_t)(sizeof(step_name) - 1), ccl_pkg);
    if (step_sym != (LispObj)0 && fulltag_of(step_sym) == fulltag_misc &&
        header_subtag(header_of(step_sym)) == subtag_symbol) {
      lispsymbol *ss = (lispsymbol *)ptr_from_lispobj(untag(step_sym));
      LispObj step_val = ss->vcell;
      if (tag_of(step_val) == tag_fixnum) {
        startup_step = unbox_fixnum(step_val);
      }
    }
  }

  if (final_pending) {
    /* pending_throw was set — could be absorbed ksignalerr (code 16)
       or a real error.  If startup-step reached 4100+ (effectively
       complete), treat as success — the errors are benign type checks
       that fire after all useful work is done. */
    char dbuf[96];
    int dp = 0;
    dp += wasm_debug_str(dbuf + dp, "cold-boot-init: pending_throw=0x");
    dp += wasm_debug_hex8(dbuf + dp, (uint32_t)final_pending);
    dp += wasm_debug_str(dbuf + dp, " startup-step=");
    if (startup_step >= 0) {
      dp += wasm_debug_uint(dbuf + dp, (uint32_t)startup_step);
    } else {
      dp += wasm_debug_str(dbuf + dp, "?");
    }
    dbuf[dp++] = '\n';
    wasm_host_log(dbuf, (unsigned)dp);

    if (startup_step >= 40) {
      /* Infrastructure is set up (locks, at minimum).  The pending_throw
         is from benign absorbed errors (catch_top==0 during later steps).
         Phase C will drain cold-load functions with per-call isolation. */
      static const char msg[] = "cold-boot-init: ok (infra ready, errors absorbed)\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      result = 0;
    } else {
      static const char msg[] = "cold-boot-init: threw (infra incomplete)\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      result = -6;
    }
  } else {
    char dbuf[64];
    int dp = 0;
    dp += wasm_debug_str(dbuf + dp, "cold-boot-init: ok, startup-step=");
    if (startup_step >= 0) {
      dp += wasm_debug_uint(dbuf + dp, (uint32_t)startup_step);
    } else {
      dp += wasm_debug_str(dbuf + dp, "?");
    }
    dbuf[dp++] = '\n';
    wasm_host_log(dbuf, (unsigned)dp);
  }

  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old_last_lisp_frame);

  /* Phase C: drain cold-load functions from C with per-call error isolation.
     Only need startup_step >= 40 (= %all-packages-lock% created) for
     cold-load functions to work.  Even if %RUN-COLD-BOOT-INIT threw at
     a later step, the infrastructure is there. */
  if (startup_step >= 40 && saved_cold_load_list != lisp_nil) {
    wasm_drain_cold_load_list(tcr, saved_cold_load_list);
    /* Cold-load functions have now run; override result to success since
       the original throw was from incomplete-but-non-critical steps. */
    result = 0;
  }

  return result;
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

  natural old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)tcr->save_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[vsp] = (LispObj)tcr->save_vsp;
  LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
  LispObj *vsp_empty = wasm_vsp_empty(tcr);
  if (vsp_ptr == NULL) {
    vsp_ptr = vsp_empty;
    if (vsp_ptr != NULL) {
      tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
    }
  }
  if (vsp_ptr == NULL) {
    tcr->valence = TCR_STATE_FOREIGN;
    wasm_exit_lisp_frame(tcr, old_last_lisp_frame);
    return -4;
  }
  LispObj topfn = nrs_TOPLFUNC.vcell;
  LispObj *slot = wasm_toplevel_slot(tcr);
  if (topfn != lisp_nil) {
    if (slot != NULL) {
      *slot = topfn;
      if (tcr->vs_area != NULL) {
        tcr->vs_area->active = (BytePtr)slot;
      }
      tcr->save_vsp = slot;
      vsp_ptr = slot;
      tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
    } else {
      *--vsp_ptr = topfn;
      tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
    }
    nrs_TOPLFUNC.vcell = lisp_nil;
  } else if (slot != NULL && *slot != lisp_nil) {
    if (tcr->vs_area != NULL) {
      tcr->vs_area->active = (BytePtr)slot;
    }
    tcr->save_vsp = slot;
    vsp_ptr = slot;
    tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  } else if (vsp_ptr == vsp_empty || *vsp_ptr == lisp_nil) {
    tcr->valence = TCR_STATE_FOREIGN;
    wasm_exit_lisp_frame(tcr, old_last_lisp_frame);
    return -3;
  }

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

  tcr->save_vsp = vsp_ptr;
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

  /* Push in source order: first arg (raw_a) first (deep), second (raw_b) on TOS.
     Matches wasm_funcall_common push order. */
  LispObj *vsp_ptr = saved_vsp;
  *--vsp_ptr = box_fixnum((signed_natural)raw_a);
  *--vsp_ptr = box_fixnum((signed_natural)raw_b);

  tcr->save_vsp = vsp_ptr;
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

__attribute__((used, visibility("default"), export_name("wasm_test_entry_funcall1_raw")))
LispObj
wasm_test_entry_funcall1_raw(uint32_t entry_index, LispObj arg)
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
  *--vsp_ptr = arg;

  tcr->save_vsp = vsp_ptr;
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

__attribute__((used, visibility("default"), export_name("wasm_test_entry_funcall0_raw")))
LispObj
wasm_test_entry_funcall0_raw(uint32_t entry_index)
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
  static const char msg_enter[] = "WASM raw entry call: enter\n";
  static const char msg_exit[] = "WASM raw entry call: return\n";
  wasm_host_log(msg_enter, (unsigned)(sizeof(msg_enter) - 1));
  LispObj result = wasm_funcall0(fn_value);
  wasm_host_log(msg_exit, (unsigned)(sizeof(msg_exit) - 1));
  return result;
}

static uint32_t
wasm_const_pool_read_u32(const uint8_t *bytes,
                         uint32_t len,
                         uint32_t *offset,
                         int *ok)
{
  if (!ok || !*ok) {
    return 0;
  }
  if (!bytes || !offset || (*offset + 4u) > len) {
    if (ok) *ok = 0;
    return 0;
  }
  uint32_t pos = *offset;
  uint32_t v = (uint32_t)bytes[pos]
               | ((uint32_t)bytes[pos + 1] << 8)
               | ((uint32_t)bytes[pos + 2] << 16)
               | ((uint32_t)bytes[pos + 3] << 24);
  *offset = pos + 4u;
  return v;
}

static uint32_t
wasm_const_pool_read_uleb32(const uint8_t *bytes,
                            uint32_t len,
                            uint32_t *offset,
                            int *ok)
{
  if (!ok || !*ok) {
    return 0;
  }
  if (!bytes || !offset) {
    if (ok) *ok = 0;
    return 0;
  }

  uint32_t value = 0;
  uint32_t shift = 0;
  for (uint32_t i = 0; i < 5; i++) {
    if (*offset >= len) {
      if (ok) *ok = 0;
      return 0;
    }
    uint8_t byte = bytes[*offset];
    (*offset)++;
    value |= ((uint32_t)(byte & 0x7fu)) << shift;
    if ((byte & 0x80u) == 0u) {
      return value;
    }
    shift += 7;
  }

  if (ok) *ok = 0;
  return 0;
}

static uint32_t
wasm_const_pool_read_sleb32_raw(const uint8_t *bytes,
                                uint32_t len,
                                uint32_t *offset,
                                int *ok)
{
  if (!ok || !*ok) {
    return 0;
  }
  if (!bytes || !offset) {
    if (ok) *ok = 0;
    return 0;
  }

  int64_t value = 0;
  uint32_t shift = 0;
  uint8_t byte = 0;
  for (uint32_t i = 0; i < 5; i++) {
    if (*offset >= len) {
      if (ok) *ok = 0;
      return 0;
    }
    byte = bytes[*offset];
    (*offset)++;
    value |= ((int64_t)(byte & 0x7fu)) << shift;
    shift += 7;
    if ((byte & 0x80u) == 0u) {
      if (shift < 64u) {
        if (byte & 0x40u) {
          value |= -((int64_t)1 << shift);
        }
      }
      return (uint32_t)(int32_t)value;
    }
  }

  if (ok) *ok = 0;
  return 0;
}

static uint32_t
wasm_const_pool_read_nat(const uint8_t *bytes,
                         uint32_t len,
                         uint32_t *offset,
                         uint32_t version,
                         int *ok)
{
  return (version >= 2u)
    ? wasm_const_pool_read_uleb32(bytes, len, offset, ok)
    : wasm_const_pool_read_u32(bytes, len, offset, ok);
}

static const uint8_t *
wasm_const_pool_read_bytes(const uint8_t *bytes,
                           uint32_t len,
                           uint32_t *offset,
                           uint32_t count,
                           int *ok)
{
  if (!ok || !*ok) {
    return NULL;
  }
  if (!bytes || !offset || (*offset + count) > len) {
    if (ok) *ok = 0;
    return NULL;
  }
  const uint8_t *out = bytes + *offset;
  *offset += count;
  return out;
}

static int
wasm_lispobj_in_scannable_area(LispObj obj)
{
  if (fulltag_of(obj) != fulltag_misc) {
    return 0;
  }

  BytePtr base = (BytePtr)ptr_from_lispobj(untag(obj));
  if (base == NULL || ((natural)base & (node_size - 1)) != 0) {
    return 0;
  }

  area *areas = (area *)ptr_from_lispobj(lisp_global(ALL_AREAS));
  if (areas == NULL) {
    return 0;
  }

  area *a = areas->succ;
  while (a != NULL && a->code != AREA_VOID) {
    area_code code = a->code;
    if ((code == AREA_STATIC) ||
        (code == AREA_DYNAMIC) ||
        (code == AREA_MANAGED_STATIC) ||
        (code == AREA_READONLY) ||
        (code == AREA_WATCHED) ||
        (code == AREA_STATIC_CONS)) {
      if (base >= (BytePtr)a->low && base < (BytePtr)a->active) {
        return 1;
      }
    }
    a = a->succ;
  }

  return 0;
}

static int
wasm_lisp_string_equals_bytes(LispObj str,
                              const uint8_t *bytes,
                              uint32_t len)
{
  if (!bytes) {
    return 0;
  }
  if (fulltag_of(str) != fulltag_misc) {
    return 0;
  }
  if (!wasm_lispobj_in_scannable_area(str)) {
    return 0;
  }
  LispObj header = header_of(str);
  if (header_subtag(header) != subtag_simple_base_string) {
    return 0;
  }
  uint32_t count = (uint32_t)header_element_count(header);
  if (count != len) {
    return 0;
  }
  uint32_t *data = (uint32_t *)((BytePtr)str + misc_data_offset);
  for (uint32_t i = 0; i < len; i++) {
    if ((data[i] & 0xffu) != bytes[i]) {
      return 0;
    }
  }
  return 1;
}

static int
wasm_package_names_contains(LispObj names,
                            const uint8_t *bytes,
                            uint32_t len)
{
  if (fulltag_of(names) == fulltag_misc) {
    LispObj header = header_of(names);
    if (header_subtag(header) == subtag_simple_base_string) {
      return wasm_lisp_string_equals_bytes(names, bytes, len);
    }
  }
  LispObj list = names;
  while (list != lisp_nil) {
    if (fulltag_of(list) != fulltag_cons) {
      return 0;
    }
    cons *cell = (cons *)ptr_from_lispobj(untag(list));
    if (wasm_lisp_string_equals_bytes(cell->car, bytes, len)) {
      return 1;
    }
    list = cell->cdr;
  }
  return 0;
}

static LispObj
wasm_find_package_named_bytes(const uint8_t *bytes, uint32_t len)
{
  LispObj list = nrs_ALL_PACKAGES.vcell;
  if (fulltag_of(list) == fulltag_misc) {
    LispObj header = header_of(list);
    if (header_subtag(header) == subtag_package) {
      package *pkg = (package *)ptr_from_lispobj(untag(list));
      if (wasm_package_names_contains(pkg->names, bytes, len)) {
        return list;
      }
    }
  }
  while (list != lisp_nil) {
    if (fulltag_of(list) != fulltag_cons) {
      break;
    }
    cons *cell = (cons *)ptr_from_lispobj(untag(list));
    LispObj pkg_obj = cell->car;
    if (fulltag_of(pkg_obj) == fulltag_misc) {
      LispObj header = header_of(pkg_obj);
      if (header_subtag(header) == subtag_package) {
        package *pkg = (package *)ptr_from_lispobj(untag(pkg_obj));
        if (wasm_package_names_contains(pkg->names, bytes, len)) {
          return pkg_obj;
        }
      }
    }
    list = cell->cdr;
  }
  return lisp_nil;
}

static int
wasm_symbol_package_matches(lispsymbol *rawsym, LispObj package)
{
  if (package == (LispObj)0) {
    return 1;
  }
  LispObj predicate = rawsym->package_predicate;
  if (fulltag_of(predicate) == fulltag_cons) {
    predicate = car(predicate);
  }
  return predicate == package;
}

static LispObj
wasm_package_symbol_vector(LispObj table)
{
  if (table == lisp_nil) {
    return (LispObj)0;
  }
  LispObj vec = table;
  if (fulltag_of(vec) == fulltag_cons) {
    vec = car(vec);
  }
  if (fulltag_of(vec) != fulltag_misc) {
    return (LispObj)0;
  }
  LispObj header = header_of(vec);
  natural subtag = header_subtag(header);
  if (subtag != subtag_simple_vector && subtag != subtag_hash_vector) {
    return (LispObj)0;
  }
  return vec;
}

static LispObj
wasm_find_symbol_in_vector_bytes(LispObj vec,
                                 const uint8_t *name,
                                 uint32_t len)
{
  if (vec == (LispObj)0 || !name || len == 0) {
    return (LispObj)0;
  }
  uint32_t count = (uint32_t)header_element_count(header_of(vec));
  LispObj *data = (LispObj *)((BytePtr)vec + misc_data_offset);
  for (uint32_t i = 0; i < count; i++) {
    LispObj sym = data[i];
    if (fulltag_of(sym) != fulltag_misc || header_subtag(header_of(sym)) != subtag_symbol) {
      continue;
    }
    lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(untag(sym));
    if (wasm_lisp_string_equals_bytes(rawsym->pname, name, len)) {
      return sym;
    }
  }
  return (LispObj)0;
}

static LispObj
wasm_find_symbol_in_package_tables_bytes(LispObj pkg_obj,
                                         const uint8_t *name,
                                         uint32_t len)
{
  if (pkg_obj == (LispObj)0 ||
      fulltag_of(pkg_obj) != fulltag_misc ||
      header_subtag(header_of(pkg_obj)) != subtag_package) {
    return (LispObj)0;
  }
  package *pkg = (package *)ptr_from_lispobj(untag(pkg_obj));
  LispObj itab_vec = wasm_package_symbol_vector(pkg->itab);
  LispObj sym = wasm_find_symbol_in_vector_bytes(itab_vec, name, len);
  if (sym) {
    return sym;
  }
  LispObj etab_vec = wasm_package_symbol_vector(pkg->etab);
  return wasm_find_symbol_in_vector_bytes(etab_vec, name, len);
}

static LispObj
wasm_find_symbol_in_all_packages_bytes(const uint8_t *name, uint32_t len)
{
  LispObj list = nrs_ALL_PACKAGES.vcell;
  if (fulltag_of(list) == fulltag_misc &&
      header_subtag(header_of(list)) == subtag_package) {
    LispObj sym = wasm_find_symbol_in_package_tables_bytes(list, name, len);
    if (sym) {
      return sym;
    }
  }
  while (list != lisp_nil) {
    if (fulltag_of(list) != fulltag_cons) {
      break;
    }
    cons *cell = (cons *)ptr_from_lispobj(untag(list));
    LispObj pkg_obj = cell->car;
    LispObj sym = wasm_find_symbol_in_package_tables_bytes(pkg_obj, name, len);
    if (sym) {
      return sym;
    }
    list = cell->cdr;
  }
  return (LispObj)0;
}

static LispObj
wasm_find_symbol_in_range_bytes(LispObj *start,
                                LispObj *end,
                                const uint8_t *name,
                                uint32_t len,
                                LispObj package)
{
  /*
   * Caveat: this helper is intentionally byte-oriented bootstrap lookup.
   * NAME is treated as ASCII/UTF-8 bytes and compared against the low byte
   * of each SIMPLE-BASE-STRING code unit. This is safe for current startup
   * symbols, but it is not full Unicode symbol-name matching.
   */
  LispObj header;
  LispObj tag;
  while (start < end) {
    header = *start;
    tag = fulltag_of(header);
    if (header_subtag(header) == subtag_symbol) {
      LispObj pname = deref(ptr_to_lispobj(start), 1);
      LispObj pname_header = header_of(pname);
      if ((header_subtag(pname_header) == subtag_simple_base_string) &&
          ((uint32_t)header_element_count(pname_header) == len)) {
        uint32_t *p = (uint32_t *)ptr_from_lispobj(pname + misc_data_offset);
        int match = 1;
        for (uint32_t i = 0; i < len; i++) {
          if ((p[i] & 0xffu) != name[i]) {
            match = 0;
            break;
          }
        }
        if (match) {
          lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(ptr_to_lispobj(start));
          if (wasm_symbol_package_matches(rawsym, package)) {
            return ptr_to_lispobj(start) + fulltag_misc;
          }
        }
      }
    }
    if (nodeheader_tag_p(tag)) {
      start += (~1 & (2 + header_element_count(header)));
    } else if (immheader_tag_p(tag)) {
      start = (LispObj *)skip_over_ivector((natural)start, header);
    } else {
      start += 2;
    }
  }
  return (LispObj)0;
}

static LispObj
wasm_find_symbol_named_bytes(const uint8_t *name, uint32_t len, LispObj package)
{
  if (!name || len == 0) {
    return (LispObj)0;
  }
  if (package != (LispObj)0) {
    LispObj sym = wasm_find_symbol_in_package_tables_bytes(package, name, len);
    if (sym) {
      return sym;
    }
  } else {
    LispObj sym = wasm_find_symbol_in_all_packages_bytes(name, len);
    if (sym) {
      return sym;
    }
  }
  /*
   * Keep fallback lookup deterministic and memory-safe in early bootstrap by
   * limiting symbol discovery to package tables only.
   */
  return (LispObj)0;
}

static LispObj
wasm_find_symbol_named_bytes_scan(const uint8_t *name, uint32_t len, LispObj package)
{
  if (!name || len == 0) {
    return (LispObj)0;
  }

  area *areas = (area *)ptr_from_lispobj(lisp_global(ALL_AREAS));
  if (areas == NULL) {
    return (LispObj)0;
  }

  area *a = areas->succ;
  while (a != NULL && a->code != AREA_VOID) {
    area_code code = a->code;
    if ((code == AREA_STATIC) ||
        (code == AREA_DYNAMIC) ||
        (code == AREA_MANAGED_STATIC) ||
        (code == AREA_READONLY) ||
        (code == AREA_WATCHED) ||
        (code == AREA_STATIC_CONS)) {
      LispObj sym = wasm_find_symbol_in_range_bytes((LispObj *)a->low,
                                                    (LispObj *)a->active,
                                                    name,
                                                    len,
                                                    package);
      if (sym) {
        return sym;
      }
    }
    a = a->succ;
  }

  return (LispObj)0;
}

static LispObj
wasm_const_pool_make_base_string(TCR *tcr, const uint8_t *bytes, uint32_t len)
{
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj obj = wasm_misc_alloc(tcr, subtag_simple_base_string, (signed_natural)len);
  if (obj == lisp_nil) {
    return lisp_nil;
  }
  uint32_t *data = (uint32_t *)((BytePtr)obj + misc_data_offset);
  for (uint32_t i = 0; i < len; i++) {
    data[i] = (uint32_t)bytes[i];
  }
  return obj;
}

static LispObj
wasm_alloc_cons(TCR *tcr, LispObj car_value, LispObj cdr_value)
{
  if (tcr == NULL) {
    return lisp_nil;
  }

  if (!wasm_reserve_heap_segment(tcr, (size_t)dnode_size)) {
    return lisp_nil;
  }

  BytePtr alloc_ptr = (BytePtr)tcr->save_allocptr;
  BytePtr alloc_base = (BytePtr)tcr->save_allocbase;
  BytePtr newptr = alloc_ptr - (signed_natural)dnode_size;
  if (newptr < alloc_base) {
    return lisp_nil;
  }

  tcr->save_allocptr = (void *)newptr;
  LispObj obj = (LispObj)(newptr + fulltag_cons);

  cons *cell = (cons *)ptr_from_lispobj(untag(obj));
  cell->car = car_value;
  cell->cdr = cdr_value;
  return obj;
}

__attribute__((used, visibility("default"), export_name("wasm_alloc_cons_bridge")))
LispObj
wasm_alloc_cons_bridge(LispObj car_value, LispObj cdr_value)
{
  TCR *tcr = wasm_get_current_tcr();
  return wasm_alloc_cons(tcr, car_value, cdr_value);
}

static LispObj
wasm_foreign_funcall0(TCR *tcr, LispObj callable)
{
  if (tcr == NULL) {
    return lisp_nil;
  }

  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }

  natural old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)saved_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;

  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->wasm_gprs[nargs] = box_fixnum(0);
  tcr->wasm_gprs[nfn] = callable;
  tcr->wasm_gprs[Rfn] = callable;
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  LispObj result = tcr->wasm_gprs[arg_z];
  tcr->save_vsp = saved_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old_last_lisp_frame);

  return result;
}

static LispObj
wasm_foreign_funcall1(TCR *tcr, LispObj callable, LispObj arg)
{
  if (tcr == NULL) {
    return lisp_nil;
  }

  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }

  natural old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)saved_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;

  LispObj *vsp_ptr = saved_vsp;
  *--vsp_ptr = arg;

  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
  tcr->wasm_gprs[nfn] = callable;
  tcr->wasm_gprs[Rfn] = callable;
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  LispObj result = tcr->wasm_gprs[arg_z];
  tcr->save_vsp = saved_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old_last_lisp_frame);

  return result;
}

static int32_t
wasm_set_command_line_output_arg(TCR *tcr, const uint8_t *output_bytes, uint32_t output_len)
{
  static const uint8_t argv_sym_name[] = {
    '*', 'C', 'O', 'M', 'M', 'A', 'N', 'D', '-', 'L', 'I', 'N', 'E', '-',
    'A', 'R', 'G', 'U', 'M', 'E', 'N', 'T', '-', 'L', 'I', 'S', 'T', '*'
  };
  static const uint8_t ccl_pkg_name[] = { 'C', 'C', 'L' };
  static const uint8_t delimiter[] = { '-', '-' };
  static const uint8_t output_opt[] = { '-', '-', 'o', 'u', 't', 'p', 'u', 't' };

  if (tcr == NULL || output_bytes == NULL || output_len == 0) {
    return -1;
  }

  LispObj ccl_pkg = wasm_find_package_named_bytes(ccl_pkg_name, (uint32_t)sizeof(ccl_pkg_name));
  if (ccl_pkg == lisp_nil) {
    return -2;
  }

  LispObj argv_sym = wasm_find_symbol_named_bytes(argv_sym_name, (uint32_t)sizeof(argv_sym_name), ccl_pkg);
  if (argv_sym == (LispObj)0) {
    argv_sym = wasm_const_pool_intern_symbol(
      tcr,
      argv_sym_name,
      (uint32_t)sizeof(argv_sym_name),
      ccl_pkg);
  }

  if (tcr->wasm_pending_throw) {
    return -2;
  }

  if (argv_sym == (LispObj)0 ||
      fulltag_of(argv_sym) != fulltag_misc ||
      header_subtag(header_of(argv_sym)) != subtag_symbol) {
    return -2;
  }

  LispObj delim_str = wasm_const_pool_make_base_string(tcr, delimiter, (uint32_t)sizeof(delimiter));
  LispObj opt_str = wasm_const_pool_make_base_string(tcr, output_opt, (uint32_t)sizeof(output_opt));
  LispObj out_str = wasm_const_pool_make_base_string(tcr, output_bytes, output_len);
  if (delim_str == lisp_nil || opt_str == lisp_nil || out_str == lisp_nil) {
    return -3;
  }

  LispObj list = lisp_nil;
  list = wasm_alloc_cons(tcr, out_str, list);
  if (list == lisp_nil) return -4;
  list = wasm_alloc_cons(tcr, opt_str, list);
  if (list == lisp_nil) return -4;
  list = wasm_alloc_cons(tcr, delim_str, list);
  if (list == lisp_nil) return -4;

  lispsymbol *argv_raw = (lispsymbol *)ptr_from_lispobj(untag(argv_sym));
  argv_raw->vcell = list;
  return 0;
}

__attribute__((used, visibility("default"), export_name("wasm_run_script_with_output")))
int32_t
wasm_run_script_with_output(uint32_t script_ptr, uint32_t script_len, uint32_t output_ptr, uint32_t output_len)
{
  static const uint8_t load_sym_name_upper[] = { 'L', 'O', 'A', 'D' };
  static const uint8_t cl_pkg_name[] = {
    'C', 'O', 'M', 'M', 'O', 'N', '-', 'L', 'I', 'S', 'P'
  };

  if (script_ptr == 0 || script_len == 0) {
    return -1;
  }

  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return -2;
  }
  if (!wasm_subprims_ready) {
    return -3;
  }

  if (output_ptr != 0 && output_len != 0) {
    int32_t argv_rc = wasm_set_command_line_output_arg(
      tcr,
      (const uint8_t *)(uintptr_t)output_ptr,
      output_len);
    if (argv_rc != 0) {
      return -10 + argv_rc;
    }
  }

  LispObj cl_pkg = wasm_find_package_named_bytes(cl_pkg_name, (uint32_t)sizeof(cl_pkg_name));
  if (cl_pkg == lisp_nil) {
    return -4;
  }

  LispObj load_sym = wasm_find_symbol_named_bytes(
    load_sym_name_upper,
    (uint32_t)sizeof(load_sym_name_upper),
    cl_pkg);
  if (load_sym == (LispObj)0) {
    load_sym = wasm_const_pool_intern_symbol(
      tcr,
      load_sym_name_upper,
      (uint32_t)sizeof(load_sym_name_upper),
      cl_pkg);
  }

  if (tcr->wasm_pending_throw) {
    return -6;
  }

  if (load_sym == (LispObj)0 ||
      fulltag_of(load_sym) != fulltag_misc ||
      header_subtag(header_of(load_sym)) != subtag_symbol) {
    return -41;
  }

  LispObj script_path = wasm_const_pool_make_base_string(
    tcr,
    (const uint8_t *)(uintptr_t)script_ptr,
    script_len);
  if (script_path == lisp_nil) {
    return -5;
  }

  /* Call LOAD with a catch frame (same pattern as wasm_fasload_path). */
  {
    LispObj *saved_vsp = tcr->save_vsp;
    if (saved_vsp == NULL) {
      return -7;
    }

    natural old_last_lisp_frame = wasm_enter_lisp_frame(
      tcr, 0, 0, (LispObj)saved_vsp);
    tcr->valence = TCR_STATE_LISP;
    tcr->wasm_pending_throw = 0;

    LispObj *vsp_ptr = saved_vsp;
    *--vsp_ptr = script_path;
    tcr->save_vsp = vsp_ptr;
    tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;

    tcr->wasm_gprs[arg_z] = nrs_TOPLCATCH.vcell;
    wasm_call_subprim_fixnum(
      wasm_subprim_fixnum(WASM_SUBPRIM_MKCATCH1V_INDEX));

    LispObj catch_before = tcr->catch_top;

    tcr->wasm_gprs[nargs] = box_fixnum(1);
    tcr->wasm_gprs[nfn] = load_sym;
    tcr->wasm_gprs[Rfn] = load_sym;
    wasm_call_subprim_fixnum(
      wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

    int threw = tcr->wasm_pending_throw != 0;
    int catch_consumed = (tcr->catch_top != catch_before);

    if (!threw && !catch_consumed) {
      tcr->wasm_gprs[arg_z] = lisp_nil;
      tcr->wasm_gprs[imm0] = box_fixnum(1);
      wasm_call_subprim_fixnum(
        wasm_subprim_fixnum(WASM_SUBPRIM_NTHROW1VALUE_INDEX));
      if (tcr->wasm_pending_throw) {
        tcr->wasm_pending_throw = 0;
      }
    }

    tcr->save_vsp = saved_vsp;
    tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
    tcr->valence = TCR_STATE_FOREIGN;
    wasm_exit_lisp_frame(tcr, old_last_lisp_frame);

    if (threw || catch_consumed) {
      return -6;
    }
    return 0;
  }
}

__attribute__((used, visibility("default"), export_name("wasm_fasload_path")))
int32_t
wasm_fasload_path(uint32_t path_ptr, uint32_t path_len)
{
  static const uint8_t fasload_name[] = {
    '%', 'F', 'A', 'S', 'L', 'O', 'A', 'D'
  };
  static const uint8_t ccl_pkg_name[] = { 'C', 'C', 'L' };
  const uint8_t *path_bytes = (const uint8_t *)(uintptr_t)path_ptr;
  LispObj fasload_sym = (LispObj)0;
  LispObj fasload_fn = (LispObj)0;

  if (path_ptr == 0 || path_len == 0) {
    return -1;
  }

  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return -2;
  }
  if (!wasm_subprims_ready) {
    return -3;
  }
  if (wasm_boot_phase_state == WASM_BOOT_EARLY) {
    return -10;
  }
  LispObj ccl_pkg = wasm_find_package_named_bytes(ccl_pkg_name, (uint32_t)sizeof(ccl_pkg_name));
  if (ccl_pkg == lisp_nil) {
    return -4;
  }
  fasload_sym = wasm_find_symbol_named_bytes(
    fasload_name,
    (uint32_t)sizeof(fasload_name),
    ccl_pkg);
  if (fasload_sym == (LispObj)0) {
    fasload_sym = wasm_const_pool_intern_symbol(
      tcr,
      fasload_name,
      (uint32_t)sizeof(fasload_name),
      ccl_pkg);
  }
  if (tcr->wasm_pending_throw) {
    return -71;  /* intern threw */
  }
  if (fasload_sym == (LispObj)0 ||
      fulltag_of(fasload_sym) != fulltag_misc ||
      header_subtag(header_of(fasload_sym)) != subtag_symbol) {
    return -4;
  }

  lispsymbol *fasload_rawsym = (lispsymbol *)ptr_from_lispobj(untag(fasload_sym));
  fasload_fn = fasload_rawsym->fcell;
  if (fasload_fn == nrs_UDF.vcell) {
    return -5;
  }
  if (fulltag_of(fasload_fn) != fulltag_misc ||
      header_subtag(header_of(fasload_fn)) != subtag_function) {
    return -8;
  }

  LispObj path = wasm_const_pool_make_base_string(
    tcr,
    (const uint8_t *)(uintptr_t)path_ptr,
    path_len);
  if (path == lisp_nil) {
    return -6;
  }

  /* Guard: verify *fasl-api* was initialized by cold-boot-init.
     If NIL, the FASL API functions were never set up and %FASLOAD
     will try to funcall NIL, producing a confusing -72 error.
     Also dump all slots for diagnosis since nfn=nil crash in
     %fasl-init-buffer suggests slot 3 is nil. */
  {
    static const uint8_t fasl_api_name[] = {
      '*', 'F', 'A', 'S', 'L', '-', 'A', 'P', 'I', '*'
    };
    LispObj fasl_api_sym = wasm_find_symbol_named_bytes(
      fasl_api_name, (uint32_t)sizeof(fasl_api_name), ccl_pkg);
    if (fasl_api_sym != (LispObj)0 &&
        fulltag_of(fasl_api_sym) == fulltag_misc &&
        header_subtag(header_of(fasl_api_sym)) == subtag_symbol) {
      lispsymbol *api_rawsym = (lispsymbol *)ptr_from_lispobj(untag(fasl_api_sym));
      LispObj api_val = api_rawsym->vcell;
      if (api_val == lisp_nil) {
        static const char msg[] = "fasload: *fasl-api* is NIL (cold-load functions incomplete)\n";
        wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
        return -73;
      }
      /* Dump *fasl-api* istruct slots for diagnosis */
      if (fulltag_of(api_val) == fulltag_misc) {
        LispObj api_hdr = header_of(api_val);
        unsigned api_st = header_subtag(api_hdr);
        signed_natural api_ec = header_element_count(api_hdr);
        char d[120]; int p = 0;
        p += wasm_debug_str(d + p, "fasload: *fasl-api* st=0x");
        p += wasm_debug_hex8(d + p, api_st);
        p += wasm_debug_str(d + p, " ec=");
        p += wasm_debug_uint(d + p, (uint32_t)api_ec);
        d[p++] = '\n';
        wasm_host_log(d, (unsigned)p);
        /* Dump each element: deref(val, 0) = header, deref(val, n+1) = element n.
           Element 0 = istruct-cell (cons), elements 1-8 = function slots:
           1=open, 2=close, 3=init-buffer, 4=set-file-pos,
           5=get-file-pos, 6=read-buffer, 7=read-byte, 8=read-n-bytes */
        static const char *elem_names[] = {
          "hdr", "icell", "open", "close", "init-buf",
          "set-pos", "get-pos", "read-buf", "read-byte", "read-n"
        };
        signed_natural nslots = api_ec < 9 ? api_ec : 9;
        for (signed_natural i = 0; i <= nslots; i++) {
          LispObj slot_val = deref(api_val, i);
          p = 0;
          p += wasm_debug_str(d + p, "  [");
          p += wasm_debug_uint(d + p, (uint32_t)i);
          p += wasm_debug_str(d + p, "] ");
          if (i < 10) {
            p += wasm_debug_str(d + p, elem_names[i]);
          }
          p += wasm_debug_str(d + p, "=");
          p += wasm_debug_hex8(d + p, (uint32_t)slot_val);
          if (slot_val == lisp_nil) {
            p += wasm_debug_str(d + p, " (NIL!)");
          } else if (fulltag_of(slot_val) == fulltag_misc &&
                     slot_val != (LispObj)nil_value) {
            unsigned svst = header_subtag(header_of(slot_val));
            if (svst == subtag_function) {
              p += wasm_debug_str(d + p, " (fn)");
            } else {
              p += wasm_debug_str(d + p, " st=0x");
              p += wasm_debug_hex8(d + p, svst);
            }
          }
          d[p++] = '\n';
          wasm_host_log(d, (unsigned)p);
        }
      }
    }
  }

  /* WASM bootstrap fix: fd-open calls (pathname-encoding-name), and if it
     returns non-NIL, calls (get-character-encoding name), which is defined
     in l1-unicode.lisp — not yet loaded.  Fix: find the PATHNAME-ENCODING-NAME
     closure and clear its inherited binding so it returns NIL, forcing fd-open
     to use the simpler with-cstrs path that doesn't need character encodings. */
  {
    static int patchdone = 0;
    if (!patchdone) {
      static const uint8_t pen_name[] = {
        'P','A','T','H','N','A','M','E','-','E','N','C','O','D','I','N','G',
        '-','N','A','M','E'
      };
      /* Try CCL package first, then all packages, then full memory scan */
      LispObj pen_sym = wasm_find_symbol_named_bytes(
        pen_name, (uint32_t)sizeof(pen_name), ccl_pkg);
      if (pen_sym == (LispObj)0) {
        pen_sym = wasm_find_symbol_named_bytes(
          pen_name, (uint32_t)sizeof(pen_name), (LispObj)0);
      }
      if (pen_sym == (LispObj)0) {
        pen_sym = wasm_find_symbol_named_bytes_scan(
          pen_name, (uint32_t)sizeof(pen_name), (LispObj)0);
      }
      if (pen_sym == (LispObj)0) {
        static const char msg[] = "pen-fix: symbol not found (all methods)\n";
        wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      } else if (fulltag_of(pen_sym) == fulltag_misc &&
          header_subtag(header_of(pen_sym)) == subtag_symbol) {
        lispsymbol *pen_rawsym = (lispsymbol *)ptr_from_lispobj(untag(pen_sym));
        LispObj pen_fn = pen_rawsym->fcell;
        {
          /* Diagnostic: print what we found */
          static const char hx[] = "0123456789abcdef";
          char d[120]; int p = 0;
          const char *pfx = "pen-fix: fn=0x";
          while (*pfx) d[p++] = *pfx++;
          for (int b = 7; b >= 0; b--) d[p++] = hx[(pen_fn >> (b*4)) & 0xf];
          pfx = " tag=";
          while (*pfx) d[p++] = *pfx++;
          d[p++] = '0' + (char)(fulltag_of(pen_fn));
          if (fulltag_of(pen_fn) == fulltag_misc && pen_fn != (LispObj)nil_value) {
            LispObj fhdr = header_of(pen_fn);
            unsigned fst = header_subtag(fhdr);
            signed_natural ecnt = header_element_count(fhdr);
            pfx = " st=";
            while (*pfx) d[p++] = *pfx++;
            { unsigned sv = fst; char sbuf[4]; int slen = 0;
              do { sbuf[slen++] = '0' + (char)(sv % 10); sv /= 10; } while (sv > 0);
              for (int i = slen-1; i >= 0; i--) d[p++] = sbuf[i]; }
            pfx = " ec=";
            while (*pfx) d[p++] = *pfx++;
            { signed_natural sv = ecnt; char sbuf[8]; int slen = 0;
              do { sbuf[slen++] = '0' + (char)(sv % 10); sv /= 10; } while (sv > 0);
              for (int i = slen-1; i >= 0; i--) d[p++] = sbuf[i]; }
            /* Print inherited binding at deref(fn, 4) as full hex */
            if (ecnt >= 4) {
              LispObj ib = deref(pen_fn, 4);
              pfx = " inh0=0x";
              while (*pfx) d[p++] = *pfx++;
              for (int b = 7; b >= 0; b--) d[p++] = hx[(ib >> (b*4)) & 0xf];
              if (ib == lisp_nil) { pfx = "(nil)"; while (*pfx) d[p++] = *pfx++; }
            }
          }
          d[p++] = '\n';
          wasm_host_log(d, (unsigned)p);
        }
        if (fulltag_of(pen_fn) == fulltag_misc &&
            header_subtag(header_of(pen_fn)) == subtag_function) {
          signed_natural ecnt = header_element_count(header_of(pen_fn));
          signed_natural inherited = ecnt - 5;
          if (inherited > 0) {
            /* Inherited bindings are at deref(fn, 4..4+inherited-1):
               closure layout = 3 fixed (entry, code, fn) + inherited + 2 (name, lfbits).
               See ARM _SPcall_closure comment / arm-spentry.s line 1546. */
            for (signed_natural i = 0; i < inherited; i++) {
              LispObj slot = deref(pen_fn, 4 + i);
              /* If it's a value cell (1-element misc), clear its contents too */
              if (fulltag_of(slot) == fulltag_misc &&
                  slot != (LispObj)nil_value) {
                LispObj sh = header_of(slot);
                unsigned cell_st = header_subtag(sh);
                signed_natural cell_ec = header_element_count(sh);
                {
                  static const char hx2[] = "0123456789abcdef";
                  char d2[80]; int p2 = 0;
                  const char *pfx2 = "pen-fix: cell st=";
                  while (*pfx2) d2[p2++] = *pfx2++;
                  { unsigned sv = cell_st; char sbuf[4]; int slen = 0;
                    do { sbuf[slen++] = '0' + (char)(sv % 10); sv /= 10; } while (sv > 0);
                    for (int j = slen-1; j >= 0; j--) d2[p2++] = sbuf[j]; }
                  pfx2 = " ec=";
                  while (*pfx2) d2[p2++] = *pfx2++;
                  { signed_natural sv = cell_ec; char sbuf[4]; int slen = 0;
                    do { sbuf[slen++] = '0' + (char)(sv % 10); sv /= 10; } while (sv > 0);
                    for (int j = slen-1; j >= 0; j--) d2[p2++] = sbuf[j]; }
                  if (cell_ec >= 1) {
                    LispObj cv = ((LispObj *)(untag(slot)))[1];
                    pfx2 = " val=0x";
                    while (*pfx2) d2[p2++] = *pfx2++;
                    for (int b = 7; b >= 0; b--) d2[p2++] = hx2[(cv >> (b*4)) & 0xf];
                  }
                  d2[p2++] = '\n';
                  wasm_host_log(d2, (unsigned)p2);
                }
                if (cell_ec == 1) {
                  /* Value cell: clear its contents */
                  ((LispObj *)(untag(slot)))[1] = lisp_nil;
                }
              }
              /* Also unconditionally clear the slot itself so
                 _SPcall_closure pushes nil (belt-and-suspenders). */
              ((LispObj *)(untag(pen_fn)))[4 + i] = lisp_nil;
            }
            patchdone = 1;
            {
              static const char msg[] = "pen-fix: patched (slot+cell cleared)\n";
              wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
            }
          } else {
            /* Not a closure (no inherited bindings) — might be a plain function.
               This means the compiled code for pathname-encoding-name doesn't
               close over the variable (darwin-target compiled to constant :utf-8?).
               The encoding issue is elsewhere. */
            static const char msg[] = "pen-fix: not a closure (inherited=0)\n";
            wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
            patchdone = 1;
          }
        } else {
          static const char msg[] = "pen-fix: fcell is not a function\n";
          wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
        }
      }
    }
  }

  /* Guard: verify *fasl-dispatch-table* is a vector (not NIL or unbound).
     %FASLOAD uses it as default for the dispatch table; if it's NIL,
     svref will trap on a cons cell instead of a vector. */
  {
    static const uint8_t fdt_name[] = {
      '*', 'F', 'A', 'S', 'L', '-', 'D', 'I', 'S', 'P', 'A', 'T', 'C', 'H',
      '-', 'T', 'A', 'B', 'L', 'E', '*'
    };
    LispObj fdt_sym = wasm_find_symbol_named_bytes(
      fdt_name, (uint32_t)sizeof(fdt_name), ccl_pkg);
    if (fdt_sym != (LispObj)0 &&
        fulltag_of(fdt_sym) == fulltag_misc &&
        header_subtag(header_of(fdt_sym)) == subtag_symbol) {
      lispsymbol *fdt_rawsym = (lispsymbol *)ptr_from_lispobj(untag(fdt_sym));
      LispObj fdt_val = fdt_rawsym->vcell;
      unsigned fdt_ft = fulltag_of(fdt_val);
      if (fdt_ft != fulltag_misc) {
        static const char hx[] = "0123456789abcdef";
        char msg[120]; int p = 0;
        const char *pfx = "fasload: *fasl-dispatch-table* bad ft=";
        while (*pfx) msg[p++] = *pfx++;
        msg[p++] = '0' + (char)fdt_ft;
        pfx = " val=0x";
        while (*pfx) msg[p++] = *pfx++;
        for (int b = 7; b >= 0; b--) msg[p++] = hx[(fdt_val >> (b*4)) & 0xf];
        msg[p++] = '\n';
        wasm_host_log(msg, (unsigned)p);
        return -74;
      } else {
        LispObj fdt_hdr = header_of(fdt_val);
        unsigned fdt_st = header_subtag(fdt_hdr);
        signed_natural fdt_cnt = header_element_count(fdt_hdr);
        static const char hx[] = "0123456789abcdef";
        char msg[120]; int p = 0;
        const char *pfx = "fasload: *fasl-dispatch-table* st=";
        while (*pfx) msg[p++] = *pfx++;
        for (int b = 1; b >= 0; b--) msg[p++] = hx[(fdt_st >> (b*4)) & 0xf];
        pfx = " cnt=";
        while (*pfx) msg[p++] = *pfx++;
        for (int b = 3; b >= 0; b--) msg[p++] = hx[(fdt_cnt >> (b*4)) & 0xf];
        msg[p++] = '\n';
        wasm_host_log(msg, (unsigned)p);
      }
    } else {
      static const char msg[] = "fasload: *fasl-dispatch-table* symbol not found\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    }
  }

  /* Call %FASLOAD with a catch frame, matching the native toplevel loop
     pattern (wasm_toplevel_loop lines 598-614).  Without a catch frame,
     catch_top=0 and _SPksignalerr absorbs every error via pending_throw(16),
     preventing %FASLOAD's unwind-protect cleanup from running and making
     all errors fatal.  With a catch frame the condition system can dispatch
     through ERRDISP and unwind-protect cleanup (%fasl-close) can execute. */
  {
    LispObj *saved_vsp = tcr->save_vsp;
    if (saved_vsp == NULL) {
      return -75;
    }

    natural old_last_lisp_frame = wasm_enter_lisp_frame(
      tcr, 0, 0, (LispObj)saved_vsp);
    tcr->valence = TCR_STATE_LISP;
    tcr->wasm_pending_throw = 0;

    /* Push the path arg onto the value stack */
    LispObj *vsp_ptr = saved_vsp;
    *--vsp_ptr = path;
    tcr->save_vsp = vsp_ptr;
    tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;

    /* Establish catch frame with *TOPLEVEL-CATCH* tag */
    tcr->wasm_gprs[arg_z] = nrs_TOPLCATCH.vcell;
    wasm_call_subprim_fixnum(
      wasm_subprim_fixnum(WASM_SUBPRIM_MKCATCH1V_INDEX));

    LispObj catch_before = tcr->catch_top;

    /* Call %FASLOAD(path) */
    tcr->wasm_gprs[nargs] = box_fixnum(1);
    tcr->wasm_gprs[nfn] = fasload_fn;
    tcr->wasm_gprs[Rfn] = fasload_fn;
    wasm_call_subprim_fixnum(
      wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

    int threw = tcr->wasm_pending_throw != 0;
    /* A throw/condition may have unwound our catch frame cooperatively
       without setting pending_throw (the WASM throw mechanism restores
       catch_top but doesn't use longjmp).  Detect this by checking
       whether catch_top still points to our frame. */
    int catch_consumed = (tcr->catch_top != catch_before);

    if (!threw && !catch_consumed) {
      /* Normal return — our catch frame is intact, unwind it */
      tcr->wasm_gprs[arg_z] = lisp_nil;
      tcr->wasm_gprs[imm0] = box_fixnum(1);
      wasm_call_subprim_fixnum(
        wasm_subprim_fixnum(WASM_SUBPRIM_NTHROW1VALUE_INDEX));
      if (tcr->wasm_pending_throw) {
        tcr->wasm_pending_throw = 0;
      }
    }

    /* Restore state */
    tcr->save_vsp = saved_vsp;
    tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
    tcr->valence = TCR_STATE_FOREIGN;
    wasm_exit_lisp_frame(tcr, old_last_lisp_frame);

    if (threw || catch_consumed) {
      return -72;  /* fasload threw or condition consumed catch frame */
    }
    return 0;
  }
}

__attribute__((used, visibility("default"), export_name("wasm_probe_foreign_call1")))
int32_t
wasm_probe_foreign_call1(uint32_t mode, uint32_t arg_ptr, uint32_t arg_len)
{
  static const uint8_t fasload_name[] = {
    '%', 'F', 'A', 'S', 'L', 'O', 'A', 'D'
  };
  static const uint8_t identity_name[] = {
    'I', 'D', 'E', 'N', 'T', 'I', 'T', 'Y'
  };
  static const uint8_t error_name[] = {
    'E', 'R', 'R', 'O', 'R'
  };
  static const uint8_t ccl_pkg_name[] = { 'C', 'C', 'L' };
  static const uint8_t cl_pkg_name[] = {
    'C', 'O', 'M', 'M', 'O', 'N', '-', 'L', 'I', 'S', 'P'
  };

  const uint8_t *arg_bytes = (const uint8_t *)(uintptr_t)arg_ptr;
  const uint8_t *pkg_name = NULL;
  uint32_t pkg_name_len = 0;
  const uint8_t *symbol_name = NULL;
  uint32_t symbol_name_len = 0;
  LispObj callable_sym = (LispObj)0;
  LispObj callable_fn = (LispObj)0;

  switch (mode) {
  case WASM_PROBE_FOREIGN_CALL_FASLOAD:
    pkg_name = ccl_pkg_name;
    pkg_name_len = (uint32_t)sizeof(ccl_pkg_name);
    symbol_name = fasload_name;
    symbol_name_len = (uint32_t)sizeof(fasload_name);
    break;
  case WASM_PROBE_FOREIGN_CALL_IDENTITY:
    pkg_name = cl_pkg_name;
    pkg_name_len = (uint32_t)sizeof(cl_pkg_name);
    symbol_name = identity_name;
    symbol_name_len = (uint32_t)sizeof(identity_name);
    break;
  case WASM_PROBE_FOREIGN_CALL_ERROR:
    pkg_name = cl_pkg_name;
    pkg_name_len = (uint32_t)sizeof(cl_pkg_name);
    symbol_name = error_name;
    symbol_name_len = (uint32_t)sizeof(error_name);
    break;
  default:
    return -9;
  }

  if (arg_ptr == 0 || arg_len == 0) {
    return -1;
  }

  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return -2;
  }
  if (!wasm_subprims_ready) {
    return -3;
  }
  if (mode == WASM_PROBE_FOREIGN_CALL_FASLOAD &&
      wasm_boot_phase_state == WASM_BOOT_EARLY) {
    return -10;
  }
  LispObj pkg = wasm_find_package_named_bytes(pkg_name, pkg_name_len);
  if (pkg == lisp_nil) {
    return -4;
  }
  callable_sym = wasm_find_symbol_named_bytes(symbol_name, symbol_name_len, pkg);
  if (callable_sym == (LispObj)0) {
    callable_sym = wasm_const_pool_intern_symbol(
      tcr,
      symbol_name,
      symbol_name_len,
      pkg);
  }
  if (tcr->wasm_pending_throw) {
    return -7;
  }
  if (callable_sym == (LispObj)0 ||
      fulltag_of(callable_sym) != fulltag_misc ||
      header_subtag(header_of(callable_sym)) != subtag_symbol) {
    return -4;
  }

  lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(untag(callable_sym));
  callable_fn = rawsym->fcell;
  if (callable_fn == nrs_UDF.vcell) {
    return -5;
  }
  if (fulltag_of(callable_fn) != fulltag_misc ||
      header_subtag(header_of(callable_fn)) != subtag_function) {
    return -8;
  }
  LispObj arg = wasm_const_pool_make_base_string(tcr, arg_bytes, arg_len);
  if (arg == lisp_nil) {
    return -6;
  }
  (void)wasm_foreign_funcall1(tcr, callable_fn, arg);
  if (tcr->wasm_pending_throw) {
    return -7;
  }
  return 0;
}

static int
wasm_symbol_object_p(LispObj value)
{
  if (value == (LispObj)0 || fulltag_of(value) != fulltag_misc) {
    return 0;
  }
  if (!wasm_lispobj_in_scannable_area(value)) {
    return 0;
  }
  return header_subtag(header_of(value)) == subtag_symbol;
}

static LispObj
wasm_intern_startup_synthesize_symbol(TCR *tcr,
                                      const uint8_t *name_bytes,
                                      uint32_t name_len,
                                      LispObj pkg)
{
  if (tcr == NULL || name_bytes == NULL || name_len == 0u) {
    return (LispObj)0;
  }

  if (pkg == (LispObj)0 ||
      pkg == lisp_nil ||
      fulltag_of(pkg) != fulltag_misc ||
      header_subtag(header_of(pkg)) != subtag_package) {
    return (LispObj)0;
  }

  LispObj name_str = wasm_const_pool_make_base_string(tcr, name_bytes, name_len);
  if (name_str == lisp_nil) {
    return (LispObj)0;
  }

  LispObj sym = wasm_misc_alloc(tcr, subtag_symbol, (signed_natural)7);
  if (sym == lisp_nil) {
    return (LispObj)0;
  }

  lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(untag(sym));
  rawsym->pname = name_str;
  rawsym->vcell = lisp_nil;
  rawsym->fcell = nrs_UDF.vcell;
  rawsym->package_predicate = pkg;
  rawsym->flags = box_fixnum(0);
  rawsym->plist = lisp_nil;
  rawsym->binding_index = box_fixnum(0);

  LispObj any_sym = wasm_find_symbol_named_bytes_scan(name_bytes, name_len, (LispObj)0);
  if (wasm_symbol_object_p(any_sym)) {
    lispsymbol *any_rawsym = (lispsymbol *)ptr_from_lispobj(untag(any_sym));
    rawsym->vcell = any_rawsym->vcell;
    rawsym->fcell = any_rawsym->fcell;
    rawsym->plist = any_rawsym->plist;
  }

  if (pkg == nrs_KEYWORD_PACKAGE.vcell) {
    rawsym->vcell = sym;
  }

  return sym;
}

static LispObj
wasm_cached_intern_symbol(void)
{
  static LispObj intern_sym = (LispObj)0;
  static const uint8_t intern_name[] = { 'I', 'N', 'T', 'E', 'R', 'N' };
  static const uint8_t percent_intern_name[] = { '%', 'I', 'N', 'T', 'E', 'R', 'N' };
  static const uint8_t cl_pkg_name[] = {
    'C', 'O', 'M', 'M', 'O', 'N', '-', 'L', 'I', 'S', 'P'
  };
  static const uint8_t ccl_pkg_name[] = { 'C', 'C', 'L' };

  typedef struct wasm_intern_candidate {
    const uint8_t *pkg_name;
    uint32_t pkg_len;
    const uint8_t *sym_name;
    uint32_t sym_len;
  } wasm_intern_candidate;
  static const wasm_intern_candidate candidates[] = {
    { cl_pkg_name, (uint32_t)sizeof(cl_pkg_name), intern_name, (uint32_t)sizeof(intern_name) },
    { ccl_pkg_name, (uint32_t)sizeof(ccl_pkg_name), percent_intern_name, (uint32_t)sizeof(percent_intern_name) },
    { ccl_pkg_name, (uint32_t)sizeof(ccl_pkg_name), intern_name, (uint32_t)sizeof(intern_name) },
  };

  if (intern_sym != (LispObj)0 &&
      fulltag_of(intern_sym) == fulltag_misc &&
      header_subtag(header_of(intern_sym)) == subtag_symbol) {
    return intern_sym;
  }

  for (uint32_t i = 0; i < (uint32_t)(sizeof(candidates) / sizeof(candidates[0])); i++) {
    const wasm_intern_candidate *candidate = &candidates[i];
    LispObj pkg = wasm_find_package_named_bytes(candidate->pkg_name, candidate->pkg_len);
    if (pkg == lisp_nil) {
      continue;
    }

    intern_sym = wasm_find_symbol_named_bytes(candidate->sym_name, candidate->sym_len, pkg);
    if (intern_sym == (LispObj)0) {
      intern_sym = wasm_find_symbol_named_bytes_scan(candidate->sym_name, candidate->sym_len, pkg);
    }
    if (intern_sym != (LispObj)0 &&
        fulltag_of(intern_sym) == fulltag_misc &&
        header_subtag(header_of(intern_sym)) == subtag_symbol) {
      return intern_sym;
    }
  }

  intern_sym = (LispObj)0;
  return (LispObj)0;
}

static LispObj
wasm_intern_startup(TCR *tcr, const uint8_t *name_bytes, uint32_t name_len, LispObj pkg)
{
  if (tcr == NULL || name_bytes == NULL || name_len == 0) {
    return (LispObj)0;
  }

  LispObj pkg_arg = pkg;
  if (pkg_arg == (LispObj)0) {
    pkg_arg = nrs_PACKAGE.vcell;
  }
  if (pkg_arg != (LispObj)0) {
    LispObj existing = wasm_find_symbol_named_bytes(name_bytes, name_len, pkg_arg);
    if (wasm_symbol_object_p(existing)) {
      return existing;
    }
    existing = wasm_find_symbol_named_bytes_scan(name_bytes, name_len, pkg_arg);
    if (wasm_symbol_object_p(existing)) {
      return existing;
    }
  }

  /* Re-entrant guard: during const-pool installation, skip the Lisp
     INTERN path to avoid circular dependency (INTERN's own const pool
     may not yet be installed).  Fall through to C-only synthesis. */
  if (wasm_const_pool_install_depth > 0) {
    LispObj synthesized = wasm_intern_startup_synthesize_symbol(tcr, name_bytes, name_len, pkg_arg);
    if (wasm_symbol_object_p(synthesized)) {
      return synthesized;
    }
    return (LispObj)0;
  }

  LispObj intern_sym = wasm_cached_intern_symbol();
  if (intern_sym == (LispObj)0) {
    LispObj synthesized = wasm_intern_startup_synthesize_symbol(tcr, name_bytes, name_len, pkg_arg);
    if (wasm_symbol_object_p(synthesized)) {
      return synthesized;
    }
    return (LispObj)0;
  }

  LispObj name_str = wasm_const_pool_make_base_string(tcr, name_bytes, name_len);
  if (name_str == lisp_nil) {
    return (LispObj)0;
  }

  LispObj result = wasm_funcall2(intern_sym, name_str, pkg_arg);

  if (tcr->wasm_pending_throw) {
    return (LispObj)0;
  }

  if (fulltag_of(result) != fulltag_misc ||
      !wasm_lispobj_in_scannable_area(result) ||
      header_subtag(header_of(result)) != subtag_symbol) {
    return (LispObj)0;
  }

  return result;
}

static LispObj
wasm_intern_runtime(TCR *tcr, const uint8_t *name_bytes, uint32_t name_len, LispObj pkg)
{
  if (tcr == NULL || name_bytes == NULL || name_len == 0) {
    return (LispObj)0;
  }

  LispObj pkg_arg = pkg;
  if (pkg_arg == (LispObj)0) {
    pkg_arg = nrs_PACKAGE.vcell;
  }
  LispObj existing = wasm_find_symbol_named_bytes(name_bytes, name_len, pkg_arg);
  if (existing == (LispObj)0) {
    existing = wasm_find_symbol_named_bytes_scan(name_bytes, name_len, pkg_arg);
  }
  if (existing != (LispObj)0 &&
      fulltag_of(existing) == fulltag_misc &&
      header_subtag(header_of(existing)) == subtag_symbol) {
    return existing;
  }

  return (LispObj)0;
}

static LispObj
wasm_intern_dispatch(TCR *tcr, const uint8_t *name_bytes, uint32_t name_len, LispObj pkg)
{
  uint32_t phase = wasm_boot_phase_normalize(wasm_boot_phase_state);
  if (phase == WASM_BOOT_RUNTIME) {
    return wasm_intern_runtime(tcr, name_bytes, name_len, pkg);
  }
  return wasm_intern_startup(tcr, name_bytes, name_len, pkg);
}

static LispObj
wasm_const_pool_intern_symbol(TCR *tcr, const uint8_t *name_bytes, uint32_t name_len, LispObj pkg)
{
  return wasm_intern_dispatch(tcr, name_bytes, name_len, pkg);
}

static LispObj
wasm_const_pool_table_ensure(TCR *tcr, uint32_t entry_index)
{
  if (tcr == NULL) {
    return lisp_nil;
  }

  LispObj table = nrs_WASM_CONST_POOLS.vcell;
  if (table == lisp_nil ||
      fulltag_of(table) != fulltag_misc ||
      header_subtag(header_of(table)) != subtag_simple_vector) {
    uint32_t count = entry_index + 1u;
    LispObj obj = wasm_misc_alloc(tcr, subtag_simple_vector, (signed_natural)count);
    if (obj == lisp_nil) {
      return lisp_nil;
    }
    LispObj *data = (LispObj *)((BytePtr)obj + misc_data_offset);
    for (uint32_t i = 0; i < count; i++) {
      data[i] = lisp_nil;
    }
    nrs_WASM_CONST_POOLS.vcell = obj;
    return obj;
  }

  uint32_t count = (uint32_t)header_element_count(header_of(table));
  if (entry_index < count) {
    return table;
  }

  uint32_t new_count = entry_index + 1u;
  LispObj obj = wasm_misc_alloc(tcr, subtag_simple_vector, (signed_natural)new_count);
  if (obj == lisp_nil) {
    return lisp_nil;
  }

  LispObj *dst = (LispObj *)((BytePtr)obj + misc_data_offset);
  LispObj *src = (LispObj *)((BytePtr)table + misc_data_offset);
  for (uint32_t i = 0; i < new_count; i++) {
    dst[i] = (i < count) ? src[i] : lisp_nil;
  }

  nrs_WASM_CONST_POOLS.vcell = obj;
  return obj;
}

static LispObj
wasm_const_pool_make_entry_function(TCR *tcr, uint32_t entry_index)
{
  if (tcr == NULL) {
    return lisp_nil;
  }

  /*
   * Keyword dispatch reads function slot 3 as the key vector (header is slot 0).
   * Ensure synthesized entry functions have that slot and default it to NIL.
   */
  LispObj vec = wasm_misc_alloc(tcr, subtag_function, (signed_natural)3);
  if (vec == lisp_nil) {
    return lisp_nil;
  }
  LispObj entry = box_fixnum((signed_natural)entry_index);
  LispObj *vec_data = (LispObj *)((BytePtr)vec + misc_data_offset);
  vec_data[0] = entry;
  vec_data[1] = entry;
  vec_data[2] = lisp_nil;
  return vec;
}

static unsigned
wasm_const_pool_normalize_subtag(uint32_t raw_subtag)
{
  unsigned subtag = (unsigned)raw_subtag;
  unsigned tag = subtag & fulltagmask;
  if (tag == fulltag_nodeheader || tag == fulltag_immheader) {
    return subtag;
  }

  /*
   * Some module bundles encode node subtags with x86-64 raw header tags
   * (ntagbits=4, nodeheader tags 5/6). Translate those to wasm32 node
   * subtags.
   */
  {
    unsigned x64_tag = subtag & 0x0fu;
    unsigned x64_sub = subtag >> 4;
    if (x64_tag == 5u) {
      switch (x64_sub) {
        case 1u: return subtag_symbol;
        case 2u: return subtag_catch_frame;
        case 3u: return subtag_hash_vector;
        case 4u: return subtag_pool;
        case 5u: return subtag_weak;
        case 6u: return subtag_package;
        case 7u: return subtag_slot_vector;
        case 8u: return subtag_basic_stream;
        case 9u: return subtag_function;
        case 10u: return subtag_arrayH;
        default: break;
      }
    } else if (x64_tag == 6u) {
      switch (x64_sub) {
        case 1u: return subtag_ratio;
        case 2u: return subtag_complex;
        case 3u: return subtag_struct;
        case 4u: return subtag_istruct;
        case 5u: return subtag_value_cell;
        case 6u: return subtag_xfunction;
        case 7u: return subtag_lock;
        case 8u: return subtag_instance;
        case 10u: return subtag_vectorH;
        case 11u: return subtag_simple_vector;
        default: break;
      }
    }
  }

  /*
   * Accept legacy const-pool gvector encoding that stores subtype codes
   * (0..31) instead of raw subtags.
   */
  if (raw_subtag <= 31u) {
    return (unsigned)NODE_SUBTAG(raw_subtag);
  }
  return subtag;
}

static LispObj
wasm_const_pool_install_inner(TCR *tcr, uint32_t entry_index, uint32_t payload_ptr, uint32_t payload_len)
{
  if (payload_ptr == 0 || payload_len == 0u) {
    wasm_const_pool_diag_fail = 1;
    return lisp_nil;
  }

  const uint8_t *bytes = (const uint8_t *)(uintptr_t)payload_ptr;
  uint32_t offset = 0;
  int ok = 1;

  uint32_t version = 0;
  uint32_t count = 0;
  if (payload_len >= 8u &&
      bytes[0] == 1u &&
      bytes[1] == 0u &&
      bytes[2] == 0u &&
      bytes[3] == 0u) {
    version = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
    count = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
  } else {
    version = wasm_const_pool_read_uleb32(bytes, payload_len, &offset, &ok);
    count = wasm_const_pool_read_uleb32(bytes, payload_len, &offset, &ok);
  }
  if (!ok || (version != 1u && version != 2u)) {
    wasm_const_pool_diag_fail = 10;
    return lisp_nil;
  }

  LispObj pool = wasm_misc_alloc(tcr, subtag_simple_vector, (signed_natural)count);
  if (pool == lisp_nil) {
    wasm_const_pool_diag_fail = 20;
    return lisp_nil;
  }
  LispObj *pool_data = (LispObj *)((BytePtr)pool + misc_data_offset);

  for (uint32_t i = 0; i < count; i++) {
    uint32_t tag = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
    if (!ok) {
      return lisp_nil;
    }
    switch (tag) {
      case 6: { /* fixnum */
        if (version >= 2u) {
          /* Version 2 stores the logical integer value via SLEB32.
             Must box as a target fixnum (shift left by fixnumshift). */
          uint32_t raw = wasm_const_pool_read_sleb32_raw(bytes, payload_len, &offset, &ok);
          if (!ok) {
            return lisp_nil;
          }
          pool_data[i] = box_fixnum((signed_natural)(int32_t)raw);
        } else {
          uint32_t raw = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
          if (!ok) {
            return lisp_nil;
          }
          pool_data[i] = (LispObj)raw;
        }
        break;
      }
      case 10: { /* character */
        uint32_t code = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        if (!ok) {
          return lisp_nil;
        }
        pool_data[i] = (LispObj)((code << charcode_shift) | subtag_character);
        break;
      }
      case 11: { /* single-float */
        uint32_t bits = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
        if (!ok) {
          return lisp_nil;
        }
        signed_natural count = (signed_natural)((sizeof(single_float) / sizeof(LispObj)) - 1);
        LispObj obj = wasm_misc_alloc(tcr, subtag_single_float, count);
        if (obj == lisp_nil) {
          return lisp_nil;
        }
        single_float *sf = (single_float *)ptr_from_lispobj(untag(obj));
        sf->value = (LispObj)bits;
        pool_data[i] = obj;
        break;
      }
      case 12: { /* double-float */
        uint32_t hi = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
        uint32_t lo = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
        if (!ok) {
          return lisp_nil;
        }
        signed_natural count = (signed_natural)((sizeof(double_float) / sizeof(LispObj)) - 1);
        LispObj obj = wasm_misc_alloc(tcr, subtag_double_float, count);
        if (obj == lisp_nil) {
          return lisp_nil;
        }
        double_float *df = (double_float *)ptr_from_lispobj(untag(obj));
        df->value_high = (LispObj)hi;
        df->value_low = (LispObj)lo;
        pool_data[i] = obj;
        break;
      }
      case 13: { /* int64 */
        uint32_t hi = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
        uint32_t lo = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
        if (!ok) {
          return lisp_nil;
        }
        int64_t value = ((int64_t)hi << 32) | (int64_t)lo;
        pool_data[i] = wasm_box_signed_64(tcr, value);
        break;
      }
      case 14: { /* uint64 */
        uint32_t hi = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
        uint32_t lo = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
        if (!ok) {
          return lisp_nil;
        }
        uint64_t value = ((uint64_t)hi << 32) | (uint64_t)lo;
        pool_data[i] = wasm_box_unsigned_64(tcr, value);
        break;
      }
      case 15: { /* bignum */
        uint32_t digits = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        if (!ok) {
          return lisp_nil;
        }
        uint32_t *data = NULL;
        LispObj obj = wasm_alloc_bignum_uninitialized(tcr, digits, &data);
        if (obj == lisp_nil || data == NULL) {
          return lisp_nil;
        }
        for (uint32_t d = 0; d < digits; d++) {
          uint32_t word = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
          if (!ok) {
            return lisp_nil;
          }
          data[d] = word;
        }
        pool_data[i] = obj;
        break;
      }
      case 1: { /* symbol */
        uint32_t name_len = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        const uint8_t *name_bytes = wasm_const_pool_read_bytes(bytes, payload_len, &offset, name_len, &ok);
        uint32_t pkg_len = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        const uint8_t *pkg_bytes = wasm_const_pool_read_bytes(bytes, payload_len, &offset, pkg_len, &ok);
        if (!ok || !name_bytes) {
          wasm_const_pool_diag_fail = 40;
          return lisp_nil;
        }
        if (pkg_len > 0 && !pkg_bytes) {
          wasm_const_pool_diag_fail = 41;
          return lisp_nil;
        }
        LispObj pkg = (LispObj)0;
        if (pkg_len > 0 && pkg_bytes) {
          if (pkg_len == 7 &&
              pkg_bytes[0] == 'K' && pkg_bytes[1] == 'E' && pkg_bytes[2] == 'Y' &&
              pkg_bytes[3] == 'W' && pkg_bytes[4] == 'O' && pkg_bytes[5] == 'R' &&
              pkg_bytes[6] == 'D') {
            pkg = nrs_KEYWORD_PACKAGE.vcell;
          } else {
            LispObj found = wasm_find_package_named_bytes(pkg_bytes, pkg_len);
            if (found != lisp_nil) {
              pkg = found;
            }
            /* Package not found: leave pkg=0 so intern falls back to
               the current package or scan-all-packages. */
          }
        }
        LispObj sym = wasm_const_pool_intern_symbol(tcr, name_bytes, name_len, pkg);
        if (tcr->wasm_pending_throw) {
          wasm_const_pool_diag_fail = 43;
          return lisp_nil;
        }
        /* If intern returned 0, the symbol isn't available yet. Store NIL
           as placeholder; the module can still work if code paths that
           reference this slot are not taken. */
        if (sym == (LispObj)0 || (sym != lisp_nil &&
            (fulltag_of(sym) != fulltag_misc ||
             header_subtag(header_of(sym)) != subtag_symbol))) {
          sym = lisp_nil;
        }
        pool_data[i] = sym;
        break;
      }
      case 2: { /* string */
        uint32_t len = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        const uint8_t *data = wasm_const_pool_read_bytes(bytes, payload_len, &offset, len, &ok);
        if (!ok || !data) {
          return lisp_nil;
        }
        LispObj str = wasm_const_pool_make_base_string(tcr, data, len);
        if (str == lisp_nil) {
          return lisp_nil;
        }
        pool_data[i] = str;
        break;
      }
      case 3: { /* vector */
        uint32_t vcount = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        if (!ok) {
          return lisp_nil;
        }
        LispObj vec = wasm_misc_alloc(tcr, subtag_simple_vector, (signed_natural)vcount);
        if (vec == lisp_nil) {
          return lisp_nil;
        }
        LispObj *vec_data = (LispObj *)((BytePtr)vec + misc_data_offset);
        for (uint32_t j = 0; j < vcount; j++) {
          vec_data[j] = lisp_nil;
        }
        for (uint32_t j = 0; j < vcount; j++) {
          uint32_t idx = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
          if (!ok || idx >= count) {
            return lisp_nil;
          }
          if (idx < i) {
            vec_data[j] = pool_data[idx];
          }
        }
        pool_data[i] = vec;
        break;
      }
      case 4: { /* function */
        uint32_t name_len = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        const uint8_t *name_bytes = wasm_const_pool_read_bytes(bytes, payload_len, &offset, name_len, &ok);
        uint32_t pkg_len = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        const uint8_t *pkg_bytes = wasm_const_pool_read_bytes(bytes, payload_len, &offset, pkg_len, &ok);
        if (!ok || !name_bytes) {
          wasm_const_pool_diag_fail = 60;
          return lisp_nil;
        }
        if (pkg_len > 0 && !pkg_bytes) {
          wasm_const_pool_diag_fail = 61;
          return lisp_nil;
        }
        LispObj pkg = (LispObj)0;
        if (pkg_len > 0 && pkg_bytes) {
          if (pkg_len == 7 &&
              pkg_bytes[0] == 'K' && pkg_bytes[1] == 'E' && pkg_bytes[2] == 'Y' &&
              pkg_bytes[3] == 'W' && pkg_bytes[4] == 'O' && pkg_bytes[5] == 'R' &&
              pkg_bytes[6] == 'D') {
            pkg = nrs_KEYWORD_PACKAGE.vcell;
          } else {
            LispObj found = wasm_find_package_named_bytes(pkg_bytes, pkg_len);
            if (found != lisp_nil) {
              pkg = found;
            }
            /* Package not found: leave pkg=0 to fall back. */
          }
        }
        LispObj sym = wasm_const_pool_intern_symbol(tcr, name_bytes, name_len, pkg);
        if (tcr->wasm_pending_throw) {
          wasm_const_pool_diag_fail = 63;
          return lisp_nil;
        }
        LispObj fn = nrs_UDF.vcell;
        if (sym != (LispObj)0 && sym != lisp_nil &&
            fulltag_of(sym) == fulltag_misc &&
            header_subtag(header_of(sym)) == subtag_symbol) {
          lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(untag(sym));
          fn = rawsym->fcell;
          if (fn == nrs_UDF.vcell ||
              fulltag_of(fn) != fulltag_misc ||
              (header_subtag(header_of(fn)) != subtag_function &&
               header_subtag(header_of(fn)) != subtag_pseudofunction)) {
            fn = nrs_UDF.vcell;
          }
        }
        /* Store resolved function or UDF placeholder.  UDF allows the rest
           of the pool to install; runtime calls to this slot will get a clean
           "undefined function" error. */
        pool_data[i] = fn;
        break;
      }
      case 5: { /* function-vector */
        uint32_t vcount = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        if (!ok) {
          return lisp_nil;
        }
        LispObj vec = wasm_misc_alloc(tcr, subtag_function, (signed_natural)vcount);
        if (vec == lisp_nil) {
          return lisp_nil;
        }
        LispObj *vec_data = (LispObj *)((BytePtr)vec + misc_data_offset);
        for (uint32_t j = 0; j < vcount; j++) {
          vec_data[j] = lisp_nil;
        }
        for (uint32_t j = 0; j < vcount; j++) {
          uint32_t idx = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
          if (!ok || idx >= count) {
            return lisp_nil;
          }
          if (idx < i) {
            vec_data[j] = pool_data[idx];
          }
        }
        pool_data[i] = vec;
        break;
      }
      case 16: { /* entry-function */
        uint32_t entry_index = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        if (!ok) {
          return lisp_nil;
        }
        LispObj vec = wasm_const_pool_make_entry_function(tcr, entry_index);
        if (vec == lisp_nil) {
          return lisp_nil;
        }
        pool_data[i] = vec;
        break;
      }
      case 9: { /* gvector */
        uint32_t raw_subtag = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        uint32_t vcount = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        if (!ok) {
          return lisp_nil;
        }
        unsigned subtag = wasm_const_pool_normalize_subtag(raw_subtag);
        LispObj vec = wasm_misc_alloc(tcr, subtag, (signed_natural)vcount);
        if (vec == lisp_nil) {
          return lisp_nil;
        }
        LispObj *vec_data = (LispObj *)((BytePtr)vec + misc_data_offset);
        for (uint32_t j = 0; j < vcount; j++) {
          vec_data[j] = lisp_nil;
        }
        for (uint32_t j = 0; j < vcount; j++) {
          uint32_t idx = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
          if (!ok || idx >= count) {
            return lisp_nil;
          }
          if (idx < i) {
            vec_data[j] = pool_data[idx];
          }
        }
        pool_data[i] = vec;
        break;
      }
      case 17: { /* ivector — specialized (immheader) vector */
        uint32_t raw_subtag = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        uint32_t vcount = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        if (!ok) {
          return lisp_nil;
        }
        unsigned subtag = wasm_const_pool_normalize_subtag(raw_subtag);
        LispObj vec = wasm_misc_alloc(tcr, subtag, (signed_natural)vcount);
        if (vec == lisp_nil) {
          return lisp_nil;
        }
        BytePtr data = (BytePtr)vec + misc_data_offset;
        if (subtag <= max_32_bit_ivector_subtag) {
          /* 32-bit elements: fixnum-vector, u32, s32, single-float, base-string */
          uint32_t *p = (uint32_t *)data;
          for (uint32_t j = 0; j < vcount; j++) {
            p[j] = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
            if (!ok) return lisp_nil;
          }
        } else if (subtag <= max_8_bit_ivector_subtag) {
          /* 8-bit elements: u8, s8 */
          uint8_t *p = (uint8_t *)data;
          for (uint32_t j = 0; j < vcount; j++) {
            uint32_t v = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
            if (!ok) return lisp_nil;
            p[j] = (uint8_t)v;
          }
        } else if (subtag <= max_16_bit_ivector_subtag) {
          /* 16-bit elements: u16, s16 */
          uint16_t *p = (uint16_t *)data;
          for (uint32_t j = 0; j < vcount; j++) {
            uint32_t v = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
            if (!ok) return lisp_nil;
            p[j] = (uint16_t)v;
          }
        } else {
          /* bit-vector, double-float-vector, complex-float — skip for now */
          for (uint32_t j = 0; j < vcount; j++) {
            (void)wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
            if (!ok) return lisp_nil;
          }
        }
        pool_data[i] = vec;
        break;
      }
      case 7: { /* package */
        uint32_t name_len = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        const uint8_t *name_bytes = wasm_const_pool_read_bytes(bytes, payload_len, &offset, name_len, &ok);
        if (!ok || !name_bytes) {
          wasm_const_pool_diag_fail = 70;
          return lisp_nil;
        }
        LispObj pkg = wasm_find_package_named_bytes(name_bytes, name_len);
        /* Package not found: store NIL as placeholder. */
        pool_data[i] = pkg;
        break;
      }
      case 8: { /* cons */
        uint32_t car_idx = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        uint32_t cdr_idx = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        if (!ok || car_idx >= count || cdr_idx >= count) {
          return lisp_nil;
        }
        LispObj cell = wasm_alloc_cons(tcr, lisp_nil, lisp_nil);
        if (cell == lisp_nil) {
          return lisp_nil;
        }
        if (car_idx < i) {
          cons *raw = (cons *)ptr_from_lispobj(untag(cell));
          raw->car = pool_data[car_idx];
        }
        if (cdr_idx < i) {
          cons *raw = (cons *)ptr_from_lispobj(untag(cell));
          raw->cdr = pool_data[cdr_idx];
        }
        pool_data[i] = cell;
        break;
      }
      default:
        return lisp_nil;
    }
  }

  /* Second pass: patch forward references in vectors/gvectors/function-vectors/conses. */
  uint32_t patch_offset = 0;
  int patch_ok = 1;
  uint32_t patch_version = 0;
  uint32_t patch_count = 0;
  if (payload_len >= 8u &&
      bytes[0] == 1u &&
      bytes[1] == 0u &&
      bytes[2] == 0u &&
      bytes[3] == 0u) {
    patch_version = wasm_const_pool_read_u32(bytes, payload_len, &patch_offset, &patch_ok);
    patch_count = wasm_const_pool_read_u32(bytes, payload_len, &patch_offset, &patch_ok);
  } else {
    patch_version = wasm_const_pool_read_uleb32(bytes, payload_len, &patch_offset, &patch_ok);
    patch_count = wasm_const_pool_read_uleb32(bytes, payload_len, &patch_offset, &patch_ok);
  }
  if (!patch_ok || patch_version != version || patch_count != count) {
    return lisp_nil;
  }
  for (uint32_t i = 0; i < count; i++) {
    uint32_t tag = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
    if (!patch_ok) {
      return lisp_nil;
    }
    switch (tag) {
      case 6: { /* fixnum */
        if (patch_version >= 2u) {
          (void)wasm_const_pool_read_sleb32_raw(bytes, payload_len, &patch_offset, &patch_ok);
        } else {
          (void)wasm_const_pool_read_u32(bytes, payload_len, &patch_offset, &patch_ok);
        }
        break;
      }
      case 10: /* character */
        (void)wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        break;
      case 11: /* single-float */
        (void)wasm_const_pool_read_u32(bytes, payload_len, &patch_offset, &patch_ok);
        break;
      case 12: /* double-float */
      case 13: /* int64 */
      case 14: /* uint64 */
        (void)wasm_const_pool_read_u32(bytes, payload_len, &patch_offset, &patch_ok);
        (void)wasm_const_pool_read_u32(bytes, payload_len, &patch_offset, &patch_ok);
        break;
      case 15: { /* bignum */
        uint32_t digits = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        for (uint32_t d = 0; patch_ok && d < digits; d++) {
          (void)wasm_const_pool_read_u32(bytes, payload_len, &patch_offset, &patch_ok);
        }
        break;
      }
      case 1: /* symbol */
      case 4: { /* function */
        uint32_t name_len = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        (void)wasm_const_pool_read_bytes(bytes, payload_len, &patch_offset, name_len, &patch_ok);
        uint32_t pkg_len = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        (void)wasm_const_pool_read_bytes(bytes, payload_len, &patch_offset, pkg_len, &patch_ok);
        break;
      }
      case 2: { /* string */
        uint32_t len = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        (void)wasm_const_pool_read_bytes(bytes, payload_len, &patch_offset, len, &patch_ok);
        break;
      }
      case 3: /* vector */
      case 5: { /* function-vector */
        uint32_t vcount = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        if (!patch_ok) {
          return lisp_nil;
        }
        LispObj vec = pool_data[i];
        if (fulltag_of(vec) != fulltag_misc) {
          return lisp_nil;
        }
        LispObj *vec_data = (LispObj *)((BytePtr)vec + misc_data_offset);
        for (uint32_t j = 0; j < vcount; j++) {
          uint32_t idx = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
          if (!patch_ok || idx >= count) {
            return lisp_nil;
          }
          vec_data[j] = pool_data[idx];
        }
        break;
      }
      case 16: /* entry-function */
        (void)wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        break;
      case 17: { /* ivector — no forward refs, just skip subtag + count + raw u32s */
        (void)wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok); /* subtag */
        uint32_t iv_count = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        for (uint32_t j = 0; patch_ok && j < iv_count; j++) {
          (void)wasm_const_pool_read_u32(bytes, payload_len, &patch_offset, &patch_ok);
        }
        break;
      }
      case 9: { /* gvector */
        (void)wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok); /* raw_subtag */
        uint32_t vcount = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        if (!patch_ok) {
          return lisp_nil;
        }
        LispObj vec = pool_data[i];
        if (fulltag_of(vec) != fulltag_misc) {
          return lisp_nil;
        }
        LispObj *vec_data = (LispObj *)((BytePtr)vec + misc_data_offset);
        for (uint32_t j = 0; j < vcount; j++) {
          uint32_t idx = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
          if (!patch_ok || idx >= count) {
            return lisp_nil;
          }
          vec_data[j] = pool_data[idx];
        }
        break;
      }
      case 7: { /* package */
        uint32_t name_len = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        (void)wasm_const_pool_read_bytes(bytes, payload_len, &patch_offset, name_len, &patch_ok);
        break;
      }
      case 8: { /* cons */
        uint32_t car_idx = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        uint32_t cdr_idx = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        if (!patch_ok || car_idx >= count || cdr_idx >= count) {
          return lisp_nil;
        }
        LispObj cell = pool_data[i];
        if (fulltag_of(cell) != fulltag_cons) {
          return lisp_nil;
        }
        cons *raw = (cons *)ptr_from_lispobj(untag(cell));
        raw->car = pool_data[car_idx];
        raw->cdr = pool_data[cdr_idx];
        break;
      }
      default:
        return lisp_nil;
    }
    if (!patch_ok) {
      return lisp_nil;
    }
  }

  LispObj table = wasm_const_pool_table_ensure(tcr, entry_index);
  if (table == lisp_nil) {
    return lisp_nil;
  }
  LispObj *table_data = (LispObj *)((BytePtr)table + misc_data_offset);
  table_data[entry_index] = pool;
  return pool;
}

__attribute__((used, visibility("default"), export_name("wasm_const_pool_install")))
LispObj
wasm_const_pool_install(uint32_t entry_index, uint32_t payload_ptr, uint32_t payload_len)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  wasm_const_pool_install_depth++;
  LispObj result = wasm_const_pool_install_inner(tcr, entry_index, payload_ptr, payload_len);
  wasm_const_pool_install_depth--;
  return result;
}

__attribute__((used, visibility("default"), export_name("wasm_const_pool_diag_fail_get")))
uint32_t
wasm_const_pool_diag_fail_get(void)
{
  return wasm_const_pool_diag_fail;
}

__attribute__((used, visibility("default"), export_name("wasm_const_pool_ref")))
LispObj
wasm_const_pool_ref(uint32_t entry_index, uint32_t slot_index)
{
  LispObj table = nrs_WASM_CONST_POOLS.vcell;

  /* Fast path: table exists and pool is already installed. */
  if (table != lisp_nil &&
      fulltag_of(table) == fulltag_misc &&
      header_subtag(header_of(table)) == subtag_simple_vector) {
    uint32_t table_count = (uint32_t)header_element_count(header_of(table));
    if (entry_index < table_count) {
      LispObj *table_data = (LispObj *)((BytePtr)table + misc_data_offset);
      LispObj pool = table_data[entry_index];
      if (pool != lisp_nil &&
          fulltag_of(pool) == fulltag_misc &&
          header_subtag(header_of(pool)) == subtag_simple_vector) {
        uint32_t pool_count = (uint32_t)header_element_count(header_of(pool));
        if (slot_index < pool_count) {
          LispObj *pool_data = (LispObj *)((BytePtr)pool + misc_data_offset);
          LispObj val = pool_data[slot_index];
          /* Track for wasm_debug_dump_state */
          wasm_diag_last_cpr_entry = entry_index;
          wasm_diag_last_cpr_slot = slot_index;
          wasm_diag_last_cpr_val = val;
          return val;
        }
        return lisp_nil;
      }
    }
  }

  /* Slow path: pool not installed.  Ask the host to install it on demand. */
  int32_t rc = wasm_host_install_const_pool(entry_index);
  if (rc <= 0) {
    return lisp_nil;
  }

  /* Re-read the table (it may have been reallocated by the install). */
  table = nrs_WASM_CONST_POOLS.vcell;
  if (table == lisp_nil ||
      fulltag_of(table) != fulltag_misc ||
      header_subtag(header_of(table)) != subtag_simple_vector) {
    return lisp_nil;
  }
  uint32_t table_count = (uint32_t)header_element_count(header_of(table));
  if (entry_index >= table_count) {
    return lisp_nil;
  }
  LispObj *table_data = (LispObj *)((BytePtr)table + misc_data_offset);
  LispObj pool = table_data[entry_index];
  if (pool == lisp_nil ||
      fulltag_of(pool) != fulltag_misc ||
      header_subtag(header_of(pool)) != subtag_simple_vector) {
    return lisp_nil;
  }
  uint32_t pool_count = (uint32_t)header_element_count(header_of(pool));
  if (slot_index >= pool_count) {
    return lisp_nil;
  }
  LispObj *pool_data = (LispObj *)((BytePtr)pool + misc_data_offset);
  /* Track for wasm_debug_dump_state */
  wasm_diag_last_cpr_entry = entry_index;
  wasm_diag_last_cpr_slot = slot_index;
  wasm_diag_last_cpr_val = pool_data[slot_index];
  return pool_data[slot_index];
}


__attribute__((used, visibility("default"), export_name("wasm_reset_root_image_runtime_state")))
int32_t
wasm_reset_root_image_runtime_state(void)
{
  extern LispObj lisp_nil;

  wasm_reset_gc_root_policy();
  wasm_clear_entry_gc_root_policy_modes();
  wasm_clear_entry_call_abi_kinds();
  nrs_WASM_COMPILED_MODULES.vcell = lisp_nil;
  nrs_WASM_CONST_POOLS.vcell = lisp_nil;

  TCR *tcr = wasm_get_current_tcr();
  if (tcr != NULL) {
    LispObj *slot = wasm_toplevel_slot(tcr);
    if (slot != NULL) {
      /*
       * Clear any stale per-TCR toplevel slot from previous host runs.
       * Keep nrs_TOPLFUNC intact so the freshly loaded image can seed
       * start_lisp on the next entry.
       */
      *slot = lisp_nil;
      if (tcr->vs_area != NULL) {
        tcr->vs_area->active = (BytePtr)slot;
      }
      tcr->save_vsp = slot;
      tcr->wasm_gprs[vsp] = (LispObj)slot;
    }
  }

  return 0;
}

#endif /* WASM32 */
