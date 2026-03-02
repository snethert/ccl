#ifdef WASM32
#include <stdint.h>
#include <string.h>

#include "lisp.h"
#include "area.h"
#include "lisp-exceptions.h"
#include "lisp_globals.h"

/* Imported from kernel module (defined in wasm-kernel-stubs.c) */
__attribute__((import_module("ccl"), import_name("wasm_debug_dump_state")))
void wasm_debug_dump_state(const char *label);

/* WASM-only catch frame with dnode-aligned size (48 bytes = 12 slots).
 * Must be a multiple of 8 bytes so that stack-allocated frames keep
 * fulltag_misc tagging intact for catch_top pointers.
 * 11 meaningful slots + 1 pad slot = 12 * 4 = 48.
 */
typedef struct wasm_catch_frame {
  LispObj header;
  LispObj link;
  LispObj mvflag;
  LispObj catch_tag;
  LispObj db_link;
  LispObj xframe;
  LispObj last_lisp_frame;
  LispObj nfp;
  LispObj save_vsp;
  LispObj cleanup_entry;
  LispObj save_spill_sp;
  LispObj _pad;
} wasm_catch_frame;

#define WASM_CATCH_FRAME_ELEMENT_COUNT ((sizeof(wasm_catch_frame) / sizeof(LispObj)) - 1)
#define WASM_CATCH_FRAME_HEADER make_header(subtag_catch_frame, WASM_CATCH_FRAME_ELEMENT_COUNT)
_Static_assert(sizeof(wasm_catch_frame) % 8 == 0,
               "wasm_catch_frame must be dnode-aligned (multiple of 8 bytes)");

__attribute__((import_module("ccl"), import_name("wasm_get_current_tcr")))
TCR *wasm_get_current_tcr(void);

__attribute__((import_module("ccl"), import_name("wasm_get_cstack_pointer")))
void *wasm_get_cstack_pointer(void);

__attribute__((import_module("ccl"), import_name("wasm_set_cstack_pointer")))
void wasm_set_cstack_pointer(void *stack_ptr);

__attribute__((import_module("ccl"), import_name("wasm_box_signed_64")))
LispObj wasm_box_signed_64(TCR *tcr, int64_t value);

__attribute__((import_module("ccl"), import_name("wasm_misc_alloc")))
LispObj wasm_misc_alloc(TCR *tcr, unsigned subtag, signed_natural count);

__attribute__((import_module("ccl"), import_name("wasm_call_subprim_fixnum")))
void wasm_call_subprim_fixnum(LispObj sp_index_fixnum);

__attribute__((import_module("ccl"), import_name("wasm_alloc_cons_bridge")))
LispObj wasm_alloc_cons_bridge(LispObj car_value, LispObj cdr_value);

__attribute__((import_module("ccl"), import_name("wasm_prepare_entry_call")))
uint32_t wasm_prepare_entry_call(uint32_t entry_index);

__attribute__((import_module("ccl"), import_name("wasm_get_trace_funcall")))
uint32_t wasm_get_trace_funcall(void);

void _SPksignalerr(void);

static LispObj wasm_alloc_cons_or_trap(TCR *tcr, LispObj car_value, LispObj cdr_value);

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
wasm_set_nargs_count(TCR *tcr, signed_natural count)
{
  LispObj nargs_value = box_fixnum(count);
  if (wasm_reg(tcr, nargs) != nargs_value) {
    wasm_set_reg(tcr, nargs, nargs_value);
  }
}

static inline LispObj
wasm_nrs_symbol_lispobj(lispsymbol *sym)
{
  return ptr_to_lispobj((BytePtr)sym + fulltag_misc);
}

static size_t
wasm_c_strlen(const char *bytes)
{
  const volatile unsigned char *cursor = (const volatile unsigned char *)bytes;
  size_t len = 0;
  while (*cursor != '\0') {
    len++;
    cursor++;
  }
  return len;
}

static unsigned
wasm_diag_append_str(char *dst, unsigned pos, const char *src)
{
  while (*src != '\0') {
    dst[pos++] = *src++;
  }
  return pos;
}

static unsigned
wasm_diag_append_hex32(char *dst, unsigned pos, uint32_t value)
{
  static const char hex[] = "0123456789abcdef";
  for (int shift = 28; shift >= 0; shift -= 4) {
    dst[pos++] = hex[(value >> shift) & 0x0fu];
  }
  return pos;
}

#define WASM_DIAG_ENTRY_UNKNOWN 0xffffffffu
#define WASM_DIAG_ENTRY_LENGTH 713u
#define WASM_DIAG_ENTRY_SEQUENCE_TYPE 917u
#define WASM_DIAG_ENTRY_SYMBOL_NAME 947u
#define WASM_DIAG_ENTRY_CLEAR_ALL_GF_CACHES 2000u
#define WASM_DIAG_EDGE_LOG_LIMIT 256u
#define WASM_DIAG_CALLSTACK_MAX 1024u

static uint32_t wasm_diag_callstack[WASM_DIAG_CALLSTACK_MAX];
static uint32_t wasm_diag_edge_log_count = 0u;

static int
wasm_diag_entry_is_watch(uint32_t entry_index)
{
  switch (entry_index) {
  case WASM_DIAG_ENTRY_LENGTH:
  case WASM_DIAG_ENTRY_SEQUENCE_TYPE:
  case WASM_DIAG_ENTRY_SYMBOL_NAME:
  case WASM_DIAG_ENTRY_CLEAR_ALL_GF_CACHES:
    return 1;
  default:
    return 0;
  }
}

static const char *
wasm_diag_entry_watch_name(uint32_t entry_index)
{
  switch (entry_index) {
  case WASM_DIAG_ENTRY_LENGTH:
    return "LENGTH";
  case WASM_DIAG_ENTRY_SEQUENCE_TYPE:
    return "SEQUENCE-TYPE";
  case WASM_DIAG_ENTRY_SYMBOL_NAME:
    return "SYMBOL-NAME";
  case WASM_DIAG_ENTRY_CLEAR_ALL_GF_CACHES:
    return "CLEAR-ALL-GF-CACHES";
  default:
    return "OTHER";
  }
}

static void
wasm_diag_log_watch_call(TCR *tcr, uint32_t caller_entry, uint32_t callee_entry, uint32_t depth)
{
  if (wasm_diag_edge_log_count >= WASM_DIAG_EDGE_LOG_LIMIT) {
    return;
  }
  if (!wasm_diag_entry_is_watch(caller_entry) && !wasm_diag_entry_is_watch(callee_entry)) {
    return;
  }
  char msg[320];
  unsigned p = 0;
  p = wasm_diag_append_str(msg, p, "edge d=0x");
  p = wasm_diag_append_hex32(msg, p, depth);
  p = wasm_diag_append_str(msg, p, " c=0x");
  p = wasm_diag_append_hex32(msg, p, caller_entry);
  p = wasm_diag_append_str(msg, p, "(");
  p = wasm_diag_append_str(msg, p, wasm_diag_entry_watch_name(caller_entry));
  p = wasm_diag_append_str(msg, p, ")->0x");
  p = wasm_diag_append_hex32(msg, p, callee_entry);
  p = wasm_diag_append_str(msg, p, "(");
  p = wasm_diag_append_str(msg, p, wasm_diag_entry_watch_name(callee_entry));
  p = wasm_diag_append_str(msg, p, ")");
  p = wasm_diag_append_str(msg, p, " n=0x");
  p = wasm_diag_append_hex32(msg, p, (uint32_t)wasm_reg(tcr, nargs));
  p = wasm_diag_append_str(msg, p, " z=0x");
  p = wasm_diag_append_hex32(msg, p, (uint32_t)wasm_reg(tcr, arg_z));
  p = wasm_diag_append_str(msg, p, " y=0x");
  p = wasm_diag_append_hex32(msg, p, (uint32_t)wasm_reg(tcr, arg_y));
  msg[p++] = '\n';
  wasm_host_log(msg, p);
  wasm_diag_edge_log_count++;
}

static void
wasm_diag_log_watch_return(TCR *tcr, uint32_t entry_index, uint32_t depth)
{
  if (wasm_diag_edge_log_count >= WASM_DIAG_EDGE_LOG_LIMIT) {
    return;
  }
  if (entry_index != WASM_DIAG_ENTRY_CLEAR_ALL_GF_CACHES) {
    return;
  }
  char msg[256];
  unsigned p = 0;
  p = wasm_diag_append_str(msg, p, "edge-ret d=0x");
  p = wasm_diag_append_hex32(msg, p, depth);
  p = wasm_diag_append_str(msg, p, " 0x");
  p = wasm_diag_append_hex32(msg, p, entry_index);
  p = wasm_diag_append_str(msg, p, "(CLEAR-ALL-GF-CACHES)");
  p = wasm_diag_append_str(msg, p, " throw=0x");
  p = wasm_diag_append_hex32(msg, p, (uint32_t)tcr->wasm_pending_throw);
  p = wasm_diag_append_str(msg, p, " n=0x");
  p = wasm_diag_append_hex32(msg, p, (uint32_t)wasm_reg(tcr, nargs));
  p = wasm_diag_append_str(msg, p, " z=0x");
  p = wasm_diag_append_hex32(msg, p, (uint32_t)wasm_reg(tcr, arg_z));
  msg[p++] = '\n';
  wasm_host_log(msg, p);
  wasm_diag_edge_log_count++;
}

static void
wasm_diag_log_misc_alloc_bad_count(TCR *tcr, LispObj subtag_val, LispObj count_val)
{
  uint32_t entry_index = 0xffffffffu;
  LispObj fn_value = wasm_reg(tcr, nfn);
  if (fulltag_of(fn_value) == fulltag_misc) {
    unsigned fn_subtag = header_subtag(header_of(fn_value));
    if (fn_subtag == subtag_function || fn_subtag == subtag_pseudofunction) {
      LispObj entry = deref(fn_value, 1);
      if (tag_of(entry) == tag_fixnum) {
        entry_index = (uint32_t)unbox_fixnum(entry);
      }
    }
  }

  char msg[160];
  unsigned pos = 0;
  pos = wasm_diag_append_str(msg, pos, "_SPmisc_alloc: bad count s=0x");
  pos = wasm_diag_append_hex32(msg, pos, (uint32_t)subtag_val);
  pos = wasm_diag_append_str(msg, pos, " c=0x");
  pos = wasm_diag_append_hex32(msg, pos, (uint32_t)count_val);
  pos = wasm_diag_append_str(msg, pos, " fn=0x");
  pos = wasm_diag_append_hex32(msg, pos, (uint32_t)fn_value);
  pos = wasm_diag_append_str(msg, pos, " e=0x");
  pos = wasm_diag_append_hex32(msg, pos, entry_index);
  msg[pos++] = '\n';
  wasm_host_log(msg, pos);
}

static LispObj *
wasm_skip_over_ivector(natural start, LispObj header)
{
  natural element_count = header_element_count(header);
  natural subtag = header_subtag(header);
  natural nbytes;

  if (nodeheader_tag_p(fulltag_of(header)) ||
      (subtag <= max_32_bit_ivector_subtag)) {
    nbytes = element_count << 2;
  } else if (subtag <= max_8_bit_ivector_subtag) {
    nbytes = element_count;
  } else if (subtag <= max_16_bit_ivector_subtag) {
    nbytes = element_count << 1;
  } else if (subtag == subtag_bit_vector) {
    nbytes = (element_count + 7) >> 3;
  } else if (subtag == subtag_complex_double_float_vector) {
    nbytes = 4 + (element_count << 4);
  } else {
    nbytes = 4 + (element_count << 3);
  }

  return ptr_from_lispobj(start + (~7 & (nbytes + 4 + 7)));
}

static LispObj wasm_misc_ref_dispatch(TCR *tcr, LispObj obj, signed_natural index);
static void wasm_misc_set_dispatch(TCR *tcr, LispObj obj, signed_natural index, LispObj value);
static void wasm_call_lisp_function(TCR *tcr, LispObj fn_value);
static void wasm_call_function_value(TCR *tcr, LispObj fn_value, LispObj name);
static void wasm_call_function_or_symbol(TCR *tcr, LispObj fn_value);
static void wasm_bind_interrupt_level(TCR *tcr, LispObj new_value);
static void wasm_maybe_deliver_interrupt(TCR *tcr);
static void wasm_sync_arg_regs_from_vsp(TCR *tcr);
static inline LispObj *wasm_vsp_or_trap(TCR *tcr);

enum {
  WASM_BUILTIN_PLUS = 0,
  WASM_BUILTIN_MINUS = 1,
  WASM_BUILTIN_TIMES = 2,
  WASM_BUILTIN_DIV = 3,
  WASM_BUILTIN_EQ = 4,
  WASM_BUILTIN_NE = 5,
  WASM_BUILTIN_GT = 6,
  WASM_BUILTIN_GE = 7,
  WASM_BUILTIN_LT = 8,
  WASM_BUILTIN_LE = 9,
  WASM_BUILTIN_EQL = 10,
  WASM_BUILTIN_LENGTH = 11,
  WASM_BUILTIN_SEQTYPE = 12,
  WASM_BUILTIN_ASSQ = 13,
  WASM_BUILTIN_MEMQ = 14,
  WASM_BUILTIN_LOGBITP = 15,
  WASM_BUILTIN_LOGIOR = 16,
  WASM_BUILTIN_LOGAND = 17,
  WASM_BUILTIN_ASH = 18,
  WASM_BUILTIN_NEGATE = 19,
  WASM_BUILTIN_LOGXOR = 20,
  WASM_BUILTIN_AREF1 = 21,
  WASM_BUILTIN_ASET1 = 22
};

static inline LispObj
wasm_t_value(void)
{
  return (LispObj)(nil_value + t_offset);
}

#define WASM_XBADKEYS 153
#define WASM_XCALLTOOMANY 167
#define WASM_XCALLTOOFEW 168
#define WASM_XCALLNOMATCH 169
#define WASM_XARROOB 112
#define WASM_XNDIMS 148
#define WASM_XWRONGTYPE 157
#define WASM_XARRLIMIT 77
#define WASM_XDIVZRO 66
#define WASM_XNOSPREAD 120
#define WASM_XFUNBND 6
#define WASM_XNOTFUN 13
#define WASM_XVUNBND 1
#define WASM_XSYMNOBIND 178
#define WASM_XNOCTAG 33

#define WASM_KEYWORD_FLAG_ALLOW_OTHER_KEYS ((LispObj)1 << fixnum_shift)
#define WASM_KEYWORD_FLAG_SEEN_ALLOW_OTHER_KEYS ((LispObj)1 << (fixnum_shift + 1))
#define WASM_KEYWORD_FLAG_REST ((LispObj)1 << (fixnum_shift + 2))
#define WASM_KEYWORD_FLAG_UNKNOWN_KEYWORD ((LispObj)1 << (fixnum_shift + 3))

#define WASM_DEBIND_MASK_KEYP (1u << 25)
#define WASM_DEBIND_MASK_AOK (1u << 26)
#define WASM_DEBIND_MASK_RESTP (1u << 27)
#define WASM_DEBIND_MASK_UNKNOWN_KEYWORD (1u << 28)
#define WASM_DEBIND_MASK_INITOPT (1u << 29)
#define WASM_DEBIND_MASK_AOK_SEEN (1u << 30)
#define WASM_DEBIND_MASK_AOK_THIS (1u << 31)

/* Keep in sync with build/wasm32/subprims-map.json. */
#define WASM_SUBPRIM_PROGVRESTORE_INDEX 114

static LispObj
wasm_make_simple_base_string(TCR *tcr, const char *bytes)
{
  if (tcr == NULL || bytes == NULL) {
    wasm_subprims_trap();
  }

  size_t len = wasm_c_strlen(bytes);
  if (len > ((size_t)INT32_MAX)) {
    wasm_subprims_trap();
  }

  LispObj obj = wasm_misc_alloc(tcr, subtag_simple_base_string, (signed_natural)len);
  if (obj == (LispObj)nil_value) {
    wasm_subprims_trap();
  }

  uint32_t *data = (uint32_t *)((BytePtr)obj + misc_data_offset);
  for (size_t i = 0; i < len; i++) {
    data[i] = (uint32_t)(unsigned char)bytes[i];
  }
  return obj;
}

