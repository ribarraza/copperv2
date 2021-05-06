import subprocess
from pathlib import Path

from cocotb.log import SimLog
from elftools.elf.elffile import ELFFile

from cocotb_utils import get_test_name

linker_script_content = """
OUTPUT_ARCH("riscv")
ENTRY(_start)

SECTIONS
{
    . = 0x00000000;
    .text.init : { *(.text.init) }
    . = ALIGN(0x1000);
    _end = .;
}
"""
linker_script = Path('linker.ld')
linker_script.write_text(linker_script_content)

def compile_test(instructions):
    log = SimLog("cocotb.copperv2.compile_test")
    test_s = Path(get_test_name()).with_suffix('.S')
    test_elf = Path(get_test_name()).with_suffix('.elf')
    test_s.write_text('\n'.join(instructions) + '\n')
    cmd = f"riscv64-unknown-elf-gcc -march=rv32i -mabi=ilp32 -Wl,-T,{linker_script},-Bstatic -nostartfiles -ffreestanding -g {test_s} -o {test_elf}"
    log.debug(f"gcc cmd: {cmd}")
    r = subprocess.run(cmd,shell=True,encoding='utf-8',capture_output=True)
    if r.returncode != 0:
        log.error(f"gcc stdout: {r.stdout}")
        log.error(f"gcc stderr: {r.stderr}")
        raise ChildProcessError(f"Failed test compile: {cmd}")
    with test_elf.open('rb') as file:
        elffile = ELFFile(file)
        elf = {}
        for spec in ['.text']:
            section = elffile.get_section_by_name(spec)
            elf[spec] = dict(
                addr = section['sh_addr'],
                data = section.data(),
            )
    log.debug(f"elf: {elf}")
    return elf

crt0 = [
    ".global _start",
    "_start:",
]

reg_abi_map = {
    "zero":0,
    "ra":1,
    "sp":2,
    "gp":3,
    "tp":4,
    "t0":5,
    "t1":6,
    "t2":7,
    "s0":8,
    "s1":9,
    "a0":10,
    "a1":11,
    "a2":12,
    "a3":13,
    "a4":14,
    "a5":15,
    "a6":16,
    "a7":17,
    "s2":18,
    "s3":19,
    "s4":20,
    "s5":21,
    "s6":22,
    "s7":23,
    "s8":24,
    "s9":25,
    "s10":26,
    "s11":27,
    "t3":28,
    "t4":29,
    "t5":30,
    "t6":31,
}
