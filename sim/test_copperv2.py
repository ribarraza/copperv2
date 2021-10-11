import logging
import dataclasses
import os
import toml
from pathlib import Path

import cocotb
from cocotb.triggers import with_timeout, Timer
from cocotb.log import SimLog
from cocotb.regression import TestFactory

from testbench import Testbench
from cocotb_utils import verilog_string, get_test_name, get_top_module, run
from riscv_utils import compile_instructions, parse_data_memory, compile_riscv_test, process_elf

if os.environ.get("VS_DEBUG",False):
    import debugpy
    debugpy.listen(4440)
    print("Info: debugpy waiting for client...")
    debugpy.wait_for_client()

if 'debug_test' in cocotb.plusargs:
    SimLog("cocotb").setLevel(logging.DEBUG)

sim_dir = Path(__file__).resolve().parent

T_ADDR = 0x80000000
O_ADDR = 0x80000004
TC_ADDR = 0x80000008
T_PASS = 0x01000001
T_FAIL = 0x02000001

@cocotb.coroutine
async def unit_test(dut, params):
    """ Copperv unit tests """
    test_name = f"{get_test_name()}_{params.name}"
    dut._log.info(f"Test {test_name} started")

    iverilog_dump = get_top_module("iverilog_dump")
    iverilog_dump.test_name <= verilog_string(test_name)

    instruction_memory = compile_instructions(params.instructions)
    data_memory = parse_data_memory(params.data_memory)
    tb = Testbench(dut,
        test_name,
        expected_data_read=params.expected_data_read,
        expected_data_write=params.expected_data_write,
        expected_regfile_read=params.expected_regfile_read,
        expected_regfile_write=params.expected_regfile_write,
        instruction_memory=instruction_memory,
        data_memory=data_memory)
    tb.bus_bfm.start_clock()
    await tb.bus_bfm.do_reset()
    await with_timeout(tb.finish(), 10000, 'ns')

    dut._log.info(f"Test {test_name} finished")

@cocotb.coroutine
async def riscv_test(dut, asm_path):
    """ RISCV compliance tests """
    test_name = f"{get_test_name()}_{asm_path.stem}"
    dut._log.info(f"Test {test_name} started")

    iverilog_dump = get_top_module("iverilog_dump")
    iverilog_dump.test_name <= verilog_string(test_name)

    instruction_memory, data_memory = compile_riscv_test(asm_path)
    tb = Testbench(dut,
        test_name,
        instruction_memory=instruction_memory,
        data_memory=data_memory,
        enable_self_checking=False,
        pass_fail_address = T_ADDR,
        pass_fail_values = {T_FAIL:False,T_PASS:True})

    tb.bus_bfm.start_clock()
    await tb.bus_bfm.do_reset()
    await Timer(1000, 'ms')
    raise cocotb.result.SimTimeoutError()

@dataclasses.dataclass
class TestParameters:
    name: str
    instructions: list = dataclasses.field(default_factory=list)
    expected_regfile_read: list = dataclasses.field(default_factory=list)
    expected_regfile_write: list = dataclasses.field(default_factory=list)
    expected_data_read: list = dataclasses.field(default_factory=list)
    expected_data_write: list = dataclasses.field(default_factory=list)
    data_memory: list = dataclasses.field(default_factory=list)
    def __repr__(self):
        p = '\n'.join([f"{k} = {repr(v)}" for k,v in dataclasses.asdict(self).items()])
        return '\n' + p

utf = TestFactory(test_function=unit_test)
toml_path = sim_dir/"tests/simple_test.toml"
tests = toml.loads(toml_path.read_text())
tests = [TestParameters(name,**test) for name,test in tests.items()]
utf.add_option('params',tests)
utf.generate_tests()

if 'riscv_test' in cocotb.plusargs:
    rvtf = TestFactory(test_function=riscv_test)
    rv_asm_paths = list(sim_dir.glob('tests/isa/rv32ui/*.S'))
    #rv_asm_paths = [rv_asm_paths[0]]
    rvtf.add_option('asm_path',rv_asm_paths)
    rvtf.generate_tests()

@cocotb.test(skip=True)
async def run_elf(dut):
    """ Run compiled program in ELF format """

    elf_path = Path(os.environ['COPPERV_ELF_PATH'])
    if not str(elf_path).startswith('/'):
        elf_path = Path(os.environ['COPPERV_ELF_PATH_CWD'])/str(elf_path)

    test_name = f"{get_test_name()}_{elf_path.stem}"
    dut._log.info(f"Test {test_name} started")

    iverilog_dump = get_top_module("iverilog_dump")
    iverilog_dump.test_name <= verilog_string(test_name)

    instruction_memory, data_memory = process_elf(elf_path)
    tb = Testbench(dut,
        test_name,
        instruction_memory=instruction_memory,
        data_memory=data_memory,
        enable_self_checking=False,
        pass_fail_address = T_ADDR,
        pass_fail_values = {T_FAIL:False,T_PASS:True},
        output_address = O_ADDR,
        timer_address = TC_ADDR)

    tb.bus_bfm.start_clock()
    await tb.bus_bfm.do_reset()
    await Timer(1000, 'ms')
    raise cocotb.result.SimTimeoutError()

#elftf = TestFactory(test_function=run_elf)
#run('make',cwd = sim_dir/'tests/dhrystone')
#elf_paths = [sim_dir/'tests/dhrystone/dhrystone.elf']
#elftf.add_option('elf_path',elf_paths)
#elftf.generate_tests()