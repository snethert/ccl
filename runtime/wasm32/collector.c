/* Isolated single-Worker copying service. No native kernel edits.
 * The owner supplies disjoint semispaces, scratch and extra root SLOT addresses.
 * All source-object identities come from a complete allocation walk. A tagged
 * interior word is never upgraded to an object. Commit updates roots only after
 * the whole reachable graph has been copied and validated. Scratch/to-space may
 * change on refusal; source space, roots and TCR publication may not.
 */
typedef unsigned int U;
typedef unsigned long long W;
#define NIL 77825u
#define LOAD(p) (*(U *)(unsigned long)(p))
#define STORE(p,v) (LOAD(p)=(v))
#define EXPORT __attribute__((visibility("default")))
typedef struct { U old, size, scan, moved; } Object;
typedef struct { U slot, value; } Update;
typedef struct {
 U tcr, from, used, limit, to, end, next;
 U stacklo, stackhi, error, count, queued, cursor, updates;
 U map, queue, log, logcap, extra, extra_count, scratch_end;
 U live, roots, reclaimed;
} State;
enum { BAD_OWNER=1, BAD_OBJECT=2, BAD_REFERENCE=3, NO_SPACE=4, BAD_ROOT=5, NO_WORKSPACE=6 };
static W memory_bytes(void) { return (W)__builtin_wasm_memory_size(0)*65536; }
static U inside(U p,U lo,U hi) { return p>=lo && p<hi; }
static U extent(U p,W bytes) { return (W)p+bytes<=memory_bytes(); }
static U overlap(U a,W n,U b,W m) { return (W)a<(W)b+m && (W)b<(W)a+n; }
static U fail(State *s,U code) { if(!s->error)s->error=code;return 0; }
static U reject(State *s,U code) { fail(s,code);return s->error; }
static Object *objects(State *s) { return (Object *)(unsigned long)s->map; }
static U *queue(State *s) { return (U *)(unsigned long)s->queue; }
static Update *updates(State *s) { return (Update *)(unsigned long)s->log; }
/* D1 node families currently constructed by the accepted emitter/loader.
 * The allowlist is intentional: admitting a new layout requires its scanner.
 */
