/* Strong EQ backing vectors for D1. Single synchronous owner; no calls or
 * safepoints during an operation. Not the native HASH-TABLE wrapper or its weak
 * variants. The fixed-capacity vector is a native-shaped GC object (subtag 74).
 * The owner supplies backed, disjoint scratch and result storage. */
typedef unsigned int U;
typedef unsigned long long W;
#define L(p) (*(U *)(unsigned long)(p))
#define S(p,v) (L(p)=(v))
#define NIL 77825u
#define TRUE 77838u
#define EMPTY 243u
#define DELETED 251u
#define TRACK (1u<<30)
#define MOVED (1u<<29)
#define NONE 0xffffffffu
#define EXPORT __attribute__((visibility("default")))
enum { BAD_OWNER=1, BAD_TABLE=2, BAD_KEY=3, FULL=4, BAD_OPERATION=5 };
static W memory_size(void){return (W)__builtin_wasm_memory_size(0)*65536;}
static U span(U p,W n){return (W)p+n<=memory_size();}
static U overlap(U a,W n,U b,W m){return (W)a<(W)b+m&&(W)b<(W)a+n;}
static U capacity_ok(U n){return n>=4&&n<=16384&&!(n&(n-1));}
static U bytes(U n){return 64+8*n;}
static U key_ok(U k){return k!=EMPTY&&k!=DELETED;}
static U hash(U k,U n){k^=k>>16;k*=0x7feb352du;k^=k>>15;k*=0x846ca68bu;k^=k>>16;return k&(n-1);}
static U key_slot(U b,U i){return b+60+8*i;}
static void invalidate(U b){S(b+40,0xfffffffcu);S(b+44,EMPTY);S(b+48,NIL);}
static void cache(U b,U i,U k,U v){S(b+40,i*4);S(b+44,k);S(b+48,v);}
static U shape(U b,U end,U *n){
 if((b&7)||end<b||!span(b,60)||end-b<60)return 0;
 U h=L(b),c=h>>8;
 if((h&255)!=74||c<22||((c-14)&1))return 0;
 *n=(c-14)/2;
 if(!capacity_ok(*n)||end-b!=bytes(*n)||!span(b,bytes(*n)))return 0;
 if((L(b+8)&~(TRACK|MOVED))||!(L(b+8)&TRACK)||L(b+52)!=*n*4||L(b+56)!=0)return 0;
 if(L(b+4)!=NIL||L(b+12)!=0||L(b+16)!=NIL||L(b+20)!=NIL||L(b+24)!=0||L(b+28)!=NIL)return 0;
 if((L(b+32)|L(b+36))&3||L(b+32)/4>*n||L(b+36)/4>*n||L(b+32)/4+L(b+36)/4>*n)return 0;
 if(L(b+40)!=0xfffffffcu&&((L(b+40)&3)||L(b+40)/4>=*n))return 0;
 if((L(b+40)==0xfffffffcu)!=(L(b+44)==EMPTY))return 0;
 return 1;
}
EXPORT U ht_size(U capacity){return capacity_ok(capacity)?bytes(capacity):0;}
EXPORT U ht_init(U base,U end,U capacity){
 if(!capacity_ok(capacity)||(base&7)||end<base||end-base!=bytes(capacity)||!span(base,bytes(capacity)))return BAD_OWNER;
 S(base,((14+capacity*2)<<8)|74);S(base+4,NIL);S(base+8,TRACK);S(base+12,0);S(base+16,NIL);S(base+20,NIL);S(base+24,0);S(base+28,NIL);S(base+32,0);S(base+36,0);invalidate(base);S(base+52,capacity*4);S(base+56,0);
 for(U i=0;i<capacity;i++){S(key_slot(base,i),EMPTY);S(key_slot(base,i)+4,NIL);}S(end-4,0);
 return 0;
}
/* Return existing slot, otherwise first tombstone/empty slot, otherwise NONE.
 * Bound the search even when the table has no empty bucket. */
