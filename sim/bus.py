import dataclasses

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly, ClockCycles, NextTimeStep
from cocotb_bus.monitors import Monitor, BusMonitor
from cocotb_bus.drivers import BusDriver
from cocotb.log import SimLog
from cocotb_bus.scoreboard import Scoreboard

@dataclasses.dataclass
class ReadTransaction:
    data: int = 0
    addr: int = 0
    type: str = "full"

class ReadBusMonitor(BusMonitor):
    _signals = [
        "addr_ready",
        "addr_valid",
        "addr_bits",
        "data_ready",
        "data_valid",
        "data_bits",
    ]
    async def _monitor_recv(self):
        transaction = None
        while True:
            await RisingEdge(self.clock)
            await ReadOnly()
            if self.bus.addr_ready.value and self.bus.addr_valid.value:
                assert transaction is None, f"Receiving new request before sending response for last request"
                transaction = ReadTransaction(
                    addr = int(self.bus.addr_bits.value),
                    type = "request",
                )
                self.log.debug("Receiving read transaction request: %s", transaction)
                self._recv(transaction)
            if transaction is not None and self.bus.data_ready.value and self.bus.data_valid.value:
                transaction = ReadTransaction(
                    data = int(self.bus.data_bits.value),
                    addr = transaction.addr,
                )
                self.log.debug("Receiving full read transaction: %s", transaction)
                self._recv(transaction)
                transaction = None

class ReadBusSourceDriver(BusDriver):
    _signals = [
        "addr_ready",
        "data_valid",
        "data_ready",
        "data_bits",
    ]
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.bus.addr_ready <= 1
    async def _driver_send(self, transaction: ReadTransaction, sync: bool = True):
        self.log.debug("Responding read transaction: %s", transaction)
        if transaction.type == "full":
            await self._wait_for_signal(self.bus.data_ready)
            await RisingEdge(self.clock)
            self.bus.data_valid <= 1
            self.bus.data_bits <= transaction.data
            await RisingEdge(self.clock)
            self.bus.data_valid <= 0
        elif transaction.type == "deassert_ready":
            await NextTimeStep()
            self.bus.addr_ready <= 0

