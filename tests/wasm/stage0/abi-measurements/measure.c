#include "../integrated-runtime/protocol.h"

extern u32 failure_code;
extern void abi_check(void);
extern u32 abi_car(u32), abi_cdr(u32);

static void check(int ok, u32 code) {
  if (!ok) { if (!LOAD(&failure_code)) STORE(&failure_code, code); __builtin_trap(); }
}

/* Inspect only after publication/restoration, never in the no-poll handoff.
   Count scanner addresses, not equal Lisp values in different root slots. */
void measure_ownership(void) {
  abi_check();
  u32 addresses[16*8+6], used=0, roots=0;
  Thread *t=self();
  for (Root *r=(Root*)t->root_head; r; r=(Root*)r->previous) {
    check(++roots<=16 && r->count<=8, 930);
    for (u32 i=0; i<r->count; i++) addresses[used++]=(u32)&r->values[i];
  }
  check(t->nvalues<=6 && t->mv_base+t->nvalues*4<=t->mv_owner_top, 930);
  for (u32 i=0; i<t->nvalues; i++) addresses[used++]=t->mv_base+i*4;
  for (u32 i=0; i<used; i++)
    for (u32 j=0; j<i; j++) check(addresses[i]!=addresses[j], 931);
  for (u32 p=t->reserved[0]; p; p=((u32*)p)[2]) {
    u32 *h=(u32*)p, base=h[29];
    if (t->mv_base==base) check(t->nvalues==h[28], 932);
    for (u32 i=0; i<h[28]; i++) {
      u32 count=0;
      for (u32 j=0; j<used; j++) count+=addresses[j]==base+i*4;
      check(count==1, 933);
    }
  }
}

static u32 mix(u32 hash, u32 value) { return (hash^value)*16777619u; }

/* Address-independent complete graph observation, including sharing/cycles.
   The queue is raw C storage: this reader cannot allocate or reach a poll. */
u32 measure_digest(u32 value) {
  u32 queue[64], count=0, head=0, hash=2166136261u;
  u32 todo[2]={value,65}, length=1;
  for (;;) {
    for (u32 i=0; i<length; i++) {
      u32 v=todo[i];
      if (v==65) hash=mix(hash,0);
      else if (!(v&3)) { hash=mix(hash,1); hash=mix(hash,v); }
      else {
        u32 j=0;
        while (j<count && queue[j]!=v) j++;
        if (j==count) { check(count<64,934); queue[count++]=v; }
        hash=mix(hash,2); hash=mix(hash,j);
      }
    }
    if (head==count) break;
    u32 p=queue[head++]; todo[0]=abi_car(p); todo[1]=abi_cdr(p); length=2;
  }
  return hash;
}
