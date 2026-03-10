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
static int wasm_debug_callable_summary(char *buf, LispObj fn);

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

/* Counters for wasm_set_symbol_function_entry paths */
static uint32_t wasm_fcell_inplace = 0;
static uint32_t wasm_fcell_newstub = 0;

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
  if (fn_value == lisp_nil) {
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

  if (subtag != subtag_function && subtag != subtag_pseudofunction &&
      subtag != subtag_xfunction) {
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
      /* ARM convention: arg_y = first formal, arg_z = last formal.
         Typed entry: param0 = first formal, param1 = last formal. */
      result = wasm_call_entry_index_binary_i32(entry_index,
                                                tcr->wasm_gprs[arg_y],
                                                tcr->wasm_gprs[arg_z]);
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

/* Re-entrant guard: when > 0, wasm_intern_startup skips the Lisp INTERN
   path and falls through to C-only synthesis.  This breaks the circular
   dependency where const-pool installation calls INTERN which itself
   needs a const pool that hasn't been installed yet. */
static uint32_t wasm_const_pool_install_depth = 0;

/* Entry-function dedup cache: maps entry_index -> LispObj function vector.
   Avoids allocating a new 3-slot function vector for every const pool that
   references the same entry_index. Allocated on first use, cleared via
   wasm_entry_fn_cache_clear(). */
static LispObj *wasm_entry_fn_cache = NULL;
static uint32_t wasm_entry_fn_cache_size = 0;
static uint32_t wasm_entry_fn_cache_hits = 0;
static uint32_t wasm_entry_fn_cache_misses = 0;

/* Diagnostic: tracks which exit-point in wasm_const_pool_install_inner
   last returned lisp_nil, for debugging const-pool failures. */
static uint32_t wasm_const_pool_diag_fail = 0;
LispObj wasm_funcall1(LispObj fn_value, LispObj arg0);
uint32_t wasm_subprim_nonlocal_exit_coherence_selftest(void);
static LispObj wasm_find_package_named_bytes(const uint8_t *bytes, uint32_t len);
static LispObj wasm_find_symbol_named_bytes(const uint8_t *name, uint32_t len, LispObj package);
static LispObj wasm_find_symbol_named_bytes_scan(const uint8_t *name, uint32_t len, LispObj package);
static LispObj wasm_find_symbol_in_all_packages_bytes(const uint8_t *name, uint32_t len);
static LispObj wasm_foreign_funcall0(TCR *tcr, LispObj callable);
static LispObj wasm_foreign_funcall1(TCR *tcr, LispObj callable, LispObj arg);
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

/* Read dynamic area bounds into a caller-provided buffer.
   buf must point to 5 uint32s: [area_low, area_active, area_high, pool_vcell, oldest_ephemeral]
   Returns 0 on success, -1 on error. */
__attribute__((used, visibility("default"), export_name("wasm_get_gc_area_bounds")))
int32_t
wasm_get_gc_area_bounds(uint32_t buf_ptr)
{
  uint32_t *buf = (uint32_t *)(uintptr_t)buf_ptr;
  if (buf == NULL) return -1;
  area *a = active_dynamic_area;
  if (a == NULL) return -1;
  buf[0] = (uint32_t)(uintptr_t)a->low;
  buf[1] = (uint32_t)(uintptr_t)a->active;
  buf[2] = (uint32_t)(uintptr_t)a->high;
  buf[3] = (uint32_t)nrs_WASM_CONST_POOLS.vcell;
  buf[4] = (uint32_t)lisp_global(OLDEST_EPHEMERAL);
  return 0;
}

/* Trigger a full garbage collection from the JS host.
   Returns bytes freed (approximate, clamped to int32 range).
   Safe to call when Lisp has returned to JS (TCR state is consistent). */
__attribute__((used, visibility("default"), export_name("wasm_trigger_gc")))
int32_t
wasm_trigger_gc(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) return 0;

  area *a = active_dynamic_area;
  if (a == NULL) return 0;

  BytePtr oldfree = a->active;

  /* Disable EGC to merge all generational areas into one contiguous
     dynamic area.  Without this, active_dynamic_area points to only the
     youngest generation (g0) and a full GC would miss objects in tenured
     space (including const pool vectors rooted from NRS symbols). */
  Boolean egc_was_on = (lisp_global(OLDEST_EPHEMERAL) != 0);
  if (egc_was_on) {
    egc_control(false, a->active);
  }

  /* active_dynamic_area now covers the full heap. */
  a = active_dynamic_area;
  oldfree = a->active;

  gc(tcr, 0);

  /* GC compaction moves a->active down but does NOT refresh the TCR's
     allocation pointers.  Reset them so the next allocation goes through
     new_heap_segment, which will carve a proper segment from the
     compacted heap. */
  tcr->save_allocptr = (void *)VOID_ALLOCPTR;
  tcr->save_allocbase = (void *)VOID_ALLOCPTR;
  tcr->last_allocptr = (void *)VOID_ALLOCPTR;

  /* Re-enable EGC if it was on before. */
  if (egc_was_on) {
    egc_control(true, a->active);
  }

  BytePtr newfree = active_dynamic_area->active;
  signed_natural freed = (signed_natural)(oldfree - newfree);
  if (freed > 0x7FFFFFFF) freed = 0x7FFFFFFF;
  if (freed < -0x7FFFFFFF) freed = -0x7FFFFFFF;
  return (int32_t)freed;
}

/* Grow the Lisp dynamic area so that at least `extra_bytes` of free space
   is available for allocation without triggering GC.  Used before bulk
   operations (const-pool install) that do many small allocations.

   After a compacting GC the dynamic area's `high` is set to
   `active + lisp_heap_gc_threshold` — typically only ~128 MiB of headroom.
   But the WASM linear memory may be much larger (up to 4 GiB).
   resize_dynamic_heap → grow_dynamic_area → CommitMemory will extend
   `high` within the existing linear memory without needing
   wasm_memory_grow_and_relocate (which fails when memory is already at
   the WASM32 4 GiB ceiling).

   Returns 0 on success, negative on failure. */
__attribute__((used, visibility("default"), export_name("wasm_grow_lisp_heap")))
int32_t
wasm_grow_lisp_heap(uint32_t extra_bytes)
{
  area *a = active_dynamic_area;
  if (a == NULL) return -1;

  natural current_free = (natural)(a->high - a->active);
  if (current_free >= extra_bytes) return 0; /* already have enough */

  if (!resize_dynamic_heap(a->active, (natural)extra_bytes)) return -2;
  return 0;
}

/* ── Heap profiler ─────────────────────────────────────────────────────
   Scan the dynamic area and report bytes consumed per subtag type.
   Uses skip_over_ivector (from GC) for correct ivector sizing.
   Writes results via wasm_host_log.  Returns number of live bytes. */
__attribute__((used, visibility("default"), export_name("wasm_heap_profile")))
uint32_t
wasm_heap_profile(void)
{
  area *a = active_dynamic_area;
  if (a == NULL) return 0;

  /* Disable EGC to see the full heap, not just the youngest generation */
  Boolean egc_was_on = (lisp_global(OLDEST_EPHEMERAL) != 0);
  if (egc_was_on) {
    egc_control(false, a->active);
    a = active_dynamic_area;
  }

  LispObj *p = (LispObj *)a->low;
  LispObj *limit = (LispObj *)a->active;

  /* 256 subtag buckets: count and total bytes (use uint32_t to avoid printf issues) */
  uint32_t counts[256];
  uint32_t byteslo[256]; /* low 32 bits of bytes */
  uint32_t cons_count = 0;
  uint32_t cons_bytes = 0;

  memset(counts, 0, sizeof(counts));
  memset(byteslo, 0, sizeof(byteslo));

  while (p < limit) {
    LispObj header = *p;
    int tag = fulltag_of(header);

    if (immheader_tag_p(tag)) {
      /* Use skip_over_ivector for exact sizing */
      LispObj *next = (LispObj *)skip_over_ivector(ptr_to_lispobj(p), header);
      uint32_t obj_bytes = (uint32_t)((BytePtr)next - (BytePtr)p);
      uint8_t subtag = header_subtag(header);
      counts[subtag]++;
      byteslo[subtag] += obj_bytes;
      p = next;
    } else if (nodeheader_tag_p(tag)) {
      natural element_count = header_element_count(header);
      uint32_t obj_bytes = (uint32_t)((element_count + 1 + (element_count & 1 ? 0 : 1)) * node_size);
      /* node objects: header + N elements, dnode-aligned */
      obj_bytes = (uint32_t)(((element_count + 1) * node_size + 7) & ~7u);
      uint8_t subtag = header_subtag(header);
      counts[subtag]++;
      byteslo[subtag] += obj_bytes;
      p = (LispObj *)((BytePtr)p + obj_bytes);
    } else {
      /* cons cell — 8 bytes (1 dnode) */
      cons_count++;
      cons_bytes += dnode_size;
      p += 2;
    }
  }

  uint32_t total_live = (uint32_t)((BytePtr)a->active - (BytePtr)a->low);
  char buf[160];
  int n;

  n = snprintf(buf, sizeof(buf),
    "HEAP-PROFILE: total=%u (%u MiB) cons=%u (%u MiB)\n",
    total_live, total_live >> 20,
    cons_count, cons_bytes >> 20);
  wasm_host_log(buf, n);

  /* Collect and sort by bytes descending */
  struct { uint8_t subtag; uint32_t count; uint32_t bytes; } entries[256];
  int nentries = 0;
  for (int i = 0; i < 256; i++) {
    if (counts[i] > 0) {
      entries[nentries].subtag = (uint8_t)i;
      entries[nentries].count = counts[i];
      entries[nentries].bytes = byteslo[i];
      nentries++;
    }
  }
  for (int i = 1; i < nentries; i++) {
    for (int j = i; j > 0 && entries[j].bytes > entries[j-1].bytes; j--) {
      typeof(entries[0]) tmp = entries[j];
      entries[j] = entries[j-1];
      entries[j-1] = tmp;
    }
  }

  static const char *subtag_names[256];
  static int names_init = 0;
  if (!names_init) {
    memset(subtag_names, 0, sizeof(subtag_names));
    subtag_names[subtag_bignum] = "bignum";
    subtag_names[subtag_ratio] = "ratio";
    subtag_names[subtag_single_float] = "sfloat";
    subtag_names[subtag_double_float] = "dfloat";
    subtag_names[subtag_complex] = "complex";
    subtag_names[subtag_bit_vector] = "bitvec";
    subtag_names[subtag_double_float_vector] = "dfvec";
    subtag_names[subtag_s16_vector] = "s16vec";
    subtag_names[subtag_u16_vector] = "u16vec";
    subtag_names[subtag_s8_vector] = "s8vec";
    subtag_names[subtag_u8_vector] = "u8vec";
    subtag_names[subtag_simple_base_string] = "string";
    subtag_names[subtag_fixnum_vector] = "fxvec";
    subtag_names[subtag_s32_vector] = "s32vec";
    subtag_names[subtag_u32_vector] = "u32vec";
    subtag_names[subtag_single_float_vector] = "sfvec";
    subtag_names[subtag_vectorH] = "vecH";
    subtag_names[subtag_arrayH] = "arrH";
    subtag_names[subtag_simple_vector] = "svec";
    subtag_names[subtag_pseudofunction] = "pseudo";
    subtag_names[subtag_macptr] = "macptr";
    subtag_names[subtag_dead_macptr] = "deadmac";
    subtag_names[subtag_code_vector] = "codevec";
    subtag_names[subtag_creole] = "creole";
    subtag_names[subtag_complex_single_float] = "csf";
    subtag_names[subtag_complex_double_float] = "cdf";
    subtag_names[subtag_catch_frame] = "catch";
    subtag_names[subtag_function] = "func";
    subtag_names[subtag_basic_stream] = "stream";
    subtag_names[subtag_symbol] = "sym";
    subtag_names[subtag_lock] = "lock";
    subtag_names[subtag_hash_vector] = "hashvec";
    subtag_names[subtag_pool] = "pool";
    subtag_names[subtag_weak] = "weak";
    subtag_names[subtag_package] = "pkg";
    subtag_names[subtag_slot_vector] = "slotvec";
    subtag_names[subtag_instance] = "inst";
    subtag_names[subtag_struct] = "struct";
    subtag_names[subtag_istruct] = "istruct";
    subtag_names[subtag_value_cell] = "vcell";
    subtag_names[subtag_xfunction] = "xfunc";
    names_init = 1;
  }

  int show = nentries < 25 ? nentries : 25;
  for (int i = 0; i < show; i++) {
    const char *nm = subtag_names[entries[i].subtag];
    if (!nm) nm = "???";
    n = snprintf(buf, sizeof(buf),
      "  0x%02x %s n=%u b=%u (%u MiB)\n",
      (unsigned)entries[i].subtag, nm,
      entries[i].count, entries[i].bytes, entries[i].bytes >> 20);
    wasm_host_log(buf, n);
  }

  if (egc_was_on) {
    egc_control(true, active_dynamic_area->active);
  }

  return total_live;
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

  /* Full GC before image save.  With EGC already disabled the entire
     heap is one contiguous area, so gc() compacts everything.  Without
     this the saved image contains all dead objects accumulated during
     the build — easily 3-5x larger than necessary. */
  {
    static const char msg_gc[] = "WASM save-image: pre-save GC...\n";
    wasm_host_log(msg_gc, (unsigned)(sizeof(msg_gc) - 1));
    wasm_trigger_gc();
    static const char msg_gc_done[] = "WASM save-image: pre-save GC done\n";
    wasm_host_log(msg_gc_done, (unsigned)(sizeof(msg_gc_done) - 1));
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
    { static const char m[] = "TL: MKCATCH1V\n";
      wasm_host_log(m, sizeof(m)-1); }
    wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKCATCH1V_INDEX));

    tcr->wasm_gprs[arg_z] = lisp_nil;
    tcr->wasm_gprs[nargs] = box_fixnum(0);
    tcr->wasm_gprs[nfn] = topfn;
    tcr->wasm_gprs[Rfn] = topfn;
    { static const char hx[] = "0123456789abcdef";
      char d[60]; int p = 0;
      const char *s = "TL: FUNCALL nfn=0x";
      while (*s) d[p++] = *s++;
      for (int b = 7; b >= 0; b--) d[p++] = hx[(topfn>>(b*4))&0xf];
      /* extract entry index from function object */
      if (fulltag_of(topfn) == fulltag_misc && topfn != lisp_nil) {
        LispObj entry = deref(topfn, 1);
        s = " e=";
        while (*s) d[p++] = *s++;
        if (tag_of(entry) == tag_fixnum) {
          uint32_t idx = (uint32_t)unbox_fixnum(entry);
          for (int b = 7; b >= 0; b--) d[p++] = hx[(idx>>(b*4))&0xf];
        } else {
          s = "non-fix"; while (*s) d[p++] = *s++;
        }
      }
      d[p++] = '\n'; wasm_host_log(d, (unsigned)p); }
    wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));
    if (tcr->wasm_pending_throw) {
      wasm_maybe_refresh_compiled_modules();
      return WASM_TOPLEVEL_PENDING_THROW;
    }

    LispObj result = tcr->wasm_gprs[arg_z];
    tcr->wasm_gprs[arg_z] = lisp_nil;
    tcr->wasm_gprs[imm0] = box_fixnum(1);
    { static const char m[] = "TL: NTHROW1VALUE\n";
      wasm_host_log(m, sizeof(m)-1); }
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

