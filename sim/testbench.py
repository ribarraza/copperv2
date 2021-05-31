import cocotb
from cocotb.log import SimLog
from cocotb_bus.scoreboard import Scoreboard
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

from bus import ReadBusMonitor, ReadBusSourceDriver, BusReadTransaction, BusWriteTransaction, WriteBusSourceDriver, WriteBusMonitor
from regfile import RegFileReadMonitor, RegFileWriteMonitor, RegFileReadTransaction, RegFileWriteTransaction
from riscv_utils import compile_test, crt0
from cocotb_utils import from_array, to_bytes

class TBConfig:
    def __init__(self, dut):
        self.dut = dut
        if cocotb.plusargs.get('dut_copperv1',False):
            self.copperv_bind(self.dut,self.dut)
        else:
            self.copperv_bind(self.dut,self.dut.core)
    def copperv_bind(self,interface,core):
        self.clock = interface.clk
        self.reset = interface.rst
        self.ir_bind = dict(
            clock = self.clock,
            addr_valid = interface.ir_addr_valid,
            addr_ready = interface.ir_addr_ready,
            addr = interface.ir_addr,
            data_valid = interface.ir_data_valid,
            data_ready = interface.ir_data_ready,
            data = interface.ir_data,
            reset = self.reset,
        )
        self.dr_bind = dict(
            clock = self.clock,
            addr_valid = interface.dr_addr_valid,
            addr_ready = interface.dr_addr_ready,
            addr = interface.dr_addr,
            data_valid = interface.dr_data_valid,
            data_ready = interface.dr_data_ready,
            data = interface.dr_data,
            reset = self.reset,
        )
        self.dw_bind = dict(
            clock = self.clock,
            req_ready = interface.dw_data_addr_ready,
            req_valid = interface.dw_data_addr_valid,
            req_data = interface.dw_data,
            req_addr = interface.dw_addr,
            req_strobe = interface.dw_strobe,
            resp_ready = interface.dw_resp_ready,
            resp_valid = interface.dw_resp_valid,
            resp = interface.dw_resp,
            reset = self.reset,
        )
        self.regfile_write_bind = dict(
            clock = self.clock,
            rd_en = core.regfile.rd_en,
            rd_addr = core.regfile.rd,
            rd_data = core.regfile.rd_din,
            reset = self.reset,
        )
        self.regfile_read_bind = dict(
            clock = self.clock,
            rs1_en = core.regfile.rs1_en,
            rs1_addr = core.regfile.rs1,
            rs1_data = core.regfile.rs1_dout,
            rs2_en = core.regfile.rs2_en,
            rs2_addr = core.regfile.rs2,
            rs2_data = core.regfile.rs2_dout,
            reset = self.reset,
        )

class Testbench():
    def __init__(self, dut, params):
        self.log = SimLog("cocotb.Testbench")
        config = TBConfig(dut)
        self.clock = config.clock
        self.reset = config.reset
        self.reset.setimmediatevalue(0)
        self.data_memory = self.parse_data_memory(params.data_memory)
        self.log.debug(f"Data memory: {self.data_memory}")
        self.instruction_memory = self.compile_instructions(params.instructions)
        self.log.debug(f"Instruction memory: {self.instruction_memory}")
        ## Instruction read
        self.bus_ir_driver = ReadBusSourceDriver("bus_ir",**config.ir_bind)
        self.bus_ir_monitor = ReadBusMonitor("bus_ir",**config.ir_bind)
        self.bus_ir_req_monitor = ReadBusMonitor("bus_ir_req",**config.ir_bind,request_only=True,
            callback=self.instruction_read_callback)
        ## Data read
        self.bus_dr_driver = ReadBusSourceDriver("bus_dr",**config.dr_bind)
        self.bus_dr_monitor = ReadBusMonitor("bus_dr",**config.dr_bind)
        self.bus_dr_req_monitor = ReadBusMonitor("bus_dr_req",**config.dr_bind,request_only=True,
            callback=self.data_read_callback)
        ## Data write
        self.bus_dw_driver = WriteBusSourceDriver("bus_dw",**config.dw_bind)
        self.bus_dw_monitor = WriteBusMonitor("bus_dw",**config.dw_bind)
        self.bus_dw_req_monitor = WriteBusMonitor("bus_dw_req",**config.dw_bind,request_only=True,
            callback=self.data_write_callback)
        ## Regfile
        self.regfile_write_monitor = RegFileWriteMonitor("regfile_write",**config.regfile_write_bind)
        self.regfile_read_monitor = RegFileReadMonitor("regfile_read",**config.regfile_read_bind)
        ## Self checking
        self.scoreboard = Scoreboard(dut)
        self.expected_regfile_read = [RegFileReadTransaction.from_string(t) for t in params.expected_regfile_read]
        self.expected_regfile_write = [RegFileWriteTransaction.from_string(t) for t in params.expected_regfile_write]
        self.expected_data_read = [BusReadTransaction.from_string(t) for t in params.expected_data_read]
        self.expected_data_write = [BusWriteTransaction.from_string(t) for t in params.expected_data_write]
        self.scoreboard.add_interface(self.regfile_write_monitor, self.expected_regfile_write)
        self.scoreboard.add_interface(self.regfile_read_monitor, self.expected_regfile_read)
        self.scoreboard.add_interface(self.bus_dr_monitor, self.expected_data_read)
        self.scoreboard.add_interface(self.bus_dw_monitor, self.expected_data_write)
    @staticmethod
    def parse_data_memory(params_data_memory):
        data_memory = {}
        for t in params_data_memory:
            t = BusReadTransaction.from_string(t)
            for i in range(4):
                data_memory[t.addr+i] =  to_bytes(t.data)[i]
        return data_memory
    @staticmethod
    def compile_instructions(instructions):
        instruction_memory = {}
        elf = compile_test(crt0 + instructions)
        section_start = elf['.text']['addr']
        section_data = elf['.text']['data']
        section_size = len(section_data)
        for addr in range(section_size):
            instruction_memory[section_start+addr] = section_data[addr]
        return instruction_memory
    def data_write_callback(self,transaction):
        mask = f"{transaction.strobe:04b}"
        for i in range(4):
            if mask[i]:
                self.data_memory[transaction.addr+i] = to_bytes(transaction.data)[i]
        self.log.debug(f"Write data memory: {self.data_memory}")
        driver_transaction = BusWriteTransaction(
            data = transaction.data,
            addr = transaction.addr,
            strobe = transaction.strobe,
            response = 1,
        )
        self.bus_dw_driver.append(driver_transaction)
    def data_read_callback(self,transaction):
        driver_transaction = BusReadTransaction(
            data = from_array(self.data_memory,transaction.addr),
            addr = transaction.addr,
        )
        self.bus_dr_driver.append(driver_transaction)
    def instruction_read_callback(self, transaction):
        driver_transaction = "deassert_ready"
        if transaction.addr < max(self.instruction_memory.keys()):
            driver_transaction = BusReadTransaction(
                data = from_array(self.instruction_memory,transaction.addr),
                addr = transaction.addr,
            )
        self.bus_ir_driver.append(driver_transaction)
    def start_clock(self):
        cocotb.fork(Clock(self.clock,10,units='ns').start())
    async def do_reset(self):
        self.reset <= 0
        await ClockCycles(self.clock,10)
        self.reset <= 1
        await RisingEdge(self.clock)
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
