/* File: stack.c
 * -------------
 * Program used for exploring runtime stack in lab.
 */
#include <ctype.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>


struct coord {
    int x, y;
    char *name;
};


/* Functions: slinky, dinky
 * ------------------------
 * Compare the disassembly for slinky and dinky to see the difference in
 * passing a struct itself versus passing a struct pointer. The struct
 * doesn't fit in a register, so where does it go?
 */

int slinky(struct coord *cptr, int n)
{
    return cptr->y + n;
}

int dinky(struct coord c, int n)
{
    return c.y + n;
}   


/* Function: winky
 * ---------------
 * Declares two structs as local variables. The struct is too big to
 * fit in a register. One of the structs ends up stored on the stack, the
 * other is not. Look at disassembly to see what is happening.  Why is the
 * cal struct treated differently than stanford? Look carefully at
 * how the call to dinky is made. You probably haven't seen a movabs 
 * instruction before. Can you figure out from the context what this 
 * instruction does?
 */
int winky(int *ptr1, int *ptr2)
{
    struct coord stanford = {.x = 0x107, .y = 0x100, .name = "Stanford"};
    struct coord cal = {.x = 0x55, .y = 0x1234, .name = "Cal"};

    int result = dinky(stanford, 5);
    result += slinky(&stanford, 7);
    result += dinky(cal, 9);
    return result;
}

/* Function: binky
 * ---------------
 * There are registers designated for the first six parameters, but what happens
 * when a function takes more.  Disassemble binky to find out!
 * Given that you cannot take address of register, what is happening when
 * passing &param to winky?
 */
int binky(int one, int two, int three, int four, int five, int six, int seven, int eight)
{
    printf("binky parameters one and eight have values %d and %d\n", one, eight);

    // pass parameters two and seven by reference,
    // look at disassembly to see how translated
    return winky(&two, &seven);
}


int main(int argc, char *argv[])
{
    printf("This program demonstrates various behaviors of the runtime stack.\n");

    printf("\nThe stack frame for main is located at address %p\n", &argc - 2);
    binky(1, 2, 3, 4, 5, 6, 7, 8);
    return 0;
}

