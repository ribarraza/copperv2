import dataclasses

import cocotb
from cocotb.triggers import RisingEdge, ReadOnly, Combine
from cocotb_bus.monitors import Monitor
from cocotb.log import SimLog
from cocotb_utils import BundleMonitor, lex

from riscv_utils import reg_abi_map

@dataclasses.dataclass
class RegFileWriteTransaction:
    reg: int = 0
    data: int = 0
    @classmethod
    def from_string(cls, string):
        tokens = lex(string)
        reg, value = tokens
        return cls(reg_abi_map[reg],int(value,0))

@dataclasses.dataclass
class RegFileReadTransaction:
    reg1: int = 0
    data1: int = 0
    reg2: int = 0
    data2: int = 0
    @classmethod
    def from_string(cls, string):
        tokens = lex(string)
        if len(tokens) == 2:
            reg, value = tokens
            return cls(reg_abi_map[reg],int(value,0))
        elif len(tokens) == 4:
            reg1, value1, reg2, value2 = tokens
            return cls(reg_abi_map[reg1],int(value1,0)
                    ,reg_abi_map[reg2],int(value2,0))
        else:
            ValueError("Invalid transaction")

class RegFileWriteMonitor(BundleMonitor):
    _signals = [
        'clock',
        'rd_en',
        'rd_addr',
        'rd_data',
    ]
    async def _monitor_recv(self):
        while True:
            await RisingEdge(self.signals.clock)
            await ReadOnly()
            if self.signals.rd_en.value:
                transaction = RegFileWriteTransaction(
                    reg = int(self.signals.rd_addr.value),
                    data = int(self.signals.rd_data.value),
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
        while True:
            await RisingEdge(self.signals.clock)
            await ReadOnly()
            if self.signals.rs1_en.value and self.signals.rs2_en.value:
                await RisingEdge(self.signals.clock)
                await ReadOnly()
                transaction = RegFileReadTransaction(
                    reg1 = int(self.signals.rs1_addr.value),
                    data1 = int(self.signals.rs1_data.value),
                    reg2 = int(self.signals.rs2_addr.value),
                    data2 = int(self.signals.rs2_data.value),
                )
                self.log.debug("Receiving register file read transaction: %s", transaction)
                self._recv(transaction)
            elif self.signals.rs1_en.value:
                await RisingEdge(self.signals.clock)
                await ReadOnly()
                transaction = RegFileReadTransaction(
                    reg1 = int(self.signals.rs1_addr.value),
                    data1 = int(self.signals.rs1_data.value),
                )
                self.log.debug("Receiving register file read transaction: %s", transaction)
                self._recv(transaction)
            elif self.signals.rs2_en.value:
                await RisingEdge(self.signals.clock)
                await ReadOnly()
                transaction = RegFileReadTransaction(
                    reg1 = int(self.signals.rs2_addr.value),
                    data1 = int(self.signals.rs2_data.value),
                )
                self.log.debug("Receiving register file read transaction: %s", transaction)
                self._recv(transaction)
