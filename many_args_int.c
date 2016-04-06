#include <stdlib.h>
#include <stdio.h>

long utilfunc(long a, long b, long c) {
  long xx = a + 2;
  long yy = b + 3;
  long zz = c + 4;
  long sum = xx + yy + zz;

  return xx * yy * zz + sum;
}

long myfunc(long a, long b, long c, long d, long e, long f, long g,
            long h) {
  long xx = a * b * c * d * e * f * g * h;
  long yy = a + b + c + d + e + f + g + h;
  long zz = utilfunc(xx, yy, xx % yy);
  return zz + 20;
}

int main (char *argv[], int argc) {
  myfunc(1, 1, 1, 1, 1, 1, 1, 1);
   exit(0);
}
