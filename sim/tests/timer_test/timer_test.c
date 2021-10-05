#include <stdio.h>
#include "riscv_test.h"

int volatile * const TEST_RESULT = T_ADDR;
int volatile * const SIM_OUT = O_ADDR;
int volatile * const TIMER_COUNTER = TC_ADDR;

void _putc(char c){
    *SIM_OUT = c;
}
void print(char* c){
    while(*c) _putc(*(c++));
}

char * get_timer_value(void) {
    int num = *TIMER_COUNTER;
    static char snum[100];
    itoa(num, snum, 10);
    return snum;
}

int main(){
    print("timer value 1: ");
    print(get_timer_value());
    print("\n");
    print("timer value 2: ");
    print(get_timer_value());
    print("\n");
    *TEST_RESULT = T_PASS;
}
