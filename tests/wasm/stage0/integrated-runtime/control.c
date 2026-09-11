#include "protocol.h"

/* Shared process state is initialized once by the supervisor before publication.
 * The real LLVM start function must not replay it when a late Worker instantiates.
 */
u32 world_gen, world_owner, world_completed, collecting, registry[4];
u32 heap_spaces[2], heap_active, heap_used, poll_finish, failure_code;
static u32 forwarding[512], copy_used;

static void fail(u32 code) { STORE(&failure_code,code); __builtin_trap(); }
static void mutator(void) {
  Thread *t=self();
  if (LOAD(&t->state)!=RUNNING || !t->admitted || LOAD(&collecting)) fail(101);
}

void initialize(u32 first,u32 second,u32 generation) {
  require(!(generation&1));
  heap_spaces[0]=first; heap_spaces[1]=second;
  heap_active=heap_used=world_completed=world_owner=collecting=poll_finish=failure_code=0;
  STORE(&world_gen,generation);
  for(u32 i=0;i<4;i++) STORE(&registry[i],0);
}

static u32 cell(u32 car,u32 cdr) {
  u32 offset=ADD(&heap_used,8);
  require(offset+8<=4096);
  u32 *p=(u32*)(heap_spaces[heap_active]+offset);
  p[0]=cdr; p[1]=car;
  return (u32)p+1;
}
/* Initialization fixture: cycle + shared tail, plus unreachable garbage. */
u32 seed_graph(u32 value) {
  require(!LOAD(&registry[0]) && !LOAD(&collecting));
  u32 root=cell(value<<2,65), tail=cell((value+1)<<2,root);
  *(u32*)(root-1)=tail;
  for(u32 i=0;i<32;i++) cell(i<<2,65);
  return root;
}
void initialize_thread(u32 address,u32 id,u32 requests,u32 roots,u32 values,u32 root) {
  Thread *t=(Thread*)address;
  for(u32 i=0;i<sizeof(Thread)/4;i++) ((u32*)t)[i]=0;
  t->id=id; t->lifetime=1; t->requests=requests; t->root_head=roots;
  t->root_slot=roots+8; t->mv_base=values; t->mv_owner_top=values+32;
  t->vsp=values+32; t->tsp=values+768; t->csp=values+1024;
  t->binding_depth=7; t->continuation=0x12340000+id;
  t->handler_cookie=0x33445566; t->binding_cookie=0x778899aa;
  Root *r=(Root*)roots; r->previous=0; r->count=2;
  r->values[0]=root; r->values[1]=root;
  state(t,PARKED);
}
void publish_initial(u32 address) {
  Thread *t=(Thread*)address; require(t->id<4 && !LOAD(&registry[t->id]));
  STORE(&registry[t->id],address);
}

static void reload(void) {
  Thread *t=self();
  t->observed_root=*(volatile u32*)t->root_slot;
  t->observed_raw=t->observed_root==65 ? 0 : t->observed_root-1;
  t->reloads++;
}
void admit(void) {
  Thread *t=self(); t->admitted=0;
  if(t->id>=4 || LOAD(&registry[t->id])!=(u32)t || t->reclaimed || LOAD(&t->state)==TERMINATING) fail(103);
  for(;;) {
    state(t,RUNNING); event(PROBE,LOAD(&world_gen));
    u32 g=LOAD(&world_gen);
    if (!(g&1)) {
      t->admitted=1; reload(); event(EVEN,g); return;
    }
    state(t,STOPPED_GC); t->stops++; event(STOPPED,g);
    while((g=LOAD(&world_gen))&1) wait_word(&world_gen,g);
    /* Even parity is a wake condition, not admission. Retry the RUNNING store. */
  }
}
void park(void) { self()->admitted=0; state(self(),PARKED); }
void safepoint(void) {
  if(LOAD(&self()->pending)&GC_PENDING) { self()->admitted=0; state(self(),STOPPED_GC); self()->stops++; event(STOPPED,LOAD(&world_gen)); admit(); }
}
u32 root_value(void) { mutator(); return *(volatile u32*)self()->root_slot; }
u32 car_value(u32 value) {
  mutator();
  if((value&7)!=1 || value-1<heap_spaces[heap_active] || value-1>=heap_spaces[heap_active]+heap_used) fail(102);
  return *(volatile u32*)(value+3);
}

