import cocotb
from cocotb.log import SimLog
from cocotb_bus.scoreboard import Scoreboard
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

from bus import ReadBusMonitor, ReadBusSourceDriver, BusReadTransaction, BusWriteTransaction, WriteBusSourceDriver, WriteBusMonitor
from regfile import RegFileReadMonitor, RegFileWriteMonitor, RegFileReadTransaction, RegFileWriteTransaction
from riscv_utils import compile_test, crt0

class TBConfig:
    def __init__(self, dut):
        self.dut = dut
        if cocotb.plusargs.get('dut_copperv1',False):
            self.copperv1_bind()
        else:
            self.copperv2_bind()
    def copperv1_bind(self):
        self.clock = self.dut.clk
        self.reset = self.dut.rst
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
        self.dw_bind = dict(
            clock = self.clock,
            req_ready = self.dut.dw_data_addr_ready,
            req_valid = self.dut.dw_data_addr_valid,
            req_data = self.dut.dw_data,
            req_addr = self.dut.dw_addr,
            req_strobe = self.dut.dw_strobe,
            resp_ready = self.dut.dw_resp_ready,
            resp_valid = self.dut.dw_resp_valid,
            resp = self.dut.dw_resp,
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
    def copperv2_bind(self):
        self.clock = self.dut.clock
        self.reset = self.dut.reset
        self.ir_bind = dict(
            clock = self.clock,
            addr_valid = self.dut.ir_addr_valid,
            addr_ready = self.dut.ir_addr_ready,
            addr = self.dut.ir_addr_bits,
            data_valid = self.dut.ir_data_valid,
            data_ready = self.dut.ir_data_ready,
            data = self.dut.ir_data_bits,
            reset = self.reset,
        )
        self.dr_bind = dict(
            clock = self.clock,
            addr_valid = self.dut.dr_addr_valid,
            addr_ready = self.dut.dr_addr_ready,
            addr = self.dut.dr_addr,
            data_valid = self.dut.dr_data_valid,
            data_ready = self.dut.dr_data_ready,
            data = self.dut.dr_data,
            reset = self.reset,
        )
        self.regfile_write_bind = dict(
            clock = self.clock,
            rd_en = self.dut.regfile.rd_en,
            rd_addr = self.dut.regfile.rd,
            rd_data = self.dut.regfile.rd_din,
            reset = self.reset,
        )
        self.regfile_read_bind = dict(
            clock = self.clock,
            rs1_en = self.dut.regfile.rs1_en,
            rs1_addr = self.dut.regfile.rs1,
            rs1_data = self.dut.regfile.rs1_dout,
            rs2_en = self.dut.regfile.rs2_en,
            rs2_addr = self.dut.regfile.rs2,
            rs2_data = self.dut.regfile.rs2_dout,
            reset = self.reset,
        )

def from_array(data,addr):
    buf = []
    for i in range(4):
        assert addr+i in data, f"Invalid data address: 0x{addr+i:X}"
        buf.append(data[addr+i])
    return int.from_bytes(buf,byteorder='little')

def to_bytes(data):
    return (data).to_bytes(length=4,byteorder='little')

class Testbench():
    def __init__(self, dut, params):
        self.log = SimLog("cocotb.Testbench")
        config = TBConfig(dut)
        self.clock = config.clock
        self.reset = config.reset
        self.reset.setimmediatevalue(0)
        # parse data memory in string format
        self.data_memory = {}
        for t in params.data_memory:
            t = BusReadTransaction.from_string(t)
            for i in range(4):
                self.data_memory[t.addr+i] =  to_bytes(t.data)[i]
        ## Instruction read
        self.bus_ir_driver = ReadBusSourceDriver("bus_ir",**config.ir_bind)
        self.bus_ir_monitor = ReadBusMonitor("bus_ir",**config.ir_bind)
        self.bus_ir_req_monitor = ReadBusMonitor("bus_ir_req",**config.ir_bind,request_only=True,
            callback=self.instruction_read_callback(params.instructions))
        ## Data read
        self.bus_dr_driver = ReadBusSourceDriver("bus_dr",**config.dr_bind)
        self.bus_dr_monitor = ReadBusMonitor("bus_dr",**config.dr_bind)
        self.bus_dr_req_monitor = ReadBusMonitor("bus_dr_req",**config.dr_bind,request_only=True,
            callback=self.data_read_callback(self.data_memory))
        ## Data write
        self.bus_dw_driver = WriteBusSourceDriver("bus_dw",**config.dw_bind)
        self.bus_dw_monitor = WriteBusMonitor("bus_dw",**config.dw_bind)
        self.bus_dw_req_monitor = WriteBusMonitor("bus_dw_req",**config.dw_bind,request_only=True,
            callback=self.data_write_callback(self.data_memory))
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
    def data_write_callback(self, data_memory):
        def callback(transaction):
            data = transaction.data
            addr = transaction.addr
            strobe = transaction.strobe
            mask = list(bin(strobe).lstrip('0b'))
            for i in range(4):
                if mask[i]:
                    data_memory[addr+i] = to_bytes(data)[i]
            self.log.debug(f"Data memory: {data_memory}")
            driver_transaction = BusWriteTransaction(
                response = 1,
            )
            self.bus_dw_driver.append(driver_transaction)
        return callback
    def data_read_callback(self, data_memory):
        self.log.debug(f"Data memory: {data_memory}")
        def callback(transaction):
            addr = transaction.addr
            driver_transaction = BusReadTransaction(
                data = from_array(data_memory,addr),
                addr = addr,
            )
            self.bus_dr_driver.append(driver_transaction)
        return callback
    def instruction_read_callback(self, instructions):
        instruction_memory = {}
        elf = compile_test(crt0 + instructions)
        section_start = elf['.text']['addr']
        section_data = elf['.text']['data']
        section_size = len(section_data)
        for addr in range(section_size):
            instruction_memory[section_start+addr] = section_data[addr]
        self.log.debug(f"Instruction memory: {instruction_memory}")
        def callback(transaction):
            driver_transaction = "deassert_ready"
            if transaction.addr < section_start + section_size:
                addr = transaction.addr
                driver_transaction = BusReadTransaction(
                    data = from_array(instruction_memory,addr),
                    addr = transaction.addr,
                )
            self.bus_ir_driver.append(driver_transaction)
        return callback
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
