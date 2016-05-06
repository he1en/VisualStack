#include <stdlib.h>
#include <stdio.h>

long utilfunc(long a, long b, long c) {
  long j = a + 2;
  long k = b + 3;
  long l = c + 4;
  long sum = j + k + l;

  return j * k * l + sum;
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
