typedef unsigned int U;typedef unsigned long long W;
#define L(p) (*(U *)(unsigned long)(p))
#define S(p,v) (L(p)=(v))
#define NIL 77825u
/* The owner reserves a fresh pinned macptr and its raw buffer. The callback
 * validates that exact grant, zeros the buffer, then returns the pointer. */
__attribute__((visibility("default"))) U counter_run(U ptr,U ptr_end,U op,U kind,U unused,U base,U end,U result){
 W limit=(W)__builtin_wasm_memory_size(0)*65536;
 if(op!=5||(kind!=0&&kind!=4)||unused!=NIL)return 1;
 U bytes=kind==0?80:8;
 if((base&7)||(W)base+16+bytes!=end||(W)end>limit||(result&3)||(W)result+16>limit||((W)result<end&&(W)base<(W)result+16))return 2;
 if(ptr!=base+6||ptr_end!=base+16||L(base)!=799||L(base+4)!=base+16||L(base+8)||L(base+12))return 3;
 for(U i=0;i<bytes;i++)*((unsigned char *)(unsigned long)(base+16+i))=0;
 S(result,ptr);S(result+4,NIL);S(result+8,1);S(result+12,0);return 0;
}
