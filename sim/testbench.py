import cocotb
from cocotb.log import SimLog
from cocotb_bus.scoreboard import Scoreboard
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

from bus import ReadBusMonitor, ReadBusSourceDriver, BusReadTransaction, BusWriteTransaction
from regfile import RegFileReadMonitor, RegFileWriteMonitor, RegFileReadTransaction, RegFileWriteTransaction

class TBConfig:
    def __init__(self, dut):
        self.dut = dut
        self.clock = dut.clk
        self.reset = dut.rst
        self.copperv1_bind()
    def copperv1_bind(self):
        self.ir_bind = dict(
            clock = self.clock,
            addr_valid = self.dut.ir_addr_valid,
            addr_ready = self.dut.ir_addr_ready,
            addr = self.dut.ir_addr,
            data_valid = self.dut.ir_data_valid,
            data_ready = self.dut.ir_data_ready,
            data = self.dut.ir_data,
        )
        self.dr_bind = dict(
            clock = self.clock,
            addr_valid = self.dut.dr_addr_valid,
            addr_ready = self.dut.dr_addr_ready,
            addr = self.dut.dr_addr,
            data_valid = self.dut.dr_data_valid,
            data_ready = self.dut.dr_data_ready,
            data = self.dut.dr_data,
        )
        self.regfile_write_bind = dict(
            clock = self.clock,
            rd_en = self.dut.regfile.rd_en,
            rd_addr = self.dut.regfile.rd,
            rd_data = self.dut.regfile.rd_din,
        )
        self.regfile_read_bind = dict(
            clock = self.clock,
            rs1_en = self.dut.regfile.rs1_en,
            rs1_addr = self.dut.regfile.rs1,
            rs1_data = self.dut.regfile.rs1_dout,
            rs2_en = self.dut.regfile.rs2_en,
            rs2_addr = self.dut.regfile.rs2,
            rs2_data = self.dut.regfile.rs2_dout,
        )

class Testbench():
    def __init__(self, dut, elf, params):
        self.log = SimLog(f"cocotb.Testbench")
        config = TBConfig(dut)
        self.clock = config.clock
        self.reset = config.reset
        self.reset.setimmediatevalue(0)
        ## Instruction read
        self.elf = elf
        self.bus_ir_driver = ReadBusSourceDriver("bus_ir", config.ir_bind)
        self.bus_ir_monitor = ReadBusMonitor("bus_ir", config.ir_bind, reset = self.reset)
        self.bus_ir_req_monitor = ReadBusMonitor("bus_ir_req", config.ir_bind, request_only=True,
            callback=self.instruction_read_callback, reset = self.reset)
        ## Data read
        self.data_memory = {}
        for t in params.data_memory:
            t = BusReadTransaction.from_string(t)
            self.data_memory[t.addr] = t.data
        self.bus_dr_driver = ReadBusSourceDriver("bus_dr", config.dr_bind)
        self.bus_dr_monitor = ReadBusMonitor("bus_dr", config.dr_bind, reset = self.reset)
        self.bus_dr_req_monitor = ReadBusMonitor("bus_dr_req", config.dr_bind, request_only=True,
            callback=self.data_read_callback, reset = self.reset)
        ## Regfile
        self.regfile_write_monitor = RegFileWriteMonitor("regfile_write", config.regfile_write_bind)
        self.regfile_read_monitor = RegFileReadMonitor("regfile_read", config.regfile_read_bind)
        ## Self checking
        self.scoreboard = Scoreboard(dut)
        self.expected_regfile_read = [RegFileReadTransaction.from_string(t) for t in params.expected_regfile_read]
        self.expected_regfile_write = [RegFileWriteTransaction.from_string(t) for t in params.expected_regfile_write]
        self.expected_data_read = [BusReadTransaction.from_string(t) for t in params.expected_data_read]
        self.expected_data_write = [BusWriteTransaction.from_string(t) for t in params.expected_data_write]
        self.scoreboard.add_interface(self.regfile_write_monitor, self.expected_regfile_write)
        self.scoreboard.add_interface(self.regfile_read_monitor, self.expected_regfile_read)
        self.scoreboard.add_interface(self.bus_dr_monitor, self.expected_data_read)
    async def do_reset(self):
        self.reset <= 0
        await ClockCycles(self.clock,10)
        self.reset <= 1
        await RisingEdge(self.clock)
    def start_clock(self):
        cocotb.fork(Clock(self.clock,10,units='ns').start())
    def data_read_callback(self, transaction):
        addr = transaction.addr
        self.log.debug(f"Data memory: {self.data_memory}")
        assert addr in self.data_memory, f"Invalid data address: 0x{addr:X}"
        driver_transaction = BusReadTransaction(
            data = self.data_memory[addr],
            addr = addr,
        )
        self.bus_dr_driver.append(driver_transaction)
    def instruction_read_callback(self, transaction):
        section_start = self.elf['.text']['addr']
        section_data = self.elf['.text']['data']
        section_size = len(section_data)
        driver_transaction = "deassert_ready"
        if transaction.addr < section_start + section_size:
            assert section_start <= transaction.addr < section_start + section_size, "Reading invalid address"
            addr = transaction.addr - section_start
            driver_transaction = BusReadTransaction(
                data = int.from_bytes(section_data[addr:addr+4],byteorder='little'),
                addr = transaction.addr,
            )
        self.bus_ir_driver.append(driver_transaction)
    @cocotb.coroutine
    async def finish(self):
        last_pending = ""
        while True:
            finish = True
            for expected in self.scoreboard.expected.values():
                if len(expected) != 0:
                    finish = False
            if finish:
                break
            pending = repr({k.name:v for k,v in self.scoreboard.expected.items()})
            if last_pending != pending:
                self.log.debug(f"Pending transactions: {pending}")
            last_pending = pending
            await RisingEdge(self.clock)
        await ClockCycles(self.clock,20)
