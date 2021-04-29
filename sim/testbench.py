import cocotb
from cocotb_bus.scoreboard import Scoreboard
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

from bus import ReadBusMonitor, ReadBusSourceDriver, ReadTransaction
from regfile import RegFileWriteMonitor, RegFileWriteTransaction

class Testbench():
    def __init__(self, dut, elf, expected_reg_file):
        self.clock = dut.clk
        self.reset = dut.rst
        ir_bind = dict(
            clock = self.clock,
            addr_valid = dut.ir_addr_valid,
            addr_ready = dut.ir_addr_ready,
            addr = dut.ir_addr,
            data_valid = dut.ir_data_valid,
            data_ready = dut.ir_data_ready,
            data = dut.ir_data,
        )
        self.elf = elf
        self.reset.setimmediatevalue(0)
        self.bus_ir_driver = ReadBusSourceDriver("bus_ir", ir_bind)
        self.bus_ir_monitor = ReadBusMonitor("bus_ir", ir_bind,
            callback=self.instruction_read_callback, reset = self.reset)
        self.regfile_monitor = RegFileWriteMonitor(dut, self.clock)
        self.scoreboard = Scoreboard(dut)
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
