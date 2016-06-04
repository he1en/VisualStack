#include <stdlib.h>
#include <stdio.h>

int main (int argc, char *argv[]) {
  int i = 0;
  int sum = 0;
  while (sum < 10) {
    sum += i;
    i += 1;
  }
  exit(0);
}
