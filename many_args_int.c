#include <stdlib.h>
#include <stdio.h>

long utilfunc(long j, long k, long l) {
  long m = j + 2;
  long n = k + 3;
  long o = l + 4;
  long sum = m + n + o;

  return m * n * o + sum;
}

long myfunc(long a, long b, long c, long d, long e, long f, long g,
            long h) {
  long x = a * b * c * d * e * f * g * h;
  long y = a + b + c + d + e + f + g + h;
  long z = utilfunc(x, y, x % y);
  return z + 20;
}

int main (int argc, char *argv[]) {
  myfunc(1, 2, 3, 4, 5, 6, 7, 8);
  exit(0);
}
