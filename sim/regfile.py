import dataclasses
import re

import cocotb
from cocotb.triggers import RisingEdge, ReadOnly, Combine
from cocotb_bus.monitors import Monitor
from cocotb.log import SimLog
from cocotb_utils import BundleMonitor

from riscv_utils import reg_abi_map

@dataclasses.dataclass
class RegFileTransaction:
    reg: int = 0
    data: int = 0
    @classmethod
    def from_string(cls, string):
        reg, value = re.split('\s+',string)
        return cls(reg_abi_map[reg],int(value,0))

class RegFileWriteMonitor(BundleMonitor):
    _signals = [
        'clock',
        'rd_en',
        'rd_addr',
        'rd_data',
    ]
    async def _monitor_recv(self):
        while True:
            await RisingEdge(self.bus.clock)
            await ReadOnly()
            if self.bus.rd_en.value:
                transaction = RegFileTransaction(
                    reg = int(self.bus.rd_addr.value),
                    data = int(self.bus.rd_data.value),
                )
                self.log.debug("Receiving register file write transaction: %s", transaction)
                self._recv(transaction)

class RegFileReadMonitor(BundleMonitor):
    _signals = [
        'clock',
        'rs1_en',
        'rs1_addr',
        'rs1_data',
        'rs2_en',
        'rs2_addr',
        'rs2_data'
    ]
    async def _monitor_recv(self):
        mon1 = cocotb.fork(self.rs1_monitor_recv())
        mon2 = cocotb.fork(self.rs2_monitor_recv())
        await Combine(mon1,mon2)
    async def rs1_monitor_recv(self):
        while True:
            await RisingEdge(self.bus.clock)
            await ReadOnly()
            if self.bus.rs1_en.value:
                await RisingEdge(self.bus.clock)
                await ReadOnly()
                transaction = RegFileTransaction(
                    reg = int(self.bus.rs1_addr.value),
                    data = int(self.bus.rs1_data.value),
                )
                self.log.debug("Receiving register file read transaction: %s", transaction)
                self._recv(transaction)
    async def rs2_monitor_recv(self):
        while True:
            await RisingEdge(self.bus.clock)
            await ReadOnly()
            if self.bus.rs2_en.value:
                await RisingEdge(self.bus.clock)
                await ReadOnly()
                transaction = RegFileTransaction(
                    reg = int(self.bus.rs2_addr.value),
                    data = int(self.bus.rs2_data.value),
                )
                self.log.debug("Receiving register file read transaction: %s", transaction)
                self._recv(transaction)
