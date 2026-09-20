/* Single-owner, non-polling package lookup/intern kernel. D1 symbols, UTF-32
 * strings, eight-cell packages, native-shaped (vector . (count . limit))
 * tables. Fixed capacity; one used package per package, sealed topology. */
typedef unsigned U;typedef unsigned long long W;
#define L(p) (*(U*)(unsigned long)(p))
#define S(p,v) (L(p)=(v))
#define NIL 77825u
#define TRUE 77838u
#define NILSYM 77864u
#define UNBOUND 51u
#define MAGIC 0x53594d31u
#define EXPORT __attribute__((visibility("default")))
enum {OWNER=1,SHAPE=2,PACKAGE=3,STRING=4,SPACE=5,HASH=6,OP=7,CONFLICT=8};
static W mem(void){return (W)__builtin_wasm_memory_size(0)*65536;}
static U span(U p,W n){return (W)p+n<=mem();}
static U inside(U c,U p,W n){return p>=L(c+4)&&(W)p+n<=L(c+12);}
static U overlap(U a,W n,U b,W m){return (W)a<(W)b+m&&(W)b<(W)a+n;}
static U config(U c,U result){
 if(c<1114112||(c&7)||!span(c,80)||L(c)!=MAGIC)return 0;
 U base=L(c+4),end=L(c+8),next=L(c+12),sc=L(c+52),sz=L(c+56);
 if((base&7)||(end&7)||(next&7)||base<4194304||end<base||next<base||next>end||!span(base,(W)end-base))return 0;
 if(sc<1114112||result<1114112||L(c+28)!=NIL||L(c+32)!=TRUE||(sc&7)||sz<8192||!span(sc,sz)||(result&3)||!span(result,16))return 0;
 if(overlap(base,(W)end-base,c,80)||overlap(base,(W)end-base,sc,sz)||overlap(base,(W)end-base,result,16)||overlap(sc,sz,c,80)||overlap(sc,sz,result,16)||overlap(c,80,result,16))return 0;
 return 1;
}
static U vector(U c,U node,U *n){if((node&7)!=6||!inside(c,node-6,4)||(L(node-6)&255)!=250)return 0;*n=L(node-6)>>8;return *n<=1024&&inside(c,node-6,((W)*n*4+11)&~7ull);}
static U string(U node,U *n){if((node&7)!=6||!span(node-6,4)||(L(node-6)&255)!=191)return 0;*n=L(node-6)>>8;if(*n>4096||!span(node-6,(W)*n*4+4))return 0;for(U i=0;i<*n;i++)if(L(node-2+4*i)>0x10ffffu)return 0;return 1;}
static U equal(U a,U b){U n,m;if(!string(a,&n)||!string(b,&m)||n!=m)return 0;for(U i=0;i<n;i++)if(L(a-2+4*i)!=L(b-2+4*i))return 0;return 1;}
static U hash(U name){U h=2166136261u,n=L(name-6)>>8;for(U i=0;i<n;i++){h^=L(name-2+4*i);h*=16777619u;}return h;}
EXPORT U symbol_hash(U name){U n;return string(name,&n)?hash(name):0;}
static U symbase(U c,U sym){U p=sym==NIL?NILSYM:sym-6;if(sym!=NIL&&(sym&7)!=6)return 0;if(sym!=NIL&&sym!=TRUE&&!inside(c,p,32))return 0;return span(p,32)&&L(p)==1850?p:0;}
static U package(U c,U p){U n,root=L(c+16);if(!vector(c,root,&n)||n<2||n>16)return 0;for(U i=0;i<n;i++)if(L(root-2+4*i)==p)return (p&7)==6&&inside(c,p-6,40)&&L(p-6)==2146;return 0;}
/* Table descriptor is two conses, whose vector holds raw symbol pointers.
 * NIL is stored as its symbol pointer, never confused with an empty bucket. */