static int
wasm_compare_lisp_string_to_c_string(lisp_char_code *lisp_string,
                                     const char *c_string,
                                     natural count)
{
  for (natural i = 0; i < count; i++) {
    if (lisp_string[i] != (lisp_char_code)c_string[i]) {
      return 1;
    }
  }
  return 0;
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
wasm_find_symbol_in_range(LispObj *start,
                          LispObj *end,
                          const char *name,
                          LispObj package)
{
  LispObj header;
  LispObj tag;
  int length = (int)wasm_c_strlen(name);
  while (start < end) {
    header = *start;
    tag = fulltag_of(header);
    if (header_subtag(header) == subtag_symbol) {
      LispObj pname = deref(ptr_to_lispobj(start), 1);
      LispObj pname_header = header_of(pname);
      if ((header_subtag(pname_header) == subtag_simple_base_string) &&
          ((int)header_element_count(pname_header) == length)) {
        lisp_char_code *p = (lisp_char_code *)ptr_from_lispobj(pname + misc_data_offset);
        if (wasm_compare_lisp_string_to_c_string(p, name, (natural)length) == 0) {
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
      start = (LispObj *)wasm_skip_over_ivector((natural)start, header);
    } else {
      start += 2;
    }
  }
  return (LispObj)NULL;
}

static LispObj
wasm_find_symbol_named(const char *name, LispObj package)
{
  area *a = ((area *)ptr_from_lispobj(lisp_global(ALL_AREAS)))->succ;
  while (a->code != AREA_VOID) {
    area_code code = a->code;
    if ((code == AREA_STATIC) ||
        (code == AREA_DYNAMIC) ||
        (code == AREA_MANAGED_STATIC) ||
        (code == AREA_READONLY) ||
        (code == AREA_WATCHED) ||
        (code == AREA_STATIC_CONS)) {
      LispObj sym = wasm_find_symbol_in_range((LispObj *)a->low,
                                              (LispObj *)a->active,
                                              name,
                                              package);
      if (sym) {
        return sym;
      }
    }
    a = a->succ;
  }
  return (LispObj)NULL;
}

static LispObj
wasm_cached_symbol_named(const char *name, LispObj package, LispObj *cache)
{
  if (*cache == (LispObj)0) {
    LispObj sym = wasm_find_symbol_named(name, package);
    if (sym == (LispObj)NULL) {
      wasm_subprims_trap();
    }
    *cache = sym;
  }
  return *cache;
}

static void
wasm_signal_capability_unavailable(TCR *tcr,
                                   const char *capability,
                                   const char *operation,
                                   const char *details)
{
  static LispObj sym_capability_unavailable = (LispObj)0;
  static LispObj kw_capability = (LispObj)0;
  static LispObj kw_operation = (LispObj)0;
  static LispObj kw_details = (LispObj)0;

  LispObj cond_sym = wasm_cached_symbol_named("CAPABILITY-UNAVAILABLE",
                                              (LispObj)0,
                                              &sym_capability_unavailable);
  LispObj cap_key = wasm_cached_symbol_named("CAPABILITY",
                                             nrs_KEYWORD_PACKAGE.vcell,
                                             &kw_capability);
  LispObj op_key = wasm_cached_symbol_named("OPERATION",
                                            nrs_KEYWORD_PACKAGE.vcell,
                                            &kw_operation);

  LispObj args[7];
  signed_natural count = 0;

  args[count++] = cond_sym;
  args[count++] = cap_key;
  args[count++] = wasm_make_simple_base_string(tcr, capability);
  args[count++] = op_key;
  args[count++] = wasm_make_simple_base_string(tcr, operation);

  if (details != NULL) {
    LispObj details_key = wasm_cached_symbol_named("DETAILS",
                                                   nrs_KEYWORD_PACKAGE.vcell,
                                                   &kw_details);
    args[count++] = details_key;
    args[count++] = wasm_make_simple_base_string(tcr, details);
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  for (signed_natural i = 0; i < count; i++) {
    *--vsp_ptr = args[i];
  }
  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
  wasm_set_nargs_count(tcr, count);
  wasm_sync_arg_regs_from_vsp(tcr);
  wasm_call_lisp_function(tcr, wasm_nrs_symbol_lispobj(&nrs_ERROR));
}

static LispObj
wasm_symbol_array(void)
{
  static LispObj sym_array = (LispObj)0;
  return wasm_cached_symbol_named("ARRAY", (LispObj)0, &sym_array);
}

static LispObj
wasm_symbol_fixnum(void)
{
  static LispObj sym_fixnum = (LispObj)0;
  return wasm_cached_symbol_named("FIXNUM", (LispObj)0, &sym_fixnum);
}

static LispObj
wasm_symbol_character(void)
{
  static LispObj sym_character = (LispObj)0;
  return wasm_cached_symbol_named("CHARACTER", (LispObj)0, &sym_character);
}

static LispObj
wasm_symbol_single_float(void)
{
  static LispObj sym_single_float = (LispObj)0;
  return wasm_cached_symbol_named("SINGLE-FLOAT", (LispObj)0, &sym_single_float);
}

static LispObj
wasm_symbol_double_float(void)
{
  static LispObj sym_double_float = (LispObj)0;
  return wasm_cached_symbol_named("DOUBLE-FLOAT", (LispObj)0, &sym_double_float);
}

static LispObj
wasm_symbol_complex(void)
{
  static LispObj sym_complex = (LispObj)0;
  return wasm_cached_symbol_named("COMPLEX", (LispObj)0, &sym_complex);
}

static LispObj
wasm_symbol_unsigned_byte(void)
{
  static LispObj sym_unsigned_byte = (LispObj)0;
  return wasm_cached_symbol_named("UNSIGNED-BYTE", (LispObj)0, &sym_unsigned_byte);
}

static LispObj
wasm_symbol_signed_byte(void)
{
  static LispObj sym_signed_byte = (LispObj)0;
  return wasm_cached_symbol_named("SIGNED-BYTE", (LispObj)0, &sym_signed_byte);
}

static LispObj
wasm_symbol_bit(void)
{
  static LispObj sym_bit = (LispObj)0;
  return wasm_cached_symbol_named("BIT", (LispObj)0, &sym_bit);
}

static LispObj
wasm_list2(TCR *tcr, LispObj first, LispObj second)
{
  LispObj tail = wasm_alloc_cons_or_trap(tcr, second, (LispObj)nil_value);
  return wasm_alloc_cons_or_trap(tcr, first, tail);
}

static LispObj
wasm_type_unsigned_byte(TCR *tcr, signed_natural bits)
{
  return wasm_list2(tcr, wasm_symbol_unsigned_byte(), box_fixnum(bits));
}

static LispObj
wasm_type_signed_byte(TCR *tcr, signed_natural bits)
{
  return wasm_list2(tcr, wasm_symbol_signed_byte(), box_fixnum(bits));
}

static LispObj
wasm_type_complex(TCR *tcr, LispObj element_type)
{
  return wasm_list2(tcr, wasm_symbol_complex(), element_type);
}

static void
wasm_signal_errdisp_2(TCR *tcr, LispObj arg0, LispObj arg1, signed_natural errnum)
{
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  wasm_set_reg(tcr, arg_x, box_fixnum(errnum));
  wasm_set_reg(tcr, arg_y, arg0);
  wasm_set_reg(tcr, arg_z, arg1);
  wasm_set_nargs_count(tcr, 3);
  _SPksignalerr();
}

static void
wasm_signal_wrong_type(TCR *tcr, LispObj datum, LispObj expected)
{
  wasm_signal_errdisp_2(tcr, datum, expected, WASM_XWRONGTYPE);
}

static void
wasm_signal_xndims(TCR *tcr, LispObj array, signed_natural nsubs)
{
  wasm_signal_errdisp_2(tcr, array, box_fixnum(nsubs), WASM_XNDIMS);
}

static void
wasm_signal_xarroob(TCR *tcr, LispObj index, LispObj array)
{
  wasm_signal_errdisp_2(tcr, index, array, WASM_XARROOB);
}

static inline LispObj
wasm_bool_to_lisp(int cond)
{
  return cond ? wasm_t_value() : (LispObj)nil_value;
}

static LispObj
wasm_builtin_function(signed_natural index)
{
  static LispObj cached_vec = (LispObj)0;
  static LispObj *cached_data = NULL;
  static signed_natural cached_count = 0;
  LispObj vec = nrs_BUILTIN_FUNCTIONS.vcell;
  if (vec != cached_vec || cached_data == NULL) {
    if (vec == (LispObj)nil_value || fulltag_of(vec) != fulltag_misc) {
      wasm_subprims_trap();
    }
    LispObj header = header_of(vec);
    unsigned subtag = header_subtag(header);
    if ((subtag & fulltagmask) != fulltag_nodeheader) {
      wasm_subprims_trap();
    }
    cached_vec = vec;
    cached_count = header_element_count(header);
    cached_data = (LispObj *)((BytePtr)vec + misc_data_offset);
  }

  if ((natural)index >= (natural)cached_count) {
    wasm_subprims_trap();
  }
  return cached_data[index];
}

static inline int
wasm_function_like_subtag(unsigned subtag)
{
  return (subtag == subtag_function) || (subtag == subtag_pseudofunction);
}

static void
wasm_call_builtin(TCR *tcr, signed_natural index, signed_natural nargs_count)
{
  LispObj fn = wasm_builtin_function(index);
  /* The WASM compiler places args into registers as:
       arg_z = 1st, arg_y = 2nd, arg_x = 3rd
     but the ARM Lisp calling convention (used by compiled functions) is:
       arg_z = last, arg_y = 2nd (or 1st for 2-arg), arg_x = 1st (for 3-arg)
     Swap to match the Lisp convention before calling. */
  if (nargs_count == 2) {
    LispObj tmp = wasm_reg(tcr, arg_z);
    wasm_set_reg(tcr, arg_z, wasm_reg(tcr, arg_y));
    wasm_set_reg(tcr, arg_y, tmp);
  } else if (nargs_count >= 3) {
    LispObj tmp = wasm_reg(tcr, arg_z);
    wasm_set_reg(tcr, arg_z, wasm_reg(tcr, arg_x));
    wasm_set_reg(tcr, arg_x, tmp);
    /* arg_y stays — it's the 2nd arg in both conventions */
  }
  wasm_set_nargs_count(tcr, nargs_count);
  wasm_call_function_or_symbol(tcr, fn);
}

static LispObj
wasm_alloc_cons_or_trap(TCR *tcr, LispObj car_value, LispObj cdr_value)
{
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  LispObj obj = wasm_alloc_cons_bridge(car_value, cdr_value);
  if (obj == (LispObj)nil_value) {
    wasm_subprims_trap();
  }
  return obj;
}

static LispObj *
wasm_cstack_alloc_simple_vector(TCR *tcr, signed_natural element_count)
{
  if (element_count < 0) {
    return NULL;
  }

  BytePtr base = (BytePtr)tcr->wasm_cstack_base;
  natural size = tcr->wasm_cstack_size;
  if (base == NULL || size == 0) {
    return NULL;
  }

  size_t words = 1u + (size_t)element_count;
  size_t bytes = words * node_size;
  bytes = (bytes + (dnode_size - 1)) & ~(size_t)(dnode_size - 1);

  size_t total = bytes + (2 * node_size);
  BytePtr sp = (BytePtr)wasm_get_cstack_pointer();
  BytePtr low = base - size;
  if ((sp < low) || ((size_t)(sp - low) < total)) {
    return NULL;
  }

  BytePtr old_sp = sp;
  BytePtr obj_sp = sp - bytes;
  BytePtr marker_sp = obj_sp - (2 * node_size);

  LispObj *headerp = (LispObj *)obj_sp;
  headerp[0] = make_header(subtag_simple_vector, (signed_natural)element_count);
  memset(&headerp[1], 0, element_count * sizeof(LispObj));

  LispObj *marker = (LispObj *)marker_sp;
  marker[0] = stack_alloc_marker;
  marker[1] = (LispObj)old_sp;

  wasm_set_cstack_pointer(marker_sp);
  return headerp;
}

static int
wasm_ivector_total_bytes(unsigned subtag, signed_natural count, size_t *bytes_out)
{
  if (count < 0) {
    return 0;
  }

  size_t element_count = (size_t)count;
  size_t total = 0;

  if (subtag <= max_32_bit_ivector_subtag) {
    if (element_count > ((SIZE_MAX - 4u) >> 2)) {
      return 0;
    }
    total = 4u + (element_count << 2);
  } else if (subtag <= max_8_bit_ivector_subtag) {
    if (element_count > (SIZE_MAX - 4u)) {
      return 0;
    }
    total = 4u + element_count;
  } else if (subtag <= max_16_bit_ivector_subtag) {
    if (element_count > ((SIZE_MAX - 4u) >> 1)) {
      return 0;
    }
    total = 4u + (element_count << 1);
  } else if (subtag == subtag_complex_double_float_vector) {
    if (element_count > ((SIZE_MAX - 8u) >> 4)) {
      return 0;
    }
    total = 8u + (element_count << 4);
  } else if (subtag == subtag_bit_vector) {
    if (element_count > (SIZE_MAX - 7u)) {
      return 0;
    }
    total = 4u + ((element_count + 7u) >> 3);
  } else {
    if (element_count > ((SIZE_MAX - 8u) >> 3)) {
      return 0;
    }
    total = 8u + (element_count << 3);
  }

  *bytes_out = (total + (dnode_size - 1)) & ~(size_t)(dnode_size - 1);
  return 1;
}

static inline signed_natural
wasm_macptr_element_count(void)
{
  return (signed_natural)((sizeof(macptr) / sizeof(LispObj)) - 1);
}

static LispObj
wasm_cstack_alloc_macptr_block(TCR *tcr, signed_natural byte_count, int zero_data)
{
  if (tcr == NULL || byte_count < 0) {
    return (LispObj)nil_value;
  }

  size_t vector_bytes = 0;
  if (!wasm_ivector_total_bytes(subtag_u8_vector, byte_count, &vector_bytes)) {
    return (LispObj)nil_value;
  }

  size_t macptr_bytes = sizeof(macptr);
  macptr_bytes = (macptr_bytes + (dnode_size - 1)) & ~(size_t)(dnode_size - 1);

  BytePtr base = (BytePtr)tcr->wasm_cstack_base;
  natural size = tcr->wasm_cstack_size;
  if (base == NULL || size == 0) {
    return (LispObj)nil_value;
  }

  size_t total = vector_bytes + macptr_bytes + (2 * node_size);
  BytePtr sp = (BytePtr)wasm_get_cstack_pointer();
  BytePtr low = base - size;
  if ((sp < low) || ((size_t)(sp - low) < total)) {
    return (LispObj)nil_value;
  }

  BytePtr old_sp = sp;
  BytePtr vec_sp = sp - vector_bytes;
  BytePtr macptr_sp = vec_sp - macptr_bytes;
  BytePtr marker_sp = macptr_sp - (2 * node_size);

  if (zero_data) {
    memset(vec_sp, 0, vector_bytes);
  }

  ((LispObj *)vec_sp)[0] = make_header(subtag_u8_vector, byte_count);

  macptr *mp = (macptr *)macptr_sp;
  mp->header = make_header(subtag_macptr, wasm_macptr_element_count());
  mp->address = (LispObj)(vec_sp + misc_data_offset);
  mp->class = 0;
  mp->type = 0;

  LispObj *marker = (LispObj *)marker_sp;
  marker[0] = stack_alloc_marker;
  marker[1] = (LispObj)old_sp;

  wasm_set_cstack_pointer(marker_sp);
  return (LispObj)(macptr_sp + fulltag_misc);
}

static LispObj
wasm_cstack_alloc_object(TCR *tcr, LispObj header, size_t bytes)
{
  if (tcr == NULL) {
    return (LispObj)nil_value;
  }

  BytePtr base = (BytePtr)tcr->wasm_cstack_base;
  natural size = tcr->wasm_cstack_size;
  if (base == NULL || size == 0) {
    return (LispObj)nil_value;
  }

  bytes = (bytes + (dnode_size - 1)) & ~(size_t)(dnode_size - 1);
  size_t total = bytes + (2 * node_size);

  BytePtr sp = (BytePtr)wasm_get_cstack_pointer();
  BytePtr low = base - size;
  if ((sp < low) || ((size_t)(sp - low) < total)) {
    return (LispObj)nil_value;
  }

  BytePtr old_sp = sp;
  BytePtr obj_sp = sp - bytes;
  BytePtr marker_sp = obj_sp - (2 * node_size);

  memset(obj_sp, 0, bytes);
  ((LispObj *)obj_sp)[0] = header;

  LispObj *marker = (LispObj *)marker_sp;
  marker[0] = stack_alloc_marker;
  marker[1] = (LispObj)old_sp;

  wasm_set_cstack_pointer(marker_sp);
  return (LispObj)(obj_sp + fulltag_misc);
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

static inline void
wasm_vpop_argregs(TCR *tcr)
{
  LispObj raw = wasm_reg(tcr, nargs);
  if (tag_of(raw) != tag_fixnum) {
    wasm_subprims_trap();
  }

  signed_natural count = unbox_fixnum(raw);
  if (count <= 0) {
    return;
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;

  wasm_set_reg(tcr, arg_z, vsp_ptr[0]);
  vsp_ptr += 1;

  if (count >= 2) {
    wasm_set_reg(tcr, arg_y, vsp_ptr[0]);
    vsp_ptr += 1;
  }

  if (count >= 3) {
    wasm_set_reg(tcr, arg_x, vsp_ptr[0]);
    vsp_ptr += 1;
  }

  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
}

static inline void
wasm_vpush_argregs(TCR *tcr)
{
  LispObj raw = wasm_reg(tcr, nargs);
  if (tag_of(raw) != tag_fixnum) {
    wasm_subprims_trap();
  }

  signed_natural count = unbox_fixnum(raw);
  if (count <= 0) {
    return;
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;

  if (count >= 3) {
    *--vsp_ptr = wasm_reg(tcr, arg_x);
  }
  if (count >= 2) {
    *--vsp_ptr = wasm_reg(tcr, arg_y);
  }
  *--vsp_ptr = wasm_reg(tcr, arg_z);

  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
}

static inline lispsymbol *
wasm_symbol_or_trap(LispObj symbol)
{
  if (fulltag_of(symbol) != fulltag_misc || header_subtag(header_of(symbol)) != subtag_symbol) {
    /* Diagnostic: log the failing value before trapping */
    {
      char msg[160];
      unsigned p = 0;
      p = wasm_diag_append_str(msg, p, "SYMBOL-TRAP: val=0x");
      p = wasm_diag_append_hex32(msg, p, (uint32_t)symbol);
      p = wasm_diag_append_str(msg, p, " ftag=0x");
      p = wasm_diag_append_hex32(msg, p, (uint32_t)fulltag_of(symbol));
      if (fulltag_of(symbol) == fulltag_misc) {
        p = wasm_diag_append_str(msg, p, " hdr=0x");
        p = wasm_diag_append_hex32(msg, p, (uint32_t)header_of(symbol));
        p = wasm_diag_append_str(msg, p, " subtag=0x");
        p = wasm_diag_append_hex32(msg, p, (uint32_t)header_subtag(header_of(symbol)));
      }
      msg[p++] = '\n';
      wasm_host_log(msg, p);
    }
    wasm_debug_dump_state("symbol-trap");
    wasm_subprims_trap();
  }
  return (lispsymbol *)ptr_from_lispobj(untag(symbol));
}

static inline signed_natural
wasm_positive_fixnum_or_trap(LispObj value)
{
  signed_natural count = wasm_unbox_fixnum_or_trap(value);
  if (count <= 0) {
    wasm_subprims_trap();
  }
  return count;
}

static inline int
wasm_fixnum_fit_u32(uint32_t val)
{
  uint32_t max_fixnum = (1u << (nbits_in_word - fixnum_shift - 1)) - 1u;
  return val <= max_fixnum;
}

static inline int64_t
wasm_fixnum_min_i64(void)
{
  return -(1LL << (nbits_in_word - fixnum_shift - 1));
}

static inline int64_t
wasm_fixnum_max_i64(void)
{
  return (1LL << (nbits_in_word - fixnum_shift - 1)) - 1;
}

static inline int
wasm_fixnum_fits_i64(int64_t value)
{
  return (value >= wasm_fixnum_min_i64()) && (value <= wasm_fixnum_max_i64());
}

static inline LispObj
wasm_box_i64_prefer_fixnum(TCR *tcr, int64_t value)
{
  if (wasm_fixnum_fits_i64(value)) {
    return box_fixnum((signed_natural)value);
  }
  return wasm_box_signed_64(tcr, value);
}

static LispObj
wasm_alloc_bignum_or_trap(TCR *tcr, signed_natural digits, uint32_t **data_out)
{
  LispObj obj = wasm_misc_alloc(tcr, subtag_bignum, digits);
  if (obj == (LispObj)nil_value) {
    wasm_subprims_trap();
  }
  if (data_out != NULL) {
    *data_out = (uint32_t *)((BytePtr)obj + misc_data_offset);
  }
  return obj;
}

static int
wasm_bignum_info(LispObj obj, signed_natural *count_out, uint32_t **digits_out)
{
  if (fulltag_of(obj) != fulltag_misc) {
    return 0;
  }
  LispObj header = header_of(obj);
  if (header_subtag(header) != subtag_bignum) {
    return 0;
  }
  signed_natural count = header_element_count(header);
  if (count < 0) {
    return 0;
  }
  if (count_out != NULL) {
    *count_out = count;
  }
  if (digits_out != NULL) {
    *digits_out = (uint32_t *)((BytePtr)obj + misc_data_offset);
  }
  return 1;
}

static LispObj
wasm_box_u32_or_trap(TCR *tcr, uint32_t value)
{
  if (wasm_fixnum_fit_u32(value)) {
    return box_fixnum((signed_natural)value);
  }

  uint32_t *digits = NULL;
  if (value & 0x80000000u) {
    LispObj obj = wasm_alloc_bignum_or_trap(tcr, 2, &digits);
    digits[0] = value;
    digits[1] = 0;
    return obj;
  }

  LispObj obj = wasm_alloc_bignum_or_trap(tcr, 1, &digits);
  digits[0] = value;
  return obj;
}

static uint32_t
wasm_unbox_u32_or_trap(TCR *tcr, LispObj value)
{
  if (tag_of(value) == tag_fixnum) {
    int32_t sval = (int32_t)unbox_fixnum(value);
    if (sval < 0) {
      wasm_subprims_trap();
    }
    return (uint32_t)sval;
  }

  signed_natural count = 0;
  uint32_t *digits = NULL;
  if (!wasm_bignum_info(value, &count, &digits)) {
    wasm_signal_wrong_type(tcr, value, wasm_type_signed_byte(tcr, 64));
    return 0;
  }

  if (count == 1) {
    uint32_t v = digits[0];
    if (v & 0x80000000u) {
      wasm_subprims_trap();
    }
    return v;
  }

  if (count == 2) {
    if (digits[1] != 0) {
      wasm_subprims_trap();
    }
    return digits[0];
  }

  wasm_subprims_trap();
  return 0;
}

static int32_t
wasm_unbox_s32_or_trap(TCR *tcr, LispObj value)
{
  if (tag_of(value) == tag_fixnum) {
    return (int32_t)unbox_fixnum(value);
  }

  signed_natural count = 0;
  uint32_t *digits = NULL;
  if (!wasm_bignum_info(value, &count, &digits) || count != 1) {
    wasm_signal_wrong_type(tcr, value, wasm_type_signed_byte(tcr, 32));
    return 0;
  }
  return (int32_t)digits[0];
}

static int
wasm_try_unbox_u32(LispObj value, uint32_t *out)
{
  if (tag_of(value) == tag_fixnum) {
    int32_t sval = (int32_t)unbox_fixnum(value);
    if (sval < 0) {
      return 0;
    }
    if (out != NULL) {
      *out = (uint32_t)sval;
    }
    return 1;
  }

  signed_natural count = 0;
  uint32_t *digits = NULL;
  if (!wasm_bignum_info(value, &count, &digits)) {
    return 0;
  }

  if (count == 1) {
    uint32_t v = digits[0];
    if (v & 0x80000000u) {
      return 0;
    }
    if (out != NULL) {
      *out = v;
    }
    return 1;
  }

  if (count == 2) {
    if (digits[1] != 0) {
      return 0;
    }
    if (out != NULL) {
      *out = digits[0];
    }
    return 1;
  }

  return 0;
}

static int
wasm_try_unbox_s32(LispObj value, int32_t *out)
{
  if (tag_of(value) == tag_fixnum) {
    if (out != NULL) {
      *out = (int32_t)unbox_fixnum(value);
    }
    return 1;
  }

  signed_natural count = 0;
  uint32_t *digits = NULL;
  if (!wasm_bignum_info(value, &count, &digits) || count != 1) {
    return 0;
  }
  if (out != NULL) {
    *out = (int32_t)digits[0];
  }
  return 1;
}

#define WASM_ELEMENT_COUNT(type) ((signed_natural)((sizeof(type) / sizeof(LispObj)) - 1))

enum {
  WASM_ARRAYH_RANK_CELL = 0,
  WASM_ARRAYH_PHYSSIZE_CELL = 1,
  WASM_ARRAYH_DATA_VECTOR_CELL = 2,
  WASM_ARRAYH_DISPLACEMENT_CELL = 3,
  WASM_ARRAYH_FLAGS_CELL = 4,
  WASM_ARRAYH_DIM0_CELL = 5
};

static LispObj
wasm_alloc_single_float_from_bits(TCR *tcr, uint32_t bits)
{
  LispObj obj = wasm_misc_alloc(tcr, subtag_single_float, WASM_ELEMENT_COUNT(single_float));
  if (obj == (LispObj)nil_value) {
    wasm_subprims_trap();
  }
  single_float *sf = (single_float *)ptr_from_lispobj(untag(obj));
  sf->value = (LispObj)bits;
  return obj;
}

static LispObj
wasm_alloc_double_float_from_bits(TCR *tcr, uint64_t bits)
{
  LispObj obj = wasm_misc_alloc(tcr, subtag_double_float, WASM_ELEMENT_COUNT(double_float));
  if (obj == (LispObj)nil_value) {
    wasm_subprims_trap();
  }
  double_float *df = (double_float *)ptr_from_lispobj(untag(obj));
  df->value_low = (LispObj)(uint32_t)bits;
  df->value_high = (LispObj)(uint32_t)(bits >> 32);
  return obj;
}

static LispObj
wasm_alloc_complex_single_float_from_bits(TCR *tcr, uint32_t real_bits, uint32_t imag_bits)
{
  LispObj obj = wasm_misc_alloc(tcr, subtag_complex_single_float, WASM_ELEMENT_COUNT(complex_single_float));
  if (obj == (LispObj)nil_value) {
    wasm_subprims_trap();
  }
  complex_single_float *cf = (complex_single_float *)ptr_from_lispobj(untag(obj));
  cf->realpart = (LispObj)real_bits;
  cf->imagpart = (LispObj)imag_bits;
  return obj;
}

static LispObj
wasm_alloc_complex_double_float_from_bits(TCR *tcr, uint64_t real_bits, uint64_t imag_bits)
{
  LispObj obj = wasm_misc_alloc(tcr, subtag_complex_double_float, WASM_ELEMENT_COUNT(complex_double_float));
  if (obj == (LispObj)nil_value) {
    wasm_subprims_trap();
  }
  complex_double_float *cf = (complex_double_float *)ptr_from_lispobj(untag(obj));
  cf->realpart_low = (LispObj)(uint32_t)real_bits;
  cf->realpart_high = (LispObj)(uint32_t)(real_bits >> 32);
  cf->imagpart_low = (LispObj)(uint32_t)imag_bits;
  cf->imagpart_high = (LispObj)(uint32_t)(imag_bits >> 32);
  return obj;
}

static LispObj
wasm_misc_ref_imm_dispatch(TCR *tcr, LispObj obj, unsigned subtag, signed_natural index)
{
  if ((subtag & fulltagmask) != fulltag_immheader) {
    wasm_subprims_trap();
  }

  switch (subtag) {
    case subtag_fixnum_vector: {
      int32_t *data = (int32_t *)((BytePtr)obj + misc_data_offset);
      return box_fixnum((signed_natural)data[index]);
    }
    case subtag_simple_base_string: {
      lisp_char_code *data = (lisp_char_code *)((BytePtr)obj + misc_data_offset);
      lisp_char_code code = data[index];
      return (LispObj)((code << charcode_shift) | subtag_character);
    }
    case subtag_u32_vector: {
      uint32_t *data = (uint32_t *)((BytePtr)obj + misc_data_offset);
      return wasm_box_u32_or_trap(tcr, data[index]);
    }
    case subtag_s32_vector: {
      int32_t *data = (int32_t *)((BytePtr)obj + misc_data_offset);
      return wasm_box_i64_prefer_fixnum(tcr, (int64_t)data[index]);
    }
    case subtag_u16_vector: {
      uint16_t *data = (uint16_t *)((BytePtr)obj + misc_data_offset);
      return box_fixnum((signed_natural)data[index]);
    }
    case subtag_s16_vector: {
      int16_t *data = (int16_t *)((BytePtr)obj + misc_data_offset);
      return box_fixnum((signed_natural)data[index]);
    }
    case subtag_u8_vector: {
      uint8_t *data = (uint8_t *)((BytePtr)obj + misc_data_offset);
      return box_fixnum((signed_natural)data[index]);
    }
    case subtag_s8_vector: {
      int8_t *data = (int8_t *)((BytePtr)obj + misc_data_offset);
      return box_fixnum((signed_natural)data[index]);
    }
    case subtag_single_float_vector: {
      float *data = (float *)((BytePtr)obj + misc_data_offset);
      float value = data[index];
      uint32_t bits = 0;
      memcpy(&bits, &value, sizeof(bits));
      return wasm_alloc_single_float_from_bits(tcr, bits);
    }
    case subtag_double_float_vector: {
      double *data = (double *)((BytePtr)obj + misc_dfloat_offset);
      double value = data[index];
      uint64_t bits = 0;
      memcpy(&bits, &value, sizeof(bits));
      return wasm_alloc_double_float_from_bits(tcr, bits);
    }
    case subtag_complex_single_float_vector: {
      float *data = (float *)((BytePtr)obj + misc_dfloat_offset);
      float real = data[index * 2];
      float imag = data[index * 2 + 1];
      uint32_t real_bits = 0;
      uint32_t imag_bits = 0;
      memcpy(&real_bits, &real, sizeof(real_bits));
      memcpy(&imag_bits, &imag, sizeof(imag_bits));
      return wasm_alloc_complex_single_float_from_bits(tcr, real_bits, imag_bits);
    }
    case subtag_complex_double_float_vector: {
      double *data = (double *)((BytePtr)obj + misc_dfloat_offset);
      double real = data[index * 2];
      double imag = data[index * 2 + 1];
      uint64_t real_bits = 0;
      uint64_t imag_bits = 0;
      memcpy(&real_bits, &real, sizeof(real_bits));
      memcpy(&imag_bits, &imag, sizeof(imag_bits));
      return wasm_alloc_complex_double_float_from_bits(tcr, real_bits, imag_bits);
    }
    case subtag_bit_vector: {
      uint32_t *data = (uint32_t *)((BytePtr)obj + misc_data_offset);
      uint32_t bit = (data[(uint32_t)index >> 5] >> ((uint32_t)index & 31u)) & 1u;
      return box_fixnum((signed_natural)bit);
    }
    case subtag_bignum: {
      /* Bignum digits are 32-bit values returned as fixnums with modular
         wrapping, matching ARM32 convention.  All CCL bignum arithmetic
         (%bignum-ref, bignum-minusp, logbitp) expects uvref to return
         fixnums for bignum elements. */
      int32_t *data = (int32_t *)((BytePtr)obj + misc_data_offset);
      return box_fixnum((signed_natural)data[index]);
    }
    default:
      break;
  }

  {
    uint32_t *data = (uint32_t *)((BytePtr)obj + misc_data_offset);
    return wasm_box_u32_or_trap(tcr, data[index]);
  }
}

static LispObj
wasm_misc_ref_dispatch(TCR *tcr, LispObj obj, signed_natural index)
{
  if (fulltag_of(obj) != fulltag_misc) {
    wasm_subprims_trap();
  }

  LispObj header = header_of(obj);
  unsigned subtag = header_subtag(header);
  signed_natural count = header_element_count(header);
  if ((natural)index >= (natural)count) {
    wasm_subprims_trap();
  }

  if ((subtag & fulltagmask) == fulltag_nodeheader) {
    LispObj *data = (LispObj *)((BytePtr)obj + misc_data_offset);
    return data[index];
  }

  return wasm_misc_ref_imm_dispatch(tcr, obj, subtag, index);
}

static void
wasm_misc_set_imm_dispatch(TCR *tcr, LispObj obj, unsigned subtag, signed_natural index, LispObj value)
{
  if ((subtag & fulltagmask) != fulltag_immheader) {
    wasm_subprims_trap();
  }

  switch (subtag) {
    case subtag_fixnum_vector: {
      if (tag_of(value) != tag_fixnum) {
        wasm_signal_wrong_type(tcr, value, wasm_symbol_fixnum());
        return;
      }
      int32_t *data = (int32_t *)((BytePtr)obj + misc_data_offset);
      data[index] = (int32_t)unbox_fixnum(value);
      return;
    }
    case subtag_simple_base_string: {
      if ((value & subtagmask) != subtag_character) {
        wasm_signal_wrong_type(tcr, value, wasm_symbol_character());
        return;
      }
      lisp_char_code code = (lisp_char_code)((uint32_t)value >> charcode_shift);
      lisp_char_code *data = (lisp_char_code *)((BytePtr)obj + misc_data_offset);
      data[index] = code;
      return;
    }
    case subtag_u32_vector: {
      uint32_t *data = (uint32_t *)((BytePtr)obj + misc_data_offset);
      uint32_t uval = 0;
      if (!wasm_try_unbox_u32(value, &uval)) {
        wasm_signal_wrong_type(tcr, value, wasm_type_unsigned_byte(tcr, 32));
        return;
      }
      data[index] = uval;
      return;
    }
    case subtag_s32_vector: {
      int32_t *data = (int32_t *)((BytePtr)obj + misc_data_offset);
      int32_t sval = 0;
      if (!wasm_try_unbox_s32(value, &sval)) {
        wasm_signal_wrong_type(tcr, value, wasm_type_signed_byte(tcr, 32));
        return;
      }
      data[index] = sval;
      return;
    }
    case subtag_u16_vector: {
      uint32_t uval = 0;
      if (!wasm_try_unbox_u32(value, &uval) || uval > 0xffffu) {
        wasm_signal_wrong_type(tcr, value, wasm_type_unsigned_byte(tcr, 16));
        return;
      }
      uint16_t *data = (uint16_t *)((BytePtr)obj + misc_data_offset);
      data[index] = (uint16_t)uval;
      return;
    }
    case subtag_s16_vector: {
      int32_t sval = 0;
      if (!wasm_try_unbox_s32(value, &sval) || sval < -32768 || sval > 32767) {
        wasm_signal_wrong_type(tcr, value, wasm_type_signed_byte(tcr, 16));
        return;
      }
      int16_t *data = (int16_t *)((BytePtr)obj + misc_data_offset);
      data[index] = (int16_t)sval;
      return;
    }
    case subtag_u8_vector: {
      uint32_t uval = 0;
      if (!wasm_try_unbox_u32(value, &uval) || uval > 0xffu) {
        wasm_signal_wrong_type(tcr, value, wasm_type_unsigned_byte(tcr, 8));
        return;
      }
      uint8_t *data = (uint8_t *)((BytePtr)obj + misc_data_offset);
      data[index] = (uint8_t)uval;
      return;
    }
    case subtag_s8_vector: {
      int32_t sval = 0;
      if (!wasm_try_unbox_s32(value, &sval) || sval < -128 || sval > 127) {
        wasm_signal_wrong_type(tcr, value, wasm_type_signed_byte(tcr, 8));
        return;
      }
      int8_t *data = (int8_t *)((BytePtr)obj + misc_data_offset);
      data[index] = (int8_t)sval;
      return;
    }
    case subtag_single_float_vector: {
      if (fulltag_of(value) != fulltag_misc || header_subtag(header_of(value)) != subtag_single_float) {
        wasm_signal_wrong_type(tcr, value, wasm_symbol_single_float());
        return;
      }
      single_float *sf = (single_float *)ptr_from_lispobj(untag(value));
      uint32_t bits = (uint32_t)sf->value;
      float fval = 0.0f;
      memcpy(&fval, &bits, sizeof(fval));
      float *data = (float *)((BytePtr)obj + misc_data_offset);
      data[index] = fval;
      return;
    }
    case subtag_double_float_vector: {
      if (fulltag_of(value) != fulltag_misc || header_subtag(header_of(value)) != subtag_double_float) {
        wasm_signal_wrong_type(tcr, value, wasm_symbol_double_float());
        return;
      }
      double_float *df = (double_float *)ptr_from_lispobj(untag(value));
      uint64_t bits = ((uint64_t)(uint32_t)df->value_high << 32) | (uint32_t)df->value_low;
      double dval = 0.0;
      memcpy(&dval, &bits, sizeof(dval));
      double *data = (double *)((BytePtr)obj + misc_dfloat_offset);
      data[index] = dval;
      return;
    }
    case subtag_complex_single_float_vector: {
      if (fulltag_of(value) != fulltag_misc || header_subtag(header_of(value)) != subtag_complex_single_float) {
        wasm_signal_wrong_type(tcr, value, wasm_type_complex(tcr, wasm_symbol_single_float()));
        return;
      }
      complex_single_float *cf = (complex_single_float *)ptr_from_lispobj(untag(value));
      uint32_t real_bits = (uint32_t)cf->realpart;
      uint32_t imag_bits = (uint32_t)cf->imagpart;
      float real = 0.0f;
      float imag = 0.0f;
      memcpy(&real, &real_bits, sizeof(real));
      memcpy(&imag, &imag_bits, sizeof(imag));
      float *data = (float *)((BytePtr)obj + misc_dfloat_offset);
      data[index * 2] = real;
      data[index * 2 + 1] = imag;
      return;
    }
    case subtag_complex_double_float_vector: {
      if (fulltag_of(value) != fulltag_misc || header_subtag(header_of(value)) != subtag_complex_double_float) {
        wasm_signal_wrong_type(tcr, value, wasm_type_complex(tcr, wasm_symbol_double_float()));
        return;
      }
      complex_double_float *cf = (complex_double_float *)ptr_from_lispobj(untag(value));
      uint64_t real_bits = ((uint64_t)(uint32_t)cf->realpart_high << 32) | (uint32_t)cf->realpart_low;
      uint64_t imag_bits = ((uint64_t)(uint32_t)cf->imagpart_high << 32) | (uint32_t)cf->imagpart_low;
      double real = 0.0;
      double imag = 0.0;
      memcpy(&real, &real_bits, sizeof(real));
      memcpy(&imag, &imag_bits, sizeof(imag));
      double *data = (double *)((BytePtr)obj + misc_dfloat_offset);
      data[index * 2] = real;
      data[index * 2 + 1] = imag;
      return;
    }
    case subtag_bit_vector: {
      uint32_t bit = 0;
      if (!wasm_try_unbox_u32(value, &bit) || (bit != 0 && bit != 1)) {
        wasm_signal_wrong_type(tcr, value, wasm_symbol_bit());
        return;
      }
      uint32_t *data = (uint32_t *)((BytePtr)obj + misc_data_offset);
      uint32_t word_index = (uint32_t)index >> 5;
      uint32_t mask = 1u << ((uint32_t)index & 31u);
      if (bit != 0) {
        data[word_index] |= mask;
      } else {
        data[word_index] &= ~mask;
      }
      return;
    }
    default:
      break;
  }

  {
    uint32_t *data = (uint32_t *)((BytePtr)obj + misc_data_offset);
    uint32_t uval = 0;
    if (!wasm_try_unbox_u32(value, &uval)) {
      wasm_signal_wrong_type(tcr, value, wasm_type_unsigned_byte(tcr, 32));
      return;
    }
    data[index] = uval;
  }
}

static void
wasm_misc_set_dispatch(TCR *tcr, LispObj obj, signed_natural index, LispObj value)
{
  if (fulltag_of(obj) != fulltag_misc) {
    wasm_subprims_trap();
  }

  LispObj header = header_of(obj);
  unsigned subtag = header_subtag(header);
  signed_natural count = header_element_count(header);
  if ((natural)index >= (natural)count) {
    wasm_subprims_trap();
  }

  if ((subtag & fulltagmask) == fulltag_nodeheader) {
    LispObj *data = (LispObj *)((BytePtr)obj + misc_data_offset);
    data[index] = value;
    return;
  }

  wasm_misc_set_imm_dispatch(tcr, obj, subtag, index, value);
}

static inline LispObj *
wasm_arrayH_data_or_trap(LispObj array, signed_natural expected_rank)
{
  if (fulltag_of(array) != fulltag_misc) {
    wasm_subprims_trap();
  }
  if (header_subtag(header_of(array)) != subtag_arrayH) {
    wasm_subprims_trap();
  }

  LispObj *data = (LispObj *)((BytePtr)array + misc_data_offset);
  signed_natural rank = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_RANK_CELL]);
  if (rank != expected_rank) {
    wasm_subprims_trap();
  }
  return data;
}

static LispObj
wasm_array_data_vector_or_trap(LispObj array, signed_natural *index)
{
  LispObj current = array;
  for (;;) {
    if (fulltag_of(current) != fulltag_misc) {
      wasm_subprims_trap();
    }

    LispObj header = header_of(current);
    unsigned subtag = header_subtag(header);
    if (subtag != subtag_arrayH && subtag != subtag_vectorH) {
      return current;
    }

    LispObj *data = (LispObj *)((BytePtr)current + misc_data_offset);
    signed_natural displacement = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_DISPLACEMENT_CELL]);
    *index += displacement;
    current = data[WASM_ARRAYH_DATA_VECTOR_CELL];
  }
}

static int
wasm_list_is_proper(LispObj list)
{
  if (list == (LispObj)nil_value) {
    return 1;
  }

  LispObj fast = list;
  LispObj slow = list;

  for (;;) {
    if (tag_of(fast) != tag_list) {
      return 0;
    }
    cons *fast_cell = (cons *)ptr_from_lispobj(untag(fast));
    fast = fast_cell->cdr;
    if (fast == (LispObj)nil_value) {
      return 1;
    }
    if (tag_of(fast) != tag_list) {
      return 0;
    }
    fast_cell = (cons *)ptr_from_lispobj(untag(fast));
    fast = fast_cell->cdr;
    if (tag_of(slow) != tag_list) {
      return 0;
    }
    cons *slow_cell = (cons *)ptr_from_lispobj(untag(slow));
    slow = slow_cell->cdr;
    if (fast == slow) {
      return 0;
    }
  }
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
  wasm_set_nargs_count(tcr, 0);
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
    wasm_set_nargs_count(tcr, 0);
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
  wasm_set_nargs_count(tcr, total);
  tcr->save_tsp = NULL;
}

static void
wasm_sync_arg_regs_from_vsp(TCR *tcr)
{
  signed_natural count = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, nargs));
  if (count <= 0) {
    return;
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;

  /* ARM convention: arg_z = last (rightmost) parameter.
     Args are pushed in source order: first arg deepest, last arg on TOS.
     TOS = vsp_ptr[0] = last arg → arg_z. */
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
  special_binding *current_binding = tcr->db_link;
  LispObj *binding_slots = tcr->tlb_pointer;

  if (binding_slots == NULL) {
    wasm_subprims_trap();
  }

  while (current_binding != target) {
    if (current_binding == NULL) {
      wasm_subprims_trap();
    }
    LispObj symidx = (LispObj)current_binding->sym;
    LispObj value = current_binding->value;
    current_binding = current_binding->link;
    binding_slots[unbox_fixnum(symidx)] = value;
  }
  tcr->db_link = target;
}

static inline wasm_catch_frame *
wasm_alloc_catch_frame(void)
{
  BytePtr stack_ptr = (BytePtr)wasm_get_cstack_pointer();
  size_t bytes = sizeof(wasm_catch_frame);
  stack_ptr -= bytes;
  wasm_set_cstack_pointer(stack_ptr);
  return (wasm_catch_frame *)stack_ptr;
}

static inline void
wasm_free_catch_frame(wasm_catch_frame *cf)
{
  BytePtr stack_ptr = (BytePtr)cf;
  stack_ptr += sizeof(wasm_catch_frame);
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

  wasm_catch_frame *cf = wasm_alloc_catch_frame();
  memset(cf, 0, sizeof(*cf));

  cf->header = WASM_CATCH_FRAME_HEADER;
  cf->link = tcr->catch_top;
  cf->mvflag = 0;
  cf->catch_tag = wasm_reg(tcr, arg_z);
  cf->db_link = (LispObj)tcr->db_link;
  cf->xframe = (LispObj)tcr->xframe;
  cf->last_lisp_frame = (LispObj)tcr->last_lisp_frame;
  cf->nfp = (LispObj)tcr->nfp;
  cf->save_vsp = wasm_reg(tcr, vsp);
  cf->cleanup_entry = 0;
  cf->save_spill_sp = (LispObj)tcr->wasm_spill_sp;

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

  wasm_catch_frame *cf = wasm_alloc_catch_frame();
  memset(cf, 0, sizeof(*cf));

  cf->header = WASM_CATCH_FRAME_HEADER;
  cf->link = tcr->catch_top;
  cf->mvflag = box_fixnum(1);
  cf->catch_tag = wasm_reg(tcr, arg_z);
  cf->db_link = (LispObj)tcr->db_link;
  cf->xframe = (LispObj)tcr->xframe;
  cf->last_lisp_frame = (LispObj)tcr->last_lisp_frame;
  cf->nfp = (LispObj)tcr->nfp;
  cf->save_vsp = wasm_reg(tcr, vsp);
  cf->cleanup_entry = 0;
  cf->save_spill_sp = (LispObj)tcr->wasm_spill_sp;

  tcr->catch_top = ptr_to_lispobj((BytePtr)cf + fulltag_misc);
}

__attribute__((used, visibility("default"), export_name("_SPmkunwind")))
void
_SPmkunwind(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  /* For WASM, callers may provide a cleanup entrypoint (subprim index fixnum)
   * in imm0. If absent or malformed, we leave it as 0 and trap on unwind.
   */
  LispObj cleanup_entry = wasm_reg(tcr, imm0);
  if (tag_of(cleanup_entry) != tag_fixnum) {
    cleanup_entry = 0;
  }

  wasm_set_reg(tcr, arg_z, (LispObj)unbound_marker);
  _SPmkcatchmv();

  LispObj target_link = tcr->catch_top;
  if (target_link == 0 || target_link == (LispObj)nil_value) {
    wasm_subprims_trap();
  }
  wasm_catch_frame *cf = (wasm_catch_frame *)ptr_from_lispobj(untag(target_link));
  cf->cleanup_entry = cleanup_entry;
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
  /* Single-value unwind: arg_z is authoritative per ABI; don't clobber from VSP. */
  wasm_set_nargs_count(tcr, 1);

  while (frame_count-- > 0) {
    LispObj target_link = tcr->catch_top;
    if (target_link == 0 || target_link == (LispObj)nil_value) {
      wasm_subprims_trap();
    }

    wasm_catch_frame *cf = (wasm_catch_frame *)ptr_from_lispobj(untag(target_link));
    special_binding *target_db = (special_binding *)cf->db_link;

    tcr->catch_top = cf->link;
    tcr->xframe = (xframe_list *)cf->xframe;
    tcr->last_lisp_frame = (natural)cf->last_lisp_frame;
    tcr->nfp = (void *)cf->nfp;

    if (tcr->db_link != target_db) {
      wasm_unbind_to(tcr, target_db);
    }

    if (cf->catch_tag == (LispObj)unbound_marker) {
      LispObj cleanup = cf->cleanup_entry;
      if (tag_of(cleanup) != tag_fixnum) {
        wasm_subprims_trap();
      }

      signed_natural count = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, nargs));
      if (count < 0) {
        wasm_subprims_trap();
      }

      if (count > 0) {
        wasm_push_value_set(tcr);
      }

      LispObj *saved_stack_ptr = (LispObj *)cf->save_vsp;
      if (saved_stack_ptr == NULL) {
        wasm_subprims_trap();
      }
      tcr->save_vsp = saved_stack_ptr;
      wasm_set_reg(tcr, vsp, (LispObj)saved_stack_ptr);

      if (cf->save_spill_sp != 0) {
        tcr->wasm_spill_sp = (LispObj *)cf->save_spill_sp;
      }

      tcr->unwinding = 0;
      wasm_call_subprim_fixnum(cleanup);
      if (wasm_pending_throw_p(tcr)) {
        tcr->save_tsp = NULL;
        return;
      }
      tcr->unwinding = 1;

      if (count > 0) {
        wasm_recover_value_sets(tcr);
      }

      wasm_free_catch_frame(cf);
      continue;
    }

    if (frame_count == 0) {
      LispObj *saved_stack_ptr = (LispObj *)cf->save_vsp;
      if (saved_stack_ptr == NULL) {
        wasm_subprims_trap();
      }
      wasm_set_reg(tcr, vsp, (LispObj)saved_stack_ptr);
      tcr->save_vsp = saved_stack_ptr;

      if (cf->save_spill_sp != 0) {
        tcr->wasm_spill_sp = (LispObj *)cf->save_spill_sp;
      }
    }

    wasm_free_catch_frame(cf);
  }

  tcr->unwinding = 0;
  wasm_set_pending_throw(tcr, box_fixnum(11));  /* nthrow1value: no matching catch */
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
    LispObj target_link = tcr->catch_top;
    if (target_link == 0 || target_link == (LispObj)nil_value) {
      wasm_subprims_trap();
    }

    wasm_catch_frame *cf = (wasm_catch_frame *)ptr_from_lispobj(untag(target_link));
    special_binding *target_db = (special_binding *)cf->db_link;

    tcr->catch_top = cf->link;
    tcr->xframe = (xframe_list *)cf->xframe;
    tcr->last_lisp_frame = (natural)cf->last_lisp_frame;
    tcr->nfp = (void *)cf->nfp;

    if (tcr->db_link != target_db) {
      wasm_unbind_to(tcr, target_db);
    }

    if (cf->catch_tag == (LispObj)unbound_marker) {
      LispObj cleanup = cf->cleanup_entry;
      if (tag_of(cleanup) != tag_fixnum) {
        wasm_subprims_trap();
      }

      signed_natural count = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, nargs));
      if (count < 0) {
        wasm_subprims_trap();
      }

      if (count > 0) {
        wasm_push_value_set(tcr);
      }

      LispObj *saved_stack_ptr = (LispObj *)cf->save_vsp;
      if (saved_stack_ptr == NULL) {
        wasm_subprims_trap();
      }
      tcr->save_vsp = saved_stack_ptr;
      wasm_set_reg(tcr, vsp, (LispObj)saved_stack_ptr);

      if (cf->save_spill_sp != 0) {
        tcr->wasm_spill_sp = (LispObj *)cf->save_spill_sp;
      }

      tcr->unwinding = 0;
      wasm_call_subprim_fixnum(cleanup);
      if (wasm_pending_throw_p(tcr)) {
        tcr->save_tsp = NULL;
        return;
      }
      tcr->unwinding = 1;

      if (count > 0) {
        wasm_recover_value_sets(tcr);
      }

      wasm_free_catch_frame(cf);
      continue;
    }

    if (frame_count == 0) {
      signed_natural count = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, nargs));
      if (count < 0) {
        wasm_subprims_trap();
      }
      LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
      if (stack_ptr == NULL) {
        wasm_subprims_trap();
      }
      LispObj *src = stack_ptr;
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
      tcr->save_vsp = dest;
      wasm_sync_arg_regs_from_vsp(tcr);

      if (cf->save_spill_sp != 0) {
        tcr->wasm_spill_sp = (LispObj *)cf->save_spill_sp;
      }
    }

    wasm_free_catch_frame(cf);
  }

  tcr->unwinding = 0;
  wasm_set_pending_throw(tcr, box_fixnum(12));  /* nthrowvalues: no matching catch */
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