static u32 move(u32 value) {
  if(value==65 || (value&3)==0) return value;
  u32 from=heap_spaces[heap_active], to=heap_spaces[1-heap_active], raw=value-1;
  if((value&7)!=1 || raw<from || raw>=from+heap_used || ((raw-from)&7)) fail(201);
  u32 index=(raw-from)/8;
  if(forwarding[index]) return forwarding[index];
  require(copy_used+8<=4096);
  u32 *target=(u32*)(to+copy_used), *source=(u32*)raw;
  target[0]=source[0]; target[1]=source[1]; copy_used+=8;
  return forwarding[index]=(u32)target+1;
}
static void scan_thread(Thread *t) {
  u32 address=t->root_head, frames=0;
  while(address) {
    Root *r=(Root*)address; require(++frames<=16 && r->count<=8);
    for(u32 i=0;i<r->count;i++) r->values[i]=move(r->values[i]);
    address=r->previous;
  }
  require(t->nvalues<=6);
  for(u32 i=0;i<t->nvalues;i++) ((u32*)t->mv_base)[i]=move(((u32*)t->mv_base)[i]);
}
static void stop_thread(Thread *t) {
  if(t==self()) return;
  event(PENDING_SET,t->id); OR(&t->pending,GC_PENDING);
  while(LOAD(&t->state)==RUNNING) wait_word(&t->state,RUNNING);
}

u32 collect(void) {
  Thread *t=self(); mutator();
  u32 observed=LOAD(&world_gen), expected=observed;
  event(BEFORE_CAS,observed);
#ifdef MUTANT_FETCH_ADD
  u32 won=!(ADD(&world_gen,1)&1);
#else
  u32 won=!(observed&1) && __atomic_compare_exchange_n(&world_gen,&expected,observed+1,0,__ATOMIC_SEQ_CST,__ATOMIC_SEQ_CST);
#endif
  if(!won) {
    t->admitted=0; state(t,STOPPED_GC); t->stops++; event(CAS_LOST,LOAD(&world_gen));
    u32 g; while((g=LOAD(&world_gen))&1) wait_word(&world_gen,g);
    admit(); t->allocation_checks++; event(RECHECK,4096-heap_used);
    return 0;
  }
  STORE(&world_owner,t->id+1); event(ACQUIRED,observed+1);
#ifdef MUTANT_OWNER_TRAP
  fail(901);
#endif
  u32 members[4], count=0;
  for(u32 i=0;i<4;i++) { u32 p=LOAD(&registry[i]); if(p) members[count++]=p; }
  event(SNAPSHOT,count);
  for(u32 i=0;i<count;i++) stop_thread((Thread*)members[i]);
#ifndef MUTANT_OMIT_RESCAN
  for(;;) {
    u32 added=0;
    for(u32 i=0;i<4;i++) {
      u32 p=LOAD(&registry[i]), found=0;
      for(u32 j=0;j<count;j++) if(members[j]==p) found=1;
      if(p && !found) { require(count<4); members[count++]=p; added=1; stop_thread((Thread*)p); }
    }
    if(!added) break;
  }
#endif
  require(LOAD(&world_owner)==t->id+1 && LOAD(&world_gen)==observed+1);
  STORE(&collecting,1); event(MEMBERSHIP_CLOSED,count);
  for(u32 i=0;i<512;i++) forwarding[i]=0;
  copy_used=0;
  for(u32 i=0;i<count;i++) scan_thread((Thread*)members[i]);
  for(u32 scan=0;scan<copy_used;scan+=8) {
    u32 *p=(u32*)(heap_spaces[1-heap_active]+scan);
    p[0]=move(p[0]); p[1]=move(p[1]);
  }
  for(u32 i=0;i<heap_used/4;i++) ((u32*)heap_spaces[heap_active])[i]=0xdeadbeef;
  heap_active=1-heap_active; heap_used=copy_used;
  require(world_completed!=0xffffffffu); world_completed++;
  event(MOVED,heap_used);
  for(u32 i=0;i<count;i++) AND(&((Thread*)members[i])->pending,~GC_PENDING);
  STORE(&collecting,0); STORE(&world_owner,0);
  STORE(&world_gen,observed+2); notify(&world_gen); event(RELEASED,observed+2);
  admit(); t->allocation_checks++; event(RECHECK,4096-heap_used);
  return count;
}
u32 collect_and_park(void) { admit(); u32 n=collect(); park(); return n; }
u32 allocate_after_collection(void) {
  admit(); collect(); mutator(); require(heap_used+8<=4096);
  u32 value=cell(404,65); event(ALLOCATED,value); park(); return value;
}

void creator(u32 child) {
  admit(); event(CREATOR_READY,child);
  Thread *c=(Thread*)child; mutator();
  /* Transfer the only reference to this graph before publishing membership. */
  *(u32*)c->root_slot=*(u32*)self()->root_slot;
  ((Root*)c->root_head)->values[1]=*(u32*)c->root_slot;
  ((Root*)self()->root_head)->values[0]=65;
  ((Root*)self()->root_head)->values[1]=65;
  require(!LOAD(&registry[c->id])); STORE(&registry[c->id],child);
  event(CHILD_PUBLISHED,c->id); safepoint(); park();
}
u32 child_read(void) { admit(); u32 value=car_value(root_value()); park(); return value; }
void polling(void) {
  admit(); event(POLLING,0);
  while(!LOAD(&poll_finish)) {
    safepoint(); u32 root=root_value(); if(root!=65) require(car_value(root)==800);
    self()->progress++;
  }
  park();
}

