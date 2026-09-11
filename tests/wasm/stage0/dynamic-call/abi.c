#include "../integrated-runtime/protocol.h"

extern u32 failure_code, heap_spaces[2], heap_active, heap_used, world_completed;
extern u32 car_value(u32), collect(void);
extern void admit(void), park(void);
typedef struct {u32 cdr, car;} Cons;
typedef struct {
  u32 layout, bytes, previous, generation, code, version, site, policy;
  u32 binding, handler, roots, self_slot, argc, nvalues, mv, reserved;
  u32 saved_root, saved_vsp, saved_tsp, saved_csp, saved_mv, saved_owner;
  u32 saved_depth, saved_binding, saved_handler, saved_request, blocks, incoming;
  u32 result_count, result_base, result_top, padding;
} Header;
_Static_assert(sizeof(Cons)==8 && __builtin_offsetof(Cons,car)==4,"independent cons layout");
_Static_assert(sizeof(Header)==128 && __builtin_offsetof(Header,saved_root)==64,"logical frame header");
_Static_assert(__builtin_offsetof(Header,self_slot)==44 && __builtin_offsetof(Header,argc)==48,"logical self/count");
_Static_assert(__builtin_offsetof(Header,result_count)==112,"owned result descriptor");
#define HEAD (self()->reserved[0])
#define SERIAL (self()->reserved[1])
#define STATE (self()->reserved[2])
#define BASE (self()->reserved[3])
#define LIMIT (self()->reserved[4])
#define REPLY (self()->reserved[5])
#define REPLY_END (self()->reserved[6])
static void bad(u32 n) {if(!LOAD(&failure_code)) STORE(&failure_code,n); __builtin_trap();}
static void yes(int ok,u32 n) {if(!ok) bad(n);}
static void running(void) {yes(LOAD(&self()->state)==RUNNING && self()->admitted,900);}
void abi_setup(u32 state,u32 base,u32 limit,u32 reply,u32 reply_end) {
  yes(LOAD(&self()->state)==PARKED && !(base&15) && limit>base && reply>=limit && reply_end>reply,901);
  HEAD=SERIAL=0;STATE=state;BASE=base;LIMIT=limit;REPLY=reply;REPLY_END=reply_end;
  for(u32 i=0;i<16;i++) ((u32*)state)[i]=0;
}
u32 abi_cdr(u32 value) {if(value==65) return 65;car_value(value);return ((Cons*)(value-1))->cdr;}
u32 abi_car(u32 value) {return value==65?65:car_value(value);}
void abi_rplaca(u32 value,u32 replacement) {car_value(value);((Cons*)(value-1))->car=replacement;}
void abi_rplacd(u32 value,u32 replacement) {car_value(value);((Cons*)(value-1))->cdr=replacement;}
u32 abi_cons(u32 a,u32 d) {
  running(); volatile Root roots={0}; roots.previous=self()->root_head;roots.count=2;
  roots.values[0]=a;roots.values[1]=d;self()->root_head=(u32)&roots;
  if(LOAD(&heap_used)+8>4096) collect();
  u32 offset=ADD(&heap_used,8);yes(offset+8<=4096,902);
  Cons *p=(Cons*)(heap_spaces[heap_active]+offset);p->car=roots.values[0];p->cdr=roots.values[1];
  self()->root_head=roots.previous;return (u32)p+1;
}
static u32 root_count(void) {
  u32 p=self()->root_head,n=0;
  while(p) {yes(++n<=16,903);Root *r=(Root*)p;yes(r->count<=8,903);p=r->previous;}
  return n;
}
void abi_check(void) {
  running();u32 p=HEAD,n=0;root_count();
  while(p) {
    yes(++n<=8 && p>=BASE && p+512<=LIMIT && !(p&15),904);Header *f=(Header*)p;
    yes(f->layout==1 && f->bytes==512 && f->generation && f->generation<=SERIAL && !f->reserved,904);
    yes(!(f->code&3) && f->version && f->site && f->argc<=32 && f->incoming==f->argc,904);
    yes(f->self_slot==136 && f->roots==(f->code>>2) && f->blocks==(f->argc+8)/8,905);
    yes(f->mv==p+112 && f->result_base==p+336 && f->result_top==p+360 && f->nvalues==f->result_count && f->nvalues<=6,905);
    yes(f->policy==1 || f->policy==3,905);
    yes(f->binding && f->handler && *(u32*)(f->binding-4)==1980 && *(u32*)(f->handler-4)==2004,908);
    for(u32 i=0;i<f->blocks+2;i++) {
      u32 address=i<f->blocks?p+128+i*40:i==f->blocks?p+328:p+368;
      u32 found=0,q=self()->root_head,steps=0;
      while(q) {yes(++steps<=16,903);if(q==address)found=1;q=((Root*)q)->previous;}
      yes(found,906);
    }
    p=f->previous;
  }
}
static void value(u32 *p,u32 v) {
  p[0]=v;p[1]=v==65?0:!(v&3)?1:2;p[2]=v==65?0:!(v&3)?v:car_value(v);
}
void abi_inspect(u32 phase) {
  abi_check();yes(REPLY+8192<=REPLY_END,907);u32 *p=(u32*)REPLY;REPLY+=8192;
  for(u32 i=0;i<2048;i++)p[i]=0;
  p[0]=0x41424931;p[2]=phase;p[3]=world_completed;p[4]=self()->vsp;p[5]=root_count();
  u32 next=HEAD,at=8,count=0;
  while(next) {
    Header *f=(Header*)next;yes(at+18+(f->argc+1+f->nvalues)*3<2048,907);
    p[at++]=next;for(u32 i=0;i<16;i++)p[at++]=((u32*)f)[i];
    p[at++]=f->policy==1?1:0;
    for(u32 i=0;i<=f->argc;i++) {u32 slot=next+128+(i/8)*40+8+(i%8)*4;value(p+at,*(u32*)slot);at+=3;}
    for(u32 i=0;i<f->nvalues;i++) {value(p+at,((u32*)f->result_base)[i]);at+=3;}
    next=f->previous;count++;
  }
  p[6]=count;STORE(&p[1],at*4);host_request(get_tcr(),(u32)p);
}
u32 abi_root_count(void) {running();return root_count();}