/* Set a symbol's function or value cell to a fresh function object with the
   given entry index.  The symbol is looked up by name (CCL, CL, all packages).
   slot: 0 = fcell (defun bindings), 1 = vcell (defvar function values like
   *RESTORE-LISP-POINTERS*).
   This is used to repair NRS function pointers broken by GC compaction. */
static LispObj
wasm_find_symbol_any_bytes(const uint8_t *sym_name, uint32_t name_len)
{
  static const uint8_t ccl_pkg[] = { 'C', 'C', 'L' };
  static const uint8_t cl_pkg[] = { 'C', 'O', 'M', 'M', 'O', 'N', '-', 'L', 'I', 'S', 'P' };

  LispObj pkg = wasm_find_package_named_bytes(ccl_pkg, (uint32_t)sizeof(ccl_pkg));
  LispObj sym = (LispObj)0;
  if (pkg != lisp_nil) {
    sym = wasm_find_symbol_named_bytes(sym_name, name_len, pkg);
  }
  if (sym == (LispObj)0) {
    pkg = wasm_find_package_named_bytes(cl_pkg, (uint32_t)sizeof(cl_pkg));
    if (pkg != lisp_nil) {
      sym = wasm_find_symbol_named_bytes(sym_name, name_len, pkg);
    }
  }
  if (sym == (LispObj)0) {
    sym = wasm_find_symbol_in_all_packages_bytes(sym_name, name_len);
  }
  if (sym == (LispObj)0) {
    sym = wasm_find_symbol_named_bytes_scan(sym_name, name_len, (LispObj)0);
  }
  if (sym == (LispObj)0 || fulltag_of(sym) != fulltag_misc ||
      header_subtag(header_of(sym)) != subtag_symbol) {
    return (LispObj)0;
  }
  return sym;
}

__attribute__((used, visibility("default"), export_name("wasm_set_symbol_function_entry")))
int32_t
wasm_set_symbol_function_entry(uint32_t name_ptr, uint32_t name_len,
                                uint32_t entry_index, uint32_t slot)
{
  if (name_len == 0 || name_ptr == 0) return -1;
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) return -2;
  if (!wasm_subprims_ready) return -3;

  const uint8_t *sym_name = (const uint8_t *)(uintptr_t)name_ptr;
  LispObj sym = wasm_find_symbol_any_bytes(sym_name, name_len);
  if (sym == (LispObj)0) return -1;

  LispObj entry = box_fixnum((signed_natural)entry_index);
  lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(untag(sym));

  if (slot == 1) {
    /* vcell — always allocate fresh (no keyvect concern). */
    LispObj fn = wasm_misc_alloc(tcr, subtag_function, (signed_natural)2);
    if (fn == lisp_nil) return -4;
    LispObj *fn_data = (LispObj *)((BytePtr)fn + misc_data_offset);
    fn_data[0] = entry;
    fn_data[1] = entry;
    rawsym->vcell = fn;
  } else {
    /* fcell — preserve existing function object if present,
       so keyvect (slot 2) and closed vars are not destroyed. */
    LispObj existing = rawsym->fcell;
    if (fulltag_of(existing) == fulltag_misc &&
        (header_subtag(header_of(existing)) == subtag_function ||
         header_subtag(header_of(existing)) == subtag_xfunction)) {
      /* Patch in place — preserves keyvect (slot 2) and all other slots. */
      LispObj *fn_data = (LispObj *)((BytePtr)existing + misc_data_offset);
      fn_data[0] = entry;
      fn_data[1] = entry;
      wasm_fcell_inplace++;
    } else {
      LispObj fn = wasm_misc_alloc(tcr, subtag_function, (signed_natural)3);
      if (fn == lisp_nil) return -4;
      LispObj *fn_data = (LispObj *)((BytePtr)fn + misc_data_offset);
      fn_data[0] = entry;
      fn_data[1] = entry;
      fn_data[2] = lisp_nil;
      rawsym->fcell = fn;
      wasm_fcell_newstub++;
    }
  }
  return 0;
}

/* Check if a symbol (found by name in all packages) is fbound.
   Returns: 1 = fbound, 0 = UDF, -1 = symbol not found. */
__attribute__((used, visibility("default"), export_name("wasm_check_symbol_fbound")))
int32_t
wasm_check_symbol_fbound(const uint8_t *name, uint32_t len)
{
  LispObj sym = wasm_find_symbol_any_bytes(name, len);
  if (sym == (LispObj)0) return -1;
  lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(sym - fulltag_misc);
  return (rawsym->fcell != nrs_UDF.vcell) ? 1 : 0;
}

__attribute__((used, visibility("default"), export_name("wasm_lookup_symbol_function")))
uint32_t
wasm_lookup_symbol_function(const uint8_t *name, uint32_t len)
{
  LispObj sym = wasm_find_symbol_any_bytes(name, len);
  if (sym == (LispObj)0) return 0;
  lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(sym - fulltag_misc);
  return (uint32_t)rawsym->fcell;
}

__attribute__((used, visibility("default"), export_name("wasm_lookup_symbol_value")))
uint32_t
wasm_lookup_symbol_value(const uint8_t *name, uint32_t len)
{
  LispObj sym = wasm_find_symbol_any_bytes(name, len);
  if (sym == (LispObj)0) return 0;
  lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(sym - fulltag_misc);
  return (uint32_t)rawsym->vcell;
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

static LispObj wasm_const_value = 0;  /* set to lisp_nil lazily */

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

  /* Zero the data area (everything after the header word).
     Previous code compared size_t bytes > misc_data_offset (-2 signed),
     which promoted -2 to huge unsigned → always false → memset never ran.
     Also, bytes - misc_data_offset = bytes+2 would overrun by 6 bytes.
     Fix: header is node_size (4) bytes; data area is bytes - node_size. */
  if (bytes > (size_t)node_size) {
    memset((BytePtr)obj + misc_data_offset, 0, bytes - node_size);
  }

  /* Diagnostic: catch creation of 8-element fixnum-vector (suspect $hprimes) */
  if (subtag == subtag_fixnum_vector && count == 8) {
    char d[80]; int p = 0;
    p += wasm_debug_str(d + p, "DIAG: alloc fixvec8 obj=0x");
    p += wasm_debug_hex8(d + p, (uint32_t)obj);
    d[p++] = '\n';
    wasm_host_log(d, (unsigned)p);
  }

  /* Diagnostic: log first 16 single-float allocations to track header integrity */
  {
    static uint32_t sfalloc_count = 0;
    if (subtag == subtag_single_float && sfalloc_count < 16) {
      sfalloc_count++;
      LispObj readback = header_of(obj);
      char d[120]; int p = 0;
      p += wasm_debug_str(d + p, "SFALLOC obj=0x");
      p += wasm_debug_hex8(d + p, (uint32_t)obj);
      p += wasm_debug_str(d + p, " hdr=0x");
      p += wasm_debug_hex8(d + p, (uint32_t)readback);
      p += wasm_debug_str(d + p, " sub=0x");
      p += wasm_debug_hex8(d + p, header_subtag(readback));
      p += wasm_debug_str(d + p, " aptr=0x");
      p += wasm_debug_hex8(d + p, (uint32_t)(uintptr_t)newptr);
      d[p++] = '\n';
      wasm_host_log(d, (unsigned)p);
    }
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
  if (base == lisp_nil) {
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

      return result;
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
  tcr->wasm_gprs[arg_y] = value1;
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
  tcr->wasm_gprs[arg_y] = value1;
  tcr->wasm_gprs[arg_x] = value2;
  tcr->wasm_gprs[nargs] = box_fixnum(3);
  if (wasm_diag_last_cpr_entry == 1102 ||
      wasm_diag_last_cpr_entry == 1103 ||
      wasm_diag_last_cpr_entry == 1104) {
    static int mv_ret3_diag_count = 0;
    if (mv_ret3_diag_count < 32) {
      char msg[256];
      int p = 0;
      mv_ret3_diag_count++;
      p += wasm_debug_str(msg + p, "RET3 cpr_e=");
      p += wasm_debug_uint(msg + p, wasm_diag_last_cpr_entry);
      p += wasm_debug_str(msg + p, " cpr_s=");
      p += wasm_debug_uint(msg + p, wasm_diag_last_cpr_slot);
      p += wasm_debug_str(msg + p, " nfn{");
      p += wasm_debug_callable_summary(msg + p, tcr->wasm_gprs[nfn]);
      p += wasm_debug_str(msg + p, "} Rfn{");
      p += wasm_debug_callable_summary(msg + p, tcr->wasm_gprs[Rfn]);
      p += wasm_debug_str(msg + p, "} v0=0x");
      p += wasm_debug_hex8(msg + p, (uint32_t)value0);
      p += wasm_debug_str(msg + p, " v1=0x");
      p += wasm_debug_hex8(msg + p, (uint32_t)value1);
      p += wasm_debug_str(msg + p, " v2=0x");
      p += wasm_debug_hex8(msg + p, (uint32_t)value2);
      p += wasm_debug_str(msg + p, "\n");
      wasm_host_log(msg, (unsigned)p);
    }
  }
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
  tcr->wasm_gprs[arg_y] = value1;
  tcr->wasm_gprs[arg_x] = value2;
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
        p += wasm_debug_str(msg + p, " nfn{");
        p += wasm_debug_callable_summary(msg + p, tcr->wasm_gprs[nfn]);
        p += wasm_debug_str(msg + p, "}");
        p += wasm_debug_str(msg + p, " Rfn{");
        p += wasm_debug_callable_summary(msg + p, tcr->wasm_gprs[Rfn]);
        p += wasm_debug_str(msg + p, "}");
        p += wasm_debug_str(msg + p, " cpr_e=");
        p += wasm_debug_uint(msg + p, wasm_diag_last_cpr_entry);
        p += wasm_debug_str(msg + p, " cpr_s=");
        p += wasm_debug_uint(msg + p, wasm_diag_last_cpr_slot);
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
    wasm_debug_dump_state("spill_push: NULL tcr");
    __builtin_trap();
  }
  LispObj *sp = tcr->wasm_spill_sp;
  if (sp == NULL || tcr->wasm_spill_base == NULL) {
    wasm_debug_dump_state("spill_push: NULL spill stack");
    __builtin_trap();
  }
  if (sp <= tcr->wasm_spill_base) {
    wasm_debug_dump_state("spill_push: overflow");
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
    wasm_debug_dump_state("spill_pop: NULL tcr");
    __builtin_trap();
  }
  LispObj *sp = tcr->wasm_spill_sp;
  if (sp == NULL || tcr->wasm_spill_limit == NULL) {
    wasm_debug_dump_state("spill_pop: NULL spill stack");
    __builtin_trap();
  }
  if (sp >= tcr->wasm_spill_limit) {
    wasm_debug_dump_state("spill_pop: underflow");
    __builtin_trap();
  }
  LispObj value = *sp++;
  tcr->wasm_spill_sp = sp;
  wasm_spill_pop_count++;
  return value;
}

/* Spill stack save/restore — for JS-level isolation of WASM calls.
   WASM traps abort compiled functions mid-call, leaving spill pushes
   unmatched.  JS callers should save before and restore after any
   call that might trap (cold-load drain, FASL loading). */
static LispObj *wasm_saved_spill_sp = NULL;

__attribute__((used, visibility("default"), export_name("wasm_spill_save")))
void
wasm_spill_save(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr) wasm_saved_spill_sp = tcr->wasm_spill_sp;
}

