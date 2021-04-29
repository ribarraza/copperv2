import dataclasses

from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep

from cocotb_utils import BusMonitor2, BusDriver2

@dataclasses.dataclass
class ReadTransaction:
    data: int = 0
    addr: int = 0
    type: str = "full"

class ReadBusMonitor(BusMonitor2):
    _signals = [
        "clock",
        "addr_ready",
        "addr_valid",
        "addr",
        "data_ready",
        "data_valid",
        "data",
    ]
    async def _monitor_recv(self):
        transaction = None
        while True:
            await RisingEdge(self.bus.clock)
            await ReadOnly()
            if self.bus.addr_ready.value and self.bus.addr_valid.value:
                assert transaction is None, f"Receiving new request before sending response for last request"
                transaction = ReadTransaction(
                    addr = int(self.bus.addr.value),
                    type = "request",
                )
                self.log.debug("Receiving read transaction request: %s", transaction)
                self._recv(transaction)
            if transaction is not None and self.bus.data_ready.value and self.bus.data_valid.value:
                transaction = ReadTransaction(
                    data = int(self.bus.data.value),
                    addr = transaction.addr,
                )
                self.log.debug("Receiving full read transaction: %s", transaction)
                self._recv(transaction)
                transaction = None

class ReadBusSourceDriver(BusDriver2):
    _signals = [
        "clock",
        "addr_ready",
        "data_valid",
        "data_ready",
        "data",
    ]
    _optional_signals = [
        "addr_valid",
        "addr",
    ]
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.bus.addr_ready <= 1
    async def _driver_send(self, transaction: ReadTransaction, sync: bool = True):
        self.log.debug("Responding read transaction: %s", transaction)
        if transaction.type == "full":
            await self._wait_for_signal(self.bus.data_ready)
            await RisingEdge(self.bus.clock)
            self.bus.data_valid <= 1
            self.bus.data <= transaction.data
            await RisingEdge(self.bus.clock)
            self.bus.data_valid <= 0
        elif transaction.type == "deassert_ready":
            await NextTimeStep()
            self.bus.addr_ready <= 0