void _SPstack_misc_alloc(void);
void _SPstack_cons_rest_arg(void);

/* ============================================================
 * Funcall Stuck Detector
 * ============================================================
 * Catches infinite loops, recursion, and mutual recursion in the
 * funcall dispatch path.  Works by maintaining a ring buffer of
 * the last FUNCALL_RING_SIZE entry indices.  Every
 * FUNCALL_CHECK_INTERVAL calls, counts the number of unique
 * entries in the ring buffer.  If there are <= FUNCALL_MAX_UNIQUE
 * unique entries, the system is stuck (repeating a tiny set of
 * functions endlessly).  Dumps the repeating pattern and traps.
 *
 * Catches:
 *   - Infinite recursion (1-2 unique entries)
 *   - Mutual recursion  (2-3 unique entries)
 *   - Infinite loops calling a few functions (3-4 unique entries)
 *
 * Normal code calls many different functions, so the ring buffer
 * always has >4 unique entries during correct operation.
 *
 * Performance: one array write + counter increment per funcall
 * (~2 ns), uniqueness check every 1M calls (~50 ns amortized).
 *
 * See doc/wasm/debugging.md for usage documentation.
 * ============================================================ */
#define FUNCALL_RING_SIZE 32
#define FUNCALL_CHECK_INTERVAL 1000000  /* restored: builtin_length/seqtype recursion fixed */
#define FUNCALL_MAX_UNIQUE 4            /* <=4 unique entries = stuck */

static uint32_t funcall_ring[FUNCALL_RING_SIZE];
static uint32_t funcall_ring_pos = 0;
static uint64_t funcall_total = 0;

static void funcall_stuck_record(TCR *tcr, uint32_t entry_index) {
  /* Skip recording during error unwinding — pending_throw causes the
     funcall dispatcher to short-circuit every call, which looks like a
     stuck loop but is actually cooperative unwinding to the C caller. */
  if (tcr != NULL && tcr->wasm_pending_throw) return;

  funcall_ring[funcall_ring_pos & (FUNCALL_RING_SIZE - 1)] = entry_index;
  funcall_ring_pos++;
  funcall_total++;
  if ((funcall_total % FUNCALL_CHECK_INTERVAL) == 0) {
    /* Count unique entries in ring buffer */
    uint32_t seen[FUNCALL_MAX_UNIQUE + 1];
    int n_unique = 0;
    for (int i = 0; i < FUNCALL_RING_SIZE; i++) {
      uint32_t e = funcall_ring[i];
      int found = 0;
      for (int j = 0; j < n_unique; j++) {
        if (seen[j] == e) { found = 1; break; }
      }
      if (!found) {
        if (n_unique <= FUNCALL_MAX_UNIQUE) seen[n_unique] = e;
        n_unique++;
        if (n_unique > FUNCALL_MAX_UNIQUE) return;  /* not stuck */
      }
    }
    /* n_unique <= FUNCALL_MAX_UNIQUE → stuck: dump and trap */
    {
      static const char hx[] = "0123456789abcdef";
      char msg[256];
      int p = 0;
      const char *pfx = "STUCK after ";
      while (*pfx) msg[p++] = *pfx++;
      /* print funcall_total / 1000 as decimal + 'k' */
      { uint64_t k = funcall_total / 1000;
        char dbuf[20]; int dlen = 0;
        do { dbuf[dlen++] = '0' + (char)(k % 10); k /= 10; } while (k > 0);
        for (int i = dlen-1; i >= 0; i--) msg[p++] = dbuf[i]; }
      msg[p++] = 'k';
      msg[p++] = ' ';
      msg[p++] = 'c'; msg[p++] = 'a'; msg[p++] = 'l';
      msg[p++] = 'l'; msg[p++] = 's'; msg[p++] = ',';
      msg[p++] = ' ';
      /* print unique entries as hex */
      for (int i = 0; i < n_unique; i++) {
        if (i > 0) { msg[p++] = ' '; }
        for (int b = 3; b >= 0; b--)
          msg[p++] = hx[(seen[i] >> (b*4)) & 0xf];
      }
      msg[p++] = '\n';
      wasm_host_log(msg, (unsigned)p);
      /* Set pending_throw instead of trapping.  This breaks the stuck loop
         gracefully — the funcall dispatcher will short-circuit, and the C
         caller (e.g. wasm_drain_cold_load_list) can recover. */
      if (tcr != NULL) {
        tcr->wasm_pending_throw = box_fixnum(16);
      } else {
        wasm_subprims_trap();  /* no TCR = can't recover, hard trap */
      }
    }
  }
}

static void
wasm_signal_funcall_error(TCR *tcr, signed_natural errnum, LispObj name)
{
  wasm_debug_dump_state("funcall-error");

  /* Diagnostic: identify the object type that failed funcall validation */
  {
    static const char hx[] = "0123456789abcdef";
    char d[160]; int p = 0;
    const char *pfx = "funcall-err: code=";
    while (*pfx) d[p++] = *pfx++;
    { uint32_t ev = (uint32_t)errnum; char ebuf[4]; int elen = 0;
      do { ebuf[elen++] = '0' + (char)(ev % 10); ev /= 10; } while (ev > 0);
      for (int i = elen-1; i >= 0; i--) d[p++] = ebuf[i]; }
    pfx = " name=0x";
    while (*pfx) d[p++] = *pfx++;
    for (int b = 7; b >= 0; b--) d[p++] = hx[(name >> (b*4)) & 0xf];
    pfx = " tag=";
    while (*pfx) d[p++] = *pfx++;
    d[p++] = '0' + (char)(fulltag_of(name));
    if (fulltag_of(name) == fulltag_misc && name != (LispObj)nil_value) {
      LispObj hdr = header_of(name);
      unsigned st = header_subtag(hdr);
      pfx = " hdr=0x";
      while (*pfx) d[p++] = *pfx++;
      for (int b = 7; b >= 0; b--) d[p++] = hx[(hdr >> (b*4)) & 0xf];
      pfx = " subtag=";
      while (*pfx) d[p++] = *pfx++;
      { unsigned sv = st; char sbuf[4]; int slen = 0;
        do { sbuf[slen++] = '0' + (char)(sv % 10); sv /= 10; } while (sv > 0);
        for (int i = slen-1; i >= 0; i--) d[p++] = sbuf[i]; }
      if (st == subtag_symbol) {
        lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(name));
        LispObj fc = sym->fcell;
        pfx = " fcell=0x";
        while (*pfx) d[p++] = *pfx++;
        for (int b = 7; b >= 0; b--) d[p++] = hx[(fc >> (b*4)) & 0xf];
        /* Print symbol name (pname) — CCL ARM/WASM uses 32-bit chars */
        LispObj pn = sym->pname;
        if (fulltag_of(pn) == fulltag_misc && pn != (LispObj)nil_value) {
          LispObj phdr = header_of(pn);
          unsigned pst = header_subtag(phdr);
          if (pst == subtag_simple_base_string) {
            unsigned plen = (unsigned)header_element_count(phdr);
            if (plen > 60) plen = 60;
            uint32_t *pchars = (uint32_t *)(untag(pn) + sizeof(LispObj));
            pfx = " sym=";
            while (*pfx) d[p++] = *pfx++;
            for (unsigned ci = 0; ci < plen && p < 148; ci++)
              d[p++] = (char)(pchars[ci] & 0x7f);
          }
        }
      }
    }
    /* Also print caller info (Rfn) */
    {
      LispObj rfn = wasm_reg(tcr, Rfn);
      pfx = " Rfn=0x";
      while (*pfx) d[p++] = *pfx++;
      for (int b = 7; b >= 0; b--) d[p++] = hx[(rfn >> (b*4)) & 0xf];
      if (fulltag_of(rfn) == fulltag_misc && rfn != (LispObj)nil_value) {
        LispObj rfn_hdr = header_of(rfn);
        unsigned rfn_st = header_subtag(rfn_hdr);
        if (rfn_st == subtag_function || rfn_st == subtag_pseudofunction) {
          LispObj eidx = deref(rfn, 1);
          pfx = " e=";
          while (*pfx) d[p++] = *pfx++;
          if (tag_of(eidx) == tag_fixnum) {
            uint32_t idx = (uint32_t)unbox_fixnum(eidx);
            char ibuf[10]; int ilen = 0;
            do { ibuf[ilen++] = '0' + (char)(idx % 10); idx /= 10; } while (idx > 0);
            for (int i = ilen-1; i >= 0; i--) d[p++] = ibuf[i];
          } else {
            pfx = "?";
            while (*pfx) d[p++] = *pfx++;
          }
        }
      }
    }
    d[p++] = '\n';
    wasm_host_log(d, (unsigned)p);
  }

  wasm_set_reg(tcr, arg_y, box_fixnum(errnum));
  wasm_set_reg(tcr, arg_z, name);
  wasm_set_nargs_count(tcr, 2);
  _SPksignalerr();
}

static uint32_t wasm_funcall_depth = 0;

/* Code_vector self-tail-call trampoline state.
   wasm_cv_trampoline_active: entry_index+1 of the entry currently in a
   trampoline loop, or 0 if none.  Nested trampolines save/restore this.
   wasm_cv_restart: set to 1 by a nested code_vector self-call to signal
   the trampoline loop to re-dispatch instead of recursing. */
static uint32_t wasm_cv_trampoline_active = 0;
static int wasm_cv_restart = 0;

static void
wasm_call_function_value(TCR *tcr, LispObj fn_value, LispObj name)
{
  wasm_funcall_depth++;
  if (wasm_funcall_depth > 800) {
    /* Approaching WASM native stack limit.  Set pending_throw instead of
       letting the JS runtime crash with RangeError.
       Build entire diagnostic into one buffer — at depth 800+ the JS call
       stack is near exhaustion so multiple wasm_host_log calls may fail. */
    {
      /* Show first 20 + last 20 entries to reveal how recursion starts. */
      char buf[600]; int p = 0;
      const char *s = "funcall depth exceeded\ncallstack first 20: ";
      while (*s) buf[p++] = *s++;
      uint32_t limit = wasm_funcall_depth < WASM_DIAG_CALLSTACK_MAX
                        ? wasm_funcall_depth : WASM_DIAG_CALLSTACK_MAX;
      uint32_t first_end = limit < 20 ? limit : 20;
      for (uint32_t i = 0; i < first_end && p < 560; i++) {
        uint32_t e = wasm_diag_callstack[i];
        char ibuf[10]; int ilen = 0;
        do { ibuf[ilen++] = '0' + (char)(e % 10); e /= 10; } while (e > 0);
        for (int j = ilen-1; j >= 0; j--) buf[p++] = ibuf[j];
        buf[p++] = ' ';
      }
      s = "\ncallstack last 20: ";
      while (*s) buf[p++] = *s++;
      uint32_t last_start = limit > 20 ? limit - 20 : 0;
      for (uint32_t i = last_start; i < limit && p < 580; i++) {
        uint32_t e = wasm_diag_callstack[i];
        char ibuf[10]; int ilen = 0;
        do { ibuf[ilen++] = '0' + (char)(e % 10); e /= 10; } while (e > 0);
        for (int j = ilen-1; j >= 0; j--) buf[p++] = ibuf[j];
        buf[p++] = ' ';
      }
      buf[p++] = '\n';
      wasm_host_log(buf, (unsigned)p);
    }
    wasm_funcall_depth = 0;
    tcr->wasm_pending_throw = 1;
    return;
  }

  /* Catch funcall-nil early: deref(nil, 1) reads nil_value+3 which is
     0x00000000 (tag_fixnum), so nil passes the entry-index check below.
     Detect and report it explicitly instead of calling entry 0. */
  if (fn_value == (LispObj)nil_value) {
    static unsigned funcall_nil_count = 0;
    funcall_nil_count++;
    if (funcall_nil_count <= 5) {
      static const char hx[] = "0123456789abcdef";
      char d[120]; int p = 0;
      const char *pfx = "FUNCALL-NIL: caller_nfn=0x";
      while (*pfx) d[p++] = *pfx++;
      LispObj caller_rfn = wasm_reg(tcr, Rfn);
      for (int b = 7; b >= 0; b--) d[p++] = hx[(caller_rfn >> (b*4)) & 0xf];
      /* Try to get caller's entry index */
      if (fulltag_of(caller_rfn) == fulltag_misc &&
          caller_rfn != (LispObj)nil_value) {
        LispObj caller_entry = deref(caller_rfn, 1);
        if (tag_of(caller_entry) == tag_fixnum) {
          uint32_t idx = (uint32_t)unbox_fixnum(caller_entry);
          pfx = " e=";
          while (*pfx) d[p++] = *pfx++;
          char ibuf[10]; int ilen = 0;
          do { ibuf[ilen++] = '0' + (char)(idx % 10); idx /= 10; } while (idx > 0);
          for (int i = ilen-1; i >= 0; i--) d[p++] = ibuf[i];
        }
      }
      pfx = " nargs=";
      while (*pfx) d[p++] = *pfx++;
      { uint32_t na = (uint32_t)wasm_reg(tcr, nargs);
        char nbuf[10]; int nlen = 0;
        do { nbuf[nlen++] = '0' + (char)(na % 10); na /= 10; } while (na > 0);
        for (int i = nlen-1; i >= 0; i--) d[p++] = nbuf[i]; }
      pfx = " name=0x";
      while (*pfx) d[p++] = *pfx++;
      for (int b = 7; b >= 0; b--) d[p++] = hx[(name >> (b*4)) & 0xf];
      /* Print name symbol if available */
      if (fulltag_of(name) == fulltag_misc && name != (LispObj)nil_value &&
          header_subtag(header_of(name)) == subtag_symbol) {
        lispsymbol *nsym = (lispsymbol *)ptr_from_lispobj(untag(name));
        LispObj pn = nsym->pname;
        if (fulltag_of(pn) == fulltag_misc && pn != (LispObj)nil_value &&
            header_subtag(header_of(pn)) == subtag_simple_base_string) {
          unsigned plen = header_element_count(header_of(pn));
          if (plen > 40) plen = 40;
          uint32_t *chars = (uint32_t *)(untag(pn) + sizeof(LispObj));
          pfx = " sym=";
          while (*pfx) d[p++] = *pfx++;
          for (unsigned ci = 0; ci < plen && p < 110; ci++)
            d[p++] = (char)(chars[ci] & 0x7f);
        }
      }
      d[p++] = '\n';
      wasm_host_log(d, (unsigned)p);
    }
    wasm_signal_funcall_error(tcr, WASM_XNOTFUN, name);
    wasm_funcall_depth--;
    return;
  }

  if (wasm_reg(tcr, nfn) != fn_value) {
    wasm_set_reg(tcr, nfn, fn_value);
  }
  if (wasm_reg(tcr, Rfn) != fn_value) {
    wasm_set_reg(tcr, Rfn, fn_value);
  }

  LispObj entry = deref(fn_value, 1);
  if (tag_of(entry) != tag_fixnum) {
    wasm_signal_funcall_error(tcr, WASM_XNOTFUN, name);
    wasm_funcall_depth--;
    return;
  }

  {
    uint32_t entry_index = (uint32_t)unbox_fixnum(entry);
    uint32_t caller_entry = WASM_DIAG_ENTRY_UNKNOWN;
    uint32_t depth = wasm_funcall_depth;
    if (depth > 0 && (depth - 1) < WASM_DIAG_CALLSTACK_MAX) {
      wasm_diag_callstack[depth - 1] = entry_index;
    }
    if (depth > 1 && (depth - 2) < WASM_DIAG_CALLSTACK_MAX) {
      caller_entry = wasm_diag_callstack[depth - 2];
    }
    wasm_diag_log_watch_call(tcr, caller_entry, entry_index, depth);

    uint32_t entry_call_abi = wasm_prepare_entry_call(entry_index);
    switch (entry_call_abi) {
    case WASM_ENTRY_CALL_ABI_UNARY_I32: {
      funcall_stuck_record(tcr, entry_index);
      { uint32_t tl = wasm_get_trace_funcall();
        if (tl >= 1) {
          static const char hx[] = "0123456789abcdef";
          char d[60]; int p = 0;
          d[p++]='U'; d[p++]='1'; d[p++]=' ';
          for (int b=7;b>=0;b--) d[p++]=hx[(entry_index>>(b*4))&0xf];
          d[p++]='\n'; wasm_host_log(d,(unsigned)p);
        }
      }
      LispObj result;
      LispObj raw_nargs = wasm_reg(tcr, nargs);
      if (raw_nargs != box_fixnum(1)) {
        signed_natural nargs_count =
          (tag_of(raw_nargs) == tag_fixnum) ? unbox_fixnum(raw_nargs) : 0;
        wasm_signal_funcall_error(tcr,
                                  (nargs_count < 1) ? WASM_XCALLTOOFEW : WASM_XCALLTOOMANY,
                                  name);
        wasm_funcall_depth--;
        return;
      }
      result = wasm_call_entry_index_unary_i32(entry_index, wasm_reg(tcr, arg_z));
      if (!wasm_pending_throw_p(tcr)) {
        wasm_set_reg(tcr, arg_z, result);
        wasm_set_nargs_count(tcr, 1);
      }
      break;
    }
    case WASM_ENTRY_CALL_ABI_BINARY_I32: {
      funcall_stuck_record(tcr, entry_index);
      { uint32_t tl = wasm_get_trace_funcall();
        if (tl >= 1) {
          static const char hx[] = "0123456789abcdef";
          char d[60]; int p = 0;
          d[p++]='B'; d[p++]='2'; d[p++]=' ';
          for (int b=7;b>=0;b--) d[p++]=hx[(entry_index>>(b*4))&0xf];
          d[p++]='\n'; wasm_host_log(d,(unsigned)p);
        }
      }
      LispObj result;
      LispObj raw_nargs = wasm_reg(tcr, nargs);
      if (raw_nargs != box_fixnum(2)) {
        signed_natural nargs_count =
          (tag_of(raw_nargs) == tag_fixnum) ? unbox_fixnum(raw_nargs) : 0;
        wasm_signal_funcall_error(tcr,
                                  (nargs_count < 2) ? WASM_XCALLTOOFEW : WASM_XCALLTOOMANY,
                                  name);
        wasm_funcall_depth--;
        return;
      }
      /* ARM convention: arg_y = first formal, arg_z = last formal.
         Typed entry: param0 = first formal, param1 = last formal. */
      result = wasm_call_entry_index_binary_i32(entry_index,
                                                wasm_reg(tcr, arg_y),
                                                wasm_reg(tcr, arg_z));
      if (!wasm_pending_throw_p(tcr)) {
        wasm_set_reg(tcr, arg_z, result);
        wasm_set_nargs_count(tcr, 1);
      }
      break;
    }
    case WASM_ENTRY_CALL_ABI_LEGACY:
    default: {
      funcall_stuck_record(tcr, entry_index);
      uint32_t trace_level = wasm_get_trace_funcall();
      if (trace_level >= 1) {
        static const char hx[] = "0123456789abcdef";
        char d[120];
        int p = 0;
        /* Level 1: entry index */
        d[p++]='C'; d[p++]='A'; d[p++]='L'; d[p++]='L'; d[p++]=' ';
        for (int b=7;b>=0;b--) d[p++]=hx[(entry_index>>(b*4))&0xf];
        if (trace_level >= 2) {
          /* Level 2: also print arg registers */
          d[p++]=' '; d[p++]='z'; d[p++]='=';
          { LispObj v = wasm_reg(tcr, arg_z);
            for (int b=7;b>=0;b--) d[p++]=hx[(v>>(b*4))&0xf]; }
          d[p++]=' '; d[p++]='y'; d[p++]='=';
          { LispObj v = wasm_reg(tcr, arg_y);
            for (int b=7;b>=0;b--) d[p++]=hx[(v>>(b*4))&0xf]; }
          d[p++]=' '; d[p++]='n'; d[p++]='=';
          { LispObj v = wasm_reg(tcr, nargs);
            for (int b=7;b>=0;b--) d[p++]=hx[(v>>(b*4))&0xf]; }
        }
        d[p++]='\n';
        wasm_host_log(d, (unsigned)p);
      }
      wasm_call_entry_index(entry_index);
      break;
    }
    }
    wasm_diag_log_watch_return(tcr, entry_index, depth);
  }
  wasm_funcall_depth--;
}