__attribute__((used, visibility("default"), export_name("wasm_spill_restore")))
void
wasm_spill_restore(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr && wasm_saved_spill_sp) tcr->wasm_spill_sp = wasm_saved_spill_sp;
}

/* Reset spill stack to empty.  Safe at known quiescent points
   (between cold-load entries, between FASL loads) when no compiled
   Lisp code is on the call stack. */
__attribute__((used, visibility("default"), export_name("wasm_spill_reset")))
void
wasm_spill_reset(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr && tcr->wasm_spill_limit) {
    tcr->wasm_spill_sp = tcr->wasm_spill_limit;
  }
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

static int
wasm_debug_callable_summary(char *buf, LispObj fn)
{
  int p = 0;
  if (fn == lisp_nil || fulltag_of(fn) != fulltag_misc) {
    p += wasm_debug_str(buf + p, "obj=0x");
    p += wasm_debug_hex8(buf + p, (uint32_t)fn);
    return p;
  }

  uint8_t sub = header_subtag(header_of(fn));
  if (sub == subtag_symbol) {
    lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(fn));
    LispObj pname = sym->pname;
    p += wasm_debug_str(buf + p, "sym=");
    if (pname != lisp_nil &&
        fulltag_of(pname) == fulltag_misc &&
        header_subtag(header_of(pname)) == subtag_simple_base_string) {
      natural len = header_element_count(header_of(pname));
      uint8_t *chars = (uint8_t *)((BytePtr)pname + misc_data_offset);
      if (len > 24) len = 24;
      for (natural i = 0; i < len && p < 120; i++) {
        buf[p++] = (char)chars[i];
      }
    } else {
      buf[p++] = '?';
    }
    LispObj fcell = sym->fcell;
    if (fcell != lisp_nil &&
        fulltag_of(fcell) == fulltag_misc &&
        header_subtag(header_of(fcell)) == subtag_function) {
      LispObj entry = deref(fcell, 1);
      if (tag_of(entry) == tag_fixnum) {
        p += wasm_debug_str(buf + p, " entry=");
        p += wasm_debug_uint(buf + p, (uint32_t)unbox_fixnum(entry));
      }
    }
    return p;
  }

  if (sub == subtag_function) {
    LispObj entry = deref(fn, 1);
    p += wasm_debug_str(buf + p, "entry=");
    if (tag_of(entry) == tag_fixnum) {
      p += wasm_debug_uint(buf + p, (uint32_t)unbox_fixnum(entry));
    } else {
      buf[p++] = '?';
    }
    natural nelems = header_element_count(header_of(fn));
    if (nelems >= 2) {
      LispObj last = deref(fn, nelems);
      if (fulltag_of(last) == fulltag_misc &&
          header_subtag(header_of(last)) == subtag_symbol) {
        lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(last));
        LispObj pname = sym->pname;
        p += wasm_debug_str(buf + p, " name=");
        if (pname != lisp_nil &&
            fulltag_of(pname) == fulltag_misc &&
            header_subtag(header_of(pname)) == subtag_simple_base_string) {
          natural len = header_element_count(header_of(pname));
          uint8_t *chars = (uint8_t *)((BytePtr)pname + misc_data_offset);
          if (len > 24) len = 24;
          for (natural i = 0; i < len && p < 120; i++) {
            buf[p++] = (char)chars[i];
          }
        } else {
          buf[p++] = '?';
        }
      }
    }
    return p;
  }

  p += wasm_debug_str(buf + p, "sub=");
  p += wasm_debug_uint(buf + p, (uint32_t)sub);
  p += wasm_debug_str(buf + p, " obj=0x");
  p += wasm_debug_hex8(buf + p, (uint32_t)fn);
  return p;
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
  if (vec == lisp_nil || fulltag_of(vec) != fulltag_misc) return 0;
  LispObj header = header_of(vec);
  signed_natural count = header_element_count(header);
  LispObj *data = (LispObj *)((BytePtr)vec + misc_data_offset);
  uint32_t logged = 0;
  static const char hx[] = "0123456789abcdef";

  for (signed_natural i = 0; i < count; i++) {
    LispObj fn = data[i];
    if (fn == lisp_nil || fulltag_of(fn) != fulltag_misc) continue;
    unsigned subtag = header_subtag(header_of(fn));
    if (subtag != subtag_function && subtag != subtag_pseudofunction &&
        subtag != subtag_xfunction) continue;
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

/* Recover TCR state after a WASM trap (unreachable) during cold-load drain.
   Traps unwind the WASM call stack without executing cleanup code, leaving
   TCR in an inconsistent state (lisp frame not exited, vsp not restored).
   This function restores TCR to a safe state for the next cold-load entry. */
__attribute__((used, visibility("default"), export_name("wasm_recover_after_trap")))
void
wasm_recover_after_trap(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_pending_throw = 0;
  tcr->valence = TCR_STATE_FOREIGN;
  tcr->catch_top = 0;
  tcr->db_link = 0;
  /* Restore vsp to top of vstack area */
  if (tcr->vs_area != NULL) {
    LispObj *top = (LispObj *)(tcr->vs_area->high - sizeof(LispObj));
    tcr->save_vsp = top;
    tcr->wasm_gprs[vsp] = (LispObj)top;
    tcr->vs_area->active = (BytePtr)top;
  }
  /* Clear last_lisp_frame chain */
  tcr->last_lisp_frame = 0;
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
    /* C-to-Lisp call: clear any stale pending_throw from prior invocations. */
    tcr->wasm_pending_throw = 0;
  } else if (tcr->wasm_pending_throw) {
    /* Lisp-to-Lisp call with an error already propagating.  Do NOT clear
       pending_throw — let the error unwind through the funcall dispatcher
       back to the C boundary.  Without this, _SPksignalerr's absorption
       flag is silently eaten and the caller proceeds with garbage state. */
    return tcr->wasm_gprs[arg_z];
  }

  LispObj *vsp_ptr = saved_vsp;
  for (signed_natural i = 0; i < count; i++) {
    *--vsp_ptr = args[i];
  }

  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[nargs] = box_fixnum(count);
  tcr->wasm_gprs[nfn] = fn_value;
  tcr->wasm_gprs[Rfn] = fn_value;

  LispObj traced_callable = lisp_nil;
  int traced_entry = -1;
  if (preserve_mv &&
      fn_value != lisp_nil &&
      fulltag_of(fn_value) == fulltag_misc) {
    traced_callable = fn_value;
    if (header_subtag(header_of(traced_callable)) == subtag_symbol) {
      lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(traced_callable));
      traced_callable = sym->fcell;
    }
    if (traced_callable != lisp_nil &&
        fulltag_of(traced_callable) == fulltag_misc &&
        header_subtag(header_of(traced_callable)) == subtag_function) {
      LispObj entry_s0 = deref(traced_callable, 1);
      if (tag_of(entry_s0) == tag_fixnum) {
        traced_entry = (int)unbox_fixnum(entry_s0);
        if (traced_entry != 1102 &&
            traced_entry != 1103 &&
            traced_entry != 1104) {
          traced_entry = -1;
        }
      }
    }
  }

  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  LispObj result = tcr->wasm_gprs[arg_z];
  if (tcr->wasm_pending_throw) {
    if (traced_entry >= 0) {
      static int mv_funcall_throw_diag_count = 0;
      if (mv_funcall_throw_diag_count < 24) {
        char msg[320];
        int p = 0;
        mv_funcall_throw_diag_count++;
        p += wasm_debug_str(msg + p, "MV-CALL throw entry=");
        p += wasm_debug_uint(msg + p, (uint32_t)traced_entry);
        p += wasm_debug_str(msg + p, " fn=0x");
        p += wasm_debug_hex8(msg + p, (uint32_t)fn_value);
        p += wasm_debug_str(msg + p, " Rfn=0x");
        p += wasm_debug_hex8(msg + p, (uint32_t)tcr->wasm_gprs[Rfn]);
        p += wasm_debug_str(msg + p, " nfn=0x");
        p += wasm_debug_hex8(msg + p, (uint32_t)tcr->wasm_gprs[nfn]);
        p += wasm_debug_str(msg + p, " pending=0x");
        p += wasm_debug_hex8(msg + p, (uint32_t)tcr->wasm_pending_throw);
        p += wasm_debug_str(msg + p, " argz=0x");
        p += wasm_debug_hex8(msg + p, (uint32_t)tcr->wasm_gprs[arg_z]);
        p += wasm_debug_str(msg + p, " argy=0x");
        p += wasm_debug_hex8(msg + p, (uint32_t)tcr->wasm_gprs[arg_y]);
        p += wasm_debug_str(msg + p, " argx=0x");
        p += wasm_debug_hex8(msg + p, (uint32_t)tcr->wasm_gprs[arg_x]);
        p += wasm_debug_str(msg + p, "\n");
        wasm_host_log(msg, (unsigned)p);
      }
    }
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
  signed_natural expected_count = 0;
  if (traced_entry == 1102 || traced_entry == 1103) {
    expected_count = 3;
  } else if (traced_entry == 1104) {
    expected_count = 4;
  }

  if (traced_entry >= 0) {
    static int mv_funcall_diag_count = 0;
    if ((expected_count != 0 && value_count != expected_count) ||
        mv_funcall_diag_count < 48) {
      char msg[384];
      int p = 0;
      if (mv_funcall_diag_count < 48) {
        mv_funcall_diag_count++;
      }
      p += wasm_debug_str(msg + p, "MV-CALL entry=");
      p += wasm_debug_uint(msg + p, (uint32_t)traced_entry);
      if (fn_value != lisp_nil &&
          fulltag_of(fn_value) == fulltag_misc &&
          header_subtag(header_of(fn_value)) == subtag_symbol) {
        lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(fn_value));
        LispObj pname = sym->pname;
        if (pname != lisp_nil &&
            fulltag_of(pname) == fulltag_misc &&
            header_subtag(header_of(pname)) == subtag_simple_base_string) {
          natural len = header_element_count(header_of(pname));
          uint8_t *chars = (uint8_t *)((BytePtr)pname + misc_data_offset);
          if (len > 48) len = 48;
          p += wasm_debug_str(msg + p, " name=");
          for (natural i = 0; i < len && p < (int)(sizeof(msg) - 2); i++) {
            msg[p++] = (char)chars[i];
          }
        }
      }
      p += wasm_debug_str(msg + p, " raw_nargs=0x");
      p += wasm_debug_hex8(msg + p, (uint32_t)raw_nargs);
      p += wasm_debug_str(msg + p, " count=");
      p += wasm_debug_uint(msg + p, (uint32_t)value_count);
      if (expected_count != 0) {
        p += wasm_debug_str(msg + p, " expected=");
        p += wasm_debug_uint(msg + p, (uint32_t)expected_count);
      }
      p += wasm_debug_str(msg + p, " argz=0x");
      p += wasm_debug_hex8(msg + p, (uint32_t)tcr->wasm_gprs[arg_z]);
      p += wasm_debug_str(msg + p, " argy=0x");
      p += wasm_debug_hex8(msg + p, (uint32_t)tcr->wasm_gprs[arg_y]);
      p += wasm_debug_str(msg + p, " argx=0x");
      p += wasm_debug_hex8(msg + p, (uint32_t)tcr->wasm_gprs[arg_x]);
      p += wasm_debug_str(msg + p, " vsp=0x");
      p += wasm_debug_hex8(msg + p, (uint32_t)tcr->wasm_gprs[vsp]);
      p += wasm_debug_str(msg + p, " save_vsp=0x");
      p += wasm_debug_hex8(msg + p, (uint32_t)(uintptr_t)saved_vsp);
      p += wasm_debug_str(msg + p, "\n");
      wasm_host_log(msg, (unsigned)p);
    }
  }

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
  if (tcr->wasm_gprs[arg_z] != lisp_nil) {
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
  if ((tcr->save_vsp[2] != mv0) ||
      (tcr->save_vsp[1] != mv1) ||
      (tcr->save_vsp[0] != mv2)) {
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
  if (tcr->wasm_gprs[arg_z] != lisp_nil) {
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

  /* ARM convention: wasm_funcall_common pushes args[0..n-1] in order,
   * making args[n-1] the TOS.  wasm_funcall_value calls
   * wasm_sync_arg_regs_from_vsp which loads TOS → arg_z (primary value
   * register).  So the primary value (funcall_mv0) must be at args[2]. */
  funcall_mv_args[0] = funcall_mv2;   /* deepest → arg_x */
  funcall_mv_args[1] = funcall_mv1;   /* middle  → arg_y */
  funcall_mv_args[2] = funcall_mv0;   /* TOS     → arg_z (primary) */
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
      (tcr->save_vsp[2] != funcall_mv0) ||
      (tcr->save_vsp[1] != funcall_mv1) ||
      (tcr->save_vsp[0] != funcall_mv2)) {
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
       Native CCL always does this after loading an image.
       ARM reads symbol.fcell via ref_nrs_function — defun sets fcell, not vcell. */
    LispObj restore_fn = nrs_RESTORE_LISP_POINTERS.fcell;
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
   ARM reads symbol.fcell via ref_nrs_function — defun sets fcell, not vcell.
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

  LispObj restore_fn = nrs_RESTORE_LISP_POINTERS.fcell;
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
/* ---- Cold-load drain: JS-driven approach ----
   The cold-load function list can have 2000+ entries.  Some thunks cause
   hard WASM traps (unreachable) that cannot be caught from C.  JavaScript
   CAN catch WASM traps with try/catch, so we export the snapshot and a
   run-one function, letting JS drive the loop with per-call isolation. */

#define COLD_LOAD_MAX 4096
static LispObj cold_load_snapshot[COLD_LOAD_MAX];
static int cold_load_snapshot_count = 0;

__attribute__((used, visibility("default"), export_name("wasm_cold_load_snapshot")))
int
wasm_cold_load_snapshot_fn(LispObj list)
{
  cold_load_snapshot_count = 0;
  if (list == lisp_nil) return 0;
  LispObj cur = list;
  while (cur != lisp_nil && fulltag_of(cur) == fulltag_cons &&
         cold_load_snapshot_count < COLD_LOAD_MAX) {
    cold_load_snapshot[cold_load_snapshot_count++] = car(cur);
    cur = cdr(cur);
  }
  int overflow = 0;
  while (cur != lisp_nil && fulltag_of(cur) == fulltag_cons) {
    overflow++;
    cur = cdr(cur);
  }
  {
    char m[128]; int p = 0;
    p += wasm_debug_str(m + p, "cold-load-snapshot: ");
    p += wasm_debug_uint(m + p, (uint32_t)cold_load_snapshot_count);
    p += wasm_debug_str(m + p, " captured");
    if (overflow > 0) {
      p += wasm_debug_str(m + p, ", ");
      p += wasm_debug_uint(m + p, (uint32_t)overflow);
      p += wasm_debug_str(m + p, " overflow");
    }
    m[p++] = '\n';
    wasm_host_log(m, (unsigned)p);
  }
  return cold_load_snapshot_count;
}

__attribute__((used, visibility("default"), export_name("wasm_cold_load_count")))
int
wasm_cold_load_count_fn(void)
{
  return cold_load_snapshot_count;
}

__attribute__((used, visibility("default"), export_name("wasm_cold_load_ref")))
uint32_t
wasm_cold_load_ref_fn(int index)
{
  if (index < 0 || index >= cold_load_snapshot_count) {
    return 0;
  }
  return (uint32_t)cold_load_snapshot[index];
}

/* Run a single cold-load function by snapshot index.
   Returns:  0 = success
             1 = skipped (not a function)
             2 = Lisp error (pending_throw, absorbed)
            -1 = invalid index */
__attribute__((used, visibility("default"), export_name("wasm_cold_load_run_one")))
int
wasm_cold_load_run_one(int index)
{
  if (index < 0 || index >= cold_load_snapshot_count) return -1;
  LispObj fn = cold_load_snapshot[index];
  /* Accept both function objects and symbols — $fasl-lfuncall can push
     symbols when the FASL says (funcall 'SOME-SYMBOL).  _SPfuncall
     handles both via the function cell lookup. */
  if (fn == lisp_nil || fulltag_of(fn) != fulltag_misc) {
    return 1;  /* skip: not a misc-tagged object */
  }
  {
    uint8_t sub = header_subtag(header_of(fn));
    if (sub != subtag_function && sub != subtag_symbol) {
      return 1;  /* skip: not callable */
    }
  }
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) return -1;

  /* Diagnostic: log details of the fn being called so we can identify stuck entries */
  {
    char m[128]; int p = 0;
    p += wasm_debug_str(m + p, "CLRO idx=");
    p += wasm_debug_uint(m + p, (uint32_t)index);
    p += wasm_debug_str(m + p, " fn=");
    p += wasm_debug_uint(m + p, (uint32_t)fn);
    LispObj hdr = header_of(fn);
    p += wasm_debug_str(m + p, " sub=");
    p += wasm_debug_uint(m + p, (uint32_t)header_subtag(hdr));
    uint8_t sub = header_subtag(hdr);
    if (sub == subtag_symbol) {
      lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(fn));
      LispObj pname = sym->pname;
      if (pname != lisp_nil && fulltag_of(pname) == fulltag_misc) {
        LispObj phdr = header_of(pname);
        if (header_subtag(phdr) == subtag_simple_base_string) {
          natural len = header_element_count(phdr);
          if (len > 40) len = 40;
          uint8_t *chars = (uint8_t *)((BytePtr)pname + misc_data_offset);
          p += wasm_debug_str(m + p, " sym=");
          for (natural ci = 0; ci < len && p < 120; ci++) m[p++] = (char)chars[ci];
        }
      }
    } else if (sub == subtag_function) {
      /* Log the entry index and function name.
         deref(fn,0) = header, deref(fn,1) = element 0 = code/entrypoint
         Function name is in the lfun-bits area.  In ARM32 CCL, element 1
         is typically the code_vector or entry index.  Dump first 4 elements
         to help identify the function. */
      natural nelems = header_element_count(hdr);
      p += wasm_debug_str(m + p, " ne=");
      p += wasm_debug_uint(m + p, (uint32_t)nelems);
      /* Element 1 = code/entry */
      LispObj cv = deref(fn, 1);
      if (tag_of(cv) == tag_fixnum) {
        p += wasm_debug_str(m + p, " eidx=");
        p += wasm_debug_uint(m + p, (uint32_t)unbox_fixnum(cv));
      }
      /* Last element is typically lfun-name (for named functions) */
      if (nelems >= 2) {
        LispObj last = deref(fn, nelems);
        if (fulltag_of(last) == fulltag_misc) {
          LispObj lhdr = header_of(last);
          if (header_subtag(lhdr) == subtag_symbol) {
            lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(last));
            LispObj pname = sym->pname;
            if (pname != lisp_nil && fulltag_of(pname) == fulltag_misc &&
                header_subtag(header_of(pname)) == subtag_simple_base_string) {
              natural len = header_element_count(header_of(pname));
              if (len > 30) len = 30;
              uint8_t *chars = (uint8_t *)((BytePtr)pname + misc_data_offset);
              p += wasm_debug_str(m + p, " nm=");
              for (natural ci = 0; ci < len && p < 120; ci++) m[p++] = (char)chars[ci];
            }
          }
        }
      }
    }
    m[p++] = '\n';
    wasm_host_log(m, (unsigned)p);
  }

  tcr->wasm_pending_throw = 0;
  (void)wasm_foreign_funcall0(tcr, fn);
  if (tcr->wasm_pending_throw) {
    tcr->wasm_pending_throw = 0;
    return 2;  /* Lisp error, absorbed */
  }
  return 0;
}

