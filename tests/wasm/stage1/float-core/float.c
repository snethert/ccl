/* D1 mixed real floating primitives, private unshared memory. No allocation,
 * safepoint or callback in the detector. All publication occurs last.
 * Owners authenticate input object starts, disjoint extents and exclusive use.
 */
typedef unsigned int U;typedef unsigned long long W;
#define GET(p) (*(U *)(unsigned long)(p))
#define EXPORT __attribute__((visibility("default")))
#define IMPORT(n) __attribute__((import_module("detector"),import_name(n)))
IMPORT("add") int fp_add(double,double);IMPORT("sub") int fp_sub(double,double);
IMPORT("mul") int fp_mul(double,double);IMPORT("div") int fp_div(double,double);
#define LIMBS 1024u
#define NIL 77825u
#define T 77838u
typedef union {W u;double f;} D;typedef union {U u;float f;} F;
typedef struct {U d[LIMBS+1],n,neg;} Big;
typedef struct {U kind;double f;Big i;} Number;
static W memory_bytes(void){return (W)__builtin_wasm_memory_size(0)*65536;}
static U region(U p,U end){return p>=131072&&!(p&7)&&!(end&7)&&p<=end&&end<=memory_bytes();}
static U length(Big *a){return a->n?(a->n-1)*32+32-__builtin_clz(a->d[a->n-1]):0;}
static void trim(Big *a){while(a->n&&!a->d[a->n-1])a->n--;if(!a->n)a->neg=0;}
static U bit(Big *a,U n){return n/32<a->n?(a->d[n/32]>>(n%32))&1:0;}
static int compare(Big *a,Big *b){if(a->n!=b->n)return a->n>b->n?1:-1;for(U i=a->n;i--;)if(a->d[i]!=b->d[i])return a->d[i]>b->d[i]?1:-1;return 0;}
static U input(Number *a,U v,U start,U end){
 a->kind=0;a->i.n=0;a->i.neg=0;
 if(!(v&3)){int n=(int)v>>2;a->i.neg=n<0;a->i.d[0]=n<0?0u-(U)n:(U)n;a->i.n=n!=0;return 0;}
 if((v&7)!=6||v<6)return 2;U p=v-6;if(p<start||(W)p+4>end)return 2;
 U h=GET(p),n=h>>8;
 if(h==271){if((W)p+8>end)return 2;F f={.u=GET(p+4)};a->kind=32;a->f=f.f;return 0;}
 if(h==791){if((W)p+16>end)return 2;D f={.u=(W)GET(p+8)|((W)GET(p+12)<<32)};a->kind=64;a->f=f.f;return 0;}
 if((h&255)!=7||!n||(W)p+4+4*(W)n>end)return 2;
 if(n>LIMBS+1)return 3;
 U hi=GET(p+4*n);a->i.neg=hi>>31;
 if(n>1){U next=GET(p+4*(n-1));if((hi==0&&!(next>>31))||(hi==0xffffffffu&&(next>>31)))return 2;}
 W carry=a->i.neg;for(U i=0;i<n;i++){U w=GET(p+4+4*i);W z=(W)(a->i.neg?~w:w)+carry;a->i.d[i]=(U)z;carry=z>>32;}
 a->i.n=n;trim(&a->i);if(a->i.n>LIMBS)return 3;
 if(a->i.n==0||(a->i.n==1&&a->i.d[0]<=(a->i.neg?536870912u:536870911u)))return 2;
 return 0;
}
static double absd(double x){return __builtin_fabs(x);}
static U nan(double x){return x!=x;}
static U inf(double x){D d={.f=x};return (d.u&0x7fffffffffffffffULL)==0x7ff0000000000000ULL;}
static U flags(U s){return s==1?20:s==2?2:s==3?1:s==4?24:s==5?16:0;}
static U enabled(U f,U mask,U safe){U x=safe?(f&mask):0;return x&1?1:x&2?2:x&4?4:x&8?8:x&16?16:0;}
/* One rounding, using integer guard and sticky bits, never double-round a
 * bignum through f64 on the way to a single float. */
