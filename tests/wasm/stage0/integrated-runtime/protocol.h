#ifndef CCL_STAGE0_PROTOCOL_H
#define CCL_STAGE0_PROTOCOL_H
typedef unsigned int u32;
typedef unsigned long long u64;
typedef struct { u32 previous, count, values[8]; } Root;
typedef struct {
  u32 prefix[6], root_head, binding_depth, vsp, tsp, csp, nvalues;
  u32 mv_base, mv_owner_top, base_reserved[18];
  u32 state, pending, id, lifetime, admitted, requests, root_slot, stops;
  u32 interrupts, reloads, allocation_checks, cleanup, nested, retire_serial;
  u32 reclaimed, mode, active_request, old_root, observed_root, observed_raw;
  u32 continuation, handler_cookie, binding_cookie, progress, reserved[8];
} Thread;
typedef struct {
  u32 opcode, owner_lifetime;
  union { u64 wake_generation; struct {u32 wake, generation;}; };
  u32 outcome, result, active;
  u32 cancel_requested, length, consumed, reserved[6];
  unsigned char payload[192];
} Request;
_Static_assert(sizeof(Thread)==256, "TCR fixture size");
_Static_assert(__builtin_offsetof(Thread, root_head)==24, "boundary root head");
_Static_assert(__builtin_offsetof(Thread, nvalues)==44, "boundary values");
_Static_assert(__builtin_offsetof(Thread, state)==128, "protocol extension");
_Static_assert(__builtin_offsetof(Thread, progress)==220, "progress field");
_Static_assert(sizeof(Request)==256, "stable request size");
_Static_assert(__builtin_offsetof(Request, wake_generation)==8, "aligned generation/wake pair");
_Static_assert(__builtin_offsetof(Request, generation)==12, "generation is high half of wake pair");
_Static_assert(__builtin_offsetof(Request, payload)==64, "stable payload offset");
enum { CREATING, PARKED, RUNNING, FOREIGN, STOPPED_GC, TERMINATING };
enum { GC_PENDING=1, INTERRUPT_PENDING=2 };
enum { ARMED, INTERRUPTED, TERMINAL };
enum { PENDING, COMPLETE, CANCELLED };
enum { PROBE=1, EVEN, STOPPED, BEFORE_CAS, ACQUIRED, CAS_LOST, SNAPSHOT,
       PENDING_SET, MEMBERSHIP_CLOSED, MOVED, RELEASED, RECHECK, WAITING,
       WOKE, INTERRUPT, REARM, RETURNING, CREATOR_READY, CHILD_PUBLISHED,
       RETIRED, RECLAIMED, POLLING, ALLOCATED };
extern u32 get_tcr(void);
__attribute__((import_module("emitted"),import_name("raise")))
extern void emitted_raise(u32);
__attribute__((import_module("schedule"),import_name("point")))
extern void point(u32 tcr, u32 event, u32 detail);
__attribute__((import_module("host"),import_name("request")))
extern void host_request(u32 tcr, u32 request);
__attribute__((import_module("host"),import_name("callback")))
extern void host_callback(u32 tcr);
__attribute__((import_module("host"),import_name("install")))
extern void host_install(u32 request);
#define LOAD(p) __atomic_load_n((p), __ATOMIC_SEQ_CST)
#define STORE(p,v) __atomic_store_n((p),(v),__ATOMIC_SEQ_CST)
#define ADD(p,v) __atomic_fetch_add((p),(v),__ATOMIC_SEQ_CST)
#define OR(p,v) __atomic_fetch_or((p),(v),__ATOMIC_SEQ_CST)
#define AND(p,v) __atomic_fetch_and((p),(v),__ATOMIC_SEQ_CST)
static inline void notify(u32 *p) { __builtin_wasm_memory_atomic_notify((int*)p, 0x7fffffff); }
static inline void wait_word(u32 *p, u32 value) {
  if (__builtin_wasm_memory_atomic_wait32((int*)p,value,1000000000LL)==2) __builtin_trap();
}
static inline Thread *self(void) { return (Thread*)get_tcr(); }
static inline void require(int yes) { if (!yes) __builtin_trap(); }
static inline void event(u32 code,u32 detail) { point(get_tcr(),code,detail); }
static inline void state(Thread *t,u32 value) { STORE(&t->state,value); notify(&t->state); }
#endif
