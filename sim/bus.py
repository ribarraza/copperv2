import dataclasses

from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep

from cocotb_utils import BundleMonitor, BundleDriver, wait_for_signal, lex

@dataclasses.dataclass
class BusReadTransaction:
    data: int = 0
    addr: int = 0
    @classmethod
    def from_string(cls, string):
        addr, data = lex(string)
        return cls(int(data,0),int(addr,0))

@dataclasses.dataclass
class BusWriteTransaction:
    data: int = 0
    addr: int = 0
    strobe: int = 0
    response: int = 0
    @classmethod
    def from_string(cls, string):
        addr, data, strobe, response = lex(string)
        return cls(int(data,0),int(addr,0),int(strobe,0),int(response,0))

class ReadBusMonitor(BundleMonitor):
    _signals = [
        "clock",
        "addr_ready",
        "addr_valid",
        "addr",
        "data_ready",
        "data_valid",
        "data",
    ]
    def __init__(self, name, bind, request_only = False, reset = None, reset_n = None, callback = None, event = None):
        self.request_only = request_only
        super().__init__(name = name, bind = bind, reset = reset,
                reset_n = reset_n, callback = callback, event = event)
    async def _monitor_recv(self):
        transaction = None
        while True:
            await RisingEdge(self.signals.clock)
            await ReadOnly()
            if self.signals.addr_ready.value and self.signals.addr_valid.value:
                if not self.request_only:
                    assert transaction is None, f"{self}: Receiving new request before sending response for last request"
                transaction = BusReadTransaction(
                    addr = int(self.signals.addr.value),
                )
                self.log.debug("Receiving read transaction request: %s", transaction)
                if self.request_only:
                    self._recv(transaction)
            if not self.request_only and transaction is not None and self.signals.data_ready.value and self.signals.data_valid.value:
                transaction = BusReadTransaction(
                    data = int(self.signals.data.value),
                    addr = transaction.addr,
                )
                self.log.debug("Receiving full read transaction: %s", transaction)
                self._recv(transaction)
                transaction = None

class ReadBusSourceDriver(BundleDriver):
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
        self.signals.addr_ready <= 1
    async def _driver_send(self, transaction: BusReadTransaction, sync: bool = True):
        self.log.debug("Responding read transaction: %s", transaction)
        if isinstance(transaction, BusReadTransaction):
            await wait_for_signal(self.signals.data_ready)
            await RisingEdge(self.signals.clock)
            self.signals.data_valid <= 1
            self.signals.data <= transaction.data
            await RisingEdge(self.signals.clock)
            self.signals.data_valid <= 0
        elif transaction == "deassert_ready":
            await NextTimeStep()
            self.signals.addr_ready <= 0
