import dataclasses
import typing

from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep, Event, First
from cocotb_bus.monitors import Monitor
from cocotb.log import SimLog

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

@dataclasses.dataclass
class ChannelTransaction:
    request: typing.Any
    response: typing.Any = None

class HalfChannelMonitor(Monitor):
    def __init__(self,name,clock,ready,valid,payload,callback=None,event=None):
        self.name = name
        self.clock = clock
        self.ready = ready
        self.valid = valid
        self.payload = payload
        super().__init__(callback=callback,event=event)
        self.log = SimLog(f"cocotb.{self.name}")
    async def _monitor_recv(self):
        while True:
            await RisingEdge(self.clock)
            await ReadOnly()
            if self.ready.value and self.valid.value:
                if isinstance(self.payload, list):
                    payload_value = [int(p.value) for p in self.payload]
                elif isinstance(self.payload, dict):
                    payload_value = {k:int(p.value) for k,p in self.payload.items()}
                else:
                    payload_value = int(self.payload.value)
                self.log.debug(f"Half channel fire: {payload_value}")
                self._recv(payload_value)

class FullChannelMonitor(Monitor):
    def __init__(self,name,clock,req_ready,req_valid,req_payload,resp_ready,
            resp_valid,resp_payload,request_only=False,callback=None,event=None):
        self.name = name
        self.clock = clock
        self.req_ready = req_ready
        self.req_valid = req_valid
        self.req_payload = req_payload
        self.resp_ready = resp_ready
        self.resp_valid = resp_valid
        self.resp_payload = resp_payload
        self.request_only = request_only
        self.resp_event = Event()
        self.req_event = Event()
        super().__init__(callback=callback,event=event)
        self.req_channel = HalfChannelMonitor(self.name+'_hreq',
            clock = self.clock,
            ready = self.req_ready,
            valid = self.req_valid,
            payload = self.req_payload,
            event=self.req_event
        )
        if not self.request_only:
            self.resp_channel = HalfChannelMonitor(self.name+'_hresp',
                clock = self.clock,
                ready = self.resp_ready,
                valid = self.resp_valid,
                payload = self.resp_payload,
                event=self.resp_event
            )
        self.log = SimLog(f"cocotb.{self.name}")
    async def _monitor_recv(self):
        transaction = None
        while True:
            await First(self.req_event.wait(), self.resp_event.wait())
            if self.req_event.is_set():
                if not self.request_only:
                    assert transaction is None, f"{self}: Receiving new request before sending response for last request"
                transaction = ChannelTransaction(
                    request = self.req_event.data,
                )
                if self.request_only:
                    self.log.debug("Receiving request transaction: %s", transaction)
                    self._recv(transaction)
                else:
                    self.log.debug("Receiving half transaction: %s", transaction)
                self.req_event.clear()
            if transaction is not None and self.resp_event.is_set():
                transaction = ChannelTransaction(
                    response = self.resp_event.data,
                    request = transaction.request,
                )
                self.log.debug("Receiving full transaction: %s", transaction)
                self._recv(transaction)
                transaction = None
                self.resp_event.clear()

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
        self.read_event = Event()
        super().__init__(name=name,bind=bind,reset=reset,reset_n=reset_n,
                callback=callback,event=event)
        self.read_channel = FullChannelMonitor(self.name+'_mon',
            clock = self.signals.clock,
            req_ready = self.signals.addr_ready,
            req_valid = self.signals.addr_valid,
            req_payload = self.signals.addr,
            resp_ready = self.signals.data_ready,
            resp_valid = self.signals.data_valid,
            resp_payload = self.signals.data,
            request_only=request_only,
            event=self.read_event
        )
    async def _monitor_recv(self):
        while True:
            await self.read_event.wait()
            read_transaction = self.read_event.data
            transaction = BusReadTransaction(addr=read_transaction.request)
            if not self.request_only:
                transaction.data=read_transaction.response
            self._recv(transaction)
            self.read_event.clear()

class WriteBusMonitor(BundleMonitor):
    _signals = [
        "clock",
        "req_ready",
        "req_valid",
        "req_data",
        "req_addr",
        "req_strobe",
        "resp_ready",
        "resp_valid",
        "resp",
    ]
    def __init__(self, name, bind, request_only = False, reset = None, reset_n = None, callback = None, event = None):
        self.request_only = request_only
        self.write_event = Event()
        super().__init__(name=name,bind=bind,reset=reset,reset_n=reset_n,
                callback=callback,event=event)
        self.write_channel = FullChannelMonitor(self.name+'_mon',
            clock = self.signals.clock,
            req_ready = self.signals.req_ready,
            req_valid = self.signals.req_valid,
            req_payload = dict(data=self.signals.req_data,addr=self.signals.req_addr,strobe=self.signals.req_strobe),
            resp_ready = self.signals.resp_ready,
            resp_valid = self.signals.resp_valid,
            resp_payload = self.signals.resp,
            request_only=request_only,
            event=self.write_event
        )
    async def _monitor_recv(self):
        while True:
            await self.write_event.wait()
            write_transaction = self.write_event.data
            transaction = BusWriteTransaction(
                data=write_transaction.request['data'],
                addr=write_transaction.request['addr'],
                strobe=write_transaction.request['strobe'],
            )
            if not self.request_only:
                transaction.response=write_transaction.response
            self._recv(transaction)
            self.write_event.clear()

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

class WriteBusSourceDriver(BundleDriver):
    _signals = [
        "clock",
        "req_ready",
        "req_valid",
        "req_data",
        "req_addr",
        "req_strobe",
        "resp_ready",
        "resp_valid",
        "resp",
    ]
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.signals.req_ready <= 1
    async def _driver_send(self, transaction: BusWriteTransaction, sync: bool = True):
        self.log.debug("Responding read transaction: %s", transaction)
        if isinstance(transaction, BusWriteTransaction):
            await wait_for_signal(self.signals.req_ready)
            await RisingEdge(self.signals.clock)
            self.signals.resp_valid <= 1
            self.signals.resp <= transaction.response
            await RisingEdge(self.signals.clock)
            self.signals.resp_valid <= 0
        elif transaction == "deassert_ready":
            await NextTimeStep()
            self.signals.req_ready <= 0