/* Legacy C-side drain for backward compatibility.  Only runs the first
   COLD_LOAD_C_MAX entries (safe subset).  JS-driven drain should be
   preferred for the full 2000+ list. */
#define COLD_LOAD_C_MAX 128
static void
wasm_log_cold_load_callable(const char *prefix, int index, LispObj fn)
{
  char m[192];
  int p = 0;
  uint8_t sub = header_subtag(header_of(fn));

  p += wasm_debug_str(m + p, prefix);
  p += wasm_debug_str(m + p, " idx=");
  p += wasm_debug_uint(m + p, (uint32_t)index);

  if (sub == subtag_symbol) {
    lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(fn));
    LispObj pname = sym->pname;
    LispObj fcell = sym->fcell;
    p += wasm_debug_str(m + p, " kind=symbol");
    if (pname != lisp_nil && fulltag_of(pname) == fulltag_misc &&
        header_subtag(header_of(pname)) == subtag_simple_base_string) {
      natural len = header_element_count(header_of(pname));
      uint8_t *chars = (uint8_t *)((BytePtr)pname + misc_data_offset);
      if (len > 40) len = 40;
      p += wasm_debug_str(m + p, " name=");
      for (natural i = 0; i < len && p < (int)(sizeof(m) - 2); i++) {
        m[p++] = (char)chars[i];
      }
    }
    if (fcell != lisp_nil &&
        fulltag_of(fcell) == fulltag_misc &&
        header_subtag(header_of(fcell)) == subtag_function) {
      LispObj entry_s0 = deref(fcell, 1);
      if (tag_of(entry_s0) == tag_fixnum) {
        p += wasm_debug_str(m + p, " fentry=");
        p += wasm_debug_uint(m + p, (uint32_t)unbox_fixnum(entry_s0));
      }
    }
  } else if (sub == subtag_function) {
    LispObj entry_s0 = deref(fn, 1);
    natural nelems = header_element_count(header_of(fn));
    p += wasm_debug_str(m + p, " kind=function");
    if (tag_of(entry_s0) == tag_fixnum) {
      p += wasm_debug_str(m + p, " entry=");
      p += wasm_debug_uint(m + p, (uint32_t)unbox_fixnum(entry_s0));
    }
    if (nelems >= 2) {
      LispObj last = deref(fn, nelems);
      if (fulltag_of(last) == fulltag_misc &&
          header_subtag(header_of(last)) == subtag_symbol) {
        lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(last));
        LispObj pname = sym->pname;
        if (pname != lisp_nil && fulltag_of(pname) == fulltag_misc &&
            header_subtag(header_of(pname)) == subtag_simple_base_string) {
          natural len = header_element_count(header_of(pname));
          uint8_t *chars = (uint8_t *)((BytePtr)pname + misc_data_offset);
          if (len > 40) len = 40;
          p += wasm_debug_str(m + p, " name=");
          for (natural i = 0; i < len && p < (int)(sizeof(m) - 2); i++) {
            m[p++] = (char)chars[i];
          }
        }
      }
    }
  } else {
    p += wasm_debug_str(m + p, " kind=other sub=");
    p += wasm_debug_uint(m + p, (uint32_t)sub);
  }

  m[p++] = '\n';
  wasm_host_log(m, (unsigned)p);
}