static U table(U c,U t,U *v,U *n){
 if((t&7)!=1||!inside(c,t-1,8))return 0;U tail=L(t-1);*v=L(t+3);
 if((tail&7)!=1||!inside(c,tail-1,8)||!vector(c,*v,n)||*n<4||*n>256||(*n&(*n-1)))return 0;
 U count=L(tail+3),limit=L(tail-1);return !(count&3)&&count/4<=*n&&limit==*n*4;
}
static U symbol(U raw){return raw==NILSYM+6?NIL:raw;}
static U rawsym(U sym){return sym==NIL?NILSYM+6:sym;}
static U bucket(U v,U i){return v-2+4*i;}
static U locate(U c,U t,U name,U *found){U v,n;if(!table(c,t,&v,&n))return 0;U at=hash(name)&(n-1);*found=0;for(U i=0;i<n;i++,at=(at+1)&(n-1)){U raw=L(bucket(v,at));if(!raw)return bucket(v,at);U p=symbase(c,symbol(raw));if(!p)return 0;if(equal(name,L(p+4))){*found=1;return bucket(v,at);}}return 0;}
static U lookup(U c,U pkg,U name,U *where,U *target){
 U status[3]={L(c+40),L(c+44),L(c+48)},tables[3]={L(pkg-2),L(pkg+2),0};U used=L(pkg+6);
 if(used!=NIL){if((used&7)!=1||!inside(c,used-1,8)||L(used-1)!=NIL||!package(c,L(used+3)))return SHAPE;tables[2]=L(L(used+3)+2);}
 *where=NIL;*target=NIL;
 for(U i=0;i<3;i++)if(tables[i]){U found=0,at=locate(c,tables[i],name,&found);if(!at){U v,n;if(!table(c,tables[i],&v,&n))return SHAPE;/* A full valid table may lack this name. */}else if(found){*where=status[i];*target=symbol(L(at));return 0;}}
 return 0;
}
/* Build all tables in expendable scratch, validate every row before copying.
 * No lookup is admitted until target hash version 1 has been published. */
