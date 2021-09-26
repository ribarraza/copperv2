
LINKER_SCRIPT = ../common/linker.ld
CC = riscv64-unknown-elf-gcc
CFLAGS = -march=rv32i -mabi=ilp32 -I../common

dhrystone.elf: dhrystone_main.o dhrystone.o syscalls.o crt0.o
	$(CC) $(CFLAGS) -Wl,-T,$(LINKER_SCRIPT),-Bstatic -nostartfiles -ffreestanding $^ -o $@

crt0.o: ../common/crt0.S
	$(CC) $(CFLAGS) -c $^ -o $@

.PHONY: clean
clean:
	rm -fv *.o *.elf