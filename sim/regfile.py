import dataclasses

import cocotb
from cocotb.triggers import RisingEdge, ReadOnly, Combine
from cocotb_bus.monitors import Monitor
from cocotb.log import SimLog

from riscv_utils import reg_abi_map

@dataclasses.dataclass
class RegFileWriteTransaction:
    reg: int = 0
    data: int = 0
    @classmethod
    def from_string(cls, string):
        tokens = string.split()
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
        tokens = string.split()
        if len(tokens) == 2:
            reg, value = tokens
            return cls(reg_abi_map[reg],int(value,0))
        elif len(tokens) == 4:
            reg1, value1, reg2, value2 = tokens
            return cls(reg_abi_map[reg1],int(value1,0)
                    ,reg_abi_map[reg2],int(value2,0))
        else:
            ValueError("Invalid transaction")
                
class RegFileBfm:
    def __init__(self,
            clock,
            reset,
            rd_en,
            rd_addr,
            rd_data,
            rs1_en,
            rs1_addr,
            rs1_data,
            rs2_en,
            rs2_addr,
            rs2_data,
        ):
        self.clock = clock
        self.reset = reset
        self.rd_en = rd_en
        self.rd_addr = rd_addr
        self.rd_data = rd_data
        self.rs1_en = rs1_en
        self.rs1_addr = rs1_addr
        self.rs1_data = rs1_data
        self.rs2_en = rs2_en
        self.rs2_addr = rs2_addr
        self.rs2_data = rs2_data
    async def recv_rd(self):
        while(True):
            await RisingEdge(self.clock)
            await ReadOnly()
            if self.rd_en.value:
                yield dict(
                    addr = int(self.rd_addr.value),
                    data = int(self.rd_data.value)
                )
    async def recv_rs(self):
        while(True):
            buf = {}
            await RisingEdge(self.clock)
            await ReadOnly()
            en1 = self.rs1_en.value
            en2 = self.rs2_en.value
            if (not en1) and (not en2):
                continue
            await RisingEdge(self.clock)
            await ReadOnly()
            if en1:
                buf['addr'] = int(self.rs1_addr.value)
                buf['data'] = int(self.rs1_data.value)
            if en2:
                buf['addr2'] = int(self.rs2_addr.value)
                buf['data2'] = int(self.rs2_data.value)
            yield buf

class RegFileWriteMonitor(Monitor):
    def __init__(self,name,bfm,callback=None,event=None):
        self.name = name
        self.log = SimLog(f"cocotb.{self.name}")
        self.bfm = bfm
        super().__init__(callback=callback,event=event)
    async def _monitor_recv(self):
        while True:
            received = await anext(self.bfm.recv_rd())
            transaction = RegFileWriteTransaction(
                reg = received['addr'],
                data = received['data'],
            )
            self.log.debug("Receiving register file write transaction: %s", transaction)
            self._recv(transaction)

class RegFileReadMonitor(Monitor):
    def __init__(self,name,bfm,callback=None,event=None):
        self.name = name
        self.log = SimLog(f"cocotb.{self.name}")
        self.bfm = bfm
        super().__init__(callback=callback,event=event)
    async def _monitor_recv(self):
        while True:
            transaction = None
            received = await anext(self.bfm.recv_rs())
            if len(received) == 4:
                transaction = RegFileReadTransaction(
                    reg1 = int(received['addr']),
                    data1 = int(received['data']),
                    reg2 = int(received['addr2']),
                    data2 = int(received['data2']),
                )
            elif 'addr' in received:
                transaction = RegFileReadTransaction(
                    reg1 = int(received['addr']),
                    data1 = int(received['data']),
                )
            elif 'addr2' in received:
                transaction = RegFileReadTransaction(
                    reg1 = int(received['addr2']),
                    data1 = int(received['data2']),
                )
            self.log.debug("Receiving register file read transaction: %s", transaction)
            self._recv(transaction)
