/* Independent x86 witness of the new single-float exactness/tininess path. */
#include <stdint.h>
#include <stdio.h>
int main(void){unsigned op,a,b;while(scanf("%u %x %x",&op,&a,&b)==3){
 union {uint32_t u;float f;} x={a},y={b};unsigned control=0x1f80,flags;
 __asm__ volatile("ldmxcsr %0"::"m"(control));
 switch(op){case 0:__asm__ volatile("addss %1,%0":"+x"(x.f):"x"(y.f));break;
 case 1:__asm__ volatile("subss %1,%0":"+x"(x.f):"x"(y.f));break;
 case 2:__asm__ volatile("mulss %1,%0":"+x"(x.f):"x"(y.f));break;
 case 3:__asm__ volatile("divss %1,%0":"+x"(x.f):"x"(y.f));break;default:return 2;}
 __asm__ volatile("stmxcsr %0":"=m"(flags));
 unsigned mapped=(flags&1?1:0)|(flags&4?2:0)|(flags&8?4:0)|(flags&16?8:0)|(flags&32?16:0);
 printf("%08x %u\n",x.u,mapped);
 }return 0;}
