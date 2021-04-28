import logging

import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.log import SimLog

from testbench import Testbench
from riscv_utils import compile_test
from cocotb_utils import verilog_string, get_test_name


@cocotb.test()
async def basic_test(tb_wrapper):
    tb_wrapper.test_name <= verilog_string(get_test_name())
    SimLog("cocotb").setLevel(logging.DEBUG)
    clock = tb_wrapper.clock
    reset = tb_wrapper.reset

    instructions = [
        ".global _start",
        "_start:",
        "lui t0, 1",
    ]
    expected_reg_file = [
        "t0 0x1000",
    ]
    #expected_data_mem = []
    #expected_alu = []

    elf = compile_test(instructions)
    tb = Testbench(tb_wrapper, clock, reset, elf, expected_reg_file)

    tb.start_clock()
    await tb.do_reset()

    while not tb.finish():
        await RisingEdge(clock)
    await ClockCycles(clock,20)