static void
wasm_call_lisp_function(TCR *tcr, LispObj fn_value)
{
  wasm_call_function_or_symbol(tcr, fn_value);
}

static void
wasm_call_function_or_symbol(TCR *tcr, LispObj fn_value)
{
  LispObj name = fn_value;
  if (fn_value == nrs_UDF.vcell) {
    wasm_signal_funcall_error(tcr, WASM_XFUNBND, name);
    return;
  }
  if (fn_value == (LispObj)nil_value || fulltag_of(fn_value) != fulltag_misc) {
    wasm_signal_funcall_error(tcr, WASM_XNOTFUN, name);
    return;
  }
  LispObj header = header_of(fn_value);
  unsigned subtag = header_subtag(header);
  if (subtag == subtag_symbol) {
    lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(fn_value));
    fn_value = sym->fcell;
    if (fn_value == nrs_UDF.vcell) {
      wasm_signal_funcall_error(tcr, WASM_XFUNBND, name);
      return;
    }
    if (fulltag_of(fn_value) != fulltag_misc) {
      wasm_signal_funcall_error(tcr, WASM_XNOTFUN, name);
      return;
    }
    header = header_of(fn_value);
    subtag = header_subtag(header);
  }
  if (subtag == subtag_code_vector) {
    /* WASM workaround: on ARM, code_vectors are executable machine code —
       jumping to one is a GOTO (no stack growth).  Code_vectors appear as
       funcall targets in two cases:
         (a) Self-tail-call: a function jumps to its own code_vector.
         (b) Closure dispatch: _SPcall_closure sets nfn to the inner
             function's code_vector and calls _SPfuncall.
       On WASM, code_vectors are 1-element stubs with just the entry index.
       We dispatch the entry directly (nfn is left as-is — the caller set
       it up correctly).  A trampoline loop handles self-calls: nested
       dispatches of the same entry signal restart instead of recursing. */
    LispObj cv_entry = deref(fn_value, 1);
    if (tag_of(cv_entry) != tag_fixnum) {
      wasm_signal_funcall_error(tcr, WASM_XNOTFUN, name);
      return;
    }
    uint32_t cv_entry_index = (uint32_t)unbox_fixnum(cv_entry);

    /* If a trampoline for this exact entry is already running,
       signal restart instead of recursing (self-tail-call). */
    if (wasm_cv_trampoline_active == cv_entry_index + 1) {
      wasm_cv_restart = 1;
      return;
    }

    /* Dispatch entry directly in a trampoline loop.
       Do NOT modify nfn/Rfn — the caller already set them up
       (e.g. _SPcall_closure sets nfn to the target code_vector). */
    {
      uint32_t saved_trampoline = wasm_cv_trampoline_active;
      wasm_cv_trampoline_active = cv_entry_index + 1;
      wasm_funcall_depth++;
      if (wasm_funcall_depth > 800) {
        wasm_funcall_depth = 0;
        wasm_cv_trampoline_active = saved_trampoline;
        tcr->wasm_pending_throw = 1;
        return;
      }
      funcall_stuck_record(tcr, cv_entry_index);
      do {
        wasm_cv_restart = 0;
        wasm_call_entry_index(cv_entry_index);
      } while (wasm_cv_restart && !wasm_pending_throw_p(tcr));
      wasm_cv_trampoline_active = saved_trampoline;
      wasm_funcall_depth--;
    }
    return;
  }
  if (!wasm_function_like_subtag(subtag)) {
    wasm_signal_funcall_error(tcr, WASM_XNOTFUN, name);
    return;
  }
  wasm_call_function_value(tcr, fn_value, name);
}

static inline void
wasm_funcall_value(TCR *tcr, LispObj fn_value)
{
  wasm_sync_arg_regs_from_vsp(tcr);
  wasm_call_function_or_symbol(tcr, fn_value);
}

static inline void
wasm_funcall_nfn(TCR *tcr)
{
  wasm_funcall_value(tcr, wasm_reg(tcr, nfn));
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

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj throw_tag = vsp_ptr[count];

  LispObj catch_top = tcr->catch_top;
  signed_natural frame_count = 0;
  wasm_catch_frame *target = NULL;
  while (catch_top != 0 && catch_top != (LispObj)nil_value) {
    wasm_catch_frame *cf = (wasm_catch_frame *)ptr_from_lispobj(untag(catch_top));
    if (cf->catch_tag == throw_tag) {
      target = cf;
      break;
    }
    catch_top = cf->link;
    frame_count++;
  }

  if (target == NULL) {
    wasm_set_reg(tcr, arg_z, throw_tag);
    wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XNOCTAG));
    wasm_set_nargs_count(tcr, 2);
    _SPksignalerr();
    return;
  }

  if (target->mvflag == 0) {
    if (count == 0) {
      *--vsp_ptr = (LispObj)nil_value;
      wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
      tcr->save_vsp = vsp_ptr;
    } else {
      vsp_ptr = vsp_ptr + (count - 1);
      wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
      tcr->save_vsp = vsp_ptr;
    }
    wasm_set_reg(tcr, arg_z, vsp_ptr[0]);
    wasm_set_nargs_count(tcr, 1);
  } else {
    wasm_sync_arg_regs_from_vsp(tcr);
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

__attribute__((used, visibility("default"), export_name("_SPinteger_sign")))
void
_SPinteger_sign(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj value = wasm_reg(tcr, arg_z);
  if (tag_of(value) == tag_fixnum) {
    wasm_set_reg(tcr, imm0, value);
    return;
  }

  signed_natural count = 0;
  uint32_t *digits = NULL;
  if (!wasm_bignum_info(value, &count, &digits) || count <= 0) {
    wasm_subprims_trap();
  }

  int32_t msd = (int32_t)digits[count - 1];
  wasm_set_reg(tcr, imm0, (LispObj)((msd < 0) ? -1 : 1));
}

__attribute__((used, visibility("default"), export_name("_SPfix_nfn_entrypoint")))
void
_SPfix_nfn_entrypoint(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj fn_value = wasm_reg(tcr, nfn);
  if (fulltag_of(fn_value) != fulltag_misc || header_subtag(header_of(fn_value)) != subtag_function) {
    wasm_subprims_trap();
  }

  LispObj entry = deref(fn_value, 2);
  deref(fn_value, 1) = entry;
  wasm_call_function_value(tcr, fn_value, fn_value);

  if (wasm_pending_throw_p(tcr)) {
    return;
  }
}

__attribute__((used, visibility("default"), export_name("_SPfuncall")))
void
_SPfuncall(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  wasm_funcall_nfn(tcr);
}

/*
 * Tailcall/jump subprims (_SPtfuncallgen, _SPtfuncallslide, _SPjmpsym,
 * _SPtcallsymgen, _SPtcallsymslide, _SPtcallnfngen, _SPtcallnfnslide)
 * are currently implemented as wrappers around shared funcall helper. This is
 * correct but not tail-call optimized (no frame reuse). Rebuilt
 * subprims.wasm. Tests: all-smoke.mjs --no-ui.
 */
__attribute__((used, visibility("default"), export_name("_SPtfuncallgen")))
void
_SPtfuncallgen(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  wasm_funcall_nfn(tcr);
}

__attribute__((used, visibility("default"), export_name("_SPtfuncallslide")))
void
_SPtfuncallslide(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  wasm_funcall_nfn(tcr);
}

__attribute__((used, visibility("default"), export_name("_SPjmpsym")))
void
_SPjmpsym(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  wasm_funcall_value(tcr, wasm_reg(tcr, fname));
}

__attribute__((used, visibility("default"), export_name("_SPtcallsymgen")))
void
_SPtcallsymgen(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  wasm_funcall_value(tcr, wasm_reg(tcr, fname));
}

__attribute__((used, visibility("default"), export_name("_SPtcallsymslide")))
void
_SPtcallsymslide(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  wasm_funcall_value(tcr, wasm_reg(tcr, fname));
}

__attribute__((used, visibility("default"), export_name("_SPtcallnfngen")))
void
_SPtcallnfngen(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  wasm_funcall_nfn(tcr);
}

__attribute__((used, visibility("default"), export_name("_SPtcallnfnslide")))
void
_SPtcallnfnslide(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  wasm_funcall_nfn(tcr);
}

__attribute__((used, visibility("default"), export_name("_SPmvpass")))
void
_SPmvpass(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  wasm_funcall_nfn(tcr);

  if (wasm_pending_throw_p(tcr)) {
    return;
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }
  signed_natural count = unbox_fixnum(raw_nargs);
  if (count <= 0) {
    wasm_set_reg(tcr, arg_z, (LispObj)nil_value);
    return;
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  wasm_set_reg(tcr, arg_z, stack_ptr[0]);
}

__attribute__((used, visibility("default"), export_name("_SPvalues")))
void
_SPvalues(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }

  signed_natural count = unbox_fixnum(raw_nargs);
  if (count <= 0) {
    wasm_set_reg(tcr, arg_z, (LispObj)nil_value);
    return;
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  wasm_set_reg(tcr, arg_z, stack_ptr[0]);
}

__attribute__((used, visibility("default"), export_name("_SPfitvals")))
void
_SPfitvals(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_desired = wasm_reg(tcr, imm0);
  if (tag_of(raw_desired) != tag_fixnum) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }

  signed_natural desired_count = unbox_fixnum(raw_desired);
  signed_natural current_count = unbox_fixnum(raw_nargs);
  if (desired_count < 0 || current_count < 0) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;

  if (desired_count == 0) {
    LispObj *new_vsp = vsp_ptr + current_count;
    wasm_set_reg(tcr, vsp, (LispObj)new_vsp);
    tcr->save_vsp = new_vsp;
    wasm_set_nargs_count(tcr, 0);
    wasm_set_reg(tcr, arg_z, (LispObj)nil_value);
    return;
  }

  if (desired_count == current_count) {
    return;
  }

  if (desired_count < current_count) {
    signed_natural diff = current_count - desired_count;
    LispObj *new_vsp = vsp_ptr + diff;
    memmove(new_vsp, vsp_ptr, (size_t)desired_count * sizeof(LispObj));
    wasm_set_reg(tcr, vsp, (LispObj)new_vsp);
    tcr->save_vsp = new_vsp;
    wasm_set_nargs_count(tcr, desired_count);
    return;
  }

  signed_natural diff = desired_count - current_count;
  LispObj *new_vsp = vsp_ptr - diff;
  memmove(new_vsp, vsp_ptr, (size_t)current_count * sizeof(LispObj));
  for (signed_natural i = current_count; i < desired_count; i++) {
    new_vsp[i] = (LispObj)nil_value;
  }

  wasm_set_reg(tcr, vsp, (LispObj)new_vsp);
  tcr->save_vsp = new_vsp;
  wasm_set_nargs_count(tcr, desired_count);
  if (current_count == 0) {
    wasm_set_reg(tcr, arg_z, (LispObj)nil_value);
  }
}

__attribute__((used, visibility("default"), export_name("_SPnthvalue")))
void
_SPnthvalue(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }

  signed_natural count = unbox_fixnum(raw_nargs);
  if (count < 0) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj raw_index = vsp_ptr[count];
  if (tag_of(raw_index) != tag_fixnum) {
    wasm_subprims_trap();
  }

  signed_natural index = unbox_fixnum(raw_index);
  LispObj result = (LispObj)nil_value;
  if (index >= 0 && index < count) {
    result = vsp_ptr[index];
  }

  LispObj *new_vsp = vsp_ptr + count + 1;
  wasm_set_reg(tcr, vsp, (LispObj)new_vsp);
  tcr->save_vsp = new_vsp;

  wasm_set_reg(tcr, arg_z, result);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPdefault_optional_args")))
void
_SPdefault_optional_args(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }

  LispObj raw_limit = wasm_reg(tcr, imm0);
  if (tag_of(raw_limit) != tag_fixnum) {
    wasm_subprims_trap();
  }

  signed_natural nargs_count = unbox_fixnum(raw_nargs);
  signed_natural limit = unbox_fixnum(raw_limit);
  if (nargs_count < 0 || limit < 0) {
    wasm_subprims_trap();
  }

  wasm_vpush_argregs(tcr);

  if (nargs_count >= limit) {
    return;
  }

  signed_natural missing = limit - nargs_count;
  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  for (signed_natural i = 0; i < missing; i++) {
    *--vsp_ptr = (LispObj)nil_value;
  }

  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
}

__attribute__((used, visibility("default"), export_name("_SPopt_supplied_p")))
void
_SPopt_supplied_p(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }

  LispObj raw_opt = wasm_reg(tcr, imm0);
  if (tag_of(raw_opt) != tag_fixnum) {
    wasm_subprims_trap();
  }

  signed_natural nargs_count = unbox_fixnum(raw_nargs);
  signed_natural opt_count = unbox_fixnum(raw_opt);
  if (nargs_count < 0 || opt_count < 0) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj flag = (LispObj)(nil_value + t_offset);
  for (signed_natural i = 0; i < opt_count; i++) {
    if (i >= nargs_count) {
      flag = (LispObj)nil_value;
    }
    *--vsp_ptr = flag;
  }

  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
}

__attribute__((used, visibility("default"), export_name("_SPheap_rest_arg")))
void
_SPheap_rest_arg(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }
  signed_natural count = unbox_fixnum(raw_nargs);
  if (count < 0) {
    wasm_subprims_trap();
  }

  wasm_vpush_argregs(tcr);

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj list = (LispObj)nil_value;
  for (signed_natural i = 0; i < count; i++) {
    LispObj value = vsp_ptr[0];
    vsp_ptr += 1;
    list = wasm_alloc_cons_or_trap(tcr, value, list);
  }

  *--vsp_ptr = list;
  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
  wasm_set_reg(tcr, arg_z, list);
}

__attribute__((used, visibility("default"), export_name("_SPreq_heap_rest_arg")))
void
_SPreq_heap_rest_arg(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  LispObj raw_required = wasm_reg(tcr, imm0);
  if (tag_of(raw_nargs) != tag_fixnum || tag_of(raw_required) != tag_fixnum) {
    wasm_subprims_trap();
  }
  signed_natural count = unbox_fixnum(raw_nargs) - unbox_fixnum(raw_required);
  if (count < 0) {
    wasm_subprims_trap();
  }

  wasm_vpush_argregs(tcr);

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj list = (LispObj)nil_value;
  for (signed_natural i = 0; i < count; i++) {
    LispObj value = vsp_ptr[0];
    vsp_ptr += 1;
    list = wasm_alloc_cons_or_trap(tcr, value, list);
  }

  *--vsp_ptr = list;
  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
  wasm_set_reg(tcr, arg_z, list);
}

__attribute__((used, visibility("default"), export_name("_SPheap_cons_rest_arg")))
void
_SPheap_cons_rest_arg(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  LispObj raw_required = wasm_reg(tcr, imm0);
  if (tag_of(raw_nargs) != tag_fixnum || tag_of(raw_required) != tag_fixnum) {
    wasm_subprims_trap();
  }
  signed_natural count = unbox_fixnum(raw_nargs) - unbox_fixnum(raw_required);
  if (count < 0) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj list = (LispObj)nil_value;
  for (signed_natural i = 0; i < count; i++) {
    LispObj value = vsp_ptr[0];
    vsp_ptr += 1;
    list = wasm_alloc_cons_or_trap(tcr, value, list);
  }

  *--vsp_ptr = list;
  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
  wasm_set_reg(tcr, arg_z, list);
}

__attribute__((used, visibility("default"), export_name("_SPstack_rest_arg")))
void
_SPstack_rest_arg(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  wasm_set_reg(tcr, imm0, box_fixnum(0));
  wasm_vpush_argregs(tcr);
  _SPstack_cons_rest_arg();
}

__attribute__((used, visibility("default"), export_name("_SPreq_stack_rest_arg")))
void
_SPreq_stack_rest_arg(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  wasm_vpush_argregs(tcr);
  _SPstack_cons_rest_arg();
}

__attribute__((used, visibility("default"), export_name("_SPstack_cons_rest_arg")))
void
_SPstack_cons_rest_arg(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  LispObj raw_required = wasm_reg(tcr, imm0);
  if (tag_of(raw_nargs) != tag_fixnum || tag_of(raw_required) != tag_fixnum) {
    wasm_subprims_trap();
  }
  signed_natural count = unbox_fixnum(raw_nargs) - unbox_fixnum(raw_required);
  if (count < 0) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj list = (LispObj)nil_value;
  if (count == 0) {
    *--vsp_ptr = list;
    wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
    tcr->save_vsp = vsp_ptr;
    wasm_set_reg(tcr, arg_z, list);
    return;
  }

  signed_natural element_count = (count * 2) + 1;
  LispObj *headerp = wasm_cstack_alloc_simple_vector(tcr, element_count);
  if (headerp == NULL) {
    _SPheap_cons_rest_arg();
    return;
  }

  BytePtr cons_base = (BytePtr)headerp + dnode_size;
  for (signed_natural i = 0; i < count; i++) {
    LispObj value = vsp_ptr[0];
    vsp_ptr += 1;

    cons *cell = (cons *)(cons_base + (i * dnode_size));
    cell->car = value;
    cell->cdr = list;
    list = (LispObj)((BytePtr)cell + fulltag_cons);
  }

  *--vsp_ptr = list;
  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
  wasm_set_reg(tcr, arg_z, list);
}

__attribute__((used, visibility("default"), export_name("_SPnvalret")))
void
_SPnvalret(void)
{
  _SPvalues();
}

__attribute__((used, visibility("default"), export_name("_SPmvslide")))
void
_SPmvslide(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }

  signed_natural count = unbox_fixnum(raw_nargs);
  if (count < 0) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  signed_natural byte_delta = (signed_natural)(int32_t)wasm_reg(tcr, imm0);
  BytePtr src_end = (BytePtr)stack_ptr + (count * node_size);
  BytePtr dst_end = src_end + byte_delta;

  for (signed_natural i = 0; i < count; i++) {
    src_end -= node_size;
    dst_end -= node_size;
    *(LispObj *)dst_end = *(LispObj *)src_end;
  }

  LispObj *new_vsp = (LispObj *)dst_end;
  wasm_set_reg(tcr, vsp, (LispObj)new_vsp);
  tcr->save_vsp = new_vsp;
}

__attribute__((used, visibility("default"), export_name("_SPmvpasssym")))
void
_SPmvpasssym(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  wasm_funcall_value(tcr, wasm_reg(tcr, fname));

  if (wasm_pending_throw_p(tcr)) {
    return;
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }
  signed_natural count = unbox_fixnum(raw_nargs);
  if (count <= 0) {
    wasm_set_reg(tcr, arg_z, (LispObj)nil_value);
    return;
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  wasm_set_reg(tcr, arg_z, stack_ptr[0]);
}

static unsigned
wasm_normalize_misc_subtag(uint32_t raw_subtag)
{
  unsigned subtag = (unsigned)raw_subtag;
  unsigned tag = subtag & fulltagmask;
  if (tag == fulltag_nodeheader || tag == fulltag_immheader) {
    return subtag;
  }

  /*
   * Accept x86-64 raw header-tag encodings (ntagbits=4, nodeheader tags 5/6)
   * from cross-target compiled module paths.
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
   * Accept legacy subtype codes (0..31) and canonicalize as node subtags.
   */
  if (raw_subtag <= 31u) {
    return (unsigned)NODE_SUBTAG(raw_subtag);
  }

  return subtag;
}

__attribute__((used, visibility("default"), export_name("_SPmisc_alloc")))
void
_SPmisc_alloc(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    static const char msg[] = "WASM _SPmisc_alloc: null TCR\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    wasm_subprims_trap();
  }

  LispObj subtag_val = wasm_reg(tcr, arg_z);
  if (tag_of(subtag_val) != tag_fixnum) {
    static const char msg[] = "WASM _SPmisc_alloc: subtag not fixnum\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    wasm_subprims_trap();
  }
  LispObj count_val = wasm_reg(tcr, arg_y);
  if (tag_of(count_val) != tag_fixnum) {
    wasm_diag_log_misc_alloc_bad_count(tcr, subtag_val, count_val);
    static const char msg[] = "WASM _SPmisc_alloc: count not fixnum\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    wasm_subprims_trap();
  }

  signed_natural subtag_raw = unbox_fixnum(subtag_val);
  signed_natural count = unbox_fixnum(count_val);
  if (subtag_raw < 0) {
    static const char msg[] = "WASM _SPmisc_alloc: subtag negative\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    wasm_subprims_trap();
  }
  unsigned subtag = wasm_normalize_misc_subtag((uint32_t)subtag_raw);
  if (count < 0 || count > 0xFFFFFF) {
    wasm_set_reg(tcr, arg_x, box_fixnum(WASM_XARRLIMIT));
    wasm_set_nargs_count(tcr, 3);
    _SPksignalerr();
    return;
  }
  unsigned subtag_tag = subtag & fulltagmask;
  if (subtag_tag != fulltag_nodeheader && subtag_tag != fulltag_immheader) {
    static const char msg[] = "WASM _SPmisc_alloc: bad subtag\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    wasm_subprims_trap();
  }

  LispObj obj = wasm_misc_alloc(tcr, subtag, count);
  if (obj == (LispObj)nil_value) {
    static const char msg[] = "WASM _SPmisc_alloc: kernel alloc failed\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    wasm_subprims_trap();
  }
  wasm_set_reg(tcr, arg_z, obj);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPmisc_alloc_init")))
void
_SPmisc_alloc_init(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj initval = wasm_reg(tcr, arg_z);
  LispObj count = wasm_reg(tcr, arg_x);
  LispObj subtag = wasm_reg(tcr, arg_y);

  wasm_set_reg(tcr, arg_z, subtag);
  wasm_set_reg(tcr, arg_y, count);
  _SPmisc_alloc();

  wasm_set_reg(tcr, arg_y, initval);
  wasm_set_nargs_count(tcr, 2);

  LispObj init_sym = wasm_nrs_symbol_lispobj(&nrs_INIT_MISC);
  wasm_call_lisp_function(tcr, init_sym);
}

__attribute__((used, visibility("default"), export_name("_SPstack_misc_alloc_init")))
void
_SPstack_misc_alloc_init(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj initval = wasm_reg(tcr, arg_z);
  LispObj count = wasm_reg(tcr, arg_x);
  LispObj subtag = wasm_reg(tcr, arg_y);

  wasm_set_reg(tcr, arg_y, count);
  wasm_set_reg(tcr, arg_z, subtag);
  _SPstack_misc_alloc();

  wasm_set_reg(tcr, arg_y, initval);
  wasm_set_nargs_count(tcr, 2);

  LispObj init_sym = wasm_nrs_symbol_lispobj(&nrs_INIT_MISC);
  wasm_call_lisp_function(tcr, init_sym);
}

__attribute__((used, visibility("default"), export_name("_SPmisc_ref")))
void
_SPmisc_ref(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj obj = wasm_reg(tcr, arg_z);
  LispObj raw_index = wasm_reg(tcr, arg_y);
  if (tag_of(raw_index) != tag_fixnum) {
    char msg[128];
    unsigned p = 0;
    p = wasm_diag_append_str(msg, p, "misc_ref: bad index tag obj=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)obj);
    p = wasm_diag_append_str(msg, p, " idx=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)raw_index);
    msg[p++] = '\n';
    wasm_host_log(msg, p);
    wasm_subprims_trap();
  }
  signed_natural index = unbox_fixnum(raw_index);
  if (fulltag_of(obj) != fulltag_misc) {
    char msg[128];
    unsigned p = 0;
    p = wasm_diag_append_str(msg, p, "misc_ref: bad tag obj=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)obj);
    p = wasm_diag_append_str(msg, p, " ft=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)fulltag_of(obj));
    p = wasm_diag_append_str(msg, p, " idx=");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)index);
    msg[p++] = '\n';
    wasm_host_log(msg, p);
    wasm_subprims_trap();
  }
  LispObj header = header_of(obj);
  unsigned subtag = header_subtag(header);
  signed_natural count = header_element_count(header);
  if ((natural)index >= (natural)count) {
    char msg[192];
    unsigned p = 0;
    p = wasm_diag_append_str(msg, p, "misc_ref: oob obj=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)obj);
    p = wasm_diag_append_str(msg, p, " idx=");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)index);
    p = wasm_diag_append_str(msg, p, " cnt=");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)count);
    p = wasm_diag_append_str(msg, p, " st=");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)subtag);
    p = wasm_diag_append_str(msg, p, " hdr=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)header);
    msg[p++] = '\n';
    wasm_host_log(msg, p);
    wasm_subprims_trap();
  }

  LispObj value;
  if ((subtag & fulltagmask) == fulltag_nodeheader) {
    LispObj *data = (LispObj *)((BytePtr)obj + misc_data_offset);
    value = data[index];
  } else {
    value = wasm_misc_ref_imm_dispatch(tcr, obj, subtag, index);
  }
  wasm_set_reg(tcr, arg_z, value);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPstack_misc_alloc")))
