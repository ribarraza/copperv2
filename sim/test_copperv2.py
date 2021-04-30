import logging
import dataclasses

import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.log import SimLog
from cocotb.regression import TestFactory
from cocotb.result import TestSuccess, TestComplete

from testbench import Testbench
from riscv_utils import compile_test, crt0
from cocotb_utils import verilog_string, get_test_name, get_top_module

@dataclasses.dataclass
class TestParameters:
    name: str
    instructions: list = dataclasses.field(default_factory=list)
    expected_regfile: list = dataclasses.field(default_factory=list)
    expected_data_read: list = dataclasses.field(default_factory=list)
    data_memory: list = dataclasses.field(default_factory=list)
    def __repr__(self):
        p = '\n'.join([f"{k} = {repr(v)}" for k,v in dataclasses.asdict(self).items()])
        return '\n' + p

@cocotb.coroutine
async def basic_test(dut, params):
    """ Copperv2 base test """
    test_name = f"{get_test_name()}_{params.name}"
    dut._log.info(f"Test {test_name} started")

    iverilog_dump = get_top_module("iverilog_dump")
    iverilog_dump.test_name <= verilog_string(test_name)
    if 'debug_test' in cocotb.plusargs:
        SimLog("cocotb").setLevel(logging.DEBUG)

    elf = compile_test(crt0 + params.instructions)
    tb = Testbench(dut, elf, params)

    tb.start_clock()
    await tb.do_reset()

    while not tb.finish():
        await RisingEdge(tb.clock)
    await ClockCycles(tb.clock,20)

    dut._log.info(f"Test {test_name} finished")

tf = TestFactory(test_function=basic_test)
tf.add_option('params', [
    TestParameters(
        name = "lui1",
        instructions=["lui t0, 0x123"],
        expected_regfile=["t0 0x123000"],
    ),
    TestParameters(
        name = "addi1",
        instructions=["addi t0, zero, 0x123"],
        expected_regfile=["t0 0x123"],
    ),
    TestParameters(
        name = "add1",
        instructions=[
            "add t0, zero, 12",
            "add t1, zero, 34",
            "add t2, t0, t1",
        ],
        expected_regfile=[
            "t0 12",
            "t1 34",
            "t2 46",
        ],
    ),
    TestParameters(
        name = "lw1",
        instructions=[
            "addi t0, zero, 11",
            "lw t1, 21(t0)",
        ],
        expected_regfile=[
            "t0 11",
            "t1 0x123",
        ],
        expected_data_read=["32 0x123"],
        data_memory=["32 0x123"]
    ),
])
tf.generate_tests()
