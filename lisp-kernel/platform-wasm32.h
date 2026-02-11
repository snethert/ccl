/*
 * Copyright 1994-2010 Clozure Associates
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#define WORD_SIZE 32
#define WASM_PAGE_SIZE (1<<16)
#ifndef WASM_ALLOW_MEMORY_GROWTH
#define WASM_ALLOW_MEMORY_GROWTH 1
#endif
#define PLATFORM_OS PLATFORM_OS_WASM
#define PLATFORM_CPU PLATFORM_CPU_WASM
#define PLATFORM_WORD_SIZE PLATFORM_WORD_SIZE_32

#define MAXIMUM_MAPPABLE_MEMORY 0xFFFFFFFFU
#define IMAGE_BASE_ADDRESS 0x0
#define WASM_DEFAULT_CSTACK_SIZE (1<<20)

#include "lisptypes.h"

typedef uint8_t opcode, *pc;

/* Legacy constants header references ExceptionInformation via pointers (TCR fields).
 * Forward-declare it before including the bridge header, then provide the
 * wasm32 definition below.
 */
typedef struct ExceptionInformation ExceptionInformation;

#include "wasm-constants-bridge.h"

/* Transitional wasm32 GPR aliases. These decouple wasm GC/runtime code from
 * direct use of legacy register-name macros while preserving current indices.
 */
enum {
  wasm_gpr_arg_z = arg_z,
  wasm_gpr_arg_y = arg_y,
  wasm_gpr_arg_x = arg_x,
  wasm_gpr_fn = Rfn
};

/* Placeholder for wasm32 bring-up; no OS ucontext or trap frame yet.
 * When completed, this will reflect a real wasm trap/interrupt context
 * (e.g., a runtime-provided register snapshot and PC/stack state).
 */
struct ExceptionInformation {
  natural gpr[16];
  natural pc;
};

#ifndef WASM_SPILL_STACK_WORDS
#define WASM_SPILL_STACK_WORDS (1u << 15)
#endif

/* xp accessors (stubs for wasm32). */
#define xpGPRvector(x) ((natural *)&((x)->gpr[0]))
#define xpGPR(x,gprno) (xpGPRvector(x)[gprno])
#define set_xpGPR(x,gpr,new) (xpGPR((x),(gpr)) = (natural)(new))
/* xpPC/xpLR must be lvalues: GC updates them in place. */
#define xpPC(x) (*(pc *)&((x)->pc))
#define set_xpPC(x,new) (xpPC(x) = (pc)(new))
#define xpLR(x) (*(pc *)&((x)->gpr[14]))

#define SIGNUM_FOR_INTN_TRAP 0
#define IS_MAYBE_INT_TRAP(info,xp) (0)
#define IS_PAGE_FAULT(info,xp) (0)
#define SIGRETURN(context)

#define PROTECT_CSTACK 0

/* Manual stack hooks for wasm hosts. */
void wasm_set_current_tcr(TCR *tcr);
TCR *wasm_get_current_tcr(void);
#define WASM_USE_GLOBAL_TCR 1

static inline TCR *wasm_get_tcr(Boolean create)
{
#if WASM_USE_GLOBAL_TCR
  (void)create;
  return wasm_get_current_tcr();
#else
  return get_tcr(create);
#endif
}

void wasm_set_cstack_bounds(void *base, natural size);
void wasm_set_cstack_pointer(void *sp);
void *wasm_get_cstack_pointer(void);
void wasm_relocate_cstack(void *new_base);
int32_t wasm_memory_grow_and_relocate(uint32_t pages);
int wasm_grow_cstack(natural min_bytes);

enum {
  WASM_GC_ROOT_INCLUDE_XP_LOCATIVES = (1u << 0),
  WASM_GC_ROOT_INCLUDE_CSTACK = (1u << 1),
  WASM_GC_ROOT_INCLUDE_CSTACK_SAVEVSP = (1u << 2),
  WASM_GC_ROOT_INCLUDE_TCR_GC_CONTEXT = (1u << 3),
  WASM_GC_ROOT_INCLUDE_TCR_XFRAMES = (1u << 4),
  WASM_GC_ROOT_INCLUDE_TCR_TLB = (1u << 5)
};

#define WASM_GC_ROOT_POLICY_DEFAULT \
  (WASM_GC_ROOT_INCLUDE_XP_LOCATIVES | \
   WASM_GC_ROOT_INCLUDE_CSTACK | \
   WASM_GC_ROOT_INCLUDE_CSTACK_SAVEVSP | \
   WASM_GC_ROOT_INCLUDE_TCR_GC_CONTEXT | \
   WASM_GC_ROOT_INCLUDE_TCR_XFRAMES | \
   WASM_GC_ROOT_INCLUDE_TCR_TLB)

#define WASM_GC_ROOT_POLICY_BOOTSTRAP \
  (WASM_GC_ROOT_POLICY_DEFAULT & ~WASM_GC_ROOT_INCLUDE_CSTACK_SAVEVSP)

enum {
  WASM_GC_ROOT_MODE_RUNTIME_DEFAULT = 0u,
  WASM_GC_ROOT_MODE_RUNTIME_BOOTSTRAP = 1u,
  WASM_GC_ROOT_MODE_HOST_MASK = 2u
};

enum {
  WASM_ENTRY_CALL_ABI_LEGACY = 0u,
  WASM_ENTRY_CALL_ABI_UNARY_I32 = 1u,
  WASM_ENTRY_CALL_ABI_BINARY_I32 = 2u
};

void wasm_publish_gc_root_policy(uint32_t policy_mask);
uint32_t wasm_current_gc_root_policy(void);
void wasm_reset_gc_root_policy(void);
void wasm_publish_gc_root_policy_mode(uint32_t mode);
uint32_t wasm_current_gc_root_policy_mode(void);
void wasm_reset_gc_root_policy_mode(void);
void wasm_register_entry_gc_root_policy_mode(uint32_t entry_index, uint32_t mode);
uint32_t wasm_lookup_entry_gc_root_policy_mode(uint32_t entry_index);
void wasm_clear_entry_gc_root_policy_modes(void);
void wasm_register_entry_call_abi_kind(uint32_t entry_index, uint32_t kind);
uint32_t wasm_lookup_entry_call_abi_kind(uint32_t entry_index);
void wasm_clear_entry_call_abi_kinds(void);
uint32_t wasm_gc_forwarding_selftest(void);
uint32_t wasm_cstack_frame_coherence_selftest(void);
uint32_t wasm_subprim_nonlocal_exit_coherence_selftest(void);

natural wasm_cstack_push_frame(TCR *tcr, LispObj savefn, pc savelr, LispObj savevsp);
void wasm_cstack_pop_frame(TCR *tcr, natural old_last_lisp_frame);
BytePtr wasm_cstack_push_alloc_marker(TCR *tcr, LispObj next);
void wasm_cstack_pop_alloc_marker(TCR *tcr, BytePtr old_sp);
Boolean lisp_frame_p(lisp_frame *spPtr);
natural wasm_enter_lisp_frame(TCR *tcr, LispObj savefn, pc savelr, LispObj savevsp);
void wasm_exit_lisp_frame(TCR *tcr, natural old_last_lisp_frame);

/* Host logging hook (required import). */
__attribute__((import_module("env"), import_name("wasm_host_log")))
void wasm_host_log(const char *bytes, unsigned len);
