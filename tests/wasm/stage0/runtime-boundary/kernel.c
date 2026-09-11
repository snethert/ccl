/* Hand-built Stage 0 fixture, not the CCL kernel or its final TCR layout.
 * No libc, WASI, implicit allocator, native signal context or GC substitute.
 */
typedef unsigned int u32;
typedef struct {
  u32 token, frame_address, tcr_before, tcr_after;
  u32 stack_ok, post_exit_effect, root_head, binding_depth;
  u32 vsp, tsp, csp, nvalues;
  u32 mv_base, mv_owner_top, reserved_values[4];
  u32 ready, release, cleanup_effect, catch_reason, observed_sp;
  u32 reserved[9];
} Tcr;

typedef struct { u32 previous, count, values[2]; } Roots;
_Static_assert(sizeof(void *) == 4 && sizeof(u32) == 4, "wasm32 required");
_Static_assert(sizeof(Tcr) == 128, "fixture TCR size");
_Static_assert(__builtin_offsetof(Tcr, root_head) == 24, "root checkpoint");
_Static_assert(__builtin_offsetof(Tcr, mv_base) == 48, "VSP result-region descriptor");
_Static_assert(__builtin_offsetof(Tcr, ready) == 72, "barrier word");
_Static_assert(__builtin_offsetof(Tcr, observed_sp) == 88, "unwind observation");
_Static_assert(sizeof(Roots) == 16, "explicit C root record");

#ifdef MUTANT_SHARED_TCR
static volatile u32 current_tcr;
/* Keep TLS metadata present so this mutant reaches the actual isolation oracle. */
static _Thread_local volatile u32 unused_tls;
#else
static _Thread_local volatile u32 current_tcr;
#endif
volatile u32 data_sentinel = 0x11223344;
volatile u32 bss_sentinel;

__attribute__((import_module("bridge"), import_name("park")))
extern void bridge_park(u32 tcr, u32 frame);
__attribute__((import_module("emitted"), import_name("raise")))
extern void emitted_raise(u32 tcr);

void set_tcr(u32 address) {
  current_tcr = address;
#ifdef MUTANT_SHARED_TCR
  unused_tls = address;
#endif
}
u32 get_tcr(void) { return current_tcr; }

static u32 add_seventeen(u32 x) { return x + 17; }
static u32 (*volatile c_function_pointer)(u32) = add_seventeen;
u32 pointer_slot(void) { return (u32)c_function_pointer; }
u32 call_pointer(u32 x) { return c_function_pointer(x); }

/* Both Workers remain inside this C activation while the supervisor holds
 * release. Address-taken volatile storage prevents scalar replacement. */
u32 hold_stack(u32 token) {
  volatile u32 frame[64];
  Tcr *tcr = (Tcr *)current_tcr;
  for (u32 i = 0; i != 64; ++i) frame[i] = token ^ (i * 0x10203u);
  tcr->token = token;
  tcr->frame_address = (u32)frame;
  tcr->tcr_before = current_tcr;
  bridge_park((u32)tcr, (u32)frame);
  u32 valid = 1;
  for (u32 i = 0; i != 64; ++i) valid &= frame[i] == (token ^ (i * 0x10203u));
  tcr->stack_ok = valid;
  tcr->tcr_after = current_tcr;
#ifdef MUTANT_UNRESOLVED
  extern u32 unapproved_helper(u32);
  valid = unapproved_helper(valid);
#endif
  return valid;
}

__attribute__((noinline))
static u32 exit_leaf(u32 mode, u32 token) {
  volatile u32 frame[32];
  volatile Roots roots;
  Tcr *tcr = (Tcr *)current_tcr;
  roots.previous = tcr->root_head;
  roots.count = 2;
  roots.values[0] = 129; /* Independent fixture cons pointer, not a raw address. */
  roots.values[1] = 4;   /* Tagged fixnum 1. */
  tcr->root_head = (u32)&roots;
  frame[0] = token;
  frame[31] = token ^ 0x5a5a5a5au;
  tcr->binding_depth += 1;
  tcr->vsp += 16;
  tcr->tsp += 16;
  tcr->csp += 16;
  tcr->observed_sp = (u32)frame;
  if (mode) emitted_raise((u32)tcr);
  tcr->post_exit_effect += 1;
  return frame[0] ^ frame[31] ^ roots.values[1];
}

u32 exit_helper(u32 mode, u32 token) {
  volatile u32 frame[32];
  volatile Roots roots;
  Tcr *tcr = (Tcr *)current_tcr;
  roots.previous = tcr->root_head;
  roots.count = 2;
  roots.values[0] = 129;
  roots.values[1] = 8;
  tcr->root_head = (u32)&roots;
  frame[0] = token;
  frame[31] = token + 1;
  u32 result = exit_leaf(mode, token);
  tcr->post_exit_effect += 1;
  return result ^ frame[0] ^ frame[31] ^ roots.values[1];
}