EXPORT U symbols_admit(U c,U result){
 if(!config(c,result))return OWNER;U root=L(c+16),np;if(!vector(c,root,&np)||np<2||np>16)return PACKAGE;
 U sc=L(c+52),used=0,tabs[32],vecs[32],sizes[32],offsets[32],nt=0;
 for(U i=0;i<np;i++){
  U pkg=L(root-2+4*i);if(!package(c,pkg))return PACKAGE;for(U j=0;j<i;j++)if(pkg==L(root-2+4*j))return PACKAGE;
  U uses=L(pkg+6);if(uses!=NIL&&((uses&7)!=1||!inside(c,uses-1,8)||L(uses-1)!=NIL||!package(c,L(uses+3))))return PACKAGE;
  for(U k=0;k<2;k++){
   U t=L(pkg-2+4*k),v,n;if(!table(c,t,&v,&n)||(W)used+n*4>L(c+56))return SHAPE;
   for(U j=0;j<nt;j++)if(v==vecs[j]||t==tabs[j])return SHAPE;
   tabs[nt]=t;vecs[nt]=v;sizes[nt]=n;offsets[nt]=used;nt++;
   for(U j=0;j<n;j++)S(sc+used+4*j,0);
   U count=0;
   for(U j=0;j<n;j++){
    U raw=L(bucket(v,j));if(!raw)continue;U s=symbol(raw),p=symbase(c,s),len;
    if(!p||!string(L(p+4),&len)||L(p+16)!=pkg)return SHAPE;
    if(pkg==L(c+36)&&(k!=1||L(p+8)!=s||(L(p+20)&72)!=72))return SHAPE;
    U at=hash(L(p+4))&(n-1);for(U z=0;z<n;z++,at=(at+1)&(n-1)){U other=L(sc+used+4*at);if(other){U q=symbase(c,symbol(other));if(equal(L(q+4),L(p+4)))return CONFLICT;}else{S(sc+used+4*at,raw);break;}}
    count++;
   }
   if(L(L(t-1)+3)!=count*4)return SHAPE;used+=n*4;
  }
  /* Refuse the same name in a package's internal and external tables. */
  U a=vecs[nt-2],b=vecs[nt-1];for(U x=0;x<sizes[nt-2];x++)if(L(bucket(a,x)))for(U y=0;y<sizes[nt-1];y++)if(L(bucket(b,y))&&equal(L(symbase(c,symbol(L(bucket(a,x))))+4),L(symbase(c,symbol(L(bucket(b,y))))+4)))return CONFLICT;
 }
 if(!package(c,L(c+36)))return PACKAGE;
 for(U i=0;i<3;i++){U p=symbase(c,L(c+40+4*i));if(!p||L(p+16)!=L(c+36)||L(p+8)!=L(c+40+4*i))return SHAPE;}
 if(L(NILSYM)!=1850||L(77832)!=1850||L(NILSYM+8)!=NIL||L(77840)!=TRUE||L(77824)!=NIL||L(77828)!=NIL)return SHAPE;
 U rebuilt=L(c+20)!=1;
 if(!rebuilt){for(U i=0;i<nt;i++)for(U j=0;j<sizes[i];j++){
  U raw=L(bucket(vecs[i],j));if(!raw)continue;
  U found=0,p=symbase(c,symbol(raw)),at=locate(c,tabs[i],L(p+4),&found);
  if(!at||!found||L(at)!=raw)return HASH;
 }}
 else {for(U i=0;i<nt;i++)for(U j=0;j<sizes[i];j++)S(bucket(vecs[i],j),L(sc+offsets[i]+4*j));}
 S(c+20,1);S(c+24,1);S(result,rebuilt);return 0;
}
/* op 0 FIND-SYMBOL, 1 INTERN, 2 MAKE-SYMBOL, 3 SYMBOL-NAME,
 * 4 SYMBOL-PACKAGE. Result: first, second, count, allocated bytes.
 * Owner admits before use and keeps tables/topology private to this service. */
EXPORT U symbols_run(U c,U op,U a,U b,U unused,U result){
 (void)unused;if(!config(c,result))return OWNER;if(L(c+24)!=1||L(c+20)!=1)return HASH;
 if(op>4)return OP;
 U v=NIL,w=NIL,n=op<2?2:1,bytes=0;
 if(op>=3){U p=symbase(c,a);if(!p)return SHAPE;v=L(p+(op==3?4:16));goto publish;}
 U len;if(!string(a,&len))return STRING;
 if(op<2){if(!package(c,b))return PACKAGE;U error=lookup(c,b,a,&w,&v);if(error)return error;if(w!=NIL||op==0)goto publish;}
 U tablep=op==1?L(b+(b==L(c+36)?2:-2)):0,found,at=0;
 if(op==1){at=locate(c,tablep,a,&found);if(!at)return SPACE;}
 bytes=((4+4*len+7)&~7u)+32;U base=L(c+12),end=L(c+8);if((W)base+bytes>end)return SPACE;
 U str=base+6,sym=base+bytes-32+6,p=sym-6;
 S(base,(len<<8)|191);for(U i=0;i<len;i++)S(base+4+4*i,L(a-2+4*i));if((len&1)==0)S(base+4+4*len,0);
 S(p,1850);S(p+4,str);S(p+8,op==1&&b==L(c+36)?sym:UNBOUND);S(p+12,L(c+68));S(p+16,op==1?b:NIL);S(p+20,op==1&&b==L(c+36)?72:0);S(p+24,NIL);S(p+28,0);
 if(op==1){S(at,rawsym(sym));U counter=L(tablep-1)+3;S(counter,L(counter)+4);}
 S(c+12,base+bytes);v=sym;
publish:S(result,v);S(result+4,w);S(result+8,n);S(result+12,bytes);return 0;
}
