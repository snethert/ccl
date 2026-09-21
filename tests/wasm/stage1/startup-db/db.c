/* Owner-admitted pinned D1 interface-dir DLL. Single synchronous Worker;
 * validate the complete list before clearing any cached DB handle. */
typedef unsigned int U;
typedef unsigned long long W;
#define L(p) (*(U *)(unsigned long)(p))
#define S(p,v) (L(p)=(v))
#define NIL 77825u
#define EXPORT __attribute__((visibility("default")))
static U span(U p,W n){return (W)p+n<=((W)__builtin_wasm_memory_size(0)*65536);}
static U member(U p,U base,U count){return p>=base+30&&((p-(base+30))%56)==0&&(p-(base+30))/56<count;}
/* Same eight-word owner-leaf signature as the reviewed hash adapter.
 * owner_base/end delimit exactly one 24-byte header and N 56-byte dirs.
 * key/value are trusted identities of their pinned structure descriptors. */
EXPORT U db_run(U head,U head_end,U op,U header_type,U dir_type,U base,U end,U result){
 if(op!=5)return 5;
 if((base&7)||end<base||(W)end-base<24||((end-base-24)%56)||!span(base,(W)end-base)||(result&3)||!span(result,16)||((W)result<end&&(W)base<(W)result+16))return 1;
 U count=(end-base-24)/56;if(count>1024)return 1;
 if(head!=base+6||head_end!=base+24||L(base)!=((4<<8)|122)||L(base+4)!=header_type||header_type==dir_type)return 2;
 for(U i=0;i<count;i++){U p=base+24+56*i;if(L(p)!=((12<<8)|122)||L(p+4)!=dir_type)return 2;}
 U prev=head,current=L(base+12),seen=0;
 while(current!=head){
  if(seen++>=count||!member(current,base,count))return 3;
  U p=current-6;if(L(p+8)!=prev)return 3;
  prev=current;current=L(p+12);
 }
 if(seen!=count||L(base+8)!=prev)return 3;
 /* No calls, allocation, polls or foreign file operations during mutation. */
 current=L(base+12);
 while(current!=head){U p=current-6;for(U slot=5;slot<12;slot++)S(p+4+4*slot,NIL);current=L(p+12);}
 /* Publish every word, even when the list was empty or already reset. */
 S(result,NIL);S(result+4,NIL);S(result+8,1);S(result+12,0);return 0;
}
