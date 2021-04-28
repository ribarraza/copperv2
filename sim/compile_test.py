import subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from utils import get_test_name

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

def compile_test(instructions,log):
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
