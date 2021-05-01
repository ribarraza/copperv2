import logging
import dataclasses

import cocotb
from cocotb.triggers import with_timeout
from cocotb.log import SimLog
from cocotb.regression import TestFactory
from cocotb.result import TestSuccess, TestComplete

from testbench import Testbench
from riscv_utils import compile_test, crt0
from cocotb_utils import verilog_string, get_test_name, get_top_module

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
    await with_timeout(tb.finish(), 10000, 'ns')
    #await tb.finish()

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

tf = TestFactory(test_function=basic_test)
tf.add_option('params', [
    TestParameters(
        name = "lui1",
        instructions=["lui t0, 0x123"],
        expected_regfile_write=["t0 0x123000"],
    ),
    TestParameters(
        name = "addi1",
        instructions=["addi t0, zero, 0x123"],
        expected_regfile_write=["t0 0x123"],
    ),
    TestParameters(
        name = "add1",
        instructions=[
            "addi t0, zero, 12",
            "addi t1, zero, 34",
            "add t2, t0, t1",
        ],
        expected_regfile_write=[
            "t0 12",
            "t1 34",
            "t2 46",
        ],
        expected_regfile_read=[
            "t0 12",
            "t1 34",
        ],
    ),
    TestParameters(
        name = "lw1",
        instructions=[
            "addi t0, zero, 11",
            "lw t1, 21(t0)",
        ],
        expected_regfile_write=[
            "t0 11",
            "t1 0x123",
        ],
        expected_data_read=["32 0x123"],
        data_memory=["32 0x123"]
    ),
    TestParameters(
        name = "sw1",
        instructions=[
            "addi t0, zero, 9",
            "addi t1, zero, 0x321",
            "sw t1, 3(t0)",
        ],
        expected_regfile_write=[
            "t0 9",
            "t1 0x321",
        ],
        expected_regfile_read=[
            "t1 0x321",
        ],
        expected_data_write=[
            "12 0x321 0b1111 1",
        ]
    ),
])
tf.generate_tests()
