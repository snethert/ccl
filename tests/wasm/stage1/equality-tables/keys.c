/* Included into the reviewed strong hash service. MODE is 1 (EQL) or 2
 * (EQUAL). Canonical D1 numbers and finite cons structures, simple strings and
 * bit vectors. Other admitted heap objects compare by identity. No allocation,
 * call to JS, FP instructions or safepoint; work is bounded before any store.
 * Owner supplies canonical owned objects. This is not an object-start census.
 */
#define KEY_DEPTH 1024u
#define KEY_STEPS 65536u
static U data_bytes(U tag,U n){
 switch(tag){
 case 7:return n&&n<=1024?n*4:NONE;
 case 15:return n==1?4:NONE;
 case 23:return n==3?12:NONE;
 case 10:case 26:return n==2?8:NONE;
 case 42:case 58:case 74:case 106:case 114:case 250:
 case 159:case 167:case 175:case 183:case 191:return n*4;
 case 199:case 207:return n;
 case 215:case 223:return n*2;
 case 231:case 239:return 4+n*8;
 case 247:return 4+n*16;
 case 255:return (n+7)/8;
 default:return NONE; /* macptr, scalar complex floats, displaced/pathnames */
 }
}
static U forbidden(U p,U n,U b,U bytes,U scratch,U scratch_end,U result){
 return overlap(p,n,b,bytes)||overlap(p,n,scratch,(W)scratch_end-scratch)||overlap(p,n,result,16)||overlap(p,n,1048576,65536);
}
static U keys_valid(U k,U b,U bytes,U scratch,U scratch_end,U result){
 U work[KEY_DEPTH],used=1,steps=0;work[0]=k;
 while(used){
  if(++steps>KEY_STEPS)return 0;k=work[--used];
  if(k==EMPTY||k==DELETED)return 0;
  if(k==NIL||k==TRUE)continue;
  if((k&7)==1){
   if(!span(k-1,8))return 0;
   if(MODE==2){
    if(forbidden(k-1,8,b,bytes,scratch,scratch_end,result)||used+2>KEY_DEPTH)return 0;
    work[used++]=L(k-1);work[used++]=L(k+3);
   }
  }else if((k&7)==6){
   U p=k-6;if(!span(p,4)||overlap(p,4,1048576,65536))return 0;
   U h=L(p),tag=h&255,n=h>>8,sz=data_bytes(tag,n);
   if(sz==NONE||!span(p,4+(W)sz))return 0;
   U inspected=tag==7||tag==15||tag==23||tag==10||tag==26||(MODE==2&&(tag==191||tag==255));
   if(inspected&&forbidden(p,4+sz,b,bytes,scratch,scratch_end,result))return 0;
   if(tag==10||tag==26){
    if(used+2>KEY_DEPTH)return 0;work[used++]=L(p+4);work[used++]=L(p+8);
   }
  }
 }
 return 1;
}
static U words_equal(U a,U b,U n){for(U i=0;i<n;i++)if(L(a+i*4)!=L(b+i*4))return 0;return 1;}
static U byte_at(U p){return *(unsigned char *)(unsigned long)p;}
static U same(U a,U b){
 U x[KEY_DEPTH],y[KEY_DEPTH],used=1;x[0]=a;y[0]=b;
 while(used){
  --used;a=x[used];b=y[used];if(a==b)continue;
  if((a&7)!=(b&7)||a==NIL||b==NIL||a==TRUE||b==TRUE)return 0;
  if(MODE==2&&(a&7)==1){
   x[used]=L(a-1);y[used++]=L(b-1);x[used]=L(a+3);y[used++]=L(b+3);continue;
  }
  if((a&7)!=6)return 0;
  U ha=L(a-6),hb=L(b-6),tag=ha&255,n=ha>>8;if(ha!=hb)return 0;
  if(tag==10||tag==26){x[used]=L(a-2);y[used++]=L(b-2);x[used]=L(a+2);y[used++]=L(b+2);continue;}
  if(tag==7||tag==15||(MODE==2&&tag==191)){if(!words_equal(a-2,b-2,n))return 0;continue;}
  if(tag==23){if(!words_equal(a+2,b+2,2))return 0;continue;}
  if(MODE==2&&tag==255){
   for(U i=0;i<(n+7)/8;i++){U mask=(i==n/8&&(n&7))?((1u<<(n&7))-1):255;if((byte_at(a-2+i)&mask)!=(byte_at(b-2+i)&mask))return 0;}continue;
  }
  return 0;
 }
 return 1;
}
static U mix(U h,U x){return (h^x)*16777619u;}
static U content_hash(U k,U cap){
 U work[KEY_DEPTH],used=1,h=2166136261u;work[0]=k;
 while(used){
  k=work[--used];
  if(k==NIL||k==TRUE||(k&7)!=1&&(k&7)!=6){h=mix(h,k);continue;}
  if(MODE==2&&(k&7)==1){h=mix(h,1);work[used++]=L(k-1);work[used++]=L(k+3);continue;}
  if((k&7)==6){
   U head=L(k-6),tag=head&255,n=head>>8;
   if(tag==10||tag==26){h=mix(h,tag);work[used++]=L(k-2);work[used++]=L(k+2);continue;}
   if(tag==7||tag==15||tag==23||(MODE==2&&(tag==191||tag==255))){
    h=mix(h,head);
    if(tag==255){for(U i=0;i<(n+7)/8;i++){U mask=(i==n/8&&(n&7))?((1u<<(n&7))-1):255;h=mix(h,byte_at(k-2+i)&mask);}}
    else {U data=tag==23?k+2:k-2,count=tag==23?2:n;for(U i=0;i<count;i++)h=mix(h,L(data+i*4));}
    continue;
   }
  }
  // Address-independent opaque contribution also handles relocation of an
  // opaque component inside a pinned EQUAL key. Collisions use exact identity.
  h=mix(h,0x9e3779b9u);
 }
 return h&(cap-1);
}
EXPORT U ht_kind(void){return MODE;}