static U node_subtag(U t) {
 return t==10||t==26||t==42||t==58||t==106||t==114||t==122||t==250;
}
/* Header counts are 24 bits; even 16-byte elements fit U arithmetic. */
static U raw_bytes(U tag,U n) {
 switch(tag) {
 case 7:return n?n*4:0xffffffffu;
 case 15:return n==1?4:0xffffffffu;
 case 23:return n==3?12:0xffffffffu;
 case 71:return n==3?12:0xffffffffu;
 case 79:return n==5?20:0xffffffffu;
 case 159:case 167:case 175:case 183:case 191:return n*4;
 case 199:case 207:return n;
 case 215:case 223:return n*2;
 case 231:case 239:return 4+n*8;
 case 247:return 4+n*16;
 case 255:return (n+7)/8;
 default:return 0xffffffffu;
 }
}
static U find(State *s,U p) {
 U lo=0,hi=s->count;
 while(lo<hi){U mid=lo+(hi-lo)/2;if(objects(s)[mid].old<p)lo=mid+1;else hi=mid;}
 return lo<s->count&&objects(s)[lo].old==p?lo:0xffffffffu;
}
static U forward(State *s,U value) {
 U tag=value&7,base,index,dest;Object *o;
 if(value==NIL || value==77838u || (tag!=1 && tag!=6))return value;
 base=value-tag;
 if(inside(base,s->to,s->end))return fail(s,BAD_REFERENCE);
 if(!inside(base,s->from,s->limit))return value;
 index=find(s,base);
 if(index==0xffffffffu)return fail(s,BAD_REFERENCE);
 o=objects(s)+index;
 if((tag==1)!=(o->scan==0xffffffffu))return fail(s,BAD_REFERENCE);
 if(o->moved)return o->moved+tag;
 if((W)s->next+o->size>s->end)return fail(s,NO_SPACE);
 dest=s->next;s->next+=o->size;o->moved=dest;
 __builtin_memcpy((void *)(unsigned long)dest,(void *)(unsigned long)base,o->size);
 queue(s)[s->queued++]=index;s->live++;
 return dest+tag;
}
static void root(State *s,U slot) {
 U old,value;
 if(s->error)return;
 if((slot&3)||!extent(slot,4)||inside(slot,s->from,s->limit)||inside(slot,s->to,s->end)||inside(slot,(U)(unsigned long)s,s->scratch_end)) {fail(s,BAD_ROOT);return;}
 if(s->updates==s->logcap){fail(s,NO_WORKSPACE);return;}
 old=LOAD(slot);value=forward(s,old);
 if(s->error)return;
 updates(s)[s->updates++]=(Update){slot,value};s->roots++;
 /* A stack-resident callable is nonmoving, but its environment/pool are roots.
  * No heap object can contain a stack callable in this admitted profile.
  */
 if(old!=77838u && (old&7)==6 && old>=s->stacklo+6 && (W)old+26<=s->stackhi) {
  if(LOAD(old-6)!=1578){fail(s,BAD_ROOT);return;}
  if(s->updates+6>s->logcap){fail(s,NO_WORKSPACE);return;}
  for(U i=0;i<6&&!s->error;i++){
   if(s->updates==s->logcap){fail(s,NO_WORKSPACE);return;}
   U slot=old-2+4*i,original=LOAD(slot);value=forward(s,original);updates(s)[s->updates++]=(Update){slot,value};
   /* Literal APPLY/MVC can keep the environment vector beside its callable.
    * Its elements are capture-cell references; the vector itself does not move.
    */
   if(i==1 && (original&7)==6 && original>=s->stacklo+6 && original<s->stackhi){
    U vector=original-6,count=LOAD(vector)>>8;
    if((LOAD(vector)&255)!=250||(W)vector+4+4*(W)count>s->stackhi){fail(s,BAD_ROOT);return;}
    if(count>s->logcap-s->updates){fail(s,NO_WORKSPACE);return;}
    for(U j=0;j<count&&!s->error;j++){U cell=vector+4+4*j;value=forward(s,LOAD(cell));updates(s)[s->updates++]=(Update){cell,value};}
   }
  }
 }
}
/* Configuration is a 96-byte State header in reserved owner scratch. map,
 * queue and update log are derived after validating the maximal object count.
 * Returns a checked status, never an engine trap for admitted owner storage.
 */