void
_SPstack_misc_alloc(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_count = wasm_reg(tcr, arg_y);
  if (tag_of(raw_count) != tag_fixnum) {
    wasm_subprims_trap();
  }
  signed_natural count = unbox_fixnum(raw_count);
  if (count < 0) {
    wasm_subprims_trap();
  }

  LispObj raw_subtag = wasm_reg(tcr, arg_z);
  signed_natural subtag_raw = wasm_unbox_fixnum_or_trap(raw_subtag);
  if (subtag_raw < 0) {
    wasm_subprims_trap();
  }
  unsigned subtag = wasm_normalize_misc_subtag((uint32_t)subtag_raw);

  unsigned tag = subtag & fulltagmask;
  size_t bytes = 0;
  if (tag == fulltag_nodeheader) {
    size_t words = 1u + (size_t)count;
    if (words > (SIZE_MAX / node_size)) {
      wasm_subprims_trap();
    }
    bytes = words * node_size;
  } else if (tag == fulltag_immheader) {
    if (!wasm_ivector_total_bytes(subtag, count, &bytes)) {
      wasm_subprims_trap();
    }
  } else {
    wasm_subprims_trap();
  }

  LispObj header = make_header(subtag, count);
  LispObj obj = wasm_cstack_alloc_object(tcr, header, bytes);
  if (obj == (LispObj)nil_value) {
    _SPmisc_alloc();
    return;
  }

  wasm_set_reg(tcr, arg_z, obj);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPgvector")))
void
_SPgvector(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }
  signed_natural count = unbox_fixnum(raw_nargs);
  if (count <= 0) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj raw_subtag = vsp_ptr[count - 1];
  signed_natural subtag_raw = wasm_unbox_fixnum_or_trap(raw_subtag);
  if (subtag_raw < 0) {
    wasm_subprims_trap();
  }
  unsigned subtag = wasm_normalize_misc_subtag((uint32_t)subtag_raw);

  signed_natural element_count = count - 1;
  LispObj obj = wasm_misc_alloc(tcr, subtag, element_count);
  if (obj == (LispObj)nil_value) {
    wasm_subprims_trap();
  }

  LispObj *data = (LispObj *)((BytePtr)obj + misc_data_offset);
  for (signed_natural i = element_count - 1; i >= 0; i--) {
    data[i] = vsp_ptr[0];
    vsp_ptr += 1;
  }

  vsp_ptr += 1; /* discard subtype */
  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
  wasm_set_reg(tcr, arg_z, obj);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPstkgvector")))
void
_SPstkgvector(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }
  signed_natural count = unbox_fixnum(raw_nargs);
  if (count <= 0) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj raw_subtag = vsp_ptr[count - 1];
  signed_natural subtag_raw = wasm_unbox_fixnum_or_trap(raw_subtag);
  if (subtag_raw < 0) {
    wasm_subprims_trap();
  }
  unsigned subtag = wasm_normalize_misc_subtag((uint32_t)subtag_raw);
  if ((subtag & fulltagmask) != fulltag_nodeheader) {
    wasm_subprims_trap();
  }

  signed_natural element_count = count - 1;
  LispObj obj = (LispObj)nil_value;
  LispObj *data = NULL;

  size_t words = 1u + (size_t)element_count;
  if (words > (SIZE_MAX / node_size)) {
    wasm_subprims_trap();
  }
  size_t bytes = words * node_size;

  LispObj header = make_header(subtag, element_count);
  obj = wasm_cstack_alloc_object(tcr, header, bytes);
  if (obj != (LispObj)nil_value) {
    data = (LispObj *)((BytePtr)obj + misc_data_offset);
  } else {
    obj = wasm_misc_alloc(tcr, subtag, element_count);
    if (obj == (LispObj)nil_value) {
      wasm_subprims_trap();
    }
    data = (LispObj *)((BytePtr)obj + misc_data_offset);
  }

  for (signed_natural i = element_count - 1; i >= 0; i--) {
    data[i] = vsp_ptr[0];
    vsp_ptr += 1;
  }

  vsp_ptr += 1; /* discard subtype */
  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
  wasm_set_reg(tcr, arg_z, obj);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPmakestacklist")))
void
_SPmakestacklist(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_count = wasm_reg(tcr, arg_y);
  signed_natural count = wasm_unbox_fixnum_or_trap(raw_count);
  if (count < 0) {
    wasm_subprims_trap();
  }

  LispObj init = wasm_reg(tcr, arg_z);
  if (count == 0) {
    wasm_set_reg(tcr, arg_z, (LispObj)nil_value);
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  signed_natural element_count = (count * 2) + 1;
  LispObj *headerp = wasm_cstack_alloc_simple_vector(tcr, element_count);
  LispObj list = (LispObj)nil_value;

  if (headerp == NULL) {
    for (signed_natural i = 0; i < count; i++) {
      list = wasm_alloc_cons_or_trap(tcr, init, list);
    }
    wasm_set_reg(tcr, arg_z, list);
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  BytePtr cons_base = (BytePtr)headerp + dnode_size;
  for (signed_natural i = 0; i < count; i++) {
    cons *cell = (cons *)(cons_base + (i * dnode_size));
    cell->car = init;
    cell->cdr = list;
    list = (LispObj)((BytePtr)cell + fulltag_cons);
  }

  wasm_set_reg(tcr, arg_z, list);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPmakestackblock")))
void
_SPmakestackblock(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_size = wasm_reg(tcr, arg_z);
  signed_natural count = wasm_unbox_fixnum_or_trap(raw_size);
  if (count < 0) {
    wasm_subprims_trap();
  }

  LispObj mac = wasm_cstack_alloc_macptr_block(tcr, count, 0);
  if (mac != (LispObj)nil_value) {
    wasm_set_reg(tcr, arg_z, mac);
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  LispObj new_gcable = wasm_nrs_symbol_lispobj(&nrs_NEW_GCABLE_PTR);
  wasm_set_nargs_count(tcr, 1);
  wasm_call_lisp_function(tcr, new_gcable);
}

__attribute__((used, visibility("default"), export_name("_SPmakestackblock0")))
void
_SPmakestackblock0(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_size = wasm_reg(tcr, arg_z);
  signed_natural count = wasm_unbox_fixnum_or_trap(raw_size);
  if (count < 0) {
    wasm_subprims_trap();
  }

  LispObj mac = wasm_cstack_alloc_macptr_block(tcr, count, 1);
  if (mac != (LispObj)nil_value) {
    wasm_set_reg(tcr, arg_z, mac);
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  LispObj new_gcable = wasm_nrs_symbol_lispobj(&nrs_NEW_GCABLE_PTR);
  wasm_set_reg(tcr, arg_y, raw_size);
  wasm_set_reg(tcr, arg_z, (LispObj)(nil_value + t_offset));
  wasm_set_nargs_count(tcr, 2);
  wasm_call_lisp_function(tcr, new_gcable);
}

__attribute__((used, visibility("default"), export_name("_SPsubtag_misc_ref")))
void
_SPsubtag_misc_ref(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj subtag_val = wasm_reg(tcr, imm0);
  if (tag_of(subtag_val) != tag_fixnum) {
    char msg[128]; unsigned p = 0;
    p = wasm_diag_append_str(msg, p, "subtag_misc_ref: imm0 not fixnum 0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)subtag_val);
    msg[p++] = '\n'; wasm_host_log(msg, p);
    wasm_debug_dump_state("subtag_misc_ref-bad-imm0");
    wasm_subprims_trap();
  }
  signed_natural subtag = unbox_fixnum(subtag_val);
  if (subtag < 0) {
    char msg[128]; unsigned p = 0;
    p = wasm_diag_append_str(msg, p, "subtag_misc_ref: negative subtag ");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)subtag);
    msg[p++] = '\n'; wasm_host_log(msg, p);
    wasm_subprims_trap();
  }

  LispObj obj = wasm_reg(tcr, arg_z);
  if (fulltag_of(obj) != fulltag_misc) {
    char msg[128]; unsigned p = 0;
    p = wasm_diag_append_str(msg, p, "subtag_misc_ref: arg_z not misc 0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)obj);
    p = wasm_diag_append_str(msg, p, " imm0=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)subtag_val);
    msg[p++] = '\n'; wasm_host_log(msg, p);
    wasm_debug_dump_state("subtag_misc_ref-bad-tag");
    wasm_subprims_trap();
  }
  LispObj header = header_of(obj);
  if (header_subtag(header) != (unsigned)subtag) {
    char msg[160]; unsigned p = 0;
    p = wasm_diag_append_str(msg, p, "subtag_misc_ref: subtag mismatch hdr=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)header);
    p = wasm_diag_append_str(msg, p, " exp=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)subtag);
    p = wasm_diag_append_str(msg, p, " obj=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)obj);
    msg[p++] = '\n'; wasm_host_log(msg, p);
    wasm_debug_dump_state("subtag_misc_ref-mismatch");
    wasm_subprims_trap();
  }
  LispObj idx_val = wasm_reg(tcr, arg_y);
  if (tag_of(idx_val) != tag_fixnum) {
    char msg[128]; unsigned p = 0;
    p = wasm_diag_append_str(msg, p, "subtag_misc_ref: arg_y not fixnum 0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)idx_val);
    msg[p++] = '\n'; wasm_host_log(msg, p);
    wasm_debug_dump_state("subtag_misc_ref-bad-idx");
    wasm_subprims_trap();
  }
  signed_natural index = unbox_fixnum(idx_val);
  signed_natural count = header_element_count(header);
  if ((natural)index >= (natural)count) {
    char msg[160]; unsigned p = 0;
    p = wasm_diag_append_str(msg, p, "subtag_misc_ref: oob idx=");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)index);
    p = wasm_diag_append_str(msg, p, " cnt=");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)count);
    p = wasm_diag_append_str(msg, p, " obj=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)obj);
    p = wasm_diag_append_str(msg, p, " hdr=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)header);
    msg[p++] = '\n'; wasm_host_log(msg, p);
    wasm_debug_dump_state("subtag_misc_ref-oob");
    wasm_subprims_trap();
  }

  LispObj value;
  if (((unsigned)subtag & fulltagmask) == fulltag_nodeheader) {
    LispObj *data = (LispObj *)((BytePtr)obj + misc_data_offset);
    value = data[index];
  } else {
    value = wasm_misc_ref_imm_dispatch(tcr, obj, (unsigned)subtag, index);
  }
  wasm_set_reg(tcr, arg_z, value);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPmisc_set")))
void
_SPmisc_set(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj obj = wasm_reg(tcr, arg_z);
  LispObj raw_index = wasm_reg(tcr, arg_y);
  LispObj value = wasm_reg(tcr, arg_x);

  if (tag_of(raw_index) != tag_fixnum) {
    char msg[256]; unsigned p = 0;
    p = wasm_diag_append_str(msg, p, "misc_set: index not fixnum idx=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)raw_index);
    p = wasm_diag_append_str(msg, p, " obj=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)obj);
    p = wasm_diag_append_str(msg, p, " val=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)value);
    p = wasm_diag_append_str(msg, p, "\nfuncall_ring(last 8): ");
    for (int i = 8; i > 0; i--) {
      uint32_t ri = funcall_ring[(funcall_ring_pos - i) & (FUNCALL_RING_SIZE - 1)];
      p = wasm_diag_append_hex32(msg, p, ri);
      if (i > 1) { msg[p++] = ' '; }
    }
    msg[p++] = '\n'; wasm_host_log(msg, p);
    wasm_debug_dump_state("misc_set-badfixnum");
    wasm_subprims_trap();
  }
  signed_natural index = unbox_fixnum(raw_index);

  if (fulltag_of(obj) != fulltag_misc) {
    char msg[80]; unsigned p = 0;
    p = wasm_diag_append_str(msg, p, "misc_set: obj not misc obj=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)obj);
    p = wasm_diag_append_str(msg, p, " ft=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)fulltag_of(obj));
    msg[p++] = '\n'; wasm_host_log(msg, p);
    wasm_debug_dump_state("misc_set-badobj");
    wasm_subprims_trap();
  }
  LispObj header = header_of(obj);
  unsigned subtag = header_subtag(header);
  signed_natural count = header_element_count(header);
  if ((natural)index >= (natural)count) {
    char msg[128]; unsigned p = 0;
    p = wasm_diag_append_str(msg, p, "misc_set: oob idx=");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)index);
    p = wasm_diag_append_str(msg, p, " count=");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)count);
    p = wasm_diag_append_str(msg, p, " subtag=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)subtag);
    p = wasm_diag_append_str(msg, p, " obj=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)obj);
    msg[p++] = '\n'; wasm_host_log(msg, p);
    wasm_debug_dump_state("misc_set-oob");
    wasm_subprims_trap();
  }

  if ((subtag & fulltagmask) == fulltag_nodeheader) {
    LispObj *data = (LispObj *)((BytePtr)obj + misc_data_offset);
    data[index] = value;
  } else {
    wasm_misc_set_imm_dispatch(tcr, obj, subtag, index, value);
  }
  wasm_set_reg(tcr, arg_z, value);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPsubtag_misc_set")))
void
_SPsubtag_misc_set(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj subtag_val = wasm_reg(tcr, imm0);
  signed_natural subtag = wasm_unbox_fixnum_or_trap(subtag_val);
  if (subtag < 0) {
    wasm_subprims_trap();
  }

  LispObj obj = wasm_reg(tcr, arg_z);
  if (fulltag_of(obj) != fulltag_misc) {
    wasm_subprims_trap();
  }
  LispObj header = header_of(obj);
  if (header_subtag(header) != (unsigned)subtag) {
    wasm_subprims_trap();
  }
  signed_natural index = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, arg_y));
  signed_natural count = header_element_count(header);
  if ((natural)index >= (natural)count) {
    wasm_subprims_trap();
  }
  LispObj value = wasm_reg(tcr, arg_x);
  if (((unsigned)subtag & fulltagmask) == fulltag_nodeheader) {
    LispObj *data = (LispObj *)((BytePtr)obj + misc_data_offset);
    data[index] = value;
  } else {
    wasm_misc_set_imm_dispatch(tcr, obj, (unsigned)subtag, index, value);
  }
  wasm_set_reg(tcr, arg_z, value);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_plus")))
void
_SPbuiltin_plus(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj a = wasm_reg(tcr, arg_z);
  LispObj b = wasm_reg(tcr, arg_y);
  if (tag_of(a) == tag_fixnum && tag_of(b) == tag_fixnum) {
    int64_t sum = (int64_t)unbox_fixnum(a) + (int64_t)unbox_fixnum(b);
    wasm_set_reg(tcr, arg_z, wasm_box_i64_prefer_fixnum(tcr, sum));
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_PLUS, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_minus")))
void
_SPbuiltin_minus(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj a = wasm_reg(tcr, arg_z);
  LispObj b = wasm_reg(tcr, arg_y);
  if (tag_of(a) == tag_fixnum && tag_of(b) == tag_fixnum) {
    int64_t diff = (int64_t)unbox_fixnum(a) - (int64_t)unbox_fixnum(b);
    wasm_set_reg(tcr, arg_z, wasm_box_i64_prefer_fixnum(tcr, diff));
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_MINUS, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_times")))
void
_SPbuiltin_times(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj a = wasm_reg(tcr, arg_z);
  LispObj b = wasm_reg(tcr, arg_y);
  if (tag_of(a) == tag_fixnum && tag_of(b) == tag_fixnum) {
    int64_t prod = (int64_t)unbox_fixnum(a) * (int64_t)unbox_fixnum(b);
    wasm_set_reg(tcr, arg_z, wasm_box_i64_prefer_fixnum(tcr, prod));
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_TIMES, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_div")))
void
_SPbuiltin_div(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_DIV, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_eq")))
void
_SPbuiltin_eq(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj a = wasm_reg(tcr, arg_z);
  LispObj b = wasm_reg(tcr, arg_y);
  /* EQ is pointer identity — works for all types, never needs Lisp fallthrough.
     The previous fixnum-only fast path fell through to wasm_call_builtin for
     non-fixnum objects (symbols, cons, nil, etc.), triggering complex method
     dispatch that crashed during cold-boot before CLOS was initialized. */
  wasm_set_reg(tcr, arg_z, wasm_bool_to_lisp(a == b));
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_ne")))
void
_SPbuiltin_ne(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj a = wasm_reg(tcr, arg_z);
  LispObj b = wasm_reg(tcr, arg_y);
  /* NEQ is pointer non-identity — works for all types, never needs Lisp fallthrough.
     See _SPbuiltin_eq comment for rationale. */
  wasm_set_reg(tcr, arg_z, wasm_bool_to_lisp(a != b));
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_gt")))
void
_SPbuiltin_gt(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj a = wasm_reg(tcr, arg_z);
  LispObj b = wasm_reg(tcr, arg_y);
  if (tag_of(a) == tag_fixnum && tag_of(b) == tag_fixnum) {
    wasm_set_reg(tcr, arg_z, wasm_bool_to_lisp(unbox_fixnum(a) > unbox_fixnum(b)));
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_GT, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_ge")))
void
_SPbuiltin_ge(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj a = wasm_reg(tcr, arg_z);
  LispObj b = wasm_reg(tcr, arg_y);
  if (tag_of(a) == tag_fixnum && tag_of(b) == tag_fixnum) {
    wasm_set_reg(tcr, arg_z, wasm_bool_to_lisp(unbox_fixnum(a) >= unbox_fixnum(b)));
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_GE, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_lt")))
void
_SPbuiltin_lt(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj a = wasm_reg(tcr, arg_z);
  LispObj b = wasm_reg(tcr, arg_y);
  if (tag_of(a) == tag_fixnum && tag_of(b) == tag_fixnum) {
    wasm_set_reg(tcr, arg_z, wasm_bool_to_lisp(unbox_fixnum(a) < unbox_fixnum(b)));
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_LT, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_le")))
void
_SPbuiltin_le(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj a = wasm_reg(tcr, arg_z);
  LispObj b = wasm_reg(tcr, arg_y);
  if (tag_of(a) == tag_fixnum && tag_of(b) == tag_fixnum) {
    wasm_set_reg(tcr, arg_z, wasm_bool_to_lisp(unbox_fixnum(a) <= unbox_fixnum(b)));
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_LE, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_eql")))
void
_SPbuiltin_eql(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj a = wasm_reg(tcr, arg_z);
  LispObj b = wasm_reg(tcr, arg_y);
  if (a == b) {
    wasm_set_reg(tcr, arg_z, wasm_t_value());
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  if (tag_of(a) == tag_fixnum && tag_of(b) == tag_fixnum) {
    wasm_set_reg(tcr, arg_z, (LispObj)nil_value);
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_EQL, 2);
}

/* Inline fast path for LENGTH, ported from ARM _SPbuiltin_length.
 * Handles vectorH, simple vectors, CL ivectors, and proper lists inline.
 * Falls through to Lisp LENGTH only for exotic types (CLOS sequences, etc.).
 * This avoids infinite recursion during cold-boot-init when CLOS is not yet
 * initialized: LENGTH -> SEQUENCE-TYPE -> SYMBOL-NAME -> LENGTH loop.
 */
__attribute__((used, visibility("default"), export_name("_SPbuiltin_length")))
void
_SPbuiltin_length(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj obj = wasm_reg(tcr, arg_z);
  unsigned typecode;

  /* extract_typecode: for misc-tagged objects, get subtag from header;
   * for everything else, use the 2-bit tag directly. */
  if (tag_of(obj) == tag_misc) {
    typecode = header_subtag(header_of(obj));
  } else {
    typecode = tag_of(obj);
  }

  /* Array header (vectorH) — return logical size field (already a fixnum) */
  if (typecode == subtag_vectorH) {
    LispObj logsize = deref(obj, 1);  /* vectorH.logsize: first data slot */
    wasm_set_reg(tcr, arg_z, logsize);
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  /* Simple vector — return element count from header */
  if (typecode == subtag_simple_vector) {
    LispObj header = header_of(obj);
    wasm_set_reg(tcr, arg_z, box_fixnum(header_element_count(header)));
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  /* CL ivector types (strings, bit-vectors, typed arrays) */
  if ((typecode & fulltagmask) == fulltag_immheader &&
      typecode >= min_cl_ivector_subtag) {
    LispObj header = header_of(obj);
    wasm_set_reg(tcr, arg_z, box_fixnum(header_element_count(header)));
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  /* List — tortoise-and-hare algorithm (Floyd's cycle detection) */
  if (typecode == tag_list) {
    LispObj fast = obj;
    LispObj slow = obj;
    signed_natural count = -1;

    for (;;) {
      count++;
      if (fast == (LispObj)nil_value) {
        /* End of proper list — return count as fixnum */
        wasm_set_reg(tcr, arg_z, box_fixnum(count));
        wasm_set_nargs_count(tcr, 1);
        return;
      }
      if (tag_of(fast) != tag_list) {
        break;  /* Dotted list — fall through to Lisp */
      }
      /* Advance fast pointer */
      cons *fast_cell = (cons *)ptr_from_lispobj(untag(fast));
      fast = fast_cell->cdr;
      /* Advance slow pointer every other step */
      if (count & 1) {
        cons *slow_cell = (cons *)ptr_from_lispobj(untag(slow));
        slow = slow_cell->cdr;
        if (slow == fast) {
          break;  /* Circular list — fall through to Lisp */
        }
      }
    }
  }

  /* Fall through to Lisp builtin for other types (CLOS, dotted/circular lists) */
  wasm_call_builtin(tcr, WASM_BUILTIN_LENGTH, 1);
}

/* Inline fast path for SEQUENCE-TYPE, ported from ARM _SPbuiltin_seqtype.
 * Returns NIL for any vector type, T for lists.
 * Falls through to Lisp only for exotic types (CLOS sequences).
 * Same cold-boot-init recursion avoidance as _SPbuiltin_length.
 */
__attribute__((used, visibility("default"), export_name("_SPbuiltin_seqtype")))
void
_SPbuiltin_seqtype(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj obj = wasm_reg(tcr, arg_z);
  unsigned typecode;

  if (tag_of(obj) == tag_misc) {
    typecode = header_subtag(header_of(obj));
  } else {
    typecode = tag_of(obj);
  }

  /* Any vector type → return NIL (meaning "vector/array sequence") */
  if (typecode == subtag_vectorH ||
      typecode == subtag_simple_vector ||
      ((typecode & fulltagmask) == fulltag_immheader &&
       typecode >= min_cl_ivector_subtag)) {
    wasm_set_reg(tcr, arg_z, (LispObj)nil_value);
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  /* List → return T (meaning "list sequence") */
  if (typecode == tag_list) {
    wasm_set_reg(tcr, arg_z, wasm_t_value());
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  /* Fall through to Lisp for other types (CLOS sequences, non-sequences) */
  wasm_call_builtin(tcr, WASM_BUILTIN_SEQTYPE, 1);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_assq")))
void
_SPbuiltin_assq(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_ASSQ, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_memq")))
void
_SPbuiltin_memq(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_MEMQ, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_logbitp")))
void
_SPbuiltin_logbitp(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj index_val = wasm_reg(tcr, arg_z);
  LispObj value = wasm_reg(tcr, arg_y);
  if (tag_of(index_val) == tag_fixnum && tag_of(value) == tag_fixnum) {
    signed_natural index = unbox_fixnum(index_val);
    signed_natural limit = nbits_in_word - fixnum_shift;
    if (index >= 0 && index < limit) {
      uint32_t bits = (uint32_t)unbox_fixnum(value);
      int set = (bits >> (uint32_t)index) & 1u;
      wasm_set_reg(tcr, arg_z, wasm_bool_to_lisp(set));
      wasm_set_nargs_count(tcr, 1);
      return;
    }
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_LOGBITP, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_logior")))
void
_SPbuiltin_logior(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj a = wasm_reg(tcr, arg_z);
  LispObj b = wasm_reg(tcr, arg_y);
  if (tag_of(a) == tag_fixnum && tag_of(b) == tag_fixnum) {
    signed_natural result = unbox_fixnum(a) | unbox_fixnum(b);
    wasm_set_reg(tcr, arg_z, box_fixnum(result));
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_LOGIOR, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_logand")))
void
_SPbuiltin_logand(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj a = wasm_reg(tcr, arg_z);
  LispObj b = wasm_reg(tcr, arg_y);
  if (tag_of(a) == tag_fixnum && tag_of(b) == tag_fixnum) {
    signed_natural result = unbox_fixnum(a) & unbox_fixnum(b);
    wasm_set_reg(tcr, arg_z, box_fixnum(result));
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_LOGAND, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_ash")))
void
_SPbuiltin_ash(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj value = wasm_reg(tcr, arg_z);
  LispObj shift_val = wasm_reg(tcr, arg_y);
  if (tag_of(value) == tag_fixnum && tag_of(shift_val) == tag_fixnum) {
    signed_natural shift = unbox_fixnum(shift_val);
    signed_natural sval = unbox_fixnum(value);

    if (shift == 0) {
      wasm_set_reg(tcr, arg_z, value);
      wasm_set_nargs_count(tcr, 1);
      return;
    }

    if (shift < 0) {
      signed_natural sh = -shift;
      if (sh >= nbits_in_word) {
        sh = nbits_in_word - 1;
      }
      signed_natural result = sval >> sh;
      wasm_set_reg(tcr, arg_z, box_fixnum(result));
      wasm_set_nargs_count(tcr, 1);
      return;
    }

    if (shift > 32) {
      {
        char msg[120]; unsigned p = 0;
        p = wasm_diag_append_str(msg, p, "ASH-FALLBACK shift>32 z=0x");
        p = wasm_diag_append_hex32(msg, p, (uint32_t)value);
        p = wasm_diag_append_str(msg, p, " y=0x");
        p = wasm_diag_append_hex32(msg, p, (uint32_t)shift_val);
        msg[p++] = '\n';
        wasm_host_log(msg, p);
      }
      wasm_call_builtin(tcr, WASM_BUILTIN_ASH, 2);
      return;
    }

    int64_t result = (int64_t)sval << shift;
    wasm_set_reg(tcr, arg_z, wasm_box_i64_prefer_fixnum(tcr, result));
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  {
    char msg[160]; unsigned p = 0;
    p = wasm_diag_append_str(msg, p, "ASH-FALLBACK nonfixnum z=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)value);
    p = wasm_diag_append_str(msg, p, " y=0x");
    p = wasm_diag_append_hex32(msg, p, (uint32_t)shift_val);
    p = wasm_diag_append_str(msg, p, " zt=");
    p = wasm_diag_append_hex32(msg, p, tag_of(value));
    p = wasm_diag_append_str(msg, p, " yt=");
    p = wasm_diag_append_hex32(msg, p, tag_of(shift_val));
    msg[p++] = '\n';
    wasm_host_log(msg, p);
  }
  wasm_call_builtin(tcr, WASM_BUILTIN_ASH, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_negate")))
void
_SPbuiltin_negate(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj value = wasm_reg(tcr, arg_z);
  if (tag_of(value) == tag_fixnum) {
    int64_t result = -(int64_t)unbox_fixnum(value);
    wasm_set_reg(tcr, arg_z, wasm_box_i64_prefer_fixnum(tcr, result));
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_NEGATE, 1);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_logxor")))
void
_SPbuiltin_logxor(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj a = wasm_reg(tcr, arg_z);
  LispObj b = wasm_reg(tcr, arg_y);
  if (tag_of(a) == tag_fixnum && tag_of(b) == tag_fixnum) {
    signed_natural result = unbox_fixnum(a) ^ unbox_fixnum(b);
    wasm_set_reg(tcr, arg_z, box_fixnum(result));
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_LOGXOR, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_aref1")))
void
_SPbuiltin_aref1(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj obj = wasm_reg(tcr, arg_z);
  LispObj index_val = wasm_reg(tcr, arg_y);
  if (tag_of(index_val) == tag_fixnum && fulltag_of(obj) == fulltag_misc) {
    signed_natural index = unbox_fixnum(index_val);
    LispObj header = header_of(obj);
    unsigned subtag = header_subtag(header);
    signed_natural count = header_element_count(header);
    if ((natural)index >= (natural)count) {
      wasm_subprims_trap();
    }
    if (subtag == subtag_simple_vector) {
      LispObj *data = (LispObj *)((BytePtr)obj + misc_data_offset);
      wasm_set_reg(tcr, arg_z, data[index]);
      wasm_set_nargs_count(tcr, 1);
      return;
    }
    if (subtag >= min_cl_ivector_subtag) {
      LispObj value;
      if ((subtag & fulltagmask) == fulltag_nodeheader) {
        LispObj *data = (LispObj *)((BytePtr)obj + misc_data_offset);
        value = data[index];
      } else {
        value = wasm_misc_ref_imm_dispatch(tcr, obj, subtag, index);
      }
      wasm_set_reg(tcr, arg_z, value);
      wasm_set_nargs_count(tcr, 1);
      return;
    }
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_AREF1, 2);
}

__attribute__((used, visibility("default"), export_name("_SPbuiltin_aset1")))
void
_SPbuiltin_aset1(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj obj = wasm_reg(tcr, arg_z);
  LispObj index_val = wasm_reg(tcr, arg_y);
  LispObj value = wasm_reg(tcr, arg_x);
  if (tag_of(index_val) == tag_fixnum && fulltag_of(obj) == fulltag_misc) {
    signed_natural index = unbox_fixnum(index_val);
    LispObj header = header_of(obj);
    unsigned subtag = header_subtag(header);
    signed_natural count = header_element_count(header);
    if ((natural)index >= (natural)count) {
      wasm_subprims_trap();
    }
    if (subtag == subtag_simple_vector) {
      LispObj *data = (LispObj *)((BytePtr)obj + misc_data_offset);
      data[index] = value;
      wasm_set_reg(tcr, arg_z, value);
      wasm_set_nargs_count(tcr, 1);
      return;
    }
    if (subtag >= min_cl_ivector_subtag) {
      if ((subtag & fulltagmask) == fulltag_nodeheader) {
        LispObj *data = (LispObj *)((BytePtr)obj + misc_data_offset);
        data[index] = value;
      } else {
        wasm_misc_set_imm_dispatch(tcr, obj, subtag, index, value);
      }
      wasm_set_reg(tcr, arg_z, value);
      wasm_set_nargs_count(tcr, 1);
      return;
    }
  }

  wasm_call_builtin(tcr, WASM_BUILTIN_ASET1, 3);
}

__attribute__((used, visibility("default"), export_name("_SPatomic_incf_node")))
void
_SPatomic_incf_node(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj base = wasm_reg(tcr, arg_y);
  signed_natural offset = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, arg_z));
  LispObj delta = wasm_reg(tcr, arg_x);

  LispObj *slot = (LispObj *)((BytePtr)base + offset);
  LispObj old_value = *slot;
  *slot = old_value + delta;

  wasm_set_reg(tcr, arg_z, *slot);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPrplaca")))
void
_SPrplaca(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj cell = wasm_reg(tcr, arg_y);
  if (fulltag_of(cell) != fulltag_cons) {
    wasm_subprims_trap();
  }
  cons *pair = (cons *)ptr_from_lispobj(untag(cell));
  pair->car = wasm_reg(tcr, arg_z);
}

__attribute__((used, visibility("default"), export_name("_SPrplacd")))
void
_SPrplacd(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj cell = wasm_reg(tcr, arg_y);
  if (fulltag_of(cell) != fulltag_cons) {
    wasm_subprims_trap();
  }
  cons *pair = (cons *)ptr_from_lispobj(untag(cell));
  pair->cdr = wasm_reg(tcr, arg_z);
}

static inline void
wasm_gvector_set_or_trap(TCR *tcr, LispObj obj, signed_natural index, LispObj value)
{
  if (fulltag_of(obj) != fulltag_misc) {
    wasm_subprims_trap();
  }
  LispObj header = header_of(obj);
  if ((header_subtag(header) & fulltagmask) != fulltag_nodeheader) {
    wasm_subprims_trap();
  }
  signed_natural count = header_element_count(header);
  if ((natural)index >= (natural)count) {
    wasm_subprims_trap();
  }

  LispObj *data = (LispObj *)((BytePtr)obj + misc_data_offset);
  data[index] = value;
}

__attribute__((used, visibility("default"), export_name("_SPgvset")))
void
_SPgvset(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj obj = wasm_reg(tcr, arg_x);
  signed_natural index = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, arg_y));
  LispObj value = wasm_reg(tcr, arg_z);
  wasm_gvector_set_or_trap(tcr, obj, index, value);
}

__attribute__((used, visibility("default"), export_name("_SPset_hash_key")))
void
_SPset_hash_key(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj obj = wasm_reg(tcr, arg_x);
  signed_natural index = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, arg_y));
  LispObj value = wasm_reg(tcr, arg_z);
  wasm_gvector_set_or_trap(tcr, obj, index, value);
}

__attribute__((used, visibility("default"), export_name("_SPstore_node_conditional")))
void
_SPstore_node_conditional(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj raw_offset = vsp_ptr[0];
  signed_natural offset = wasm_unbox_fixnum_or_trap(raw_offset);
  vsp_ptr += 1;
  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;

  LispObj obj = wasm_reg(tcr, arg_x);
  LispObj expected = wasm_reg(tcr, arg_y);
  LispObj new_value = wasm_reg(tcr, arg_z);

  LispObj *slot = (LispObj *)((BytePtr)obj + offset);
  if (*slot == expected) {
    *slot = new_value;
    wasm_set_reg(tcr, arg_z, (LispObj)(nil_value + t_offset));
  } else {
    wasm_set_reg(tcr, arg_z, (LispObj)nil_value);
  }
}

__attribute__((used, visibility("default"), export_name("_SPset_hash_key_conditional")))
void
_SPset_hash_key_conditional(void)
{
  _SPstore_node_conditional();
}

__attribute__((used, visibility("default"), export_name("_SPconslist")))
void
_SPconslist(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }
  signed_natural count = unbox_fixnum(raw_nargs);
  if (count < 0) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj list = (LispObj)nil_value;
  for (signed_natural i = 0; i < count; i++) {
    LispObj value = vsp_ptr[0];
    vsp_ptr += 1;
    list = wasm_alloc_cons_or_trap(tcr, value, list);
  }

  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
  wasm_set_reg(tcr, arg_z, list);
  wasm_set_nargs_count(tcr, 0);
}

__attribute__((used, visibility("default"), export_name("_SPconslist_star")))
void
_SPconslist_star(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }
  signed_natural count = unbox_fixnum(raw_nargs);
  if (count < 0) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj list = wasm_reg(tcr, arg_z);
  for (signed_natural i = 0; i < count; i++) {
    LispObj value = vsp_ptr[0];
    vsp_ptr += 1;
    list = wasm_alloc_cons_or_trap(tcr, value, list);
  }

  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
  wasm_set_reg(tcr, arg_z, list);
  wasm_set_nargs_count(tcr, 0);
}

/*
 * Minimal safe stack-consing for wasm32:
 * - Stack objects live on the wasm cstack as simple-vectors with a
 *   stack_alloc_marker/old-sp header below them.
 * - stkconslist* builds cons cells inside that backing store and
 *   falls back to heap consing if cstack space is tight.
 * - _SPdiscard_stack_object pops the cstack back to the saved pointer.
 *
 * This is a stopgap; full tstack/stack-object semantics and GC
 * integration can be tightened later.
 */
__attribute__((used, visibility("default"), export_name("_SPstkconslist")))
void
_SPstkconslist(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }
  signed_natural count = unbox_fixnum(raw_nargs);
  if (count < 0) {
    wasm_subprims_trap();
  }

  if (count == 0) {
    wasm_set_reg(tcr, arg_z, (LispObj)nil_value);
    wasm_set_nargs_count(tcr, 0);
    return;
  }

  signed_natural element_count = (count * 2) + 1;
  LispObj *headerp = wasm_cstack_alloc_simple_vector(tcr, element_count);
  if (headerp == NULL) {
    _SPconslist();
    return;
  }

  BytePtr cons_base = (BytePtr)headerp + dnode_size;
  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj list = (LispObj)nil_value;

  for (signed_natural i = 0; i < count; i++) {
    LispObj value = vsp_ptr[0];
    vsp_ptr += 1;

    cons *cell = (cons *)(cons_base + (i * dnode_size));
    cell->car = value;
    cell->cdr = list;
    list = (LispObj)((BytePtr)cell + fulltag_cons);
  }

  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
  wasm_set_reg(tcr, arg_z, list);
  wasm_set_nargs_count(tcr, 0);
}

__attribute__((used, visibility("default"), export_name("_SPstkconslist_star")))
void
_SPstkconslist_star(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }
  signed_natural count = unbox_fixnum(raw_nargs);
  if (count < 0) {
    wasm_subprims_trap();
  }

  LispObj list = wasm_reg(tcr, arg_z);
  if (count == 0) {
    wasm_set_reg(tcr, arg_z, list);
    wasm_set_nargs_count(tcr, 0);
    return;
  }

  signed_natural element_count = (count * 2) + 1;
  LispObj *headerp = wasm_cstack_alloc_simple_vector(tcr, element_count);
  if (headerp == NULL) {
    _SPconslist_star();
    return;
  }

  BytePtr cons_base = (BytePtr)headerp + dnode_size;
  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;

  for (signed_natural i = 0; i < count; i++) {
    LispObj value = vsp_ptr[0];
    vsp_ptr += 1;

    cons *cell = (cons *)(cons_base + (i * dnode_size));
    cell->car = value;
    cell->cdr = list;
    list = (LispObj)((BytePtr)cell + fulltag_cons);
  }

  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
  wasm_set_reg(tcr, arg_z, list);
  wasm_set_nargs_count(tcr, 0);
}

__attribute__((used, visibility("default"), export_name("_SPmkstackv")))
void
_SPmkstackv(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  if (tag_of(raw_nargs) != tag_fixnum) {
    wasm_subprims_trap();
  }
  signed_natural count = unbox_fixnum(raw_nargs);
  if (count < 0) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj *headerp = wasm_cstack_alloc_simple_vector(tcr, count);
  LispObj obj = (LispObj)nil_value;
  LispObj *data = NULL;

  if (headerp != NULL) {
    obj = (LispObj)((BytePtr)headerp + fulltag_misc);
    data = headerp + 1;
  } else {
    obj = wasm_misc_alloc(tcr, subtag_simple_vector, count);
    if (obj == (LispObj)nil_value) {
      wasm_subprims_trap();
    }
    data = (LispObj *)((BytePtr)obj + misc_data_offset);
  }

  for (signed_natural i = count - 1; i >= 0; i--) {
    data[i] = vsp_ptr[0];
    vsp_ptr += 1;
  }

  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
  wasm_set_reg(tcr, arg_z, obj);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SParef2")))
void
_SParef2(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj array = wasm_reg(tcr, arg_x);
  LispObj *data = NULL;
  if (fulltag_of(array) == fulltag_misc) {
    LispObj header = header_of(array);
    unsigned subtag = header_subtag(header);
    if (subtag == subtag_arrayH) {
      data = (LispObj *)((BytePtr)array + misc_data_offset);
      signed_natural rank = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_RANK_CELL]);
      if (rank != 2) {
        wasm_signal_xndims(tcr, array, 2);
        return;
      }
    } else if (subtag == subtag_vectorH || subtag == subtag_simple_vector || subtag >= min_cl_ivector_subtag) {
      wasm_signal_xndims(tcr, array, 2);
      return;
    } else {
      wasm_signal_wrong_type(tcr, array, wasm_symbol_array());
      return;
    }
  } else {
    wasm_signal_wrong_type(tcr, array, wasm_symbol_array());
    return;
  }

  LispObj raw_i = wasm_reg(tcr, arg_y);
  if (tag_of(raw_i) != tag_fixnum) {
    wasm_signal_wrong_type(tcr, raw_i, wasm_symbol_fixnum());
    return;
  }
  LispObj raw_j = wasm_reg(tcr, arg_z);
  if (tag_of(raw_j) != tag_fixnum) {
    wasm_signal_wrong_type(tcr, raw_j, wasm_symbol_fixnum());
    return;
  }

  signed_natural i = unbox_fixnum(raw_i);
  signed_natural j = unbox_fixnum(raw_j);
  if (i < 0) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }
  if (j < 0) {
    wasm_signal_xarroob(tcr, raw_j, array);
    return;
  }

  signed_natural dim0 = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_DIM0_CELL]);
  signed_natural dim1 = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_DIM0_CELL + 1]);
  if (dim0 < 0) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }
  if (dim1 < 0) {
    wasm_signal_xarroob(tcr, raw_j, array);
    return;
  }
  if (i >= dim0) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }
  if (j >= dim1) {
    wasm_signal_xarroob(tcr, raw_j, array);
    return;
  }

  int64_t idx64 = (int64_t)i * (int64_t)dim1 + (int64_t)j;
  signed_natural index = (signed_natural)idx64;
  if ((int64_t)index != idx64) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }

  LispObj data_vector = wasm_array_data_vector_or_trap(array, &index);
  LispObj value = wasm_misc_ref_dispatch(tcr, data_vector, index);
  wasm_set_reg(tcr, arg_z, value);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SParef3")))
void
_SParef3(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj array = wasm_reg(tcr, temp0);
  LispObj *data = NULL;
  if (fulltag_of(array) == fulltag_misc) {
    LispObj header = header_of(array);
    unsigned subtag = header_subtag(header);
    if (subtag == subtag_arrayH) {
      data = (LispObj *)((BytePtr)array + misc_data_offset);
      signed_natural rank = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_RANK_CELL]);
      if (rank != 3) {
        wasm_signal_xndims(tcr, array, 3);
        return;
      }
    } else if (subtag == subtag_vectorH || subtag == subtag_simple_vector || subtag >= min_cl_ivector_subtag) {
      wasm_signal_xndims(tcr, array, 3);
      return;
    } else {
      wasm_signal_wrong_type(tcr, array, wasm_symbol_array());
      return;
    }
  } else {
    wasm_signal_wrong_type(tcr, array, wasm_symbol_array());
    return;
  }

  LispObj raw_i = wasm_reg(tcr, arg_x);
  if (tag_of(raw_i) != tag_fixnum) {
    wasm_signal_wrong_type(tcr, raw_i, wasm_symbol_fixnum());
    return;
  }
  LispObj raw_j = wasm_reg(tcr, arg_y);
  if (tag_of(raw_j) != tag_fixnum) {
    wasm_signal_wrong_type(tcr, raw_j, wasm_symbol_fixnum());
    return;
  }
  LispObj raw_k = wasm_reg(tcr, arg_z);
  if (tag_of(raw_k) != tag_fixnum) {
    wasm_signal_wrong_type(tcr, raw_k, wasm_symbol_fixnum());
    return;
  }

  signed_natural i = unbox_fixnum(raw_i);
  signed_natural j = unbox_fixnum(raw_j);
  signed_natural k = unbox_fixnum(raw_k);
  if (i < 0) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }
  if (j < 0) {
    wasm_signal_xarroob(tcr, raw_j, array);
    return;
  }
  if (k < 0) {
    wasm_signal_xarroob(tcr, raw_k, array);
    return;
  }

  signed_natural dim0 = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_DIM0_CELL]);
  signed_natural dim1 = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_DIM0_CELL + 1]);
  signed_natural dim2 = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_DIM0_CELL + 2]);
  if (dim0 < 0) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }
  if (dim1 < 0) {
    wasm_signal_xarroob(tcr, raw_j, array);
    return;
  }
  if (dim2 < 0) {
    wasm_signal_xarroob(tcr, raw_k, array);
    return;
  }
  if (i >= dim0) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }
  if (j >= dim1) {
    wasm_signal_xarroob(tcr, raw_j, array);
    return;
  }
  if (k >= dim2) {
    wasm_signal_xarroob(tcr, raw_k, array);
    return;
  }

  int64_t plane = (int64_t)dim1 * (int64_t)dim2;
  int64_t idx64 = (int64_t)i * plane + (int64_t)j * (int64_t)dim2 + (int64_t)k;
  signed_natural index = (signed_natural)idx64;
  if ((int64_t)index != idx64) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }

  LispObj data_vector = wasm_array_data_vector_or_trap(array, &index);
  LispObj value = wasm_misc_ref_dispatch(tcr, data_vector, index);
  wasm_set_reg(tcr, arg_z, value);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPaset2")))
void
_SPaset2(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj array = wasm_reg(tcr, temp0);
  LispObj *data = NULL;
  if (fulltag_of(array) == fulltag_misc) {
    LispObj header = header_of(array);
    unsigned subtag = header_subtag(header);
    if (subtag == subtag_arrayH) {
      data = (LispObj *)((BytePtr)array + misc_data_offset);
      signed_natural rank = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_RANK_CELL]);
      if (rank != 2) {
        wasm_signal_xndims(tcr, array, 2);
        return;
      }
    } else if (subtag == subtag_vectorH || subtag == subtag_simple_vector || subtag >= min_cl_ivector_subtag) {
      wasm_signal_xndims(tcr, array, 2);
      return;
    } else {
      wasm_signal_wrong_type(tcr, array, wasm_symbol_array());
      return;
    }
  } else {
    wasm_signal_wrong_type(tcr, array, wasm_symbol_array());
    return;
  }

  LispObj raw_i = wasm_reg(tcr, arg_x);
  if (tag_of(raw_i) != tag_fixnum) {
    wasm_signal_wrong_type(tcr, raw_i, wasm_symbol_fixnum());
    return;
  }
  LispObj raw_j = wasm_reg(tcr, arg_y);
  if (tag_of(raw_j) != tag_fixnum) {
    wasm_signal_wrong_type(tcr, raw_j, wasm_symbol_fixnum());
    return;
  }

  signed_natural i = unbox_fixnum(raw_i);
  signed_natural j = unbox_fixnum(raw_j);
  if (i < 0) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }
  if (j < 0) {
    wasm_signal_xarroob(tcr, raw_j, array);
    return;
  }

  signed_natural dim0 = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_DIM0_CELL]);
  signed_natural dim1 = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_DIM0_CELL + 1]);
  if (dim0 < 0) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }
  if (dim1 < 0) {
    wasm_signal_xarroob(tcr, raw_j, array);
    return;
  }
  if (i >= dim0) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }
  if (j >= dim1) {
    wasm_signal_xarroob(tcr, raw_j, array);
    return;
  }

  int64_t idx64 = (int64_t)i * (int64_t)dim1 + (int64_t)j;
  signed_natural index = (signed_natural)idx64;
  if ((int64_t)index != idx64) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }

  LispObj value = wasm_reg(tcr, arg_z);
  LispObj data_vector = wasm_array_data_vector_or_trap(array, &index);
  wasm_misc_set_dispatch(tcr, data_vector, index, value);
  wasm_set_reg(tcr, arg_z, value);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPaset3")))
void
_SPaset3(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj array = wasm_reg(tcr, temp1);
  LispObj *data = NULL;
  if (fulltag_of(array) == fulltag_misc) {
    LispObj header = header_of(array);
    unsigned subtag = header_subtag(header);
    if (subtag == subtag_arrayH) {
      data = (LispObj *)((BytePtr)array + misc_data_offset);
      signed_natural rank = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_RANK_CELL]);
      if (rank != 3) {
        wasm_signal_xndims(tcr, array, 3);
        return;
      }
    } else if (subtag == subtag_vectorH || subtag == subtag_simple_vector || subtag >= min_cl_ivector_subtag) {
      wasm_signal_xndims(tcr, array, 3);
      return;
    } else {
      wasm_signal_wrong_type(tcr, array, wasm_symbol_array());
      return;
    }
  } else {
    wasm_signal_wrong_type(tcr, array, wasm_symbol_array());
    return;
  }

  LispObj raw_i = wasm_reg(tcr, temp0);
  if (tag_of(raw_i) != tag_fixnum) {
    wasm_signal_wrong_type(tcr, raw_i, wasm_symbol_fixnum());
    return;
  }
  LispObj raw_j = wasm_reg(tcr, arg_x);
  if (tag_of(raw_j) != tag_fixnum) {
    wasm_signal_wrong_type(tcr, raw_j, wasm_symbol_fixnum());
    return;
  }
  LispObj raw_k = wasm_reg(tcr, arg_y);
  if (tag_of(raw_k) != tag_fixnum) {
    wasm_signal_wrong_type(tcr, raw_k, wasm_symbol_fixnum());
    return;
  }

  signed_natural i = unbox_fixnum(raw_i);
  signed_natural j = unbox_fixnum(raw_j);
  signed_natural k = unbox_fixnum(raw_k);
  if (i < 0) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }
  if (j < 0) {
    wasm_signal_xarroob(tcr, raw_j, array);
    return;
  }
  if (k < 0) {
    wasm_signal_xarroob(tcr, raw_k, array);
    return;
  }

  signed_natural dim0 = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_DIM0_CELL]);
  signed_natural dim1 = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_DIM0_CELL + 1]);
  signed_natural dim2 = wasm_unbox_fixnum_or_trap(data[WASM_ARRAYH_DIM0_CELL + 2]);
  if (dim0 < 0) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }
  if (dim1 < 0) {
    wasm_signal_xarroob(tcr, raw_j, array);
    return;
  }
  if (dim2 < 0) {
    wasm_signal_xarroob(tcr, raw_k, array);
    return;
  }
  if (i >= dim0) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }
  if (j >= dim1) {
    wasm_signal_xarroob(tcr, raw_j, array);
    return;
  }
  if (k >= dim2) {
    wasm_signal_xarroob(tcr, raw_k, array);
    return;
  }

  int64_t plane = (int64_t)dim1 * (int64_t)dim2;
  int64_t idx64 = (int64_t)i * plane + (int64_t)j * (int64_t)dim2 + (int64_t)k;
  signed_natural index = (signed_natural)idx64;
  if ((int64_t)index != idx64) {
    wasm_signal_xarroob(tcr, raw_i, array);
    return;
  }

  LispObj value = wasm_reg(tcr, arg_z);
  LispObj data_vector = wasm_array_data_vector_or_trap(array, &index);
  wasm_misc_set_dispatch(tcr, data_vector, index, value);
  wasm_set_reg(tcr, arg_z, value);
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPspread_lexprz")))
void
_SPspread_lexprz(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj *lexpr = (LispObj *)wasm_reg(tcr, arg_z);
  if (lexpr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_count = lexpr[0];
  signed_natural count = wasm_unbox_fixnum_or_trap(raw_count);
  if (count < 0) {
    wasm_subprims_trap();
  }

  signed_natural orig_count = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, nargs));
  if (orig_count < 0) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  for (signed_natural i = 0; i < count; i++) {
    LispObj value = lexpr[1 + i];
    *--vsp_ptr = value;
  }

  signed_natural total = orig_count + count;
  wasm_set_nargs_count(tcr, total);
  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
  wasm_vpop_argregs(tcr);
}

__attribute__((used, visibility("default"), export_name("_SPcheck_fpu_exception")))
void
_SPcheck_fpu_exception(void)
{
  /* No FPU exception state on wasm32; nothing to do. */
}

__attribute__((used, visibility("default"), export_name("_SPdiscard_stack_object")))
void
_SPdiscard_stack_object(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj *sp = (LispObj *)wasm_get_cstack_pointer();
  if (sp == NULL) {
    wasm_subprims_trap();
  }

  if (sp[0] == stack_alloc_marker) {
    wasm_set_cstack_pointer((void *)sp[1]);
  }
}

/* File-scope so wasm_reset_ksignalerr_counters can reach them. */
static unsigned ksignalerr_count = 0;
static unsigned ksignalerr_absorbed = 0;

__attribute__((used, visibility("default"), export_name("wasm_reset_ksignalerr_counters")))
void
wasm_reset_ksignalerr_counters(void)
{
  ksignalerr_count = 0;
  ksignalerr_absorbed = 0;
}

__attribute__((used, visibility("default"), export_name("_SPksignalerr")))
void
_SPksignalerr(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  unsigned this_call = ksignalerr_count++;

  /* Verbose diagnostics for first 5 errors only */
  if (this_call < 5) {
    wasm_debug_dump_state("ksignalerr");

    /* Print the name of the undefined function (if arg_z is a symbol) */
    {
      LispObj err_arg = wasm_reg(tcr, arg_z);
      LispObj err_code = wasm_reg(tcr, arg_y);
      LispObj fname_reg = tcr->wasm_gprs[8]; /* temp1/fname */
      static const char hex[] = "0123456789abcdef";
      char msg[128];
      int p = 0;

      /* Print fname register */
      msg[p++] = ' '; msg[p++] = ' ';
      msg[p++] = 'f'; msg[p++] = 'n'; msg[p++] = 'a'; msg[p++] = 'm'; msg[p++] = 'e';
      msg[p++] = '='; msg[p++] = '0'; msg[p++] = 'x';
      for (int i = 7; i >= 0; i--) msg[p++] = hex[(fname_reg >> (i*4)) & 0xf];
      msg[p++] = '\n';
      wasm_host_log(msg, (unsigned)p);

      /* Unconditional: dump error code + datum header + expected type.
         Previous conditional (if err_code == XWRONGTYPE) was eliminated by -O2 DCE. */
      {
        LispObj ax = wasm_reg(tcr, arg_x);
        LispObj ay = wasm_reg(tcr, arg_y);
        LispObj az = wasm_reg(tcr, arg_z);
        p = 0;
        p = wasm_diag_append_str(msg, p, "  errcode=0x");
        p = wasm_diag_append_hex32(msg, p, ax);
        p = wasm_diag_append_str(msg, p, " datum=0x");
        p = wasm_diag_append_hex32(msg, p, ay);
        p = wasm_diag_append_str(msg, p, " ft=");
        msg[p++] = hex[fulltag_of(ay) & 0xf];
        if (fulltag_of(ay) == fulltag_misc) {
          LispObj dhdr = header_of(ay);
          p = wasm_diag_append_str(msg, p, " hdr=0x");
          p = wasm_diag_append_hex32(msg, p, dhdr);
          p = wasm_diag_append_str(msg, p, " sub=0x");
          unsigned dsub = header_subtag(dhdr);
          msg[p++] = hex[(dsub >> 4) & 0xf];
          msg[p++] = hex[dsub & 0xf];
          /* Print first data word (float value for single-float).
             misc_data_offset is relative to the TAGGED pointer
             (-fulltag_misc + node_size = -2), so use ay directly. */
          LispObj *data = (LispObj *)((char *)ptr_from_lispobj(ay) + misc_data_offset);
          p = wasm_diag_append_str(msg, p, " d0=0x");
          p = wasm_diag_append_hex32(msg, p, data[0]);
        }
        msg[p++] = '\n';
        wasm_host_log(msg, (unsigned)p);
        /* Expected type */
        p = 0;
        p = wasm_diag_append_str(msg, p, "  expected=0x");
        p = wasm_diag_append_hex32(msg, p, az);
        p = wasm_diag_append_str(msg, p, " ft=");
        msg[p++] = hex[fulltag_of(az) & 0xf];
        if (fulltag_of(az) == fulltag_cons) {
          LispObj cell = az;
          p = wasm_diag_append_str(msg, p, " (");
          for (int depth = 0; depth < 4 && fulltag_of(cell) == fulltag_cons; depth++) {
            if (depth > 0) msg[p++] = ' ';
            LispObj cv = car(cell);
            p = wasm_diag_append_str(msg, p, "0x");
            p = wasm_diag_append_hex32(msg, p, cv);
            cell = cdr(cell);
          }
          msg[p++] = ')';
        }
        msg[p++] = '\n';
        wasm_host_log(msg, (unsigned)p);
      }

      /* Try to print symbol pname from arg_z */
      if (fulltag_of(err_arg) == fulltag_misc) {
        LispObj hdr = header_of(err_arg);
        if (header_subtag(hdr) == subtag_symbol) {
          lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(err_arg));
          LispObj pname = sym->pname;
          if (fulltag_of(pname) == fulltag_misc) {
            LispObj pname_hdr = header_of(pname);
            if (header_subtag(pname_hdr) == subtag_simple_base_string) {
              unsigned count = header_element_count(pname_hdr);
              if (count > 80) count = 80;
              /* Characters are 32-bit (4 bytes each) on ARM32/WASM */
              uint32_t *chars32 = (uint32_t *)((char *)ptr_from_lispobj(untag(pname)) + sizeof(LispObj));
              p = 0;
              msg[p++] = ' '; msg[p++] = ' '; msg[p++] = 's'; msg[p++] = 'y'; msg[p++] = 'm';
              msg[p++] = ':'; msg[p++] = ' ';
              for (unsigned i = 0; i < count && p < 120; i++) msg[p++] = (char)(chars32[i] & 0xff);
              msg[p++] = '\n';
              wasm_host_log(msg, (unsigned)p);
            }
          }
          /* Also print the fcell value */
          LispObj fcell = sym->fcell;
          p = 0;
          msg[p++] = ' '; msg[p++] = ' ';
          msg[p++] = 'f'; msg[p++] = 'c'; msg[p++] = 'e'; msg[p++] = 'l'; msg[p++] = 'l';
          msg[p++] = '='; msg[p++] = '0'; msg[p++] = 'x';
          for (int i = 7; i >= 0; i--) msg[p++] = hex[(fcell >> (i*4)) & 0xf];
          /* If fcell looks like a function, print its entry index */
          if (fulltag_of(fcell) == fulltag_misc) {
            LispObj fc_hdr = header_of(fcell);
            unsigned fc_sub = header_subtag(fc_hdr);
            if (fc_sub == subtag_function || fc_sub == subtag_pseudofunction) {
              LispObj entry = deref(fcell, 1);
              msg[p++] = ' '; msg[p++] = 'e'; msg[p++] = 'n'; msg[p++] = 't'; msg[p++] = '=';
              msg[p++] = '0'; msg[p++] = 'x';
              for (int i = 7; i >= 0; i--) msg[p++] = hex[(entry >> (i*4)) & 0xf];
            }
          }
          msg[p++] = '\n';
          wasm_host_log(msg, (unsigned)p);
        } else {
          /* arg_z is misc but not symbol — print subtag */
          p = 0;
          msg[p++] = ' '; msg[p++] = ' ';
          msg[p++] = 'a'; msg[p++] = 'r'; msg[p++] = 'g'; msg[p++] = '_'; msg[p++] = 'z';
          msg[p++] = ':'; msg[p++] = ' '; msg[p++] = 's'; msg[p++] = 'u'; msg[p++] = 'b';
          msg[p++] = 't'; msg[p++] = 'a'; msg[p++] = 'g'; msg[p++] = '=';
          msg[p++] = '0'; msg[p++] = 'x';
          unsigned st = header_subtag(hdr);
          for (int i = 1; i >= 0; i--) msg[p++] = hex[(st >> (i*4)) & 0xf];
          msg[p++] = '\n';
          wasm_host_log(msg, (unsigned)p);
        }
      }

    }
  }

  /* No catch handler — ERRDISP would dispatch through the condition system
     which ultimately THROWs; with no catch frame that recurses into
     _SPksignalerr.  Set pending_throw so the funcall dispatcher (which
     checks pending_throw after every call) unwinds the call stack.
     Without pending_throw, the error-causing code loops forever (v15
     produced 4M+ absorbed errors in an infinite loop).
     The C wrapper (wasm_run_cold_boot_init) checks *WASM-STARTUP-STEP*
     to decide whether work completed before the error hit. */
  if (tcr->catch_top == 0 || tcr->catch_top == (LispObj)nil_value) {
    ksignalerr_absorbed++;
    /* Log first 5 absorbed, then every millionth */
    if (ksignalerr_absorbed <= 5 ||
        (ksignalerr_absorbed % 1000000) == 0) {
      char m[80]; unsigned mp = 0;
      mp = wasm_diag_append_str(m, mp, "ksignalerr: absorbed=0x");
      mp = wasm_diag_append_hex32(m, mp, ksignalerr_absorbed);
      mp = wasm_diag_append_str(m, mp, " calls=0x");
      mp = wasm_diag_append_hex32(m, mp, ksignalerr_count);
      m[mp++] = '\n';
      wasm_host_log(m, mp);
    }
    wasm_set_pending_throw(tcr, box_fixnum(16)); /* absorbed ksignalerr */
    return;
  }

  /*
   * If ERRDISP is unavailable (or recursively faults while signaling),
   * avoid non-terminating self-recursion and surface a pending throw
   * to the host boundary instead.
   */
  static int reentering_errdisp = 0;
  if (reentering_errdisp) {
    wasm_set_pending_throw(tcr, box_fixnum(13));  /* ksignalerr: re-entrant */
    return;
  }

  LispObj errdisp = wasm_nrs_symbol_lispobj(&nrs_ERRDISP);
  if (fulltag_of(errdisp) != fulltag_misc || header_subtag(header_of(errdisp)) != subtag_symbol) {
    wasm_set_pending_throw(tcr, box_fixnum(14));  /* errdisp: bad symbol */
    return;
  }

  lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(untag(errdisp));
  LispObj fn = rawsym->fcell;
  if (fn == nrs_UDF.vcell || fulltag_of(fn) != fulltag_misc) {
    wasm_set_pending_throw(tcr, box_fixnum(15));  /* errdisp: UDF fcell */
    return;
  }

  reentering_errdisp = 1;
  wasm_call_lisp_function(tcr, errdisp);
  reentering_errdisp = 0;
}

static LispObj
wasm_error_name_from_tcr(TCR *tcr)
{
  LispObj name = wasm_reg(tcr, fname);
  if (fulltag_of(name) == fulltag_misc && header_subtag(header_of(name)) == subtag_symbol) {
    return name;
  }
  name = wasm_reg(tcr, nfn);
  return name;
}

__attribute__((used, visibility("default"), export_name("_SPwasm_macro_apply_stub")))
void
_SPwasm_macro_apply_stub(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj name = wasm_error_name_from_tcr(tcr);
  wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XNOTFUN));
  wasm_set_reg(tcr, arg_z, name);
  wasm_set_nargs_count(tcr, 2);
  _SPksignalerr();
}

__attribute__((used, visibility("default"), export_name("_SPwasm_udf_stub")))
void
_SPwasm_udf_stub(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  /* Print the entry index from nfn that led to this UDF stub */
  {
    static const char hex[] = "0123456789abcdef";
    char msg[64];
    int p = 0;
    LispObj nfn_val = wasm_reg(tcr, nfn);
    msg[p++] = 'U'; msg[p++] = 'D'; msg[p++] = 'F'; msg[p++] = ' ';
    msg[p++] = 'n'; msg[p++] = 'f'; msg[p++] = 'n'; msg[p++] = '=';
    msg[p++] = '0'; msg[p++] = 'x';
    for (int i = 7; i >= 0; i--) msg[p++] = hex[(nfn_val >> (i*4)) & 0xf];
    if (fulltag_of(nfn_val) == fulltag_misc) {
      LispObj entry = deref(nfn_val, 1);
      msg[p++] = ' '; msg[p++] = 'e'; msg[p++] = 'n'; msg[p++] = 't'; msg[p++] = '=';
      msg[p++] = '0'; msg[p++] = 'x';
      for (int i = 7; i >= 0; i--) msg[p++] = hex[(entry >> (i*4)) & 0xf];
    }
    msg[p++] = '\n';
    wasm_host_log(msg, (unsigned)p);
  }

  /* During early boot, _SPksignalerr dispatches through ERRDISP which
     triggers GF dispatch before methods are installed, causing infinite
     recursion in %%no-applicable-method.  Set pending_throw directly
     so the caller gets a clean error instead of stack overflow. */
  tcr->wasm_pending_throw = 1;
}

__attribute__((used, visibility("default"), export_name("_SPreset")))
void
_SPreset(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  *--vsp_ptr = nrs_TOPLCATCH.vcell;
  *--vsp_ptr = box_fixnum(75); /* XSTKOVER */
  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
  wasm_set_nargs_count(tcr, 1);
  _SPthrow();
}

__attribute__((used, visibility("default"), export_name("_SPunused1")))
void
_SPunused1(void)
{
  /* Intentional no-op used by smoke tests to validate subprim dispatch. */
}

__attribute__((used, visibility("default"), export_name("_SPunused2")))
void
_SPunused2(void)
{
  /* Intentional no-op used by smoke tests to validate subprim dispatch. */
}

__attribute__((used, visibility("default"), export_name("_SPpopj")))
void
_SPpopj(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  /* WASM lisp-frame popping is handled by callers; no-op for now. */
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
  wasm_set_reg(tcr, arg_z, wasm_box_i64_prefer_fixnum(tcr, (int64_t)val));
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPmakeu32")))
void
_SPmakeu32(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw = wasm_reg(tcr, imm0);
  uint32_t val = (tag_of(raw) == tag_fixnum) ? (uint32_t)unbox_fixnum(raw) : (uint32_t)raw;

  if (wasm_fixnum_fit_u32(val)) {
    wasm_set_reg(tcr, arg_z, box_fixnum((signed_natural)val));
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  uint32_t *digits = NULL;
  if (val & 0x80000000u) {
    wasm_set_reg(tcr, arg_z, wasm_alloc_bignum_or_trap(tcr, 2, &digits));
    digits[0] = val;
    digits[1] = 0;
  } else {
    wasm_set_reg(tcr, arg_z, wasm_alloc_bignum_or_trap(tcr, 1, &digits));
    digits[0] = val;
  }
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPmakeu64")))
void
_SPmakeu64(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_lo = wasm_reg(tcr, imm0);
  LispObj raw_hi = wasm_reg(tcr, imm1);
  uint32_t lo = (tag_of(raw_lo) == tag_fixnum) ? (uint32_t)unbox_fixnum(raw_lo) : (uint32_t)raw_lo;
  uint32_t hi = (tag_of(raw_hi) == tag_fixnum) ? (uint32_t)unbox_fixnum(raw_hi) : (uint32_t)raw_hi;

  if (hi == 0) {
    if (wasm_fixnum_fit_u32(lo)) {
      wasm_set_reg(tcr, arg_z, box_fixnum((signed_natural)lo));
      wasm_set_nargs_count(tcr, 1);
      return;
    }

    uint32_t *digits = NULL;
    if (lo & 0x80000000u) {
      wasm_set_reg(tcr, arg_z, wasm_alloc_bignum_or_trap(tcr, 2, &digits));
      digits[0] = lo;
      digits[1] = 0;
    } else {
      wasm_set_reg(tcr, arg_z, wasm_alloc_bignum_or_trap(tcr, 1, &digits));
      digits[0] = lo;
    }
    wasm_set_nargs_count(tcr, 1);
    return;
  }

  uint32_t *digits = NULL;
  if (hi & 0x80000000u) {
    wasm_set_reg(tcr, arg_z, wasm_alloc_bignum_or_trap(tcr, 3, &digits));
    digits[0] = lo;
    digits[1] = hi;
    digits[2] = 0;
  } else {
    wasm_set_reg(tcr, arg_z, wasm_alloc_bignum_or_trap(tcr, 2, &digits));
    digits[0] = lo;
    digits[1] = hi;
  }
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPmakes64")))
void
_SPmakes64(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_lo = wasm_reg(tcr, imm0);
  LispObj raw_hi = wasm_reg(tcr, imm1);
  uint32_t lo = (tag_of(raw_lo) == tag_fixnum) ? (uint32_t)unbox_fixnum(raw_lo) : (uint32_t)raw_lo;
  uint32_t hi = (tag_of(raw_hi) == tag_fixnum) ? (uint32_t)unbox_fixnum(raw_hi) : (uint32_t)raw_hi;
  int64_t value = ((int64_t)(int32_t)hi << 32) | (int64_t)lo;

  wasm_set_reg(tcr, arg_z, wasm_box_i64_prefer_fixnum(tcr, value));
  wasm_set_nargs_count(tcr, 1);
}

__attribute__((used, visibility("default"), export_name("_SPgets32")))
void
_SPgets32(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj value = wasm_reg(tcr, arg_z);
  if (tag_of(value) == tag_fixnum) {
    wasm_set_reg(tcr, imm0, (LispObj)(int32_t)unbox_fixnum(value));
    return;
  }

  signed_natural count = 0;
  uint32_t *digits = NULL;
  if (!wasm_bignum_info(value, &count, &digits) || count != 1) {
    wasm_signal_wrong_type(tcr, value, wasm_type_signed_byte(tcr, 32));
    return;
  }
  wasm_set_reg(tcr, imm0, (LispObj)(int32_t)digits[0]);
}

__attribute__((used, visibility("default"), export_name("_SPgetu32")))
void
_SPgetu32(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj value = wasm_reg(tcr, arg_z);
  uint32_t result = 0;

  if (tag_of(value) == tag_fixnum) {
    result = (uint32_t)unbox_fixnum(value);
    wasm_set_reg(tcr, imm0, (LispObj)result);
    wasm_set_reg(tcr, imm1, (LispObj)0);
    return;
  }

  signed_natural count = 0;
  uint32_t *digits = NULL;
  if (!wasm_bignum_info(value, &count, &digits)) {
    wasm_signal_wrong_type(tcr, value, wasm_type_unsigned_byte(tcr, 32));
    return;
  }

  if (count == 1) {
    result = digits[0];
  } else if (count == 2) {
    result = digits[0];
    if (digits[1] != 0) {
      wasm_signal_wrong_type(tcr, value, wasm_type_unsigned_byte(tcr, 32));
      return;
    }
  } else {
    wasm_signal_wrong_type(tcr, value, wasm_type_unsigned_byte(tcr, 32));
    return;
  }

  wasm_set_reg(tcr, imm0, (LispObj)result);
  wasm_set_reg(tcr, imm1, (LispObj)0);
}

__attribute__((used, visibility("default"), export_name("_SPudiv64by32")))
void
_SPudiv64by32(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  uint32_t denom = (uint32_t)wasm_reg(tcr, imm2);
  if (denom == 0) {
    wasm_subprims_trap();
  }

  uint32_t lo = (uint32_t)wasm_reg(tcr, imm0);
  uint32_t hi = (uint32_t)wasm_reg(tcr, imm1);
  uint64_t numer = ((uint64_t)hi << 32) | (uint64_t)lo;
  uint64_t quot = numer / (uint64_t)denom;
  uint32_t rem = (uint32_t)(numer % (uint64_t)denom);

  wasm_set_reg(tcr, imm0, (LispObj)(uint32_t)quot);
  wasm_set_reg(tcr, imm1, (LispObj)(uint32_t)(quot >> 32));
  wasm_set_reg(tcr, imm2, (LispObj)rem);
}

__attribute__((used, visibility("default"), export_name("_SPgetu64")))
void
_SPgetu64(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj value = wasm_reg(tcr, arg_z);
  if (tag_of(value) == tag_fixnum) {
    int32_t sval = (int32_t)unbox_fixnum(value);
    if (sval < 0) {
      wasm_signal_wrong_type(tcr, value, wasm_type_unsigned_byte(tcr, 64));
      return;
    }
    wasm_set_reg(tcr, imm0, (LispObj)(uint32_t)sval);
    wasm_set_reg(tcr, imm1, (LispObj)0);
    return;
  }

  signed_natural count = 0;
  uint32_t *digits = NULL;
  if (!wasm_bignum_info(value, &count, &digits)) {
    wasm_signal_wrong_type(tcr, value, wasm_type_unsigned_byte(tcr, 64));
    return;
  }

  if (count == 1) {
    uint32_t lo = digits[0];
    if (lo & 0x80000000u) {
      wasm_signal_wrong_type(tcr, value, wasm_type_unsigned_byte(tcr, 64));
      return;
    }
    wasm_set_reg(tcr, imm0, (LispObj)lo);
    wasm_set_reg(tcr, imm1, (LispObj)0);
    return;
  }

  if (count == 2) {
    uint32_t lo = digits[0];
    uint32_t hi = digits[1];
    if (hi & 0x80000000u) {
      wasm_signal_wrong_type(tcr, value, wasm_type_unsigned_byte(tcr, 64));
      return;
    }
    wasm_set_reg(tcr, imm0, (LispObj)lo);
    wasm_set_reg(tcr, imm1, (LispObj)hi);
    return;
  }

  if (count == 3) {
    if (digits[2] != 0) {
      wasm_signal_wrong_type(tcr, value, wasm_type_unsigned_byte(tcr, 64));
      return;
    }
    wasm_set_reg(tcr, imm0, (LispObj)digits[0]);
    wasm_set_reg(tcr, imm1, (LispObj)digits[1]);
    return;
  }

  wasm_signal_wrong_type(tcr, value, wasm_type_unsigned_byte(tcr, 64));
}

__attribute__((used, visibility("default"), export_name("_SPgets64")))
void
_SPgets64(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj value = wasm_reg(tcr, arg_z);
  if (tag_of(value) == tag_fixnum) {
    int32_t sval = (int32_t)unbox_fixnum(value);
    wasm_set_reg(tcr, imm0, (LispObj)sval);
    wasm_set_reg(tcr, imm1, (LispObj)(sval >> 31));
    return;
  }

  signed_natural count = 0;
  uint32_t *digits = NULL;
  if (!wasm_bignum_info(value, &count, &digits)) {
    wasm_signal_wrong_type(tcr, value, wasm_type_signed_byte(tcr, 64));
    return;
  }

  if (count == 1) {
    uint32_t lo = digits[0];
    wasm_set_reg(tcr, imm0, (LispObj)lo);
    wasm_set_reg(tcr, imm1, (LispObj)((int32_t)lo >> 31));
    return;
  }

  if (count == 2) {
    wasm_set_reg(tcr, imm0, (LispObj)digits[0]);
    wasm_set_reg(tcr, imm1, (LispObj)digits[1]);
    return;
  }

  wasm_signal_wrong_type(tcr, value, wasm_type_signed_byte(tcr, 64));
}

__attribute__((used, visibility("default"), export_name("_SPspecref")))
void
_SPspecref(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj symbol = wasm_reg(tcr, arg_z);
  if (fulltag_of(symbol) != fulltag_misc) {
    wasm_host_log("DIAG specref: bad fulltag\n", 27);
    wasm_subprims_trap();
  }

  if (header_subtag(header_of(symbol)) != subtag_symbol) {
    wasm_host_log("DIAG specref: not symbol\n", 26);
    wasm_subprims_trap();
  }

  lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(symbol));
  LispObj binding_index = sym->binding_index;
  if (tag_of(binding_index) != tag_fixnum) {
    wasm_host_log("DIAG specref: bad binding_index\n", 33);
    wasm_subprims_trap();
  }

  LispObj limit = tcr->tlb_limit;
  if (tag_of(limit) != tag_fixnum) {
    wasm_host_log("DIAG specref: bad tlb_limit\n", 29);
    wasm_subprims_trap();
  }

  LispObj *binding_slots = tcr->tlb_pointer;
  if (binding_slots == NULL) {
    wasm_host_log("DIAG specref: null tlb_ptr\n", 28);
    wasm_subprims_trap();
  }

  LispObj idx = binding_index;
  if ((unsigned)idx >= (unsigned)limit) {
    idx = box_fixnum(0);
  }

  LispObj value = binding_slots[unbox_fixnum(idx)];
  if (value == (LispObj)no_thread_local_binding_marker) {
    value = sym->vcell;
  }

  wasm_set_reg(tcr, arg_y, symbol);
  wasm_set_reg(tcr, imm1, idx);
  wasm_set_reg(tcr, arg_z, value);
}

__attribute__((used, visibility("default"), export_name("_SPspecrefcheck")))
void
_SPspecrefcheck(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj symbol = wasm_reg(tcr, arg_z);
  lispsymbol *sym = wasm_symbol_or_trap(symbol);
  LispObj binding_index = sym->binding_index;
  if (tag_of(binding_index) != tag_fixnum) {
    wasm_subprims_trap();
  }

  LispObj limit = tcr->tlb_limit;
  if (tag_of(limit) != tag_fixnum) {
    wasm_subprims_trap();
  }

  LispObj *binding_slots = tcr->tlb_pointer;
  if (binding_slots == NULL) {
    wasm_subprims_trap();
  }

  LispObj idx = binding_index;
  if ((unsigned)idx >= (unsigned)limit) {
    idx = box_fixnum(0);
  }

  LispObj value = binding_slots[unbox_fixnum(idx)];
  if (value == (LispObj)no_thread_local_binding_marker) {
    value = sym->vcell;
  }

  if (value == (LispObj)unbound_marker) {
    wasm_set_reg(tcr, arg_z, symbol);
    wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XVUNBND));
    wasm_set_nargs_count(tcr, 2);
    _SPksignalerr();
    return;
  }

  wasm_set_reg(tcr, arg_y, symbol);
  wasm_set_reg(tcr, imm1, idx);
  wasm_set_reg(tcr, arg_z, value);
}

__attribute__((used, visibility("default"), export_name("_SPspecset")))
void
_SPspecset(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj symbol = wasm_reg(tcr, arg_y);
  lispsymbol *sym = wasm_symbol_or_trap(symbol);

  LispObj binding_index = sym->binding_index;
  if (tag_of(binding_index) != tag_fixnum) {
    wasm_subprims_trap();
  }

  LispObj limit = tcr->tlb_limit;
  if (tag_of(limit) != tag_fixnum) {
    wasm_subprims_trap();
  }

  LispObj *binding_slots = tcr->tlb_pointer;
  if (binding_slots == NULL) {
    wasm_subprims_trap();
  }

  signed_natural index = unbox_fixnum(binding_index);
  signed_natural limit_count = unbox_fixnum(limit);
  if (limit_count < 0) {
    wasm_subprims_trap();
  }

  if ((unsigned)index >= (unsigned)limit_count) {
    index = 0;
  }

  if (index > 0) {
    LispObj old_value = binding_slots[index];
    if (old_value != (LispObj)no_thread_local_binding_marker) {
      binding_slots[index] = wasm_reg(tcr, arg_z);
      return;
    }
  }

  sym->vcell = wasm_reg(tcr, arg_z);
}

__attribute__((used, visibility("default"), export_name("_SPsetqsym")))
void
_SPsetqsym(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj symbol = wasm_reg(tcr, arg_y);
  lispsymbol *sym = wasm_symbol_or_trap(symbol);

  LispObj flags = sym->flags;
  if (tag_of(flags) != tag_fixnum) {
    wasm_subprims_trap();
  }

  LispObj const_mask = (LispObj)1 << (1 + fixnum_shift);
  if ((flags & const_mask) != 0) {
    LispObj errdisp = wasm_nrs_symbol_lispobj(&nrs_ERRDISP);
    wasm_set_reg(tcr, arg_z, symbol);
    wasm_set_reg(tcr, arg_y, box_fixnum(115)); /* XCONST */
    wasm_set_nargs_count(tcr, 2);
    wasm_call_lisp_function(tcr, errdisp);
    return;
  }

  _SPspecset();
}

__attribute__((used, visibility("default"), export_name("_SPspreadargz")))
void
_SPspreadargz(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj list = wasm_reg(tcr, arg_z);
  LispObj orig_list = list;
  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *orig_vsp = stack_ptr;
  signed_natural orig_count = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, nargs));
  if (orig_count < 0) {
    wasm_subprims_trap();
  }

  LispObj *vsp_ptr = orig_vsp;
  signed_natural added = 0;

  while (list != (LispObj)nil_value) {
    if (tag_of(list) != tag_list) {
      wasm_set_reg(tcr, vsp, (LispObj)orig_vsp);
      tcr->save_vsp = orig_vsp;
      wasm_set_reg(tcr, arg_z, orig_list);
      wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XNOSPREAD));
      wasm_set_nargs_count(tcr, 2);
      _SPksignalerr();
      return;
    }

    cons *cell = (cons *)ptr_from_lispobj(untag(list));
    LispObj value = cell->car;
    list = cell->cdr;

    *--vsp_ptr = value;
    added++;
  }

  signed_natural total = orig_count + added;
  wasm_set_nargs_count(tcr, total);
  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
  wasm_vpop_argregs(tcr);
}