static int
wasm_drain_cold_load_list(TCR *tcr, LispObj list)
{
  if (list == lisp_nil) {
    static const char msg[] = "cold-load-drain: list empty\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return 0;
  }

  /* Snapshot into the global array (also used by JS-driven drain) */
  int snap_count = wasm_cold_load_snapshot_fn(list);

  int limit = snap_count < COLD_LOAD_C_MAX ? snap_count : COLD_LOAD_C_MAX;
  int count = 0, errors = 0, skipped = 0;

  for (int i = 0; i < limit; i++) {
    LispObj fn = cold_load_snapshot[i];
    count++;

    /* Accept both functions and symbols — see cold_load_run_one comment */
    if (fn == lisp_nil || fulltag_of(fn) != fulltag_misc) {
      skipped++;
      continue;
    }
    {
      uint8_t sub = header_subtag(header_of(fn));
      if (sub != subtag_function && sub != subtag_symbol) {
        skipped++;
        continue;
      }
    }

    wasm_log_cold_load_callable("CF", i, fn);

    tcr->wasm_pending_throw = 0;
    (void)wasm_foreign_funcall0(tcr, fn);

    if (tcr->wasm_pending_throw) {
      errors++;
      wasm_log_cold_load_callable("CF-ERR", i, fn);
      tcr->wasm_pending_throw = 0;
    }
  }

  /* NOTE: Do NOT trigger GC here — the JS-driven drain still needs
     the cold_load_snapshot[] array to contain valid pointers.  GC
     would compact the heap and invalidate them.  The JS caller should
     trigger GC after the full drain (C + JS passes) is complete. */

  /* Log summary */
  {
    char dbuf[128];
    int dp = 0;
    dp += wasm_debug_str(dbuf + dp, "cold-load-drain: ");
    dp += wasm_debug_uint(dbuf + dp, (uint32_t)count);
    dp += wasm_debug_str(dbuf + dp, "/");
    dp += wasm_debug_uint(dbuf + dp, (uint32_t)snap_count);
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

  /* Read *WASM-STARTUP-STEP* to determine how far cold-boot-init got.
     Must read through TLB (thread-local bindings) since _SPspecset may
     have written to the TLB slot rather than the vcell. */
  signed_natural startup_step = -1;
  {
    static const uint8_t step_name[] = "*WASM-STARTUP-STEP*";
    LispObj step_sym = wasm_find_symbol_named_bytes(
      step_name, (uint32_t)(sizeof(step_name) - 1), ccl_pkg);
    if (step_sym != (LispObj)0 && fulltag_of(step_sym) == fulltag_misc &&
        header_subtag(header_of(step_sym)) == subtag_symbol) {
      lispsymbol *ss = (lispsymbol *)ptr_from_lispobj(untag(step_sym));
      LispObj step_val = ss->vcell;
      /* Check TLB for a thread-local binding */
      LispObj bi = ss->binding_index;
      if (tag_of(bi) == tag_fixnum) {
        signed_natural idx = unbox_fixnum(bi);
        LispObj lim = tcr->tlb_limit;
        if (tag_of(lim) == tag_fixnum && idx > 0 &&
            (unsigned)idx < (unsigned)unbox_fixnum(lim) &&
            tcr->tlb_pointer != NULL) {
          LispObj tval = tcr->tlb_pointer[idx];
          if (tval != (LispObj)no_thread_local_binding_marker) {
            step_val = tval;
          }
        }
      }
      if (tag_of(step_val) == tag_fixnum) {
        startup_step = unbox_fixnum(step_val);
      }
    }
  }

  /* Diagnostic: if startup-step is 0 or unknown and there was a throw,
     check whether *WASM-STARTUP-STEP* was written to a non-canonical
     (synthesized) symbol object — a different heap object with the same
     pname but not in the package hash table. */
  if (final_pending && startup_step <= 0) {
    static const uint8_t diag_step_name[] = "*WASM-STARTUP-STEP*";
    LispObj canonical = wasm_find_symbol_named_bytes(
      diag_step_name, (uint32_t)(sizeof(diag_step_name) - 1), ccl_pkg);
    LispObj scanned = wasm_find_symbol_named_bytes_scan(
      diag_step_name, (uint32_t)(sizeof(diag_step_name) - 1), (LispObj)0);
    if (scanned != (LispObj)0 && scanned != canonical) {
      lispsymbol *ss2 = (lispsymbol *)ptr_from_lispobj(untag(scanned));
      LispObj step_val2 = ss2->vcell;
      char d2[128]; int p2 = 0;
      p2 += wasm_debug_str(d2 + p2, "cold-boot-init: DIAG alt *WASM-STARTUP-STEP* sym=0x");
      p2 += wasm_debug_hex8(d2 + p2, (uint32_t)scanned);
      p2 += wasm_debug_str(d2 + p2, " val=0x");
      p2 += wasm_debug_hex8(d2 + p2, (uint32_t)step_val2);
      if (tag_of(step_val2) == tag_fixnum) {
        p2 += wasm_debug_str(d2 + p2, " (step=");
        p2 += wasm_debug_uint(d2 + p2, (uint32_t)unbox_fixnum(step_val2));
        p2 += wasm_debug_str(d2 + p2, ")");
      }
      d2[p2++] = '\n';
      wasm_host_log(d2, (unsigned)p2);
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

  /* Phase C is intentionally deferred to JS.
     Preserve the saved list as a snapshot for the JS-driven drain, but do not
     auto-run it here.  Snapshotting must happen after the internal setup above
     so the kernel can still perform binding-index/error activation first, and
     immediately before return so no further kernel-side work can GC and stale
     the saved function pointers before JS reads them. */
  (void)wasm_cold_load_snapshot_fn(saved_cold_load_list);

  /* Phase D: run deferred binding-index setup.
     Step 80 in %RUN-COLD-BOOT-INIT calls closure-backed functions
     (%set-binding-index, cold-load-binding-index) whose environments
     aren't available until Phase C executes their let* cold-load function.
     So step 80 is deferred to here (after Phase C). */
  if (result == 0) {
    static const uint8_t setup_name[] = "%RUN-BINDING-INDEX-SETUP";
    LispObj setup_sym = wasm_find_symbol_named_bytes(
      setup_name, (uint32_t)(sizeof(setup_name) - 1), ccl_pkg);
    if (setup_sym != (LispObj)0 && fulltag_of(setup_sym) == fulltag_misc) {
      lispsymbol *setup_rawsym = (lispsymbol *)ptr_from_lispobj(untag(setup_sym));
      LispObj setup_fn = setup_rawsym->fcell;
      /* Inspect %SET-BINDING-INDEX closure before calling setup */
      {
        static const uint8_t sbi_name[] = "%SET-BINDING-INDEX";
        LispObj sbi_sym = wasm_find_symbol_named_bytes(
          sbi_name, (uint32_t)(sizeof(sbi_name) - 1), ccl_pkg);
        if (sbi_sym != (LispObj)0 && fulltag_of(sbi_sym) == fulltag_misc) {
          lispsymbol *sbi_raw = (lispsymbol *)ptr_from_lispobj(untag(sbi_sym));
          LispObj sbi_fn = sbi_raw->fcell;
          char dd[160]; int dp = 0;
          dp += wasm_debug_str(dd + dp, "D-diag: SBI fcell=0x");
          dp += wasm_debug_hex8(dd + dp, (uint32_t)sbi_fn);
          if (sbi_fn != lisp_nil && fulltag_of(sbi_fn) == fulltag_misc) {
            LispObj hdr = header_of(sbi_fn);
            dp += wasm_debug_str(dd + dp, " hdr=0x");
            dp += wasm_debug_hex8(dd + dp, (uint32_t)hdr);
            dp += wasm_debug_str(dd + dp, " s0=0x");
            dp += wasm_debug_hex8(dd + dp, (uint32_t)deref(sbi_fn, 1));
            dp += wasm_debug_str(dd + dp, " s1=0x");
            dp += wasm_debug_hex8(dd + dp, (uint32_t)deref(sbi_fn, 2));
            natural nslots = header_element_count(hdr);
            if (nslots >= 3) {
              dp += wasm_debug_str(dd + dp, " s2=0x");
              dp += wasm_debug_hex8(dd + dp, (uint32_t)deref(sbi_fn, 3));
            }
            if (nslots >= 4) {
              dp += wasm_debug_str(dd + dp, " s3=0x");
              dp += wasm_debug_hex8(dd + dp, (uint32_t)deref(sbi_fn, 4));
            }
          }
          dd[dp++] = '\n';
          wasm_host_log(dd, (unsigned)dp);
        }
      }
      /* Inspect setup_fn itself */
      {
        LispObj setup_hdr = header_of(setup_fn);
        char dd2[128]; int dp2 = 0;
        dp2 += wasm_debug_str(dd2 + dp2, "D-diag: setup fcell=0x");
        dp2 += wasm_debug_hex8(dd2 + dp2, (uint32_t)setup_fn);
        dp2 += wasm_debug_str(dd2 + dp2, " hdr=0x");
        dp2 += wasm_debug_hex8(dd2 + dp2, (uint32_t)setup_hdr);
        dp2 += wasm_debug_str(dd2 + dp2, " s0=0x");
        dp2 += wasm_debug_hex8(dd2 + dp2, (uint32_t)deref(setup_fn, 1));
        dp2 += wasm_debug_str(dd2 + dp2, " s1=0x");
        dp2 += wasm_debug_hex8(dd2 + dp2, (uint32_t)deref(setup_fn, 2));
        natural ns = header_element_count(setup_hdr);
        if (ns >= 3) {
          dp2 += wasm_debug_str(dd2 + dp2, " s2=0x");
          dp2 += wasm_debug_hex8(dd2 + dp2, (uint32_t)deref(setup_fn, 3));
        }
        dd2[dp2++] = '\n';
        wasm_host_log(dd2, (unsigned)dp2);
      }

      if (setup_fn != lisp_nil &&
          fulltag_of(setup_fn) == fulltag_misc &&
          header_subtag(header_of(setup_fn)) == subtag_function) {
        natural old_frame2 = wasm_enter_lisp_frame(
          tcr, 0, 0, (LispObj)tcr->save_vsp);
        tcr->valence = TCR_STATE_LISP;
        tcr->wasm_pending_throw = 0;
        tcr->wasm_gprs[nargs] = box_fixnum(0);
        tcr->wasm_gprs[nfn] = setup_fn;
        wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));
        if (tcr->wasm_pending_throw) {
          static const char msg[] = "binding-index-setup threw\n";
          wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
          tcr->wasm_pending_throw = 0;
        } else {
          static const char msg[] = "binding-index-setup: ok\n";
          wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
        }
        tcr->valence = TCR_STATE_FOREIGN;
        wasm_exit_lisp_frame(tcr, old_frame2);
      }
    }
  }

  /* Phase E: Activate L1 error handlers before any external %fasload.
     l1-boot-3.lisp does (fset 'error #'error/full) etc., but that
     activation thunk is one of the cold-load functions.  If it failed
     (among the 28 errors), ERROR etc. remain UDF and FASL loading
     cascades on the first signaled condition.
     Fix: for each pair, if /FULL is fbound and the plain name is still
     UDF, copy the fcell.  This mirrors l1-boot-3:46-55. */
  {
    static const struct {
      const char *plain;
      const char *full;
    } error_activations[] = {
      { "%KERNEL-RESTART",          "%KERNEL-RESTART/FULL" },
      { "%KERNEL-RESTART-INTERNAL", "%KERNEL-RESTART-INTERNAL/FULL" },
      { "%ERR-DISP",               "%ERR-DISP/FULL" },
      { "%ERR-DISP-INTERNAL",      "%ERR-DISP-INTERNAL/FULL" },
      { "%ERR-DISP-COMMON",        "%ERR-DISP-COMMON/FULL" },
      { "%ERROR",                   "%ERROR/FULL" },
      { "ERROR",                    "ERROR/FULL" },
      { "CERROR",                   "CERROR/FULL" },
      { "%ERRNO-DISP",             "%ERRNO-DISP/FULL" },
      { "%ERRNO-DISP-INTERNAL",    "%ERRNO-DISP-INTERNAL/FULL" },
    };
    int n_activated = 0;
    for (unsigned i = 0; i < sizeof(error_activations)/sizeof(error_activations[0]); i++) {
      const char *pname = error_activations[i].plain;
      const char *full_name = error_activations[i].full;
      /* Search all packages: ERROR/CERROR are CL symbols (inherited
         by CCL via use-list, not in CCL itab/etab), while %ERROR etc.
         are CCL-internal.  All-packages search finds both. */
      LispObj plain_sym = wasm_find_symbol_named_bytes(
        (const uint8_t *)pname, (uint32_t)strlen(pname), (LispObj)0);
      LispObj full_sym = wasm_find_symbol_named_bytes(
        (const uint8_t *)full_name, (uint32_t)strlen(full_name), (LispObj)0);
      if (plain_sym == 0 || full_sym == 0) continue;
      if (fulltag_of(plain_sym) != fulltag_misc) continue;
      if (fulltag_of(full_sym) != fulltag_misc) continue;
      lispsymbol *plain_raw = (lispsymbol *)ptr_from_lispobj(untag(plain_sym));
      lispsymbol *full_raw = (lispsymbol *)ptr_from_lispobj(untag(full_sym));
      LispObj full_fn = full_raw->fcell;
      /* Only activate if /FULL is fbound and plain is UDF */
      if (full_fn != lisp_nil &&
          fulltag_of(full_fn) == fulltag_misc &&
          header_subtag(header_of(full_fn)) == subtag_function &&
          plain_raw->fcell == nrs_UDF.vcell) {
        plain_raw->fcell = full_fn;
        n_activated++;
      }
    }
    {
      char msg[80]; int p = 0;
      p += wasm_debug_str(msg + p, "error-activate: ");
      p += wasm_debug_uint(msg + p, (uint32_t)n_activated);
      p += wasm_debug_str(msg + p, " of 10 activated\n");
      wasm_host_log(msg, (unsigned)p);
    }
  }

  /* Phase F: Invariant gate — check critical symbols before FASL loading.
     Log which key runtime symbols are still UDF so we know whether
     cold-load-drain + retry + error-activate was sufficient. */
  {
    static const char *gate_symbols[] = {
      "VALUES-SPECIFIER-TYPE",
      "WRITE-CHAR",
      "HASH-TABLE-P",
      "ERROR",
      "CERROR",
      "%ERROR",
      "%FASLOAD",
      "GETHASH",
      "MAKE-HASH-TABLE",
      "%CONS-HASH-TABLE",
      "HOUSEKEEPING",
      "%USE-TOPLEVEL-COMMANDS",
    };
    int n_gate = (int)(sizeof(gate_symbols) / sizeof(gate_symbols[0]));
    int n_fbound = 0, n_udf = 0;
    for (int g = 0; g < n_gate; g++) {
      const char *sname = gate_symbols[g];
      LispObj gsym = wasm_find_symbol_named_bytes(
        (const uint8_t *)sname, (uint32_t)strlen(sname), (LispObj)0);
      if (gsym == 0 || fulltag_of(gsym) != fulltag_misc) {
        n_udf++;
        continue;
      }
      lispsymbol *graw = (lispsymbol *)ptr_from_lispobj(untag(gsym));
      LispObj gfn = graw->fcell;
      if (gfn == nrs_UDF.vcell || gfn == lisp_nil) {
        n_udf++;
        char gd[80]; int gp = 0;
        gp += wasm_debug_str(gd + gp, "GATE-UDF: ");
        gp += wasm_debug_str(gd + gp, sname);
        gd[gp++] = '\n';
        wasm_host_log(gd, (unsigned)gp);
      } else {
        n_fbound++;
      }
    }
    {
      char gm[96]; int gmp = 0;
      gmp += wasm_debug_str(gm + gmp, "gate-check: ");
      gmp += wasm_debug_uint(gm + gmp, (uint32_t)n_fbound);
      gmp += wasm_debug_str(gm + gmp, "/");
      gmp += wasm_debug_uint(gm + gmp, (uint32_t)n_gate);
      gmp += wasm_debug_str(gm + gmp, " fbound, ");
      gmp += wasm_debug_uint(gm + gmp, (uint32_t)n_udf);
      gmp += wasm_debug_str(gm + gmp, " UDF\n");
      wasm_host_log(gm, (unsigned)gmp);
    }
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
  /* Clear any pending_throw from previous FASL so this one starts clean */
  tcr->wasm_pending_throw = 0;
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
                     slot_val != lisp_nil) {
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
          if (fulltag_of(pen_fn) == fulltag_misc && pen_fn != lisp_nil) {
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
                  slot != lisp_nil) {
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
  rawsym->vcell = unbound_marker;
  rawsym->fcell = nrs_UDF.vcell;
  rawsym->package_predicate = pkg;
  rawsym->flags = box_fixnum(0);
  rawsym->plist = lisp_nil;
  rawsym->binding_index = box_fixnum(0);

  /*
   * Package identity matters here.  Boot const-pool synthesis runs before the
   * runtime package/type system is fully live, so a same-name symbol from the
   * wrong package can carry an incompatible fcell into early startup.  That is
   * exactly how CCL-internal bootstrap symbols such as STRING/%FIND-PKG pick up
   * late COMMON-LISP/runtime definitions too early.  Only inherit cells from an
   * exact package match.
   */
  LispObj pkg_sym = wasm_find_symbol_named_bytes(name_bytes, name_len, pkg);
  if (!wasm_symbol_object_p(pkg_sym)) {
    pkg_sym = wasm_find_symbol_named_bytes_scan(name_bytes, name_len, pkg);
  }
  if (wasm_symbol_object_p(pkg_sym)) {
    lispsymbol *pkg_rawsym = (lispsymbol *)ptr_from_lispobj(untag(pkg_sym));
    rawsym->vcell = pkg_rawsym->vcell;
    rawsym->fcell = pkg_rawsym->fcell;
    rawsym->plist = pkg_rawsym->plist;
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

  /* Re-entrant guard: const-pool installation must not synthesize fresh
     symbol objects after EARLY boot.  Those non-canonical symbols are not
     registered in package tables and can carry stale UDF fcells into FASL
     startup.  EARLY boot still needs synthesis for boot pools because some
     level-0 symbols exist in the heap before their package tables are built.

     Once boot reaches L0_READY or RUNTIME, lookup/scan only: either the
     canonical symbol exists and should be used, or the install should leave
     a NIL/UDF placeholder instead of creating a duplicate symbol object. */
  if (wasm_const_pool_install_depth > 0) {
    uint32_t phase = wasm_boot_phase_normalize(wasm_boot_phase_state);
    if (phase != WASM_BOOT_EARLY) {
      return wasm_intern_runtime(tcr, name_bytes, name_len, pkg_arg);
    }
    /* EARLY phase: fall through to synthesis for boot pools. */
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
        /* Check entry-function cache first (cache is calloc'd so 0 = empty) */
        LispObj vec = (LispObj)0;
        if (wasm_entry_fn_cache != NULL && entry_index < wasm_entry_fn_cache_size) {
          vec = wasm_entry_fn_cache[entry_index];
        }
        if (vec != (LispObj)0) {
          wasm_entry_fn_cache_hits++;
        } else {
          wasm_entry_fn_cache_misses++;
          vec = wasm_const_pool_make_entry_function(tcr, entry_index);
          if (vec == lisp_nil) {
            return lisp_nil;
          }
          /* Store in cache — grow if needed */
          if (wasm_entry_fn_cache == NULL || entry_index >= wasm_entry_fn_cache_size) {
            uint32_t new_size = (entry_index + 1024u) & ~1023u;
            LispObj *new_cache = (LispObj *)calloc(new_size, sizeof(LispObj));
            if (new_cache != NULL) {
              if (wasm_entry_fn_cache != NULL) {
                memcpy(new_cache, wasm_entry_fn_cache, wasm_entry_fn_cache_size * sizeof(LispObj));
                free(wasm_entry_fn_cache);
              }
              wasm_entry_fn_cache = new_cache;
              wasm_entry_fn_cache_size = new_size;
            }
          }
          if (wasm_entry_fn_cache != NULL && entry_index < wasm_entry_fn_cache_size) {
            wasm_entry_fn_cache[entry_index] = vec;
          }
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
      case 18: { /* class-ref — serialize class by name, wrap in sentinel cons */
        uint32_t name_len = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        const uint8_t *name_bytes = wasm_const_pool_read_bytes(bytes, payload_len, &offset, name_len, &ok);
        uint32_t pkg_len = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        const uint8_t *pkg_bytes = wasm_const_pool_read_bytes(bytes, payload_len, &offset, pkg_len, &ok);
        if (!ok || !name_bytes) {
          return lisp_nil;
        }
        if (pkg_len > 0 && !pkg_bytes) {
          return lisp_nil;
        }
        LispObj pkg = (LispObj)0;
        if (pkg_len > 0 && pkg_bytes) {
          LispObj found = wasm_find_package_named_bytes(pkg_bytes, pkg_len);
          if (found != lisp_nil) {
            pkg = found;
          }
        }
        LispObj sym = wasm_const_pool_intern_symbol(tcr, name_bytes, name_len, pkg);
        if (sym == (LispObj)0 || (fulltag_of(sym) != fulltag_misc)) {
          sym = lisp_nil;
        }
        /* Wrap in (sym . sentinel) so wasm_const_pool_resolve_class_refs
           can distinguish class-ref slots from ordinary symbol slots.
           Sentinel = boxed fixnum 0x434C ('CL'). */
        LispObj sentinel = box_fixnum(0x434C);
        LispObj cell = wasm_alloc_cons(tcr, sym, sentinel);
        pool_data[i] = (cell != lisp_nil) ? cell : sym;
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
      case 18: { /* class-ref — same wire format as symbol: name + package strings */
        uint32_t name_len = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        (void)wasm_const_pool_read_bytes(bytes, payload_len, &patch_offset, name_len, &patch_ok);
        uint32_t pkg_len = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        (void)wasm_const_pool_read_bytes(bytes, payload_len, &patch_offset, pkg_len, &patch_ok);
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

__attribute__((used, visibility("default"), export_name("wasm_const_pool_alias")))
LispObj
wasm_const_pool_alias(uint32_t target_entry, uint32_t source_entry)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj table = nrs_WASM_CONST_POOLS.vcell;
  if (table == lisp_nil ||
      fulltag_of(table) != fulltag_misc ||
      header_subtag(header_of(table)) != subtag_simple_vector) {
    return lisp_nil;
  }
  uint32_t count = (uint32_t)header_element_count(header_of(table));
  if (source_entry >= count) {
    return lisp_nil;
  }
  LispObj *src_data = (LispObj *)((BytePtr)table + misc_data_offset);
  LispObj src_pool = src_data[source_entry];
  if (src_pool == lisp_nil) {
    return lisp_nil;
  }
  /* Copy the pool vector (don't share) — cold-boot-init may mutate pool slots.
     Elements (function objects, symbols, etc.) are shared by reference. */
  if (fulltag_of(src_pool) != fulltag_misc) {
    return lisp_nil;
  }
  uint32_t pool_count = (uint32_t)header_element_count(header_of(src_pool));
  LispObj new_pool = wasm_misc_alloc(tcr, subtag_simple_vector, (signed_natural)pool_count);
  if (new_pool == lisp_nil) {
    return lisp_nil;
  }
  LispObj *new_data = (LispObj *)((BytePtr)new_pool + misc_data_offset);
  LispObj *old_data = (LispObj *)((BytePtr)src_pool + misc_data_offset);
  for (uint32_t i = 0; i < pool_count; i++) {
    new_data[i] = old_data[i];
  }
  /* wasm_misc_alloc may have grown the table; re-fetch. */
  table = wasm_const_pool_table_ensure(tcr, target_entry);
  if (table == lisp_nil) {
    return lisp_nil;
  }
  LispObj *tgt_data = (LispObj *)((BytePtr)table + misc_data_offset);
  tgt_data[target_entry] = new_pool;
  return new_pool;
}

__attribute__((used, visibility("default"), export_name("wasm_entry_fn_cache_clear")))
void
wasm_entry_fn_cache_clear(void)
{
  {
    char buf[128];
    int n = snprintf(buf, sizeof(buf),
      "entry-fn-cache: hits=%u misses=%u size=%u\n",
      wasm_entry_fn_cache_hits, wasm_entry_fn_cache_misses,
      wasm_entry_fn_cache_size);
    wasm_host_log(buf, n);
  }
  if (wasm_entry_fn_cache != NULL) {
    free(wasm_entry_fn_cache);
    wasm_entry_fn_cache = NULL;
    wasm_entry_fn_cache_size = 0;
  }
  wasm_entry_fn_cache_hits = 0;
  wasm_entry_fn_cache_misses = 0;
}

/* Purge all const pool data from the table — set every slot to fixnum 0.
   LEGACY: no longer called.  Pools are pre-baked in the image with class-refs
   resolved at build time.  Kept for potential debugging use. */
__attribute__((used, visibility("default"), export_name("wasm_const_pool_purge_all")))
uint32_t
wasm_const_pool_purge_all(void)
{
  LispObj table = nrs_WASM_CONST_POOLS.vcell;
  if (table == lisp_nil ||
      fulltag_of(table) != fulltag_misc ||
      header_subtag(header_of(table)) != subtag_simple_vector) {
    return 0;
  }
  uint32_t count = (uint32_t)header_element_count(header_of(table));
  LispObj *data = (LispObj *)((BytePtr)table + misc_data_offset);
  uint32_t purged = 0;
  for (uint32_t i = 0; i < count; i++) {
    if (data[i] != lisp_nil && data[i] != 0) {
      data[i] = lisp_nil;  /* set to NIL so wasm_const_pool_ref triggers on-demand install */
      purged++;
    }
  }
  char buf[128];
  int n = snprintf(buf, sizeof(buf),
    "const-pool-purge: %u/%u entries purged\n", purged, count);
  wasm_host_log(buf, n);
  return purged;
}

/* Resolve class-ref sentinel cons cells in all const pools.
   After all pools are installed and cold-boot-init has completed, walk every
   pool entry.  Entries that are (symbol . fixnum-0x434C) cons cells are
   class-refs: look up the class via FIND-CLASS and replace the cons cell with
   the actual class object.  If FIND-CLASS returns NIL (class not defined yet),
   leave the symbol as-is (no cons wrapper). */
__attribute__((used, visibility("default"), export_name("wasm_const_pool_resolve_class_refs")))
uint32_t
wasm_const_pool_resolve_class_refs(void)
{
  LispObj table = nrs_WASM_CONST_POOLS.vcell;
  if (table == lisp_nil ||
      fulltag_of(table) != fulltag_misc ||
      header_subtag(header_of(table)) != subtag_simple_vector) {
    return 0;
  }

  /* Find FIND-CLASS symbol: CL:FIND-CLASS */
  static const uint8_t fc_name[] = "FIND-CLASS";
  static const uint8_t cl_pkg[] = "COMMON-LISP";
  LispObj cl = wasm_find_package_named_bytes(cl_pkg, (uint32_t)sizeof(cl_pkg) - 1);
  LispObj find_class_sym = (cl != lisp_nil)
    ? wasm_find_symbol_named_bytes(fc_name, (uint32_t)sizeof(fc_name) - 1, cl)
    : (LispObj)0;

  if (find_class_sym == (LispObj)0 || find_class_sym == lisp_nil) {
    static const char msg[] = "const-pool-resolve: FIND-CLASS not found, skipping\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return 0;
  }

  LispObj sentinel = box_fixnum(0x434C);
  uint32_t table_count = (uint32_t)header_element_count(header_of(table));
  LispObj *table_data = (LispObj *)((BytePtr)table + misc_data_offset);
  uint32_t resolved = 0;
  uint32_t unresolved = 0;

  for (uint32_t e = 0; e < table_count; e++) {
    LispObj pool = table_data[e];
    if (pool == lisp_nil || pool == 0) continue;
    if (fulltag_of(pool) != fulltag_misc) continue;
    if (header_subtag(header_of(pool)) != subtag_simple_vector) continue;

    uint32_t pool_count = (uint32_t)header_element_count(header_of(pool));
    LispObj *pool_data = (LispObj *)((BytePtr)pool + misc_data_offset);

    for (uint32_t s = 0; s < pool_count; s++) {
      LispObj slot = pool_data[s];
      /* Check for sentinel cons: (symbol . fixnum-0x434C) */
      if (fulltag_of(slot) != fulltag_cons) continue;
      LispObj cdr_val = deref(slot, 1);
      if (cdr_val != sentinel) continue;

      LispObj sym = deref(slot, 0);
      if (fulltag_of(sym) != fulltag_misc ||
          header_subtag(header_of(sym)) != subtag_symbol) {
        /* car is not a symbol — unwrap sentinel, store raw value */
        pool_data[s] = sym;
        continue;
      }

      /* Call (FIND-CLASS sym NIL) — NIL second arg means don't error */
      LispObj cls = wasm_funcall2(find_class_sym, sym, lisp_nil);
      if (cls != lisp_nil && cls != 0 && fulltag_of(cls) == fulltag_misc) {
        pool_data[s] = cls;
        resolved++;
      } else {
        /* Class not found — store bare symbol as fallback */
        pool_data[s] = sym;
        unresolved++;
      }
    }
  }

  char buf[128];
  int n = snprintf(buf, sizeof(buf),
    "const-pool-resolve: %u class-refs resolved, %u unresolved\n",
    resolved, unresolved);
  wasm_host_log(buf, n);
  return resolved;
}

__attribute__((used, visibility("default"), export_name("wasm_const_pool_diag_fail_get")))
uint32_t
wasm_const_pool_diag_fail_get(void)
{
  return wasm_const_pool_diag_fail;
}

/* Diagnostic: count const-pool-ref failures for debugging. */
static uint32_t wasm_cpr_fail_count = 0;

__attribute__((used, visibility("default"), export_name("wasm_const_pool_ref")))
LispObj
wasm_const_pool_ref(uint32_t entry_index, uint32_t slot_index)
{
  uint32_t install_attempted = 0;

retry_lookup:
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
          /* Diagnostic: slot_index out of range */
          if (wasm_cpr_fail_count < 5) {
            char msg[128]; int p = 0;
            p += wasm_debug_str(msg + p, "CPR-FAIL: slot OOB e=");
            p += wasm_debug_uint(msg + p, entry_index);
            p += wasm_debug_str(msg + p, " s=");
            p += wasm_debug_uint(msg + p, slot_index);
            p += wasm_debug_str(msg + p, " cnt=");
            p += wasm_debug_uint(msg + p, pool_count);
            msg[p++] = '\n';
            wasm_host_log(msg, (unsigned)p);
            wasm_cpr_fail_count++;
          }
          return lisp_nil;
        }
        /* Diagnostic: pool entry has wrong type */
        if (wasm_cpr_fail_count < 5) {
          char msg[128]; int p = 0;
          p += wasm_debug_str(msg + p, "CPR-FAIL: pool bad e=");
          p += wasm_debug_uint(msg + p, entry_index);
          p += wasm_debug_str(msg + p, " pool=0x");
          p += wasm_debug_hex8(msg + p, (uint32_t)pool);
          p += wasm_debug_str(msg + p, " ftag=");
          p += wasm_debug_uint(msg + p, (uint32_t)fulltag_of(pool));
          msg[p++] = '\n';
          wasm_host_log(msg, (unsigned)p);
          wasm_cpr_fail_count++;
        }
      }
    }

    if (!install_attempted) {
      int32_t host_rc = wasm_host_install_const_pool(entry_index);
      install_attempted = 1;
      if (host_rc > 0) {
        goto retry_lookup;
      }
    }
  }

  /* Slow path: host install failed or did not materialize the requested pool.
   * Dump diagnostics and trap so we can identify the cause. */
  {
    LispObj table = nrs_WASM_CONST_POOLS.vcell;
    char msg[160]; int p = 0;
    p += wasm_debug_str(msg + p, "CPR-TRAP: pool not baked e=");
    p += wasm_debug_uint(msg + p, entry_index);
    p += wasm_debug_str(msg + p, " s=");
    p += wasm_debug_uint(msg + p, slot_index);
    p += wasm_debug_str(msg + p, " tbl=0x");
    p += wasm_debug_hex8(msg + p, (uint32_t)table);
    if (table != lisp_nil &&
        fulltag_of(table) == fulltag_misc &&
        header_subtag(header_of(table)) == subtag_simple_vector) {
      uint32_t tc = (uint32_t)header_element_count(header_of(table));
      p += wasm_debug_str(msg + p, " tc=");
      p += wasm_debug_uint(msg + p, tc);
      if (entry_index < tc) {
        LispObj *td = (LispObj *)((BytePtr)table + misc_data_offset);
        LispObj pool_val = td[entry_index];
        p += wasm_debug_str(msg + p, " pool=0x");
        p += wasm_debug_hex8(msg + p, (uint32_t)pool_val);
        p += wasm_debug_str(msg + p, " ft=");
        p += wasm_debug_uint(msg + p, (uint32_t)fulltag_of(pool_val));
      }
    }
    msg[p++] = '\n';
    wasm_host_log(msg, (unsigned)p);
  }
  wasm_debug_dump_state("wasm_const_pool_ref: pool not installed (should be pre-baked)");
  __builtin_trap();
  return lisp_nil;  /* unreachable */
}


/*
 * wasm_repair_udf_binding: Given a symbol name (in the CCL package) and
 * a compiled-module entry index, check whether the symbol's function cell
 * is UDF.  If so, synthesize a function object pointing to the given entry
 * and install it as the symbol's fcell.
 *
 * Returns:
 *   0  = repaired (was UDF, now bound)
 *   1  = already bound (no action taken)
 *  -1  = symbol not found
 *  -2  = no TCR
 *  -3  = allocation failed
 *  -4  = invalid entry_index
 */
__attribute__((used, visibility("default"), export_name("wasm_repair_udf_binding")))
int32_t
wasm_repair_udf_binding(uint32_t name_ptr, uint32_t name_len, uint32_t entry_index)
{
  if (name_len == 0 || name_ptr == 0) {
    return -1;
  }
  static const uint8_t ccl_pkg_name[] = { 'C', 'C', 'L' };
  static const uint8_t cl_pkg_name[] = {
    'C', 'O', 'M', 'M', 'O', 'N', '-', 'L', 'I', 'S', 'P'
  };
  const uint8_t *sym_name = (const uint8_t *)(uintptr_t)name_ptr;

  /* Try CCL package first, then CL */
  LispObj pkg = wasm_find_package_named_bytes(ccl_pkg_name, (uint32_t)sizeof(ccl_pkg_name));
  LispObj sym = (LispObj)0;
  if (pkg != lisp_nil) {
    sym = wasm_find_symbol_named_bytes(sym_name, name_len, pkg);
  }
  if (sym == (LispObj)0) {
    pkg = wasm_find_package_named_bytes(cl_pkg_name, (uint32_t)sizeof(cl_pkg_name));
    if (pkg != lisp_nil) {
      sym = wasm_find_symbol_named_bytes(sym_name, name_len, pkg);
    }
  }
  if (sym == (LispObj)0) {
    /* Try all packages as last resort */
    sym = wasm_find_symbol_in_all_packages_bytes(sym_name, name_len);
  }
  if (sym == (LispObj)0 ||
      fulltag_of(sym) != fulltag_misc ||
      header_subtag(header_of(sym)) != subtag_symbol) {
    return -1;
  }

  lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(untag(sym));
  LispObj current_fcell = rawsym->fcell;

  /* If the function cell is NOT UDF, leave it alone */
  if (current_fcell != nrs_UDF.vcell) {
    return 1;
  }

  /* Validate entry index */
  if (entry_index == 0 || entry_index > 0xFFFF) {
    return -4;
  }

  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return -2;
  }

  LispObj entry = box_fixnum((signed_natural)entry_index);
  LispObj existing = rawsym->fcell;

  if (fulltag_of(existing) == fulltag_misc &&
      (header_subtag(header_of(existing)) == subtag_function ||
       header_subtag(header_of(existing)) == subtag_xfunction)) {
    /* Patch in place — preserves keyvect (slot 2) and all other slots. */
    LispObj *fn_data = (LispObj *)((BytePtr)existing + misc_data_offset);
    fn_data[0] = entry;
    fn_data[1] = entry;
  } else {
    /* Synthesize a function object: 3 slots (entry, entry, nil for keys) */
    LispObj fn = wasm_misc_alloc(tcr, subtag_function, (signed_natural)3);
    if (fn == lisp_nil) {
      return -3;
    }
    LispObj *fn_data = (LispObj *)((BytePtr)fn + misc_data_offset);
    fn_data[0] = entry;
    fn_data[1] = entry;
    fn_data[2] = lisp_nil;
    rawsym->fcell = fn;
  }
  return 0;
}

/*
 * Batch repair: walk the heap ONCE, find all symbols with UDF fcell, and
 * match them against a provided name→entryIndex lookup table.
 *
 * table_ptr points to an array of packed entries:
 *   [name_offset:u32, name_len:u32, entry_index:u32] × table_count
 * where name_offset is a pointer into linear memory containing the name bytes.
 *
 * Returns the number of symbols repaired.
 */
__attribute__((used, visibility("default"), export_name("wasm_repair_udf_bindings_scan")))
int32_t
wasm_repair_udf_bindings_scan(uint32_t table_ptr, uint32_t table_count)
{
  if (table_ptr == 0 || table_count == 0) {
    return 0;
  }
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return -1;
  }

  typedef struct {
    uint32_t name_offset;
    uint32_t name_len;
    uint32_t entry_index;
  } repair_entry;

  const repair_entry *entries = (const repair_entry *)(uintptr_t)table_ptr;
  LispObj udf_fn = nrs_UDF.vcell;
  int32_t repaired = 0;

  /* Walk all non-stack memory areas looking for symbols with UDF fcell */
  area *areas = (area *)ptr_from_lispobj(lisp_global(ALL_AREAS));
  if (areas == NULL) {
    return 0;
  }

  area *a = areas->succ;
  while (a != NULL && a->code != AREA_VOID) {
    area_code code = a->code;
    if (code != AREA_CSTACK && code != AREA_VSTACK && code != AREA_TSTACK) {
      LispObj *start = (LispObj *)a->low;
      LispObj *end = (LispObj *)a->active;

      while (start < end) {
        LispObj header = *start;
        natural tag = fulltag_of(header);

        if (header_subtag(header) == subtag_symbol) {
          lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(ptr_to_lispobj(start));

          /* Only process symbols with UDF fcell */
          if (rawsym->fcell == udf_fn) {
            /* Get symbol's pname */
            LispObj pname = rawsym->pname;
            if (fulltag_of(pname) == fulltag_misc &&
                header_subtag(header_of(pname)) == subtag_simple_base_string) {
              uint32_t pname_len = (uint32_t)header_element_count(header_of(pname));
              uint32_t *pname_data = (uint32_t *)ptr_from_lispobj(pname + misc_data_offset);

              /* Match against table entries */
              for (uint32_t i = 0; i < table_count; i++) {
                if (entries[i].name_len != pname_len) continue;
                if (entries[i].entry_index == 0 || entries[i].entry_index > 0xFFFF) continue;

                const uint8_t *name = (const uint8_t *)(uintptr_t)entries[i].name_offset;
                int match = 1;
                for (uint32_t j = 0; j < pname_len; j++) {
                  if ((pname_data[j] & 0xffu) != name[j]) {
                    match = 0;
                    break;
                  }
                }
                if (match) {
                  LispObj entry_val = box_fixnum((signed_natural)entries[i].entry_index);
                  LispObj existing = rawsym->fcell;
                  if (fulltag_of(existing) == fulltag_misc &&
                      (header_subtag(header_of(existing)) == subtag_function ||
                       header_subtag(header_of(existing)) == subtag_xfunction)) {
                    /* Patch in place — preserves keyvect and all other slots. */
                    LispObj *fn_data = (LispObj *)((BytePtr)existing + misc_data_offset);
                    fn_data[0] = entry_val;
                    fn_data[1] = entry_val;
                  } else {
                    LispObj fn = wasm_misc_alloc(tcr, subtag_function, (signed_natural)3);
                    if (fn != lisp_nil) {
                      LispObj *fn_data = (LispObj *)((BytePtr)fn + misc_data_offset);
                      fn_data[0] = entry_val;
                      fn_data[1] = entry_val;
                      fn_data[2] = lisp_nil;
                      rawsym->fcell = fn;
                    }
                  }
                  repaired++;
                  break;
                }
              }
            }
          }
        }

        /* Advance to next heap object */
        if (nodeheader_tag_p(tag)) {
          start += (~1 & (2 + header_element_count(header)));
        } else if (immheader_tag_p(tag)) {
          start = (LispObj *)skip_over_ivector((natural)start, header);
        } else {
          start += 2;
        }
      }
    }
    a = a->succ;
  }

  return repaired;
}

/*
 * Force-rebind: like wasm_repair_udf_bindings_scan but unconditionally
 * overwrites the fcell of matching symbols (not just UDF ones).
 * Used pre-restore-lisp-pointers when package tables are unreliable
 * and many fcells have stale bindings from the image build phase.
 */
__attribute__((used, visibility("default"), export_name("wasm_force_rebind_scan")))
int32_t
wasm_force_rebind_scan(uint32_t table_ptr, uint32_t table_count)
{
  if (table_ptr == 0 || table_count == 0) {
    return 0;
  }
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return -1;
  }

  typedef struct {
    uint32_t name_offset;
    uint32_t name_len;
    uint32_t entry_index;
    uint32_t fn_slots;
  } repair_entry;

  const repair_entry *entries = (const repair_entry *)(uintptr_t)table_ptr;
  int32_t rebound = 0;

  /* Walk ALL non-stack memory areas looking for symbols.
   * Include READONLY / WATCHED — some symbols live there after image load. */
  area *areas = (area *)ptr_from_lispobj(lisp_global(ALL_AREAS));
  if (areas == NULL) {
    return 0;
  }

  area *a = areas->succ;
  while (a != NULL && a->code != AREA_VOID) {
    area_code code = a->code;
    if (code != AREA_CSTACK && code != AREA_VSTACK && code != AREA_TSTACK) {
      LispObj *start = (LispObj *)a->low;
      LispObj *end = (LispObj *)a->active;

      while (start < end) {
        LispObj header = *start;
        natural tag = fulltag_of(header);

        if (header_subtag(header) == subtag_symbol) {
          lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(ptr_to_lispobj(start));
          LispObj pname = rawsym->pname;
          if (fulltag_of(pname) == fulltag_misc &&
              header_subtag(header_of(pname)) == subtag_simple_base_string) {
            uint32_t pname_len = (uint32_t)header_element_count(header_of(pname));
            uint32_t *pname_data = (uint32_t *)ptr_from_lispobj(pname + misc_data_offset);

            for (uint32_t i = 0; i < table_count; i++) {
              if (entries[i].name_len != pname_len) continue;
              if (entries[i].entry_index == 0 || entries[i].entry_index > 0xFFFF) continue;

              const uint8_t *name = (const uint8_t *)(uintptr_t)entries[i].name_offset;
              int match = 1;
              for (uint32_t j = 0; j < pname_len; j++) {
                if ((pname_data[j] & 0xffu) != name[j]) {
                  match = 0;
                  break;
                }
              }
              if (match) {
                LispObj existing = rawsym->fcell;
                LispObj entry_val = box_fixnum((signed_natural)entries[i].entry_index);

                if (fulltag_of(existing) == fulltag_misc &&
                    (header_subtag(header_of(existing)) == subtag_function ||
                     header_subtag(header_of(existing)) == subtag_xfunction)) {
                  /* Existing function/xfunction — patch entry slots in place,
                     preserving keyvect (slot 2) and closed vars (slot 3+). */
                  LispObj *fn_data = (LispObj *)((BytePtr)existing + misc_data_offset);
                  fn_data[0] = entry_val;
                  fn_data[1] = entry_val;
                } else {
                  /* No existing function — allocate stub with correct slot count.
                     Closure functions need extra slots for closed-over variables;
                     using fn_slots from the manifest preserves the layout that
                     compiled WASM code expects when accessing nfn[3+]. */
                  uint32_t slots = entries[i].fn_slots;
                  if (slots < 3) slots = 3;
                  LispObj fn = wasm_misc_alloc(tcr, subtag_function, (signed_natural)slots);
                  if (fn == lisp_nil) {
                    break;  /* allocation failed — skip this symbol */
                  }
                  LispObj *fn_data = (LispObj *)((BytePtr)fn + misc_data_offset);
                  fn_data[0] = entry_val;
                  fn_data[1] = entry_val;
                  for (uint32_t s = 2; s < slots; s++) {
                    fn_data[s] = lisp_nil;
                  }
                  rawsym->fcell = fn;
                }
                rebound++;
                break;
              }
            }
          }
        }

        /* Advance to next heap object */
        if (nodeheader_tag_p(tag)) {
          start += (~1 & (2 + header_element_count(header)));
        } else if (immheader_tag_p(tag)) {
          start = (LispObj *)skip_over_ivector((natural)start, header);
        } else {
          start += 2;
        }
      }
    }
    a = a->succ;
  }

  return rebound;
}

/* Vcell repair pass — analogous to wasm_force_rebind_scan for fcells.
 * Walks all symbols in the heap and canonicalizes value cells.
 * For each symbol whose vcell is unbound_marker, look up the canonical
 * symbol (via package hash table) and copy its vcell if bound.
 * This repairs synthesized symbol duplicates created during const-pool
 * install whose vcells were never set by defvar (because defvar ran on
 * the canonical symbol, not the duplicate). */
__attribute__((used, visibility("default"), export_name("wasm_repair_vcell_scan")))
int32_t
wasm_repair_vcell_scan(void)
{
  extern LispObj lisp_nil;
  int32_t repaired = 0;

  area *areas_head = (area *)ptr_from_lispobj(lisp_global(ALL_AREAS));
  if (areas_head == NULL) return 0;

  area *a = areas_head->succ;
  while (a != NULL && a->code != AREA_VOID) {
    area_code code = a->code;
    if (code != AREA_CSTACK && code != AREA_VSTACK && code != AREA_TSTACK) {
      LispObj *start = (LispObj *)a->low;
      LispObj *end = (LispObj *)a->active;

      while (start < end) {
        LispObj header = *start;
        natural tag = fulltag_of(header);

        if (header_subtag(header) == subtag_symbol) {
          lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(ptr_to_lispobj(start));
          LispObj sym_obj = ptr_to_lispobj(start) | fulltag_misc;

          /* Only repair symbols whose vcell is unbound or nil (the old bug) */
          if (rawsym->vcell == unbound_marker || rawsym->vcell == lisp_nil) {
            LispObj pname = rawsym->pname;
            if (fulltag_of(pname) == fulltag_misc &&
                header_subtag(header_of(pname)) == subtag_simple_base_string) {
              uint32_t pname_len = (uint32_t)header_element_count(header_of(pname));
              /* Extract pname bytes (stored as 32-bit elements, ASCII in low byte) */
              uint32_t *pname_data = (uint32_t *)ptr_from_lispobj(pname + misc_data_offset);
              uint8_t name_buf[256];
              if (pname_len <= sizeof(name_buf)) {
                for (uint32_t j = 0; j < pname_len; j++) {
                  name_buf[j] = (uint8_t)(pname_data[j] & 0xffu);
                }
                /* Package-table lookup (fast, O(1) per symbol) */
                LispObj pkg = rawsym->package_predicate;
                LispObj canonical = wasm_find_symbol_named_bytes(name_buf, pname_len, pkg);
                if (canonical != (LispObj)0 && canonical != sym_obj) {
                  lispsymbol *canon_raw = (lispsymbol *)ptr_from_lispobj(untag(canonical));
                  if (canon_raw->vcell != unbound_marker) {
                    rawsym->vcell = canon_raw->vcell;
                    repaired++;
                  }
                }
              }
            }
          }
        }

        /* Advance to next heap object */
        if (nodeheader_tag_p(tag)) {
          start += (~1 & (2 + header_element_count(header)));
        } else if (immheader_tag_p(tag)) {
          start = (LispObj *)skip_over_ivector((natural)start, header);
        } else {
          start += 2;
        }
      }
    }
    a = a->succ;
  }

  return repaired;
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
  /* Keep const pools — they are GC-rooted through the NRS symbol and
     survive compaction.  The deterministic launcher needs them pre-baked
     in the saved image for zero-cost startup. */

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