EXPORT U collect(U config) {
 State *s;U p,header,n,tag,bytes,scan,max,head,prior,slots,base,cap,index;
 W total,size;U seen=0,visited;
 if((config&15)||!extent(config,sizeof(State)))return BAD_OWNER;
 s=(State *)(unsigned long)config;s->error=s->count=s->queued=s->cursor=s->updates=s->live=s->roots=s->reclaimed=0;
 if((s->tcr&15)||!extent(s->tcr,256))return reject(s,BAD_OWNER);
 s->from=LOAD(s->tcr+56);s->used=LOAD(s->tcr+48);s->limit=LOAD(s->tcr+52);
 s->stacklo=LOAD(s->tcr+68);s->stackhi=LOAD(s->tcr+72);s->next=s->to;
 if(!s->from||!s->to||((s->from|s->used|s->limit|s->to|s->end)&7)||s->from>s->used||s->used>s->limit||s->to>s->end||!extent(s->from,(W)s->limit-s->from)||!extent(s->to,(W)s->end-s->to)||overlap(s->from,(W)s->limit-s->from,s->to,(W)s->end-s->to))return reject(s,BAD_OWNER);
 if(s->scratch_end<config+sizeof(State)||!extent(config,(W)s->scratch_end-config)||s->stacklo<8||s->stackhi<s->stacklo||!extent(s->stacklo,(W)s->stackhi-s->stacklo))return reject(s,BAD_OWNER);
 if(overlap(config,(W)s->scratch_end-config,s->from,(W)s->limit-s->from)||overlap(config,(W)s->scratch_end-config,s->to,(W)s->end-s->to)||overlap(config,(W)s->scratch_end-config,s->stacklo-8,(W)s->stackhi-s->stacklo+8)||overlap(config,(W)s->scratch_end-config,s->tcr,256))return reject(s,BAD_OWNER);
 max=(s->used-s->from)/8;s->map=config+sizeof(State);s->queue=s->map+max*sizeof(Object);s->log=s->queue+max*4;
 total=(W)sizeof(State)+(W)max*20+(W)s->logcap*(sizeof(Update)+4);
 if(total>(W)s->scratch_end-config||!extent(s->extra,(W)s->extra_count*4))return reject(s,NO_WORKSPACE);
 /* Inventory BEFORE copying, never infer boundaries from a root pointer. */
 p=s->from;
 while(p<s->used){
  header=LOAD(p);tag=header&255;n=header>>8;scan=0xffffffffu;size=8;
  if((tag&7)==2||(tag&7)==7){
   if(tag==74){
    /* Only strong owner-created EQ vectors; never infer weak semantics. */
    U capacity=n>=14?(n-14)/2:0;
    if(n<22||((n-14)&1)||capacity>16384||(capacity&(capacity-1))||(W)p+4+4*(W)n>s->used)return reject(s,BAD_OBJECT);
    if((LOAD(p+8)&~((1u<<30)|(1u<<29)))||!(LOAD(p+8)&(1u<<30))||LOAD(p+52)!=capacity*4||LOAD(p+56)!=0)return reject(s,BAD_OBJECT);
    if(LOAD(p+4)!=NIL||LOAD(p+12)!=0||LOAD(p+16)!=NIL||LOAD(p+20)!=NIL||LOAD(p+24)!=0||LOAD(p+28)!=NIL)return reject(s,BAD_OBJECT);
    if(((LOAD(p+32)|LOAD(p+36))&3)||LOAD(p+32)/4>capacity||LOAD(p+36)/4>capacity||LOAD(p+32)/4+LOAD(p+36)/4>capacity)return reject(s,BAD_OBJECT);
    if(LOAD(p+40)!=0xfffffffcu&&((LOAD(p+40)&3)||LOAD(p+40)/4>=capacity))return reject(s,BAD_OBJECT);
    scan=n;size=4+(W)n*4;
   }
   else if(tag==90){
    /* Stage 1 populations retain members strongly; the native GC link is zero. */
    if(n!=3||(W)p+16>s->used||LOAD(p+4)!=0||(LOAD(p+8)!=0&&LOAD(p+8)!=4))return reject(s,BAD_OBJECT);
    scan=3;size=16;
   }
   else if(tag==66){if(n!=6)return reject(s,BAD_OBJECT);scan=n;size=4+(W)n*4;}
   else if(tag==50){if(n!=4&&n!=7)return reject(s,BAD_OBJECT);scan=n;size=4+(W)n*4;}
   else if(tag==82){if(n!=1)return reject(s,BAD_OBJECT);scan=0;size=8;}
   else if(node_subtag(tag)||(tag==130&&n>=1)){if(tag==42&&n!=6&&n!=7)return reject(s,BAD_OBJECT);scan=n;size=4+(W)n*4;}
   else {bytes=raw_bytes(tag,n);if(bytes==0xffffffffu)return reject(s,BAD_OBJECT);scan=0;size=4+(W)bytes;}
   size=(size+7)&~(W)7;
  }
  if(size>(W)s->used-p)return reject(s,BAD_OBJECT);
  objects(s)[s->count++]=(Object){p,(U)size,scan,0};p+=(U)size;
 }
 /* Validate the extra callable field after inventory, before any copy. */
 for(index=0;index<s->count;index++){
  p=objects(s)[index].old;
  if(LOAD(p)==1834){
   U value=LOAD(p+28),q=value-6,i;
   if((value&7)!=6||!extent(q,32)||LOAD(q)!=2042||inside(q,s->to,s->end))return reject(s,BAD_OBJECT);
   if(inside(q,s->from,s->limit)){
    i=find(s,q);if(i==0xffffffffu||objects(s)[i].size!=32)return reject(s,BAD_OBJECT);
   }
   if(inside(q,s->stacklo,s->stackhi))return reject(s,BAD_OBJECT);
  }
 }
 /* Root chain uses the actual current descriptor shapes, including indirect
  * arena result buffers. Saved binding/control payloads are already on it.
  */
 head=LOAD(s->tcr+128);prior=s->stackhi;visited=s->log+s->logcap*sizeof(Update);
 while(head && !s->error){
  if(seen==s->logcap){fail(s,NO_WORKSPACE);break;}
  for(index=0;index<seen;index++)if(LOAD(visited+4*index)==head){fail(s,BAD_ROOT);break;}
  if(s->error)break;STORE(visited+4*seen++,head);
  if((head&7)||head<s->stacklo-8||(W)head+8>prior){fail(s,BAD_ROOT);break;}
  n=LOAD(head+4);slots=head+8;
  if(n==0xffffffffu){
   if((W)head+48>prior){fail(s,BAD_ROOT);break;}
   slots=LOAD(head+8);n=LOAD(head+12);
   if(n && !(slots==head+32&&n<=4) && !(slots>=LOAD(s->tcr+80)+16&&(W)slots+4*(W)n<=LOAD(s->tcr+76))){fail(s,BAD_ROOT);break;}
  }else if((W)slots+4*(W)n>prior){fail(s,BAD_ROOT);break;}
  if(n>s->logcap-s->updates){fail(s,NO_WORKSPACE);break;}
  for(index=0;index<n&&!s->error;index++)root(s,slots+4*index);
  head=LOAD(head);
 }
 /* Active result words have their own scanner; reserved capacity is not live. */
 n=LOAD(s->tcr+116);slots=LOAD(s->tcr+120);
 if((W)slots+4*(W)n>LOAD(s->tcr+124))fail(s,BAD_ROOT);
 if(n>s->logcap-s->updates)fail(s,NO_WORKSPACE);
 for(index=0;index<n&&!s->error;index++)root(s,slots+4*index);
 base=LOAD(s->tcr+104);cap=LOAD(s->tcr+108);
 if(cap>16777215u||(base&3)||!extent(base,4*(W)cap))fail(s,BAD_ROOT);
 if(inside(base,s->from,s->limit)){
  if(base<4||LOAD(base-4)!=(cap*256+250))fail(s,BAD_ROOT);
  p=forward(s,base+2); /* raw element address -> tagged vector */
  if(!s->error){if(s->updates==s->logcap)fail(s,NO_WORKSPACE);else updates(s)[s->updates++]=(Update){s->tcr+104,p-2};}
 } else {
  if(cap>s->logcap-s->updates)fail(s,NO_WORKSPACE);
  for(index=0;index<cap&&!s->error;index++)root(s,base+4*index);
 }
 if(s->extra_count>s->logcap-s->updates)fail(s,NO_WORKSPACE);
 for(index=0;index<s->extra_count&&!s->error;index++)root(s,LOAD(s->extra+4*index));
 while(s->cursor<s->queued && !s->error){
  Object *o=objects(s)+queue(s)[s->cursor++];
  scan=o->scan;p=o->moved;
  /* Native pools discard recyclable contents at every collection.
   * Clear only the destination; source/root publication remains atomic. */
  if(LOAD(p)==338)STORE(p+4,NIL);
  if(scan==0xffffffffu)scan=2;else p+=4;
  for(index=0;index<scan&&!s->error;index++){U old=LOAD(p+4*index),v=forward(s,old);STORE(p+4*index,v);
   /* Payload index 14 is object word 15: first key. Cached keys are roots,
    * but only bucket-key movement requests a rehash. Destination-only write
    * preserves the collector's source/root atomicity on refusal. */
   if((LOAD(o->moved)&255)==74&&index>=14&&!(index&1)&&old!=v)
    STORE(o->moved+8,LOAD(o->moved+8)|(1u<<29));}
 }
 if(s->error)return s->error;
 /* No call, poll, owner callback or allocation between validation and commit. */
 for(index=0;index<s->updates;index++)STORE(updates(s)[index].slot,updates(s)[index].value);
 s->reclaimed=(s->used-s->from)-(s->next-s->to);
 STORE(s->tcr+56,s->to);STORE(s->tcr+48,s->next);STORE(s->tcr+52,s->end);
 return 0;
}
