/* Same private-memory transaction as the arithmetic service. libm is compiled
 * into this module; no host function or Lisp allocation is called here.
 * This profile admits finite, correctly typed inputs with nearest rounding.
 * Inexact/underflow trap modes are refused until their exact flags are proved.
 */
#define DECLARE(name) extern double name(double); extern float name##f(float);
DECLARE(sin) DECLARE(cos) DECLARE(acos) DECLARE(asin) DECLARE(cosh)
DECLARE(asinh) DECLARE(acosh) DECLARE(atanh) DECLARE(sqrt)
DECLARE(log) DECLARE(tan) DECLARE(atan) DECLARE(exp) DECLARE(sinh) DECLARE(tanh)
extern double pow(double,double),atan2(double,double);
extern float powf(float,float),atan2f(float,float);
static U transcend(U op,U av,U bv,U in,U end,U out,U limit,U result,U mask,U safe){
 U i=(op-12)/2,width=(op&1)?32:64,binary=i==0||i==9;
 if(safe&&(mask&24))return 5;
 Number a,b;U err=input(&a,av,in,end);if(err)return err;
 if(a.kind!=width||nan(a.f)||inf(a.f))return 2;
 double x=a.f,y=0,r=0;
 if(binary){err=input(&b,bv,in,end);if(err)return err;if(b.kind!=width||nan(b.f)||inf(b.f))return 2;y=b.f;}
#define UNARY(k,name) case k:r=width==32?name##f((float)x):name(x);break;
 switch(i){
 case 0:r=width==32?powf((float)x,(float)y):pow(x,y);break;
 UNARY(1,sin) UNARY(2,cos) UNARY(3,acos) UNARY(4,asin) UNARY(5,cosh)
 UNARY(6,log) UNARY(7,tan) UNARY(8,atan)
 case 9:r=width==32?atan2f((float)x,(float)y):atan2(x,y);break;
 UNARY(10,exp) UNARY(11,sinh) UNARY(12,tanh)
 UNARY(13,asinh) UNARY(14,acosh) UNARY(15,atanh) UNARY(16,sqrt)
 default:return 5;
 }
#undef UNARY
 U f=nan(r)?1:inf(r)?((i==6&&x==0)||(i==15&&(x==1||x==-1))||(i==0&&x==0&&y<0)?2:4):0;
 U chosen=enabled(f,mask,safe),size=chosen?0:width==32?8:16;
 if((W)out+size>limit)return 3;
 if(size){if(width==32){F v={.f=(float)r};GET(out)=271;GET(out+4)=v.u;}
 else{D v={.f=r};GET(out)=791;GET(out+4)=0;GET(out+8)=(U)v.u;GET(out+12)=(U)(v.u>>32);}}
 GET(result)=chosen?NIL:out+6;GET(result+4)=safe?f:0;GET(result+8)=chosen;GET(result+12)=3;
 GET(result+16)=out+size;GET(result+20)=width;GET(result+24)=0;GET(result+28)=0;return 0;
}