static Request *request_at(Thread *t,u32 index) { require(index<2); return (Request*)(t->requests+index*256); }
static void prepare(Request *r,u32 opcode) {
  mutator();
  if(LOAD(&r->active) && !LOAD(&r->outcome)) fail(301);
  u32 generation=(u32)(LOAD(&r->wake_generation)>>32);
  require(generation!=0xffffffffu);
  STORE(&r->wake_generation,(u64)(generation+1)<<32);
  r->owner_lifetime=self()->lifetime; r->opcode=opcode;
  r->cancel_requested=r->consumed=r->result=0; r->length=16;
  for(u32 i=0;i<16;i++) r->payload[i]=(unsigned char)(0xa0+i);
  STORE(&r->outcome,PENDING); STORE(&r->active,1);
}

/* Real C frame remains live across atomic waits, GC and nested emitted callbacks. */
u32 suspend_request(u32 opcode,u32 index,u32 input) {
  Thread *t=self(); mutator();
  volatile u32 locals[64]; for(u32 i=0;i<64;i++) locals[i]=0xc0010000+i;
  volatile Root roots={0}; roots.previous=t->root_head; roots.count=2;
  roots.values[0]=input; roots.values[1]=input;
  t->root_head=(u32)&roots; t->old_root=input;
  u32 previous_request=LOAD(&t->active_request);
  Request *r=request_at(t,index); prepare(r,opcode); STORE(&t->active_request,(u32)r);
  t->admitted=0; state(t,FOREIGN); host_request((u32)t,(u32)r);
  for(;;) {
    u32 wake=(u32)LOAD(&r->wake_generation);
    if(!(LOAD(&t->pending)&INTERRUPT_PENDING) && !LOAD(&r->outcome) && wake==ARMED) {
      event(WAITING,(u32)r); wait_word(&r->wake,ARMED);
    }
    event(WOKE,(u32)r); admit();
    u32 moved=roots.values[0];
#ifdef MUTANT_STALE_C_ROOT
    moved=input;
#endif
    t->observed_root=moved; t->observed_raw=moved-1;
    car_value(moved); /* re-derived interior access, checked against active semispace */
    if(AND(&t->pending,~INTERRUPT_PENDING)&INTERRUPT_PENDING) {
      t->interrupts++; event(INTERRUPT,(u32)r);
      if(t->mode==1 && !index && !t->nested) { t->nested++; host_callback((u32)t); }
      if(t->mode==2 && !index) {
        STORE(&r->cancel_requested,1);
        emitted_raise((u32)t); /* outer emitted adapter owns exceptional restoration */
      }
    }
    /* A nested debugger callback may itself have collected. */
#ifndef MUTANT_STALE_C_ROOT
    moved=roots.values[0];
#endif
    t->observed_root=moved; t->observed_raw=moved-1; car_value(moved);
    if(LOAD(&t->pending)&INTERRUPT_PENDING) continue;
    u32 outcome=LOAD(&r->outcome);
    if(outcome) {
      require(outcome==COMPLETE || outcome==CANCELLED);
      require(r->owner_lifetime==t->lifetime);
      r->consumed=outcome; STORE(&r->active,0);
      if(opcode==2 && outcome==COMPLETE) host_install((u32)r);
      for(u32 i=0;i<64;i++) require(locals[i]==0xc0010000+i);
      t->root_head=roots.previous;
      STORE(&t->active_request,previous_request);
      event(RETURNING,moved); return moved;
    }
    t->admitted=0; state(t,FOREIGN);
    AND(&r->wake_generation,0xffffffff00000000ULL); event(REARM,(u32)r);
    /* Recheck after arming. The next loop waits only if all reasons are absent. */
  }
}
void retire(void) {
  admit(); mutator(); Thread *t=self();
  require(LOAD(&registry[t->id])==(u32)t);
  STORE(&registry[t->id],0); t->retire_serial=LOAD(&world_completed);
  t->admitted=0; state(t,TERMINATING); event(RETIRED,t->retire_serial);
}
u32 try_reclaim(u32 address) {
  mutator(); Thread *t=(Thread*)address;
  if(t->reclaimed || LOAD(&t->state)!=TERMINATING || LOAD(&world_completed)<=t->retire_serial) return 0;
#ifndef MUTANT_PREMATURE_REUSE
  for(u32 i=0;i<2;i++) { Request *r=request_at(t,i); if(LOAD(&r->active) && !LOAD(&r->outcome)) return 0; }
#endif
  require(t->lifetime!=0xffffffffu); t->lifetime++; t->reclaimed=1;
  for(u32 i=0;i<2;i++) {
    Request *r=request_at(t,i); u32 generation=(u32)(LOAD(&r->wake_generation)>>32);
    require(generation!=0xffffffffu);
    STORE(&r->wake_generation,(u64)(generation+1)<<32);
    r->owner_lifetime=t->lifetime; STORE(&r->active,0);
  }
  event(RECLAIMED,address); return 1;
}
u32 reclaim_and_park(u32 address) { admit(); u32 result=try_reclaim(address); park(); return result; }
