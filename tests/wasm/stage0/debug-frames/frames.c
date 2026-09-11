#include "../integrated-runtime/protocol.h"
#include "build-id.h"

/* This is the independent C interpretation of the emitted 64-byte header. */
typedef struct {
  u32 layout_version, frame_bytes, previous, generation, code_id, code_version;
  u32 site, policy, binding_checkpoint, handler_checkpoint, root_descriptor;
  u32 self_slot, argc, nvalues, mv_descriptor, reserved;
  struct {u32 previous, count, values[6];} roots;
  u32 raw_snapshot, unavailable_poison, saved_vsp, saved_tsp, saved_csp;
  u32 saved_binding_depth, saved_handler_cookie, saved_binding_cookie;
  u32 saved_mv_base, saved_mv_owner_top, saved_active_request, unused[5];
} Frame;
_Static_assert(sizeof(Frame)==160, "complete logical frame");
_Static_assert(__builtin_offsetof(Frame, raw_snapshot)==96, "non-root payload");
_Static_assert(__builtin_offsetof(Frame, saved_vsp)==104, "restoration payload");
_Static_assert(__builtin_offsetof(Frame, roots)==64, "64-byte logical header");
_Static_assert(__builtin_offsetof(Frame, roots.values)==72, "first payload root");
_Static_assert(__builtin_offsetof(Frame, generation)==12, "lifetime token");
_Static_assert(__builtin_offsetof(Frame, code_id)==16, "tagged code ID");
_Static_assert(__builtin_offsetof(Frame, self_slot)==44, "self offset");
#define FRAME_BYTES 160u
#define REPLY_BYTES 4096u
#define MAGIC 0x44424731u
#define HEAD (self()->reserved[0])
#define SERIAL (self()->reserved[1])
#define CURSOR (self()->reserved[2])
#define BASE (self()->reserved[3])
#define LIMIT (self()->reserved[4])
#define REPLY (self()->reserved[5])
#define REPLY_LIMIT (self()->reserved[6])
extern u32 failure_code, world_completed;
extern void admit(void), park(void);
extern u32 car_value(u32);
static void bad(u32 code) { if(!LOAD(&failure_code)) STORE(&failure_code,code); __builtin_trap(); }
static void ensure(int yes,u32 code) { if(!yes) bad(code); }
static void admitted(void) { ensure(LOAD(&self()->state)==RUNNING && self()->admitted,700); }
static u32 word(Frame *f,u32 offset) { return ((u32*)f)[offset/4]; }
static Frame *bounded(u32 address) {
  ensure(address>=BASE && address<=LIMIT-FRAME_BYTES && !((address-BASE)%FRAME_BYTES),701);
  return (Frame*)address;
}
static u32 lexical_base(Frame *f) {
  u32 id=f->code_id>>2;
  ensure(!(f->code_id&3),704);
  if(id==41 && f->code_version==1 && (f->site==4101||f->site==4102||f->site==4141||f->site==4142||f->site==4143)) return 41000;
  if(id==41 && f->code_version==2 && (f->site==4111||f->site==4112)) return 141000;
  if(id==42 && f->code_version==1 && (f->site==4201||f->site==4202)) return 42000;
  if(id==43 && f->code_version==1 && (f->site==4301||f->site==4302)) return 43000;
  bad(704); return 0;
}
static void validate(Frame *f,u32 check_roots) {
  ensure(f->layout_version==1 && f->frame_bytes==160 && !f->reserved,702);
  ensure(f->generation && f->generation<=SERIAL,703);
  lexical_base(f);
  ensure(f->root_descriptor==(f->code_id>>2) && f->self_slot==72 && f->argc==2,705);
  ensure(f->roots.count==6 && f->mv_descriptor==(u32)&self()->nvalues && f->nvalues==self()->nvalues,705);
  ensure(f->policy==1 || f->policy==3,706);
  if(!check_roots) return;
  u32 root=self()->root_head, found=0, steps=0;
  while(root) {
    ensure(++steps<=16,705);
    if(root==(u32)&f->roots) found=1;
    root=((Root*)root)->previous;
  }
  ensure(found,705);
}
void debug_setup(u32 base,u32 limit,u32 reply,u32 reply_limit) {
  ensure(LOAD(&self()->state)==PARKED && !(base&7) && limit>base && reply>=limit && reply_limit>reply,701);
  HEAD=SERIAL=0; BASE=CURSOR=base; LIMIT=limit; REPLY=reply; REPLY_LIMIT=reply_limit;
}
u32 debug_reserve(void) {
  admitted(); ensure(CURSOR<=LIMIT-FRAME_BYTES,701); ensure(SERIAL!=0xffffffffu,703);
#ifdef MUTANT_REUSED_GENERATION
  SERIAL=1;
#else
  SERIAL++;
#endif
  u32 address=CURSOR; CURSOR+=FRAME_BYTES;
  for(u32 i=0;i<FRAME_BYTES/4;i++) ((u32*)address)[i]=0;
  return address;
}
void debug_commit(u32 address) {
  admitted(); Frame *f=bounded(address);
  ensure(f->previous==HEAD && f->roots.previous==self()->root_head,705);
  HEAD=address;
#ifndef MUTANT_MISSING_ROOT
  self()->root_head=(u32)&f->roots;
#endif
  validate(f,1);
}
void debug_site(u32 site) { admitted(); Frame *f=bounded(HEAD); f->site=site; lexical_base(f); }
static void pop(u32 check_roots) {
  Frame *f=bounded(HEAD); validate(f,check_roots);
  self()->root_head=f->roots.previous;
  self()->vsp=word(f,104); self()->tsp=word(f,108); self()->csp=word(f,112);
  self()->binding_depth=word(f,116); self()->handler_cookie=word(f,120); self()->binding_cookie=word(f,124);
  self()->mv_base=word(f,128); self()->mv_owner_top=word(f,132); STORE(&self()->active_request,word(f,136));
  CURSOR=(u32)f; HEAD=f->previous;
}
void debug_pop(void) { admitted(); ensure(self()->root_head==(u32)&bounded(HEAD)->roots,705); pop(1); }
void debug_unwind(u32 target) {
  admitted(); u32 count=0;
  /* The Wasm EH boundary has restored __stack_pointer. C activations are gone;
   * discard their published records before walking the surviving Lisp frames.
   * No poll, allocation or inspection occurs until all checkpoints are restored. */
  while(HEAD!=target) {
    ensure(HEAD && ++count<=8,707);
    self()->root_head=(u32)&bounded(HEAD)->roots; pop(0);
  }
  for(u32 i=0;i<2;i++) {
    Request *r=(Request*)(self()->requests+i*256);
    if(LOAD(&r->active) && !LOAD(&r->outcome)) STORE(&r->cancel_requested,1);
  }
}
u32 debug_handle(u32 address,u32 generation,u32 lifetime) {
  admitted();
#ifdef MUTANT_REJECT_LIVE_HANDLE
  return 0;
#endif
  if(lifetime!=self()->lifetime) return 0; u32 next=HEAD,steps=0;
  while(next) {
    ensure(++steps<=8,701); Frame *f=bounded(next); validate(f,1);
    if(next==address) return f->generation==generation;
    next=f->previous;
  }
  return 0;
}
u32 debug_handle_query(u32 address,u32 generation,u32 lifetime) { admit(); u32 yes=debug_handle(address,generation,lifetime); park(); return yes; }
static u32 *packet(u32 kind,u32 detail) {
  admitted(); ensure(REPLY<=REPLY_LIMIT-REPLY_BYTES,708);
  u32 *p=(u32*)REPLY; REPLY+=REPLY_BYTES;
  for(u32 i=0;i<REPLY_BYTES/4;i++) p[i]=0;
  p[0]=MAGIC; p[2]=kind; p[3]=detail;
  const u32 build[8]=BUILD_ID_WORDS;
  for(u32 i=0;i<8;i++) p[4+i]=build[i];
  return p;
}
static void publish(u32 *p,u32 words) {
  ensure(words<=REPLY_BYTES/4,708); STORE(&p[1],words*4);
  /* This packet is never reused during the run. No host reads the Lisp heap. */
  host_request(get_tcr(),(u32)p);
}
static void value(u32 *out,u32 tagged) {
  out[0]=tagged;
  if(tagged==65) {out[1]=0;out[2]=0;return;}
  if(!(tagged&3)) {out[1]=1;out[2]=tagged;return;}
  out[1]=2; out[2]=car_value(tagged);
}
void debug_inspect(u32 phase) {
  admitted(); u32 *p=packet(1,phase), next=HEAD, count=0, at=16;
  p[12]=self()->nvalues; p[13]=HEAD; p[14]=0; p[15]=world_completed;
  ensure(self()->nvalues<=6,705);
  for(u32 i=0;i<self()->nvalues;i++) {value(p+at,((u32*)self()->mv_base)[i]);at+=3;}
  while(next) {
    ensure(++count<=8,701); Frame *f=bounded(next); validate(f,1); u32 lex=lexical_base(f);
    ensure(at+12+8*6<=REPLY_BYTES/4,708);
    p[at++]=next;p[at++]=f->generation;p[at++]=f->code_id;p[at++]=f->code_version;
    p[at++]=f->site;p[at++]=f->policy;p[at++]=f->previous;p[at++]=f->binding_checkpoint;
    p[at++]=f->handler_checkpoint;p[at++]=f->argc;p[at++]=f->nvalues;p[at++]=8;
    for(u32 slot=0;slot<8;slot++) {
      u32 availability=slot==7?2:(f->policy==1 && slot==3?1:(f->policy==1 && slot==5?3:0));
      u32 lexical=lex+slot+1;
#ifdef MUTANT_WRONG_LEXICAL_ID
      if(slot==3) lexical=41004;
#endif
      p[at]=lexical;p[at+1]=availability;p[at+2]=slot==7?0:(slot==6?2:1);
      if(!availability) {
        if(slot==6) {p[at+3]=word(f,96);p[at+4]=3;p[at+5]=word(f,96);}
        else {
          u32 v=f->roots.values[slot];
#ifdef MUTANT_STALE_SLOT
          if(world_completed && slot==2) v=word(f,96);
#endif
          value(p+at+3,v);
        }
      }
#ifdef MUTANT_FABRICATED_VALUE
      if(availability) {p[at+1]=0;p[at+2]=1;value(p+at+3,65);}
#endif
      at+=6;
    }
    next=f->previous;
  }
  p[14]=count;publish(p,at);
}
void debug_handle_reply(u32 address,u32 generation,u32 lifetime) {
  u32 *p=packet(2,debug_handle(address,generation,lifetime));p[12]=address;p[13]=generation;p[14]=lifetime;publish(p,15);
}
u32 debug_read_capture(void) { admit();u32 v=car_value(((Root*)self()->root_head)->values[1]);park();return v; }

void debug_live_handle_reply(void) {
  admitted(); Frame *f=bounded(HEAD);
  u32 *p=packet(3,debug_handle(HEAD,f->generation,self()->lifetime));
  p[12]=HEAD;p[13]=f->generation;p[14]=self()->lifetime;publish(p,15);
}