__attribute__((used, visibility("default"), export_name("_SPbind")))
void
_SPbind(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj symbol = wasm_reg(tcr, arg_y);
  lispsymbol *sym = wasm_symbol_or_trap(symbol);

  LispObj binding_index = sym->binding_index;
  signed_natural index = wasm_unbox_fixnum_or_trap(binding_index);
  if (index == 0) {
    wasm_set_reg(tcr, arg_z, symbol);
    wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XSYMNOBIND));
    wasm_set_nargs_count(tcr, 2);
    _SPksignalerr();
    return;
  }
  if (index < 0) {
    wasm_subprims_trap();
  }

  LispObj limit = tcr->tlb_limit;
  signed_natural limit_count = wasm_positive_fixnum_or_trap(limit);
  if ((unsigned)index >= (unsigned)limit_count) {
    wasm_subprims_trap();
  }

  LispObj *binding_slots = tcr->tlb_pointer;
  if (binding_slots == NULL) {
    wasm_subprims_trap();
  }

  LispObj old_value = binding_slots[index];
  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *new_vsp = stack_ptr - 3;
  new_vsp[0] = (LispObj)tcr->db_link;
  new_vsp[1] = binding_index;
  new_vsp[2] = old_value;

  binding_slots[index] = wasm_reg(tcr, arg_z);
  tcr->db_link = (special_binding *)new_vsp;
  tcr->save_vsp = new_vsp;
  wasm_set_reg(tcr, vsp, (LispObj)new_vsp);
}

