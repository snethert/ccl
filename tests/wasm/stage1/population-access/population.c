/* Strong-population-v1 accessors. No weak headers and no allocation or poll.
 * Owner-admitted ordinary vector: type code 0/1 and contents list. */
typedef unsigned U;typedef unsigned long long W;
#define L(p) (*(U *)(unsigned long)(p))
#define S(p,v) (L(p)=(v))
#define NIL 77825u
#define EXPORT __attribute__((visibility("default")))
static U backed(U p,W n){return (W)p+n<=((W)__builtin_wasm_memory_size(0)<<16);}
static U overlap(U p,U n,U q,U m){return (W)p+n>q&&(W)q+m>p;}
EXPORT U pop_run(U object,U end,U op,U key,U value,U scratch,U scratch_end,U result){
 (void)value;(void)scratch;(void)scratch_end;
 U base=object-6,answer;
 if((object&7)!=6||(base&7)||!backed(base,16)||end!=(W)base+16||L(base)!=762||L(base+4)>4||(L(base+4)&3)||L(base+12)!=0)return 2;
 if((result&3)||!backed(result,16)||overlap(base,16,result,16))return 1;
 if(op>2)return 5;
 if(op==1&&key!=NIL&&((key&7)!=1||!backed(key-1,8)))return 3;
 if(op==0)answer=L(base+8);
 else if(op==1){S(base+8,key);answer=key;}
 else answer=L(base+4);
 S(result,answer);S(result+4,NIL);S(result+8,1);S(result+12,0);return 0;
}
