import cocotb
from cocotb.log import SimLog
from cocotb_bus.scoreboard import Scoreboard
from cocotb.triggers import RisingEdge, ClockCycles

from bus import BusReadTransaction, BusWriteTransaction, BusBfm, BusMonitor, BusSourceDriver
from regfile import RegFileReadMonitor, RegFileWriteMonitor, RegFileReadTransaction, RegFileWriteTransaction, RegFileBfm
from cocotb_utils import from_array, to_bytes

class Testbench():
    def __init__(self, dut, params, 
            instruction_memory = None, 
            data_memory = None, 
            enable_self_checking = True
        ):
        self.log = SimLog("cocotb.Testbench")
        self.dut = dut
        self.clock = self.dut.clk
        self.reset = self.dut.rst
        core = self.dut.core
        if cocotb.plusargs.get('dut_copperv1',False):
            core = self.dut
        self.reset.setimmediatevalue(0)
        ## Process parameters
        self.instruction_memory = instruction_memory
        self.data_memory = data_memory
        if enable_self_checking:
            self.expected_regfile_read = [RegFileReadTransaction.from_string(t) for t in params.expected_regfile_read]
            self.expected_regfile_write = [RegFileWriteTransaction.from_string(t) for t in params.expected_regfile_write]
            self.expected_data_read = [BusReadTransaction.from_string(t) for t in params.expected_data_read]
            self.expected_data_write = [BusWriteTransaction.from_string(t) for t in params.expected_data_write]
        self.log.debug(f"Data memory: {self.data_memory}")
        self.log.debug(f"Instruction memory: {self.instruction_memory}")
        ## Bus functional models
        self.bus_bfm = BusBfm(
            clock = self.clock,
            reset = self.reset,
            ir_addr_valid = self.dut.ir_addr_valid,
            ir_addr_ready = self.dut.ir_addr_ready,
            ir_addr = self.dut.ir_addr,
            ir_data_valid = self.dut.ir_data_valid,
            ir_data_ready = self.dut.ir_data_ready,
            ir_data = self.dut.ir_data,
            dr_addr_valid = self.dut.dr_addr_valid,
            dr_addr_ready = self.dut.dr_addr_ready,
            dr_addr = self.dut.dr_addr,
            dr_data_valid = self.dut.dr_data_valid,
            dr_data_ready = self.dut.dr_data_ready,
            dr_data = self.dut.dr_data,
            dw_data_addr_ready = self.dut.dw_data_addr_ready,
            dw_data_addr_valid = self.dut.dw_data_addr_valid,
            dw_data = self.dut.dw_data,
            dw_addr = self.dut.dw_addr,
            dw_strobe = self.dut.dw_strobe,
            dw_resp_ready = self.dut.dw_resp_ready,
            dw_resp_valid = self.dut.dw_resp_valid,
            dw_resp = self.dut.dw_resp,
        )
        if enable_self_checking:
            regfile_bfm = RegFileBfm(
                clock = self.clock,
                reset = self.reset,
                rd_en = core.regfile.rd_en,
                rd_addr = core.regfile.rd,
                rd_data = core.regfile.rd_din,
                rs1_en = core.regfile.rs1_en,
                rs1_addr = core.regfile.rs1,
                rs1_data = core.regfile.rs1_dout,
                rs2_en = core.regfile.rs2_en,
                rs2_addr = core.regfile.rs2,
                rs2_data = core.regfile.rs2_dout,
            )
        ## Instruction read
        self.bus_ir_driver = BusSourceDriver("bus_ir",BusReadTransaction,self.bus_bfm.send_ir_resp,self.bus_bfm.drive_ir_ready)
        self.bus_ir_monitor = BusMonitor("bus_ir",BusReadTransaction,self.bus_bfm.recv_ir_req,self.bus_bfm.recv_ir_resp)
        self.bus_ir_req_monitor = BusMonitor("bus_ir_req",BusReadTransaction,self.bus_bfm.recv_ir_req,
            callback=self.instruction_read_callback)
        ## Data read
        self.bus_dr_driver = BusSourceDriver("bus_dr",BusReadTransaction,self.bus_bfm.send_dr_resp,self.bus_bfm.drive_dr_ready)
        self.bus_dr_monitor = BusMonitor("bus_dr",BusReadTransaction,self.bus_bfm.recv_dr_req,self.bus_bfm.recv_dr_resp)
        self.bus_dr_req_monitor = BusMonitor("bus_dr_req",BusReadTransaction,self.bus_bfm.recv_dr_req,
            callback=self.data_read_callback)
        ## Data write
        self.bus_dw_driver = BusSourceDriver("bus_dw",BusWriteTransaction,self.bus_bfm.send_dw_resp,self.bus_bfm.drive_dw_ready)
        self.bus_dw_monitor = BusMonitor("bus_dw",BusWriteTransaction,self.bus_bfm.recv_dw_req,self.bus_bfm.recv_dw_resp)
        self.bus_dw_req_monitor = BusMonitor("bus_dw_req",BusWriteTransaction,self.bus_bfm.recv_dw_req,
            callback=self.data_write_callback)
        if enable_self_checking:
            ## Regfile
            self.regfile_write_monitor = RegFileWriteMonitor("regfile_write",regfile_bfm)
            self.regfile_read_monitor = RegFileReadMonitor("regfile_read",regfile_bfm)
            ## Self checking
            self.scoreboard = Scoreboard(dut)
            self.scoreboard.add_interface(self.regfile_write_monitor, self.expected_regfile_write)
            self.scoreboard.add_interface(self.regfile_read_monitor, self.expected_regfile_read)
            self.scoreboard.add_interface(self.bus_dr_monitor, self.expected_data_read)
            self.scoreboard.add_interface(self.bus_dw_monitor, self.expected_data_write)
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
        await ClockCycles(self.clock,2)