static U locate(U b,U n,U key,U *found){
 U at=hash(key,n),free=NONE;*found=0;
 for(U i=0;i<n;i++,at=(at+1)&(n-1)){
  U k=L(key_slot(b,at));
  if(k==key){*found=1;return at;}
  if(k==DELETED&&free==NONE)free=at;
  if(k==EMPTY)return free==NONE?at:free;
 }
 return free;
}
/* All validation precedes rehash writes. Scratch contains exactly the live
 * pairs. Rehash is synchronous: no collector sees its transient layout. */
static U rehash(U b,U n,U scratch){
 U used=0,dead=0;
 for(U i=0;i<n;i++){S(scratch+i*8,EMPTY);S(scratch+i*8+4,NIL);}
 for(U i=0;i<n;i++){
  U p=key_slot(b,i),k=L(p),v=L(p+4);
  if(k==EMPTY||k==DELETED){if(v!=NIL)return BAD_TABLE;if(k==DELETED)dead++;}
  else {
   U at=hash(k,n);used++;
   for(U j=0;j<n;j++,at=(at+1)&(n-1)){
    U present=L(scratch+at*8);
    if(present==k)return BAD_TABLE;
    if(present==EMPTY){S(scratch+at*8,k);S(scratch+at*8+4,v);break;}
   }
  }
 }
 if(used!=L(b+36)/4||dead!=L(b+32)/4)return BAD_TABLE;
 invalidate(b);
 __builtin_memcpy((void *)(unsigned long)(b+60),(void *)(unsigned long)scratch,n*8);
 S(b+32,0);S(b+8,L(b+8)&~MOVED);
 return 0;
}
/* op 0 GET (value,present), 1 SET (value), 2 REMOVE (present), 3 COUNT.
 * Four publication words: value0, value1, number of values, rehashed?.
 * Refusal preserves the vector and publication; scratch is expendable.
 * The owner supplies an exact object extent, not an arbitrary heap limit. */
EXPORT U ht_run(U table,U end,U op,U key,U value,U scratch,U scratch_end,U result){
 U b=table-6,n,found,at,p,v,rehashed=0;
 if((table&7)!=6||!shape(b,end,&n))return BAD_TABLE;
 if((scratch&7)||(result&3)||scratch_end<scratch||(W)scratch_end-scratch<(W)n*8||!span(scratch,(W)scratch_end-scratch)||!span(result,16)||overlap(b,bytes(n),scratch,(W)scratch_end-scratch)||overlap(b,bytes(n),result,16)||overlap(scratch,(W)scratch_end-scratch,result,16))return BAD_OWNER;
 if(op>3)return BAD_OPERATION;
 if(op!=3&&!key_ok(key))return BAD_KEY;
 /* Full-table insertion refuses before rehash, preserving the vector. */
 if(op==1&&L(b+36)/4==n){found=0;for(U i=0;i<n;i++)if(L(key_slot(b,i))==key)found=1;if(!found)return FULL;}
 if(L(b+8)&MOVED){U status=rehash(b,n,scratch);if(status)return status;rehashed=1;}
 if(op==3){v=L(b+36);found=NIL;goto publish;}
 if(L(b+44)==key){at=L(b+40)/4;found=1;v=L(b+48);}
 else {at=locate(b,n,key,&found);v=found?L(key_slot(b,at)+4):value;}
 if(op==0){if(found)cache(b,at,key,v);found=found?TRUE:NIL;goto publish;}
 if(op==1){
  if(at==NONE)return BAD_TABLE;
  p=key_slot(b,at);
  if(!found){if(L(p)==DELETED)S(b+32,L(b+32)-4);S(b+36,L(b+36)+4);S(p,key);}
  S(p+4,value);cache(b,at,key,value);v=value;found=NIL;goto publish;
 }
 if(found){p=key_slot(b,at);S(p,DELETED);S(p+4,NIL);S(b+32,L(b+32)+4);S(b+36,L(b+36)-4);invalidate(b);v=TRUE;}
 else v=NIL;
 found=NIL;
publish:
 S(result,v);S(result+4,found);S(result+8,op==0?2:1);S(result+12,rehashed);return 0;
}
