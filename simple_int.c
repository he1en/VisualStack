#include <stdlib.h>
#include <stdio.h>

int P(int x, int y) {
  int z = x * x;
  int a = x + y;
  return z + a;
}

int main(void *argv[]) {
  int x = 1;
  int y = 2;
  printf("~~%d~~\n", P(x, y));
  exit(0);
}