__attribute__((used, visibility("default"), export_name("_SPbind_self")))
void
_SPbind_self(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj symbol = wasm_reg(tcr, arg_z);
  lispsymbol *sym = wasm_symbol_or_trap(symbol);

  LispObj binding_index = sym->binding_index;
  signed_natural index = wasm_unbox_fixnum_or_trap(binding_index);
  if (index == 0) {
    wasm_set_reg(tcr, arg_z, symbol);
    wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XSYMNOBIND));
    wasm_set_nargs_count(tcr, 2);
    _SPksignalerr();
    return;
  }
  if (index < 0) {
    wasm_subprims_trap();
  }

  LispObj limit = tcr->tlb_limit;
  signed_natural limit_count = wasm_positive_fixnum_or_trap(limit);
  if ((unsigned)index >= (unsigned)limit_count) {
    wasm_subprims_trap();
  }

  LispObj *binding_slots = tcr->tlb_pointer;
  if (binding_slots == NULL) {
    wasm_subprims_trap();
  }

  LispObj old_value = binding_slots[index];
  LispObj value = old_value;
  if (old_value == (LispObj)no_thread_local_binding_marker) {
    value = sym->vcell;
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *new_vsp = stack_ptr - 3;
  new_vsp[0] = (LispObj)tcr->db_link;
  new_vsp[1] = binding_index;
  new_vsp[2] = old_value;

  binding_slots[index] = value;
  tcr->db_link = (special_binding *)new_vsp;
  tcr->save_vsp = new_vsp;
  wasm_set_reg(tcr, vsp, (LispObj)new_vsp);
}

__attribute__((used, visibility("default"), export_name("_SPbind_nil")))
void
_SPbind_nil(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj symbol = wasm_reg(tcr, arg_z);
  wasm_set_reg(tcr, arg_y, symbol);
  wasm_set_reg(tcr, arg_z, (LispObj)nil_value);
  _SPbind();
}

__attribute__((used, visibility("default"), export_name("_SPbind_self_boundp_check")))
void
_SPbind_self_boundp_check(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj symbol = wasm_reg(tcr, arg_z);
  lispsymbol *sym = wasm_symbol_or_trap(symbol);

  LispObj binding_index = sym->binding_index;
  signed_natural index = wasm_unbox_fixnum_or_trap(binding_index);
  if (index == 0) {
    wasm_set_reg(tcr, arg_z, symbol);
    wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XSYMNOBIND));
    wasm_set_nargs_count(tcr, 2);
    _SPksignalerr();
    return;
  }
  if (index < 0) {
    wasm_subprims_trap();
  }

  LispObj limit = tcr->tlb_limit;
  signed_natural limit_count = wasm_positive_fixnum_or_trap(limit);
  if ((unsigned)index >= (unsigned)limit_count) {
    wasm_subprims_trap();
  }

  LispObj *binding_slots = tcr->tlb_pointer;
  if (binding_slots == NULL) {
    wasm_subprims_trap();
  }

  LispObj old_value = binding_slots[index];
  LispObj value = old_value;
  if (old_value == (LispObj)no_thread_local_binding_marker) {
    value = sym->vcell;
  }
  if (value == (LispObj)unbound_marker) {
    wasm_set_reg(tcr, arg_z, symbol);
    wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XVUNBND));
    wasm_set_nargs_count(tcr, 2);
    _SPksignalerr();
    return;
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *new_vsp = stack_ptr - 3;
  new_vsp[0] = (LispObj)tcr->db_link;
  new_vsp[1] = binding_index;
  new_vsp[2] = old_value;

  binding_slots[index] = value;
  tcr->db_link = (special_binding *)new_vsp;
  tcr->save_vsp = new_vsp;
  wasm_set_reg(tcr, vsp, (LispObj)new_vsp);
}

__attribute__((used, visibility("default"), export_name("_SPbind_interrupt_level_0")))
void
_SPbind_interrupt_level_0(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj *binding_slots = tcr->tlb_pointer;
  if (binding_slots == NULL) {
    wasm_subprims_trap();
  }
  LispObj old_value = binding_slots[INTERRUPT_LEVEL_BINDING_INDEX];

  wasm_bind_interrupt_level(tcr, box_fixnum(0));

  if (tag_of(old_value) == tag_fixnum && unbox_fixnum(old_value) < 0) {
    wasm_maybe_deliver_interrupt(tcr);
  }
}

__attribute__((used, visibility("default"), export_name("_SPbind_interrupt_level_m1")))
void
_SPbind_interrupt_level_m1(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  wasm_bind_interrupt_level(tcr, -box_fixnum(1));
}

__attribute__((used, visibility("default"), export_name("_SPbind_interrupt_level")))
void
_SPbind_interrupt_level(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj value = wasm_reg(tcr, arg_z);
  if (value == 0) {
    _SPbind_interrupt_level_0();
    return;
  }
  LispObj *binding_slots = tcr->tlb_pointer;
  if (binding_slots == NULL) {
    wasm_subprims_trap();
  }
  LispObj old_value = binding_slots[INTERRUPT_LEVEL_BINDING_INDEX];
  wasm_bind_interrupt_level(tcr, value);
  if (tag_of(old_value) == tag_fixnum && unbox_fixnum(old_value) < 0) {
    if (tag_of(value) == tag_fixnum && unbox_fixnum(value) >= 0) {
      wasm_maybe_deliver_interrupt(tcr);
    }
  }
}

