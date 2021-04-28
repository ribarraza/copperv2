import dataclasses
import re

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly, ClockCycles, NextTimeStep
from cocotb_bus.monitors import Monitor, BusMonitor
from cocotb_bus.drivers import BusDriver
from cocotb.log import SimLog
from cocotb_bus.scoreboard import Scoreboard

from riscv_utils import abi_map

@dataclasses.dataclass
class RegFileWriteTransaction:
    reg: int = 0
    data: int = 0
    @classmethod
    def from_string(cls, string):
        reg, value = re.split('\s+',string)
        return cls(abi_map[reg],int(value,0))

class RegFileWriteMonitor(Monitor):
    def __init__(self, dut, clock, callback=None, event=None):
        self.name = "regfile"
        self.log = SimLog("cocotb.%s.%s" % (dut._path, self.name))
        self.clock = clock
        regfile = dut.regfile
        self.rd_en = regfile.rd_en
        self.rd = regfile.rd
        self.rd_din = regfile.rd_din
        super().__init__(callback,event)
    async def _monitor_recv(self):
        while True:
            await RisingEdge(self.clock)
            await ReadOnly()
            if self.rd_en.value:
                transaction = RegFileWriteTransaction(
                    reg = int(self.rd.value),
                    data = int(self.rd_din.value),
                )
                self.log.debug("Receiving register file transaction: %s", transaction)
                self._recv(transaction)
