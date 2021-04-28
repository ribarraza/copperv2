import logging

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.log import SimLog
from cocotb_bus.scoreboard import Scoreboard

from bus import ReadBusMonitor, ReadBusSourceDriver, ReadTransaction
from regfile import RegFileWriteMonitor, RegFileWriteTransaction
from compile_test import compile_test
from utils import verilog_string, get_test_name

class Testbench():
    def __init__(self, tb_wrapper, clock, reset, elf, expected_reg_file):
        self.clock = clock
        self.reset = reset
        self.elf = elf
        self.reset.setimmediatevalue(0)
        self.bus_ir_driver = ReadBusSourceDriver(tb_wrapper, "bus_ir", self.clock)
        self.bus_ir_monitor = ReadBusMonitor(tb_wrapper, "bus_ir", self.clock,
            callback=self.instruction_read_callback, reset = self.reset)
        self.regfile_monitor = RegFileWriteMonitor(tb_wrapper.dut, self.clock)
        self.scoreboard = Scoreboard(tb_wrapper.dut)
        self.expected_reg_file = [RegFileWriteTransaction.from_string(t) for t in expected_reg_file]
        self.scoreboard.add_interface(self.regfile_monitor, self.expected_reg_file)
    async def do_reset(self):
        self.reset <= 0
        await ClockCycles(self.clock,10)
        self.reset <= 1
        await RisingEdge(self.clock)
    def start_clock(self):
        cocotb.fork(Clock(self.clock,10,units='ns').start())
    def instruction_read_callback(self, transaction):
        if transaction.type == "request":
            section_start = self.elf['.text']['addr']
            section_data = self.elf['.text']['data']
            section_size = len(section_data)
            driver_transaction = ReadTransaction(type="deassert_ready")
            if transaction.addr < section_start + section_size:
                assert section_start <= transaction.addr < section_start + section_size, "Reading invalid address"
                addr = transaction.addr - section_start
                driver_transaction = ReadTransaction(
                    data = int.from_bytes(section_data[addr:addr+4],byteorder='little'),
                    addr = transaction.addr,
                )
            self.bus_ir_driver.append(driver_transaction)
    def finish(self):
        return len(self.expected_reg_file) == 0

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
