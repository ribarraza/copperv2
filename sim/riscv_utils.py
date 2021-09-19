import subprocess
from pathlib import Path

from cocotb.log import SimLog
from elftools.elf.elffile import ELFFile

from cocotb_utils import get_test_name
from bus import BusReadTransaction
from cocotb_utils import to_bytes

sim_dir = Path(__file__).resolve().parent
linker_script = sim_dir/'tests/linker.ld'

def compile_test(instructions):
    log = SimLog("cocotb.copperv2.compile_test")
    test_s = Path(get_test_name()).with_suffix('.S')
    test_elf = Path(get_test_name()).with_suffix('.elf')
    test_s.write_text('\n'.join(crt0 + instructions) + '\n')
    cmd = f"riscv64-unknown-elf-gcc -march=rv32i -mabi=ilp32 -Wl,-T,{linker_script},-Bstatic -nostartfiles -ffreestanding -g {test_s} -o {test_elf}"
    run_gcc(log, cmd)
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

def run_gcc(log, cmd):
    log.debug(f"gcc cmd: {cmd}")
    r = subprocess.run(cmd,shell=True,encoding='utf-8',capture_output=True)
    if r.returncode != 0:
        log.error(f"gcc stdout: {r.stdout}")
        log.error(f"gcc stderr: {r.stderr}")
        raise ChildProcessError(f"Failed Riscv compilation: {cmd}")
    return r

def compile_riscv_test(asm_path):
    log = SimLog("cocotb.copperv2.compile_riscv_test")
    test_s = asm_path
    linker_script = sim_dir/'tests/linker.ld'
    crt0_s = sim_dir/'tests/crt0.S'
    crt0_obj = Path(crt0_s.name).with_suffix('.o')
    test_obj = Path(test_s.name).with_suffix('.o')
    test_elf = Path(test_s.name).with_suffix('.elf')
    cmd_crt0 = f"riscv64-unknown-elf-gcc -march=rv32i -mabi=ilp32 -I{sim_dir/'tests/isa'} -I{sim_dir/'tests/isa/macros/scalar'} -g -DENTRY_POINT={test_s.stem} -c {crt0_s} -o {crt0_obj}"
    cmd_test = f"riscv64-unknown-elf-gcc -march=rv32i -mabi=ilp32 -I{sim_dir/'tests/isa'} -I{sim_dir/'tests/isa/macros/scalar'} -g -DTEST_NAME={test_s.stem} -c {test_s} -o {test_obj}"
    cmd_link = f"riscv64-unknown-elf-gcc -march=rv32i -mabi=ilp32 -I{sim_dir/'tests/isa'} -I{sim_dir/'tests/isa/macros/scalar'} -Wl,-T,{linker_script},-Bstatic -nostartfiles -ffreestanding -g {crt0_obj} {test_obj} -o {test_elf}" 
    run_gcc(log,cmd_crt0)
    run_gcc(log,cmd_test)
    run_gcc(log,cmd_link)
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

def compile_instructions(instructions):
    instruction_memory = {}
    elf = compile_test(instructions)
    section_start = elf['.text']['addr']
    section_data = elf['.text']['data']
    section_size = len(section_data)
    for addr in range(section_size):
        instruction_memory[section_start+addr] = section_data[addr]
    return instruction_memory

def parse_data_memory(params_data_memory):
    data_memory = {}
    for t in params_data_memory:
        t = BusReadTransaction.from_string(t)
        for i in range(4):
            data_memory[t.addr+i] = to_bytes(t.data)[i]
    return data_memory