static double integer_float(Big *a,U width,U *status){
 U p=width==32?24:53,max=width==32?127:1023,bias=width==32?127:1023,n=length(a);*status=0;
 if(!n)return 0;U e=n-1,drop=n>p?n-p:0;W sig=0;
 for(U j=n;j-->drop;)sig=(sig<<1)|bit(a,j);
 U sticky=0;if(drop)for(U j=0;j+1<drop;j++)sticky|=bit(a,j);
 U guard=drop?bit(a,drop-1):0;
 if(guard||sticky)*status=5;
 if(guard&&(sticky||(sig&1)))sig++;
 if(sig==((W)1<<p)){sig>>=1;e++;}
 if(n<p)sig<<=p-n;
 if(e>max){*status=1;if(width==32){F f={.u=(a->neg<<31)|0x7f800000u};return f.f;}D d={.u=((W)a->neg<<63)|0x7ff0000000000000ULL};return d.f;}
 if(width==32){F f={.u=(a->neg<<31)|((e+bias)<<23)|((U)sig&0x7fffff)};return f.f;}
 D d={.u=((W)a->neg<<63)|((W)(e+bias)<<52)|(sig&0xfffffffffffffULL)};return d.f;
}
static double coerce(Number *a,U width,U full,U *status){
 if(!a->kind){double r=integer_float(&a->i,width,status);if(!full&&*status==5)*status=0;return r;}
 *status=0;if(width==64||a->kind==32)return a->f;
 double r=(float)a->f;
 if(nan(a->f))return r;
 if(inf(r)&&!inf(a->f)){*status=1;return r;}
 if(full&&r!=a->f){double mag=absd(a->f);*status=(mag<0x1p-126-0x1p-151)?4:5;}
 return r;
}
/* Compare without coercing an integer to the float's precision. */
static int int_float(Big *a,double f){
 if(inf(f))return f>0?-1:1;
 U neg=f<0;if(a->neg!=neg)return a->neg?-1:1;
 D d={.f=absd(f)};U exponent=(U)(d.u>>52);W sig=d.u&0xfffffffffffffULL;if(exponent)sig|=1ULL<<52;
 int shift=(int)(exponent?exponent:1)-1023-52;Big b;for(U i=0;i<=LIMBS;i++)b.d[i]=0;b.n=0;b.neg=0;U fraction=0;
 for(U j=0;j<53;j++)if((sig>>j)&1){int k=shift+(int)j;if(k<0)fraction=1;else{b.d[(U)k/32]|=1u<<((U)k%32);if(b.n<(U)k/32+1)b.n=(U)k/32+1;}}
 int c=compare(a,&b);if(!c&&fraction)c=-1;return a->neg?-c:c;
}
static int order(Number *a,Number *b){
 if(!a->kind&&!b->kind){if(a->i.neg!=b->i.neg)return a->i.neg?-1:1;int c=compare(&a->i,&b->i);return a->i.neg?-c:c;}
 if(!a->kind)return int_float(&a->i,b->f);if(!b->kind)return -int_float(&b->i,a->f);
 return a->f<b->f?-1:a->f>b->f?1:0;
}
static double operation(U op,double a,double b,U width){
 if(width==32){float x=(float)a,y=(float)b;return op==0?x+y:op==1?x-y:op==2?x*y:x/y;}
 return op==0?a+b:op==1?a-b:op==2?a*b:a/b;
}
static U classify(U op,double a,double b,double r){
 if(nan(a)||nan(b))return 0;if(nan(r))return 3;
 if(op==3&&b==0&&!inf(a))return 2;
 if(inf(r)&&!inf(a)&&!inf(b))return 1;
 return 0;
}
/* f32 operands widen exactly; products have <=48 bits. Division witnesses
 * r*b==a exactly. TwoSum catches an addend too small even for the f64 sum.
 * At the smallest normal, the quarter-ulp threshold is representable in f64. */
