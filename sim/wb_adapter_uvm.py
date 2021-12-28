import logging
from typing import Awaitable
import cocotb
from cocotb.decorators import RunningTask
from cocotb.triggers import First, PythonTrigger
import pyuvm as uvm
import random

from cocotb_utils import anext

class BusSeqItem(uvm.uvm_sequence_item):
    def __init__(self, name):
        super().__init__(name)
        self.addr = None
        self.data = None
        self.strobe = None
        self.addr_width = 32
        self.data_width = 32
        self.strobe_width = self.data_width // 8
    def __eq__(self, other):
        same = self.addr == other.addr
        if self.data is not None or other.data is not None:
            same = same and self.data == other.data
        return same
    def __str__(self):
        res = f'{self.get_name()} : '
        if self.data is not None:
            res += f'data: 0x{self.data:0{self.data_width//4}X} '
        if self.addr is not None:
            res += f'addr: 0x{self.addr:0{self.addr_width//4}X} '
        if self.strobe is not None:
            res += f'strobe: 0b{self.strobe:0{self.strobe_width}b}'
        return res
    def randomize(self):
        self.addr = random.randint(0, (2**self.addr_width)-1)
        if random.choice([False,True]):
            self.data = random.randint(0, (2**self.data_width)-1)
            self.strobe = random.randint(0, (2**self.strobe_width)-1)

class BusSeq(uvm.uvm_sequence):
    async def body(self):
        for i in range(10):
            bus_tr = BusSeqItem("bus_tr")
            await self.start_item(bus_tr)
            bus_tr.randomize()
            await self.finish_item(bus_tr)

class BusDriver(uvm.uvm_driver):
    def connect_phase(self):
        self.bfm = self.cdb_get("BUS_BFM")
    async def run_phase(self):
        while True:
            transaction: BusSeqItem = await self.seq_item_port.get_next_item()
            if transaction.data is None:
                await self.bfm['read'].addr.send(addr=transaction.addr)
            else:
                await self.bfm['write'].req.send(addr=transaction.addr,data=transaction.data,strobe=transaction.strobe)
            self.logger.debug(f"Sent transaction: {transaction}")
            self.seq_item_port.item_done()

class Coverage(uvm.uvm_subscriber):
    def end_of_elaboration_phase(self):
        self.cvg = set()
    def write(self, bus_transaction):
        transaction_type = 'write' if 'resp' in bus_transaction else 'read'
        self.cvg.add(transaction_type)
    def check_phase(self):
        target = {'write','read'}
        if len(target - self.cvg) > 0:
            self.logger.error(f"Functional coverage error. "
                              f"Missed: {target-self.cvg}")

class Scoreboard(uvm.uvm_component):
    def build_phase(self):
        self.bus_fifo = uvm.uvm_tlm_analysis_fifo("bus_fifo", self)
        self.wb_fifo = uvm.uvm_tlm_analysis_fifo("wb_fifo", self)
        self.bus_port = uvm.uvm_get_port("bus_port", self)
        self.wb_port = uvm.uvm_get_port("wb_port", self)
        self.bus_export = self.bus_fifo.analysis_export
        self.wb_export = self.wb_fifo.analysis_export
    def connect_phase(self):
        self.bus_port.connect(self.bus_fifo.get_export)
        self.wb_port.connect(self.wb_fifo.get_export)
    def check_phase(self):
        while self.bus_port.can_get():
            _, actual_result = self.wb_port.try_get()
            ref_success, ref = self.bus_port.try_get()
            if not ref_success:
                self.logger.critical(f"result {actual_result} had no command")
            else:
                if ref == actual_result:
                    self.logger.info(f"PASSED: {ref} = {actual_result}")
                else:
                    self.logger.error(f"FAILED: {ref} != {actual_result}")
                    assert False

class WbMonitor(uvm.uvm_component):
    def __init__(self, name, parent):
        super().__init__(name, parent)
    def build_phase(self):
        self.ap = uvm.uvm_analysis_port("ap", self)
    def connect_phase(self):
        self.bfm = self.cdb_get("WB_BFM")
    async def run_phase(self):
        while True:
            datum = await anext(self.bfm.sink_receive())
            self.ap.write(datum)

class BusMonitor(uvm.uvm_component):
    def __init__(self, name, parent):
        super().__init__(name, parent)
    def build_phase(self):
        self.ap = uvm.uvm_analysis_port("ap", self)
    def connect_phase(self):
        self.bfm = self.cdb_get("BUS_BFM")
    async def run_phase(self):
        while True:
            datum = await First(anext(self.bfm['read'].addr.receive()),anext(self.bfm['write'].req.receive()))
            self.ap.write(datum)

class WbAdapterEnv(uvm.uvm_env):
    def build_phase(self):
        self.wb_mon = WbMonitor("wb_mon", self)
        self.bus_mon = BusMonitor("bus_mon", self)
        self.scoreboard = Scoreboard("scoreboard", self)
        self.coverage = Coverage("coverage", self)
        self.driver = BusDriver("driver", self)
        self.seqr = uvm.uvm_sequencer("seqr", self)
        uvm.ConfigDB().set(None, "*", "SEQR", self.seqr)
    def connect_phase(self):
        self.bus_mon.ap.connect(self.scoreboard.bus_export)
        self.bus_mon.ap.connect(self.coverage.analysis_export)
        self.wb_mon.ap.connect(self.scoreboard.wb_export)
        self.driver.seq_item_port.connect(self.seqr.seq_item_export)

class WbAdapterTest(uvm.uvm_test):
    def build_phase(self):
        self.env = WbAdapterEnv.create("env", self)
    async def run_phase(self):
        self.raise_objection()
        seqr = uvm.ConfigDB().get(self, "", "SEQR")
        seq = BusSeq("seq")
        await seq.start(seqr)
        self.drop_objection()
    def end_of_elaboration_phase(self):
        self.set_logging_level_hier(logging.DEBUG)

