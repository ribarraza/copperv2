import logging
import dataclasses
import os
import toml
from pathlib import Path

import cocotb
from cocotb.triggers import with_timeout
from cocotb.log import SimLog
from cocotb.regression import TestFactory

from testbench import Testbench
from cocotb_utils import verilog_string, get_test_name, get_top_module
from riscv_utils import compile_instructions, parse_data_memory, compile_riscv_test

if os.environ.get("VS_DEBUG",False):
    import debugpy
    debugpy.listen(4440)
    print("Info: debugpy waiting for client...")
    debugpy.wait_for_client()

if 'debug_test' in cocotb.plusargs:
    SimLog("cocotb").setLevel(logging.DEBUG)

@cocotb.coroutine
async def unit_test(dut, params):
    """ Copperv unit tests """
    test_name = f"{get_test_name()}_{params.name}"
    dut._log.info(f"Test {test_name} started")

    iverilog_dump = get_top_module("iverilog_dump")
    iverilog_dump.test_name <= verilog_string(test_name)

    instruction_memory = compile_instructions(params.instructions)
    data_memory = parse_data_memory(params.data_memory)
    tb = Testbench(dut, params,
        instruction_memory=instruction_memory,
        data_memory=data_memory)
    tb.bus_bfm.start_clock()
    await tb.bus_bfm.do_reset()
    await with_timeout(tb.finish(), 10000, 'ns')

    dut._log.info(f"Test {test_name} finished")

@cocotb.coroutine
async def riscv_test(dut, asm_path):
    """ compliance tests for RISCV """
    test_name = f"{get_test_name()}_{asm_path.name}"
    dut._log.info(f"Test {test_name} started")

    iverilog_dump = get_top_module("iverilog_dump")
    iverilog_dump.test_name <= verilog_string(test_name)

    instruction_memory, data_memory = compile_riscv_test(asm_path)
    tb = Testbench(dut, asm_path,
        instruction_memory=instruction_memory,
        data_memory=data_memory)
    tb.bus_bfm.start_clock()
    await tb.bus_bfm.do_reset()
    await with_timeout(tb.finish(), 10000, 'ns')

    dut._log.info(f"Test {test_name} finished")

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
sim_dir = Path(__file__).resolve().parent
toml_path = sim_dir/"tests/simple_test.toml"
tests = toml.loads(toml_path.read_text())
tests = [TestParameters(name,**test) for name,test in tests.items()]
utf.add_option('params',tests)
utf.generate_tests()

rvtf = TestFactory(test_function=riscv_test)
rv_asm_paths = list(sim_dir.glob('tests/isa/rv32ui/*.S'))
rv_asm_paths = [rv_asm_paths[0]]
rvtf.add_option('asm_path',rv_asm_paths)
#rvtf.generate_tests()