__attribute__((used, visibility("default"), export_name("_SPunbind_interrupt_level")))
void
_SPunbind_interrupt_level(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  special_binding *current_binding = tcr->db_link;
  LispObj *binding_slots = tcr->tlb_pointer;
  if (current_binding == NULL || binding_slots == NULL) {
    wasm_subprims_trap();
  }

  LispObj old_value = binding_slots[INTERRUPT_LEVEL_BINDING_INDEX];
  LispObj symidx = (LispObj)current_binding->sym;
  LispObj value = current_binding->value;
  current_binding = current_binding->link;

  binding_slots[wasm_unbox_fixnum_or_trap(symidx)] = value;
  tcr->db_link = current_binding;

  if (tag_of(old_value) == tag_fixnum && unbox_fixnum(old_value) < 0) {
    if (tag_of(value) == tag_fixnum && unbox_fixnum(value) >= 0) {
      wasm_maybe_deliver_interrupt(tcr);
    }
  }
}

__attribute__((used, visibility("default"), export_name("_SPunbind")))
void
_SPunbind(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  special_binding *current_binding = tcr->db_link;
  LispObj *binding_slots = tcr->tlb_pointer;
  if (current_binding == NULL || binding_slots == NULL) {
    wasm_subprims_trap();
  }

  LispObj symidx = (LispObj)current_binding->sym;
  LispObj value = current_binding->value;
  current_binding = current_binding->link;

  binding_slots[wasm_unbox_fixnum_or_trap(symidx)] = value;
  tcr->db_link = current_binding;
}

static void
wasm_bind_interrupt_level(TCR *tcr, LispObj new_value)
{
  LispObj limit = tcr->tlb_limit;
  signed_natural limit_count = wasm_positive_fixnum_or_trap(limit);

  if ((unsigned)INTERRUPT_LEVEL_BINDING_INDEX >= (unsigned)limit_count) {
    wasm_subprims_trap();
  }

  LispObj *binding_slots = tcr->tlb_pointer;
  if (binding_slots == NULL) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *new_vsp = stack_ptr - 3;
  LispObj old_value = binding_slots[INTERRUPT_LEVEL_BINDING_INDEX];
  new_vsp[0] = (LispObj)tcr->db_link;
  new_vsp[1] = box_fixnum(INTERRUPT_LEVEL_BINDING_INDEX);
  new_vsp[2] = old_value;

  binding_slots[INTERRUPT_LEVEL_BINDING_INDEX] = new_value;
  tcr->db_link = (special_binding *)new_vsp;
  tcr->save_vsp = new_vsp;
  wasm_set_reg(tcr, vsp, (LispObj)new_vsp);
}

static void
wasm_maybe_deliver_interrupt(TCR *tcr)
{
  if (tcr == NULL) {
    return;
  }
  if (tcr->interrupt_pending <= 0) {
    return;
  }

  LispObj *tlb = tcr->tlb_pointer;
  if (tlb == NULL) {
    return;
  }
  LispObj level = tlb[INTERRUPT_LEVEL_BINDING_INDEX];
  if (tag_of(level) != tag_fixnum || unbox_fixnum(level) < 0) {
    return;
  }

  wasm_set_reg(tcr, arg_z, (LispObj)nil_value);
  wasm_set_nargs_count(tcr, 0);
  wasm_call_lisp_function(tcr, wasm_nrs_symbol_lispobj(&nrs_CMAIN));
}

__attribute__((used, visibility("default"), export_name("_SPunbind_n")))
void
_SPunbind_n(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  signed_natural count = (signed_natural)wasm_reg(tcr, imm0);
  if (count < 0) {
    wasm_subprims_trap();
  }
  if (count == 0) {
    return;
  }

  special_binding *current_binding = tcr->db_link;
  LispObj *binding_slots = tcr->tlb_pointer;
  if (current_binding == NULL || binding_slots == NULL) {
    wasm_subprims_trap();
  }

  while (count-- > 0) {
    if (current_binding == NULL) {
      wasm_subprims_trap();
    }
    LispObj symidx = (LispObj)current_binding->sym;
    LispObj value = current_binding->value;
    current_binding = current_binding->link;
    binding_slots[wasm_unbox_fixnum_or_trap(symidx)] = value;
  }

  tcr->db_link = current_binding;
}

__attribute__((used, visibility("default"), export_name("_SPunbind_to")))
void
_SPunbind_to(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  special_binding *target = (special_binding *)wasm_reg(tcr, imm0);
  wasm_unbind_to(tcr, target);
}

__attribute__((used, visibility("default"), export_name("_SPprogvsave")))
void
_SPprogvsave(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj values = wasm_reg(tcr, arg_z);
  if (!wasm_list_is_proper(values)) {
    wasm_set_reg(tcr, arg_y, box_fixnum(170)); /* XIMPROPERLIST */
    wasm_set_nargs_count(tcr, 2);
    _SPksignalerr();
    return;
  }

  LispObj symbols = wasm_reg(tcr, arg_y);
  LispObj *binding_slots = tcr->tlb_pointer;
  if (binding_slots == NULL) {
    wasm_subprims_trap();
  }

  signed_natural limit_count = wasm_positive_fixnum_or_trap(tcr->tlb_limit);

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj *saved_stack_ptr = vsp_ptr;
  special_binding *old_db = tcr->db_link;

  vsp_ptr -= 3;
  vsp_ptr[0] = (LispObj)old_db;
  vsp_ptr[1] = (LispObj)unbound_marker;
  vsp_ptr[2] = (LispObj)saved_stack_ptr;
  special_binding *db = (special_binding *)vsp_ptr;

  LispObj sym_list = symbols;
  LispObj val_list = values;

  while (sym_list != (LispObj)nil_value) {
    if (tag_of(sym_list) != tag_list) {
      wasm_subprims_trap();
    }
    cons *sym_cell = (cons *)ptr_from_lispobj(untag(sym_list));
    LispObj sym_obj = sym_cell->car;
    sym_list = sym_cell->cdr;

    lispsymbol *sym = wasm_symbol_or_trap(sym_obj);
    LispObj binding_index = sym->binding_index;
    signed_natural index = wasm_positive_fixnum_or_trap(binding_index);
    if ((unsigned)index >= (unsigned)limit_count) {
      wasm_subprims_trap();
    }

    LispObj old_value = binding_slots[index];
    LispObj new_value = (LispObj)unbound_marker;

    if (val_list != (LispObj)nil_value) {
      if (tag_of(val_list) != tag_list) {
        wasm_subprims_trap();
      }
      cons *val_cell = (cons *)ptr_from_lispobj(untag(val_list));
      new_value = val_cell->car;
      val_list = val_cell->cdr;
    }

    vsp_ptr -= 3;
    vsp_ptr[0] = (LispObj)db;
    vsp_ptr[1] = binding_index;
    vsp_ptr[2] = old_value;
    db = (special_binding *)vsp_ptr;

    binding_slots[index] = new_value;
  }

  tcr->db_link = db;
  tcr->save_vsp = vsp_ptr;
  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);

  /* Install cleanup entrypoint for unwind-protect: _SPprogvrestore. */
  wasm_set_reg(tcr, imm0, box_fixnum(WASM_SUBPRIM_PROGVRESTORE_INDEX));
  _SPmkunwind();
}

__attribute__((used, visibility("default"), export_name("_SPprogvrestore")))
void
_SPprogvrestore(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj *binding_slots = tcr->tlb_pointer;
  if (binding_slots == NULL) {
    wasm_subprims_trap();
  }

  special_binding *current_binding = tcr->db_link;
  while (current_binding != NULL) {
    LispObj symidx = (LispObj)current_binding->sym;
    if (symidx == (LispObj)unbound_marker) {
      special_binding *old_db = current_binding->link;
      LispObj *saved_stack_ptr = (LispObj *)current_binding->value;
      if (saved_stack_ptr == NULL) {
        wasm_subprims_trap();
      }
      tcr->db_link = old_db;
      tcr->save_vsp = saved_stack_ptr;
      wasm_set_reg(tcr, vsp, (LispObj)saved_stack_ptr);
      return;
    }

    LispObj value = current_binding->value;
    current_binding = current_binding->link;
    binding_slots[wasm_unbox_fixnum_or_trap(symidx)] = value;
  }

  wasm_subprims_trap();
}

__attribute__((used, visibility("default"), export_name("_SPcall_closure")))
void
_SPcall_closure(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj closure = wasm_reg(tcr, nfn);
  if (fulltag_of(closure) != fulltag_misc || header_subtag(header_of(closure)) != subtag_function) {
    wasm_subprims_trap();
  }

  signed_natural argc = wasm_unbox_fixnum_or_trap(wasm_reg(tcr, nargs));
  if (argc < 0) {
    wasm_subprims_trap();
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  int vsp_has_args = 0;
  if (argc > 0) {
    vsp_has_args = (vsp_ptr[0] == wasm_reg(tcr, arg_z));
    if (argc > 1) {
      vsp_has_args = vsp_has_args && (vsp_ptr[1] == wasm_reg(tcr, arg_y));
    }
    if (argc > 2) {
      vsp_has_args = vsp_has_args && (vsp_ptr[2] == wasm_reg(tcr, arg_x));
    }
  }

  if (!vsp_has_args && argc <= 3) {
    wasm_vpush_argregs(tcr);
    stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
    if (stack_ptr == NULL) {
      wasm_subprims_trap();
    }
    vsp_ptr = stack_ptr;
  }

  LispObj header = header_of(closure);
  signed_natural element_count = header_element_count(header);
  signed_natural inherited = element_count - 5;
  if (inherited < 0) {
    inherited = 0;
  }

  if (inherited > 0) {
    LispObj *new_vsp = vsp_ptr - inherited;
    signed_natural total = inherited + argc;

    /* Copy explicit args (currently reversed on the vstack) into call order. */
    LispObj explicit_args[3];
    LispObj *explicit = explicit_args;
    if (argc > 3) {
      explicit = (LispObj *)__builtin_alloca((size_t)argc * sizeof(LispObj));
    }
    for (signed_natural i = 0; i < argc; i++) {
      explicit[i] = vsp_ptr[argc - 1 - i];
    }

    LispObj *combined = (LispObj *)__builtin_alloca((size_t)total * sizeof(LispObj));
    for (signed_natural i = 0; i < inherited; i++) {
      combined[i] = deref(closure, 4 + i);
    }
    for (signed_natural i = 0; i < argc; i++) {
      combined[inherited + i] = explicit[i];
    }

    for (signed_natural i = 0; i < total; i++) {
      new_vsp[i] = combined[total - 1 - i];
    }

    vsp_ptr = new_vsp;
    wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
    tcr->save_vsp = vsp_ptr;
    wasm_set_nargs_count(tcr, total);

    /* CCL calling convention: last min(nargs, 3) args go in arg_z/arg_y/arg_x,
       NOT on the vstack.  The ARM _SPcall_closure sets registers directly for
       total <= nargregs, and calls vpop_all_argregs for total > nargregs.
       We use wasm_vpop_argregs to pop the register args off the vstack. */
    wasm_vpop_argregs(tcr);
  }

  /* On ARM, _SPcall_closure tail-jumps into the inner function (fn)
     via vrefr(nfn,nfn,2) then ldr pc,[nfn,entrypoint] — a GOTO.
     On WASM, we can't tail-jump; instead RETURN so the compiled WASM
     code after `call _SPcall_closure` (the function body) executes.

     Closure layout (ARM comment: "first three = entrypoint, closure
     code, fn; last two = name, lfbits"):
       deref(closure, 1) = entrypoint (fixnum)
       deref(closure, 2) = closure code (code_vector)
       deref(closure, 3) = fn (inner function) ← nfn target
       deref(closure, 4..ec-2) = inherited bindings
       deref(closure, ec-1) = name
       deref(closure, ec) = lfun-bits

     ARM: vrefr(nfn,nfn,2) = element 2 (0-indexed) = deref(closure, 3). */
  LispObj target_fn = deref(closure, 3);
  wasm_set_reg(tcr, nfn, target_fn);
  /* Do NOT call _SPfuncall — just return into the body code. */
  return;
}

__attribute__((used, visibility("default"), export_name("_SPkeyword_bind")))
void
_SPkeyword_bind(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  LispObj raw_prev = wasm_reg(tcr, imm0);
  LispObj keyword_flags = wasm_reg(tcr, arg_y);
  if (tag_of(raw_nargs) != tag_fixnum || tag_of(raw_prev) != tag_fixnum || tag_of(keyword_flags) != tag_fixnum) {
    wasm_subprims_trap();
  }

  signed_natural nargs_count = unbox_fixnum(raw_nargs);
  signed_natural prev_count = unbox_fixnum(raw_prev);
  if (nargs_count < 0 || prev_count < 0) {
    wasm_subprims_trap();
  }

  signed_natural key_value_count = nargs_count - prev_count;
  if (key_value_count < 0) {
    key_value_count = 0;
  }
  if (key_value_count & 1) {
    wasm_set_nargs_count(tcr, key_value_count);
    _SPconslist();
    wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XBADKEYS));
    wasm_set_nargs_count(tcr, 2);
    _SPksignalerr();
    return;
  }

  LispObj fn_obj = wasm_reg(tcr, Rfn);
  if (fulltag_of(fn_obj) != fulltag_misc) {
    wasm_subprims_trap();
  }

  LispObj keyvec = deref(fn_obj, 3);
  signed_natural keyvec_len = 0;
  if (keyvec != (LispObj)nil_value) {
    if (fulltag_of(keyvec) != fulltag_misc) {
      wasm_subprims_trap();
    }
    keyvec_len = header_element_count(header_of(keyvec));
    if (keyvec_len < 0 || keyvec_len > 256) {
      wasm_subprims_trap();
    }
  }

  LispObj values[256];
  LispObj supplied[256];
  for (signed_natural i = 0; i < keyvec_len; i++) {
    values[i] = (LispObj)nil_value;
    supplied[i] = (LispObj)nil_value;
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *vsp_ptr = stack_ptr;
  LispObj *pairs_base = vsp_ptr;
  LispObj *pairs_copy = NULL;
  signed_natural pair_count = key_value_count / 2;
  if ((keyword_flags & WASM_KEYWORD_FLAG_REST) && key_value_count > 0) {
    pairs_copy = (LispObj *)__builtin_alloca((size_t)key_value_count * sizeof(LispObj));
    memcpy(pairs_copy, pairs_base, (size_t)key_value_count * sizeof(LispObj));
  }

  LispObj allow_key = wasm_nrs_symbol_lispobj(&nrs_KALLOWOTHERKEYS);
  int allow_other = (keyword_flags & WASM_KEYWORD_FLAG_ALLOW_OTHER_KEYS) != 0;
  int saw_aok = 0;
  int unknown = 0;

  for (signed_natural j = 0; j < pair_count; j++) {
    signed_natural key_idx = key_value_count - 1 - (2 * j);
    signed_natural val_idx = key_value_count - 2 - (2 * j);
    LispObj key = pairs_base[key_idx];
    LispObj val = pairs_base[val_idx];

    if (key == allow_key) {
      if (!saw_aok) {
        saw_aok = 1;
        if (val != (LispObj)nil_value) {
          allow_other = 1;
        }
      }
      continue;
    }

    signed_natural found = -1;
    for (signed_natural i = 0; i < keyvec_len; i++) {
      if (deref(keyvec, 1 + i) == key) {
        found = i;
        break;
      }
    }
    if (found < 0) {
      if (!allow_other) {
        unknown = 1;
      }
      continue;
    }
    if (supplied[found] == (LispObj)nil_value) {
      supplied[found] = wasm_t_value();
      values[found] = val;
    }
  }

  if (unknown && !allow_other) {
    wasm_set_nargs_count(tcr, key_value_count);
    _SPconslist();
    wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XBADKEYS));
    wasm_set_nargs_count(tcr, 2);
    _SPksignalerr();
    return;
  }

  if (key_value_count > 0) {
    vsp_ptr += key_value_count;
  }

  for (signed_natural i = 0; i < keyvec_len; i++) {
    *--vsp_ptr = values[i];
    *--vsp_ptr = supplied[i];
  }

  if (keyword_flags & WASM_KEYWORD_FLAG_REST) {
    for (signed_natural j = 0; j < pair_count; j++) {
      signed_natural key_idx = key_value_count - 1 - (2 * j);
      signed_natural val_idx = key_value_count - 2 - (2 * j);
      LispObj key = pairs_copy ? pairs_copy[key_idx] : pairs_base[key_idx];
      LispObj val = pairs_copy ? pairs_copy[val_idx] : pairs_base[val_idx];
      *--vsp_ptr = key;
      *--vsp_ptr = val;
    }
  }

  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
}

__attribute__((used, visibility("default"), export_name("_SPdebind")))
void
_SPdebind(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  LispObj arg_reg = wasm_reg(tcr, arg_z);
  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();
  }
  LispObj *orig_vsp = stack_ptr;
  LispObj *vsp_ptr = orig_vsp;
  LispObj orig_list = arg_reg;

  uint32_t raw = (uint32_t)wasm_reg(tcr, nargs);
  uint32_t req_count = raw & 0xffu;
  uint32_t opt_count = (raw >> 8) & 0xffu;
  uint32_t key_count = (raw >> 16) & 0xffu;

  LispObj nil = (LispObj)nil_value;
  LispObj tval = wasm_t_value();

  for (uint32_t i = 0; i < req_count; i++) {
    if (arg_reg == nil) {
      wasm_set_reg(tcr, vsp, (LispObj)orig_vsp);
      tcr->save_vsp = orig_vsp;
      wasm_set_reg(tcr, arg_z, orig_list);
      wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XCALLTOOFEW));
      wasm_set_nargs_count(tcr, 2);
      _SPksignalerr();
      return;
    }
    if (tag_of(arg_reg) != tag_list) {
      wasm_set_reg(tcr, vsp, (LispObj)orig_vsp);
      tcr->save_vsp = orig_vsp;
      wasm_set_reg(tcr, arg_z, orig_list);
      wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XCALLNOMATCH));
      wasm_set_nargs_count(tcr, 2);
      _SPksignalerr();
      return;
    }
    cons *cell = (cons *)ptr_from_lispobj(untag(arg_reg));
    *--vsp_ptr = cell->car;
    arg_reg = cell->cdr;
  }

  if (opt_count > 0) {
    if (raw & WASM_DEBIND_MASK_INITOPT) {
      for (uint32_t i = 0; i < opt_count; i++) {
        if (arg_reg == nil) {
          *--vsp_ptr = nil;
          *--vsp_ptr = nil;
          continue;
        }
        if (tag_of(arg_reg) != tag_list) {
          wasm_set_reg(tcr, vsp, (LispObj)orig_vsp);
          tcr->save_vsp = orig_vsp;
          wasm_set_reg(tcr, arg_z, orig_list);
          wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XCALLNOMATCH));
          wasm_set_nargs_count(tcr, 2);
          _SPksignalerr();
          return;
        }
        cons *cell = (cons *)ptr_from_lispobj(untag(arg_reg));
        *--vsp_ptr = cell->car;
        *--vsp_ptr = tval;
        arg_reg = cell->cdr;
      }
    } else {
      for (uint32_t i = 0; i < opt_count; i++) {
        if (arg_reg == nil) {
          *--vsp_ptr = nil;
          continue;
        }
        if (tag_of(arg_reg) != tag_list) {
          wasm_set_reg(tcr, vsp, (LispObj)orig_vsp);
          tcr->save_vsp = orig_vsp;
          wasm_set_reg(tcr, arg_z, orig_list);
          wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XCALLNOMATCH));
          wasm_set_nargs_count(tcr, 2);
          _SPksignalerr();
          return;
        }
        cons *cell = (cons *)ptr_from_lispobj(untag(arg_reg));
        *--vsp_ptr = cell->car;
        arg_reg = cell->cdr;
      }
    }
  }

  if (raw & WASM_DEBIND_MASK_RESTP) {
    *--vsp_ptr = arg_reg;
    if (!(raw & WASM_DEBIND_MASK_KEYP)) {
      wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
      tcr->save_vsp = vsp_ptr;
      return;
    }
  } else if (!(raw & WASM_DEBIND_MASK_KEYP)) {
    if (arg_reg != nil) {
      wasm_set_reg(tcr, vsp, (LispObj)orig_vsp);
      tcr->save_vsp = orig_vsp;
      wasm_set_reg(tcr, arg_z, orig_list);
      wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XCALLTOOMANY));
      wasm_set_nargs_count(tcr, 2);
      _SPksignalerr();
      return;
    }
    wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
    tcr->save_vsp = vsp_ptr;
    return;
  }

  LispObj key_list = arg_reg;
  int limit = 256;
  while (key_list != nil) {
    if (limit-- <= 0) {
      wasm_set_reg(tcr, vsp, (LispObj)orig_vsp);
      tcr->save_vsp = orig_vsp;
      wasm_set_reg(tcr, arg_z, orig_list);
      wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XCALLTOOMANY));
      wasm_set_nargs_count(tcr, 2);
      _SPksignalerr();
      return;
    }
    if (tag_of(key_list) != tag_list) {
      wasm_set_reg(tcr, vsp, (LispObj)orig_vsp);
      tcr->save_vsp = orig_vsp;
      wasm_set_reg(tcr, arg_z, orig_list);
      wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XCALLNOMATCH));
      wasm_set_nargs_count(tcr, 2);
      _SPksignalerr();
      return;
    }
    cons *cell = (cons *)ptr_from_lispobj(untag(key_list));
    key_list = cell->cdr;
    if (key_list == nil) {
      wasm_set_reg(tcr, vsp, (LispObj)orig_vsp);
      tcr->save_vsp = orig_vsp;
      wasm_set_reg(tcr, arg_z, orig_list);
      wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XBADKEYS));
      wasm_set_nargs_count(tcr, 2);
      _SPksignalerr();
      return;
    }
    if (tag_of(key_list) != tag_list) {
      wasm_set_reg(tcr, vsp, (LispObj)orig_vsp);
      tcr->save_vsp = orig_vsp;
      wasm_set_reg(tcr, arg_z, orig_list);
      wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XCALLNOMATCH));
      wasm_set_nargs_count(tcr, 2);
      _SPksignalerr();
      return;
    }
    cell = (cons *)ptr_from_lispobj(untag(key_list));
    key_list = cell->cdr;
  }

  LispObj keyvec = wasm_reg(tcr, nfn);
  signed_natural keyvec_len = 0;
  if (keyvec != nil) {
    if (fulltag_of(keyvec) != fulltag_misc) {
      wasm_subprims_trap();
    }
    keyvec_len = header_element_count(header_of(keyvec));
    if (keyvec_len < 0 || keyvec_len > 256) {
      wasm_subprims_trap();
    }
  }

  if ((signed_natural)key_count < keyvec_len) {
    keyvec_len = (signed_natural)key_count;
  }

  LispObj values[256];
  LispObj supplied[256];
  for (signed_natural i = 0; i < keyvec_len; i++) {
    values[i] = nil;
    supplied[i] = nil;
  }

  LispObj allow_key = wasm_nrs_symbol_lispobj(&nrs_KALLOWOTHERKEYS);
  int allow_other = (raw & WASM_DEBIND_MASK_AOK) != 0;
  int saw_aok = 0;
  int unknown = 0;

  key_list = arg_reg;
  while (key_list != nil) {
    cons *cell = (cons *)ptr_from_lispobj(untag(key_list));
    LispObj key = cell->car;
    key_list = cell->cdr;
    cell = (cons *)ptr_from_lispobj(untag(key_list));
    LispObj val = cell->car;
    key_list = cell->cdr;

    if (key == allow_key) {
      if (!saw_aok) {
        saw_aok = 1;
        if (val != nil) {
          allow_other = 1;
        }
      }
      continue;
    }

    signed_natural found = -1;
    for (signed_natural i = 0; i < keyvec_len; i++) {
      if (deref(keyvec, 1 + i) == key) {
        found = i;
        break;
      }
    }
    if (found < 0) {
      if (!allow_other) {
        unknown = 1;
      }
      continue;
    }
    if (supplied[found] == nil) {
      supplied[found] = tval;
      values[found] = val;
    }
  }

  if (unknown && !allow_other) {
    wasm_set_reg(tcr, vsp, (LispObj)orig_vsp);
    tcr->save_vsp = orig_vsp;
    wasm_set_reg(tcr, arg_z, orig_list);
    wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XBADKEYS));
    wasm_set_nargs_count(tcr, 2);
    _SPksignalerr();
    return;
  }

  for (signed_natural i = 0; i < keyvec_len; i++) {
    *--vsp_ptr = values[i];
    *--vsp_ptr = supplied[i];
  }

  wasm_set_reg(tcr, vsp, (LispObj)vsp_ptr);
  tcr->save_vsp = vsp_ptr;
}

__attribute__((used, visibility("default"), export_name("_SPeabi_ff_call_simple")))
void
_SPeabi_ff_call_simple(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  wasm_signal_capability_unavailable(tcr, ":foreign/ffi", "CALL-SIMPLE", NULL);
}

__attribute__((used, visibility("default"), export_name("_SPeabi_ff_callhf")))
void
_SPeabi_ff_callhf(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  wasm_signal_capability_unavailable(tcr, ":foreign/ffi", "CALL-HF", NULL);
}

__attribute__((used, visibility("default"), export_name("_SPeabi_callback")))
void
_SPeabi_callback(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }
  wasm_signal_capability_unavailable(tcr, ":foreign/ffi", "CALLBACK", NULL);
}

__attribute__((used, visibility("default"), export_name("_SPudiv32")))
void
_SPudiv32(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  uint32_t denom = (uint32_t)wasm_reg(tcr, imm1);
  if (denom == 0) {
    wasm_subprims_trap();
  }

  uint32_t numer = (uint32_t)wasm_reg(tcr, imm0);
  uint32_t quot = numer / denom;
  uint32_t rem = numer % denom;
  wasm_set_reg(tcr, imm0, (LispObj)quot);
  wasm_set_reg(tcr, imm1, (LispObj)rem);
}

__attribute__((used, visibility("default"), export_name("_SPsdiv32")))
void
_SPsdiv32(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    wasm_subprims_trap();
  }

  int32_t denom = (int32_t)wasm_reg(tcr, imm1);
  if (denom == 0) {
    int32_t numer = (int32_t)wasm_reg(tcr, imm0);
    wasm_set_reg(tcr, arg_z, wasm_box_i64_prefer_fixnum(tcr, (int64_t)numer));
    wasm_set_reg(tcr, arg_y, box_fixnum(WASM_XDIVZRO));
    wasm_set_nargs_count(tcr, 2);
    _SPksignalerr();
    return;
  }

  int32_t numer = (int32_t)wasm_reg(tcr, imm0);
  int32_t quot = 0;
  int32_t rem = 0;
  if (numer == INT32_MIN && denom == -1) {
    quot = numer;
    rem = 0;
  } else {
    quot = numer / denom;
    rem = numer % denom;
  }
  wasm_set_reg(tcr, imm0, (LispObj)quot);
  wasm_set_reg(tcr, imm1, (LispObj)rem);
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
  wasm_set_reg(tcr, arg_z, wasm_box_i64_prefer_fixnum(tcr, (int64_t)val));
  wasm_set_nargs_count(tcr, 1);
}

/* Trap stub for null table entries.  Installed by JS host into all
   unoccupied slots of the indirect-function table so that call_indirect
   produces a diagnosable Lisp error instead of an opaque "unreachable". */
__attribute__((used, visibility("default"), export_name("_SPentry_not_installed")))
void
_SPentry_not_installed(void)
{
  TCR *tcr = wasm_get_current_tcr();
  char msg[80]; unsigned p = 0;
  p = wasm_diag_append_str(msg, p, "ENTRY NOT INSTALLED fn=0x");
  { LispObj fn = tcr ? wasm_reg(tcr, nfn) : 0;
    p = wasm_diag_append_hex32(msg, p, (uint32_t)fn); }
  p = wasm_diag_append_str(msg, p, " nargs=0x");
  { LispObj na = tcr ? wasm_reg(tcr, nargs) : 0;
    p = wasm_diag_append_hex32(msg, p, (uint32_t)na); }
  msg[p++] = '\n';
  wasm_host_log(msg, p);

  if (tcr) {
    wasm_signal_funcall_error(tcr, WASM_XNOTFUN, wasm_reg(tcr, nfn));
  } else {
    __builtin_trap();
  }
}
#endif
