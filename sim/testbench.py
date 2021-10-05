import cocotb
from cocotb.log import SimLog
from cocotb_bus.scoreboard import Scoreboard
from cocotb.triggers import RisingEdge, ClockCycles
from pathlib import Path
from tabulate import tabulate

from bus import BusReadTransaction, BusWriteTransaction, BusBfm, BusMonitor, BusSourceDriver
from regfile import RegFileReadMonitor, RegFileWriteMonitor, RegFileReadTransaction, RegFileWriteTransaction, RegFileBfm
from cocotb_utils import from_array, to_bytes
from riscv_utils import StackMonitor

class Testbench():
    def __init__(self, dut,
            test_name,
            expected_regfile_read = None,
            expected_regfile_write = None,
            expected_data_read = None,
            expected_data_write = None,
            instruction_memory = None, 
            data_memory = None, 
            enable_self_checking = True,
            pass_fail_address = None,
            pass_fail_values = None,
            output_address = None,
            timer_address = None,
        ):
        self.log = SimLog('cocotb.'+__name__+'.'+self.__class__.__name__)
        self.test_name = test_name
        self.dut = dut
        self.clock = self.dut.clk
        self.reset = self.dut.rst
        if cocotb.plusargs.get('dut_copperv1',False):
            core = self.dut
        else:
            core = self.dut.core
        self.reset.setimmediatevalue(0)
        self.pass_fail_address = pass_fail_address
        self.pass_fail_values = pass_fail_values
        self.output_address = output_address
        self.fake_uart = []
        self.timer_counter = 0
        self.timer_address = timer_address
        if self.timer_address is not None:
            cocotb.fork(self.timer())
        ## Process parameters
        self.memory = {**instruction_memory,**data_memory}
        if 'debug_test' in cocotb.plusargs:
            csv_path = Path(test_name+'_memory.csv')
            self.log.debug(f"Dumping initial memory content to {csv_path.resolve()}")
            memory = [(f'0x{k:X}',f'0x{v:X}') for k,v in self.memory.items()]
            csv_path.write_text(tabulate(memory, ['address','value'], tablefmt="plain"))
        self.end_i_address = None
        if enable_self_checking:
            self.end_i_address = max(instruction_memory.keys())
            self.expected_regfile_read = [RegFileReadTransaction.from_string(t) for t in expected_regfile_read]
            self.expected_regfile_write = [RegFileWriteTransaction.from_string(t) for t in expected_regfile_write]
            self.expected_data_read = [BusReadTransaction.from_string(t) for t in expected_data_read]
            self.expected_data_write = [BusWriteTransaction.from_string(t) for t in expected_data_write]
        #self.log.debug(f"Instruction memory: {instruction_memory}")
        #self.log.debug(f"Data memory: {data_memory}")
        #self.log.debug(f"Memory: {self.memory}")
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
            callback=self.memory_callback,bus_name="bus_ir")
        ## Data read
        self.bus_dr_driver = BusSourceDriver("bus_dr",BusReadTransaction,self.bus_bfm.send_dr_resp,self.bus_bfm.drive_dr_ready)
        self.bus_dr_monitor = BusMonitor("bus_dr",BusReadTransaction,self.bus_bfm.recv_dr_req,self.bus_bfm.recv_dr_resp)
        self.bus_dr_req_monitor = BusMonitor("bus_dr_req",BusReadTransaction,self.bus_bfm.recv_dr_req,
            callback=self.memory_callback,bus_name="bus_dr")
        ## Data write
        self.bus_dw_driver = BusSourceDriver("bus_dw",BusWriteTransaction,self.bus_bfm.send_dw_resp,self.bus_bfm.drive_dw_ready)
        self.bus_dw_monitor = BusMonitor("bus_dw",BusWriteTransaction,self.bus_bfm.recv_dw_req,self.bus_bfm.recv_dw_resp)
        self.bus_dw_req_monitor = BusMonitor("bus_dw_req",BusWriteTransaction,self.bus_bfm.recv_dw_req,
            callback=self.memory_callback,bus_name="bus_dw")
        ## Regfile
        self.regfile_write_monitor = RegFileWriteMonitor("regfile_write",regfile_bfm)
        self.regfile_read_monitor = RegFileReadMonitor("regfile_read",regfile_bfm)
        ## Stack Monitor
        #StackMonitor(self.regfile_write_monitor)
        if enable_self_checking:
            ## Self checking
            self.scoreboard = Scoreboard(dut)
            self.scoreboard.add_interface(self.regfile_write_monitor, self.expected_regfile_write)
            self.scoreboard.add_interface(self.regfile_read_monitor, self.expected_regfile_read)
            self.scoreboard.add_interface(self.bus_dr_monitor, self.expected_data_read)
            self.scoreboard.add_interface(self.bus_dw_monitor, self.expected_data_write)
    async def timer(self):
        while True:
            await RisingEdge(self.clock)
            self.timer_counter += 1
    def memory_callback(self, transaction):
        if isinstance(transaction,BusReadTransaction) and transaction.bus_name == 'bus_ir':
            driver_transaction = "deassert_ready"
            if self.end_i_address is None or (self.end_i_address is not None and transaction.addr < self.end_i_address):
                driver_transaction = BusReadTransaction(
                    bus_name = transaction.bus_name,
                    data = from_array(self.memory,transaction.addr),
                    addr = transaction.addr)
            self.bus_ir_driver.append(driver_transaction)
            #self.log.debug('instruction_read_callback transaction: %s driver_transaction %s',
            #    transaction,driver_transaction)
        elif isinstance(transaction,BusReadTransaction) and transaction.bus_name == 'bus_dr':
            driver_transaction = BusReadTransaction(
                bus_name = transaction.bus_name,
                data = self.handle_data_read(transaction),
                addr = transaction.addr,
            )
            self.bus_dr_driver.append(driver_transaction)
            #self.log.debug('data_read_callback transaction: %s driver_transaction %s',
            #    transaction,driver_transaction)
        elif isinstance(transaction,BusWriteTransaction):
            self.handle_data_write(transaction)
            driver_transaction = BusWriteTransaction(
                bus_name = transaction.bus_name,
                data = transaction.data,
                addr = transaction.addr,
                strobe = transaction.strobe,
                response = 1,
            )
            self.bus_dw_driver.append(driver_transaction)
            #self.log.debug('data_write_callback transaction: %s driver_transaction %s',
            #    transaction,driver_transaction)
        else:
            raise ValueError(f"Unsupported transaction type: {transaction}")
    def handle_data_write(self,transaction):
        if self.pass_fail_address is not None and self.pass_fail_address == transaction.addr:
            if len(self.fake_uart) > 0:
                self.log.info("Fake UART output:\n%s",''.join(self.fake_uart))
            if self.pass_fail_values[transaction.data]:
                self.log.info("Received test pass from bus")
                raise cocotb.result.TestSuccess("Received test pass from bus")
            else:
                raise cocotb.result.TestFailure("Received test fail from bus")
        elif self.output_address is not None and self.output_address == transaction.addr:
            recv = chr(transaction.data)
            self.fake_uart.append(recv)
            self.log.info('Fake UART received: %s',repr(recv))
        else:
            mask = f"{transaction.strobe:04b}"
            #self.log.debug('write start: %X mask: %s',from_array(self.memory,transaction.addr),mask)
            for i in range(4):
                if int(mask[3-i]):
                    #self.log.debug('writing %X -> %X',transaction.addr+i,to_bytes(transaction.data)[i])
                    self.memory[transaction.addr+i] = to_bytes(transaction.data)[i]
            #self.log.debug('write finished: %X',from_array(self.memory,transaction.addr))
    def handle_data_read(self,transaction):
        value = None
        if self.timer_address is not None and self.timer_address == transaction.addr:
            value = self.timer_counter
        else:
            value = from_array(self.memory,transaction.addr)
        return value
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