static U witness32(U op,double a,double b,double r){
 U exact;double truth=0;
 if(op<2){if(op==1)b=-b;double sum=a+b,bb=sum-a,err=(a-(sum-bb))+(b-bb);exact=r==sum&&err==0;truth=sum;}
 else if(op==2){truth=a*b;exact=r==truth;}
 else exact=r*b==a;
 if(exact)return 0;
 U tiny=absd(r)<0x1p-126;
 if(absd(r)==0x1p-126){if(op==3)tiny=absd(a)<(0x1p-126-0x1p-151)*absd(b);else tiny=absd(truth)<0x1p-126-0x1p-151;}
 return tiny?4:5;
}
/* Ops 0..3 add/sub/mul/div, 4..9 <, <=, =, /=, >=, >,
 * 10/11 explicit coercion to single/double. Integer-only arithmetic belongs
 * to the separate integer service; comparisons remain exact for integers.
 * Result words: value, detected flags, selected flag, stage, next, width,
 * operand-A flags, operand-B flags. Stage 1/2 conversion, 3 operation.
 * Enabled conditions publish no allocated result; the Lisp adapter signals.
 */
EXPORT U float_calculate(U op,U av,U bv,U in,U end,U out,U limit,U result,U mask,U safe){
 if(!region(in,end)||!region(out,limit)||result<131072||(result&7)||(W)result+32>memory_bytes()||mask>31||safe>1)return 1;
 U starts[3]={in,out,result};W ends[3]={end,limit,(W)result+32};
 for(U i=0;i<3;i++)for(U j=i+1;j<3;j++)if((W)starts[i]<ends[j]&&(W)starts[j]<ends[i])return 1;
 if(op>11)return 5;
 Number a,b;U error=input(&a,av,in,end);if(error)return error;
 if(op<10){error=input(&b,bv,in,end);if(error)return error;}else b.kind=0;
 U width=op==10?32:op==11?64:(a.kind==64||b.kind==64)?64:32;
 U f=0,chosen=0,stage=3,fa=0,fb=0,size=0,value=NIL;double r=0;
 if(op>=4&&op<=9){
  U unordered=(a.kind&&nan(a.f))||(b.kind&&nan(b.f));int c=unordered?0:order(&a,&b);
  U yes=op==4?c<0:op==5?c<=0:op==6?c==0:op==7?c!=0:op==8?c>=0:c>0;
  if(unordered)yes=op==7;value=yes?T:NIL;width=0;f=safe&&unordered?1:0;chosen=enabled(f,mask,safe);
 }else{
  if(op<4&&!a.kind&&!b.kind)return 5;
  U full=safe&&(mask&24),status=0;double x=coerce(&a,width,full,&status);fa=safe?flags(status):0;chosen=enabled(fa,mask,safe);
  if(chosen){f=fa;stage=1;goto commit;}
  if(op>=10){r=x;f=fa;stage=1;goto result;}
  double y=coerce(&b,width,full,&status);fb=safe?flags(status):0;chosen=enabled(fb,mask,safe);
  if(chosen){f=fb;stage=2;goto commit;}
  r=operation(op,x,y,width);status=safe?classify(op,x,y,r):0;
  if(full&&!status&&!nan(x)&&!nan(y)&&!inf(x)&&!inf(y)&&!inf(r)){
   if(width==32)status=witness32(op,x,y,r);
   else status=op==0?fp_add(x,y):op==1?fp_sub(x,y):op==2?fp_mul(x,y):fp_div(x,y);
  }
  f=safe?flags(status):0;chosen=enabled(f,mask,safe);
result:
  if(!chosen){size=width==32?8:16;if((W)out+size>limit)return 3;value=out+6;}
 }
commit:
 if(chosen)value=NIL;
 if(size){if(width==32){F x={.f=(float)r};GET(out)=271;GET(out+4)=x.u;}else{D x={.f=r};GET(out)=791;GET(out+4)=0;GET(out+8)=(U)x.u;GET(out+12)=(U)(x.u>>32);}}
 GET(result)=value;GET(result+4)=f;GET(result+8)=chosen;GET(result+12)=stage;GET(result+16)=out+size;GET(result+20)=width;GET(result+24)=fa;GET(result+28)=fb;return 0;
}
