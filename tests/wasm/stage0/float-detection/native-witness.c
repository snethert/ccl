/* Native x86-64 SSE witness for the floating-point oracle on the macOS reference
   machine. For each stdin line "op a b" (hexadecimal f64 bit patterns; b ignored
   for sqrt) it resets MXCSR to its default 0x1F80 (flags clear, every exception
   masked, round to nearest, DAZ and FTZ off), performs one scalar double
   instruction through volatile operands, and prints "op a b result flags" with
   the six MXCSR exception flags (IE DE ZE OE UE PE, bits 0..5). Underflow is
   detected after rounding, as the hardware defines it. */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <emmintrin.h>
static double from_bits(unsigned long long u) { double d; memcpy(&d, &u, 8); return d; }
static unsigned long long to_bits(double d) { unsigned long long u; memcpy(&u, &d, 8); return u; }
int main(void) {
  char op[8]; unsigned long long a, b; volatile double x, y, r;
  while (scanf("%7s %llx %llx", op, &a, &b) == 3) {
    x = from_bits(a); y = from_bits(b);
    _mm_setcsr(0x1F80u);
    if (!strcmp(op, "add")) r = x + y;
    else if (!strcmp(op, "sub")) r = x - y;
    else if (!strcmp(op, "mul")) r = x * y;
    else if (!strcmp(op, "div")) r = x / y;
    else if (!strcmp(op, "sqrt")) r = _mm_cvtsd_f64(_mm_sqrt_sd(_mm_set_sd(x), _mm_set_sd(x)));
    else return 2;
    unsigned csr = _mm_getcsr();
    printf("%s %016llx %016llx %016llx %02x\n", op, a, b, to_bits(r), csr & 0x3Fu);
  }
  return 0;
}
