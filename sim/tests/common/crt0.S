#include "riscv_test.h"

.section .init, "ax"
.global _start
_start:
    .cfi_startproc
    .cfi_undefined ra
    .option push
    .option norelax
    la gp, __global_pointer$
    .option pop
    la sp, __stack_top
    add s0, sp, zero
#ifdef ENTRY_POINT
    .global ENTRY_POINT;
    jal zero, ENTRY_POINT
#endif
    .cfi_endproc
    .end