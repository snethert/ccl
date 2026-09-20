/* Checked D1 integer arithmetic, single synchronous owner, no calls/safepoints.
 * a/b are tagged integers. The owner authenticates object starts in [in, end).
 * All regions are disjoint and outside the module's reserved low C stack.
 * Scratch is disposable. Failure does not change input, output or result words.
 * No fallback calls, memory growth, condition delivery or allocation retry here.
 */
typedef unsigned int U;
typedef unsigned long long W;
#define MAX_LIMBS 1024u
#define STRIDE (MAX_LIMBS+2u)
#define WORK_BYTES (4u*STRIDE*4u)
#define GET(p) (*(U *)(unsigned long)(p))
#define EXPORT __attribute__((visibility("default")))
enum {OK=0, OWNER=1, INTEGER=2, CAPACITY=3, ZERO_DIVISOR=4, OPERATION=5};
enum {ADD=0,SUB=1,MUL=2,ASH=3,LENGTH=4,TRUNCATE=5};
typedef struct {U *d,n,neg;} Big;
static W bytes(void){return (W)__builtin_wasm_memory_size(0)*65536u;}
static U range(U p,U end){return p>=131072u && !(p&7) && !(end&7) && p<=end && end<=bytes();}
static void clear(Big *x){for(U i=0;i<STRIDE;i++)x->d[i]=0;x->n=0;x->neg=0;}
static void trim(Big *x){while(x->n && !x->d[x->n-1])x->n--;if(!x->n)x->neg=0;}
static U bitlength(Big *x){return x->n?(x->n-1)*32+32-__builtin_clz(x->d[x->n-1]):0;}
static U fitsfix(Big *x){return x->n==0 || (x->n==1 && x->d[0] <= (x->neg?536870912u:536870911u));}
static U read_integer(Big *x,U v,U in,U end){
 if(!(v&3)){U raw=(U)((int)v>>2);x->neg=raw>>31;x->d[0]=x->neg?0u-raw:raw;x->n=x->d[0]?1:0;return OK;}
 if((v&7)!=6 || v<6)return INTEGER;
 U p=v-6;if((p&7)||p<in||(W)p+4>end)return INTEGER;
 U h=GET(p),n=h>>8;
 if((h&255)!=7||!n||n>MAX_LIMBS+1||(W)p+4+4*(W)n>end)return INTEGER;
 U high=GET(p+4*n);x->neg=high>>31;
 if(n>1){U next=GET(p+4*(n-1));if((high==0&&!(next>>31))||(high==0xffffffffu&&(next>>31)))return INTEGER;}
 W carry=x->neg;
 for(U i=0;i<n;i++){U w=GET(p+4+4*i);W z=(W)(x->neg?~w:w)+carry;x->d[i]=(U)z;carry=z>>32;}
 x->n=n;trim(x);if(x->n>MAX_LIMBS)return CAPACITY;if(fitsfix(x))return INTEGER;return OK;
}
static int cmp(Big *a,Big *b){if(a->n!=b->n)return a->n>b->n?1:-1;for(U i=a->n;i--;){if(a->d[i]!=b->d[i])return a->d[i]>b->d[i]?1:-1;}return 0;}
static void plus(Big *r,Big *a,Big *b){
 U n=a->n>b->n?a->n:b->n;W carry=0;
 for(U i=0;i<n;i++){W z=(W)(i<a->n?a->d[i]:0)+(i<b->n?b->d[i]:0)+carry;r->d[i]=(U)z;carry=z>>32;}
 r->n=n;if(carry)r->d[r->n++]=(U)carry;
}
/* Magnitudes a >= b. r can alias a. */
static void minus(Big *r,Big *a,Big *b){
 W borrow=0;U n=a->n;
 for(U i=0;i<n;i++){W av=a->d[i],bv=(W)(i<b->n?b->d[i]:0)+borrow;r->d[i]=(U)(av-bv);borrow=av<bv;}
 r->n=n;trim(r);
}
static U add(Big *r,Big *a,Big *b){
 if(a->neg==b->neg){plus(r,a,b);r->neg=a->neg;}else if(cmp(a,b)>=0){minus(r,a,b);r->neg=a->neg;}else{minus(r,b,a);r->neg=b->neg;}
 trim(r);return r->n>MAX_LIMBS?CAPACITY:OK;
}
static U multiply(Big *r,Big *a,Big *b){
 if(!a->n||!b->n)return OK;
 if(a->n+b->n>MAX_LIMBS+1)return CAPACITY;
 r->n=a->n+b->n;r->neg=a->neg^b->neg;
 for(U i=0;i<a->n;i++){W carry=0;for(U j=0;j<b->n;j++){W z=(W)a->d[i]*b->d[j]+r->d[i+j]+carry;r->d[i+j]=(U)z;carry=z>>32;}r->d[i+b->n]=(U)carry;}
 trim(r);return r->n>MAX_LIMBS?CAPACITY:OK;
}
static void increment(Big *r){U i=0;while(i<r->n && ++r->d[i]==0)i++;if(i==r->n)r->d[r->n++]=1;}
static U shift(Big *r,Big *a,Big *b){
 if(!a->n)return OK;
 U count=b->n>1?0xffffffffu:(b->n?b->d[0]:0),bits=bitlength(a);
 if(!b->neg){
  if(count>MAX_LIMBS*32u-bits)return CAPACITY;
  U words=count/32,part=count%32;W carry=0;
  for(U i=0;i<a->n;i++){W z=((W)a->d[i]<<part)|carry;r->d[i+words]=(U)z;carry=z>>32;}
  r->n=a->n+words;if(carry)r->d[r->n++]=(U)carry;r->neg=a->neg;
 }else{
  if(count>=bits){r->n=a->neg;r->d[0]=a->neg;r->neg=a->neg;return OK;}
  U words=count/32,part=count%32,discard=0;
  for(U i=0;i<words;i++)discard|=a->d[i];
  if(part)discard|=a->d[words]&((1u<<part)-1);
  for(U i=words;i<a->n;i++){U x=a->d[i]>>part;if(part&&i+1<a->n)x|=a->d[i+1]<<(32-part);r->d[i-words]=x;}
  r->n=a->n-words;trim(r);if(a->neg&&discard)increment(r);r->neg=a->neg;
 }
 trim(r);return OK;
}
static void left_one(Big *x,U bit){W carry=bit;for(U i=0;i<x->n;i++){W z=((W)x->d[i]<<1)|carry;x->d[i]=(U)z;carry=z>>32;}if(carry)x->d[x->n++]=(U)carry;}
static U divide(Big *q,Big *r,Big *a,Big *b){
 if(!b->n)return ZERO_DIVISOR;
 q->n=a->n;q->neg=a->neg^b->neg;
 for(U bit=bitlength(a);bit--;){left_one(r,(a->d[bit/32]>>(bit%32))&1);if(cmp(r,b)>=0){minus(r,r,b);q->d[bit/32]|=1u<<(bit%32);}}
 trim(q);r->neg=a->neg;trim(r);return OK;
}
/* Convert sign/magnitude to minimal D1 two's complement in scratch. */
static U encode(Big *x,U *tagged){
 if(fitsfix(x)){*tagged=(x->neg?0u-x->d[0]:x->d[0])<<2;return 0;}
 W carry=x->neg;for(U i=0;i<x->n;i++){W z=(W)(x->neg?~x->d[i]:x->d[i])+carry;x->d[i]=(U)z;carry=z>>32;}
 if((x->d[x->n-1]>>31)!=x->neg)x->d[x->n++]=x->neg?0xffffffffu:0;
 return (4+4*x->n+7)&~7u;
}
static void write_object(Big *x,U p,U size){GET(p)=(x->n<<8)|7;for(U i=0;i<x->n;i++)GET(p+4+4*i)=x->d[i];for(U i=4+4*x->n;i<size;i+=4)GET(p+i)=0;}
/* Result area is 16 bytes: first value, second value, value count, next alloc.
 * Caller supplies a reservation; commit has no call, poll or failure point.
 * Owners may retry CAPACITY only after distinguishing workspace/heap requests.
 */
EXPORT U integer_calculate(U op,U av,U bv,U in,U end,U out,U limit,U scratch,U scratch_end,U result){
 if(!range(in,end)||!range(out,limit)||!range(scratch,scratch_end)||result<131072u||(result&7)||(W)result+16>bytes())return OWNER;
 if((W)scratch+WORK_BYTES>scratch_end)return CAPACITY;
 U starts[4]={in,out,scratch,result};W ends[4]={end,limit,scratch_end,(W)result+16};
 for(U i=0;i<4;i++)for(U j=i+1;j<4;j++)if((W)starts[i]<ends[j]&&(W)starts[j]<ends[i])return OWNER;
 if(op>TRUNCATE)return OPERATION;
 Big a={(U *)(unsigned long)scratch,0,0},b={a.d+STRIDE,0,0},r={b.d+STRIDE,0,0},rem={r.d+STRIDE,0,0};
 clear(&a);clear(&b);clear(&r);clear(&rem);
 U error=read_integer(&a,av,in,end);if(error)return error;
 if(op!=LENGTH){error=read_integer(&b,bv,in,end);if(error)return error;}
 switch(op){
 case ADD:error=add(&r,&a,&b);break;
 case SUB:if(b.n)b.neg^=1;error=add(&r,&a,&b);break;
 case MUL:error=multiply(&r,&a,&b);break;
 case ASH:error=shift(&r,&a,&b);break;
 case LENGTH:
  if(a.neg){b.n=1;b.d[0]=1;minus(&a,&a,&b);}
  r.d[0]=bitlength(&a);r.n=r.d[0]?1:0;break;
 case TRUNCATE:error=divide(&r,&rem,&a,&b);break;
 }
 if(error)return error;
 U first=0,second=0,n=encode(&r,&first),m=op==TRUNCATE?encode(&rem,&second):0;
 if((W)out+n+m>limit)return CAPACITY;
 if(n){write_object(&r,out,n);first=out+6;}
 if(m){write_object(&rem,out+n,m);second=out+n+6;}
 GET(result)=first;GET(result+4)=second;GET(result+8)=op==TRUNCATE?2:1;GET(result+12)=out+n+m;
 return OK;
}
EXPORT U integer_workspace_bytes(void){return WORK_BYTES;}
