import dataclasses
import typing

from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep, Event, First
from cocotb_bus.monitors import Monitor
from cocotb_bus.drivers import Driver
from cocotb.log import SimLog

from cocotb_utils import wait_for_signal, lex

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
class MonitorTransaction:
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
        self.request_only = request_only
        self.resp_event = Event()
        self.req_event = Event()
        super().__init__(callback=callback,event=event)
        self.req_channel = HalfChannelMonitor(self.name+'_hreq',
            clock = clock,
            ready = req_ready,
            valid = req_valid,
            payload = req_payload,
            event=self.req_event
        )
        if not self.request_only:
            self.resp_channel = HalfChannelMonitor(self.name+'_hresp',
                clock = clock,
                ready = resp_ready,
                valid = resp_valid,
                payload = resp_payload,
                event=self.resp_event
            )
        self.log = SimLog(f"cocotb.{self.name}")
    async def _monitor_recv(self):
        transaction = None
        while True:
            await First(self.req_event.wait(), self.resp_event.wait())
            if self.req_event.is_set():
                if not self.request_only:
                    assert transaction is None, f"{self}: Receiving new request before sending response to previous request"
                transaction = MonitorTransaction(
                    request = self.req_event.data,
                )
                if self.request_only:
                    self.log.debug("Receiving request transaction: %s", transaction)
                    self._recv(transaction)
                else:
                    self.log.debug("Receiving half transaction: %s", transaction)
                self.req_event.clear()
            if transaction is not None and self.resp_event.is_set():
                transaction = MonitorTransaction(
                    response = self.resp_event.data,
                    request = transaction.request,
                )
                self.log.debug("Receiving full transaction: %s", transaction)
                self._recv(transaction)
                transaction = None
                self.resp_event.clear()

class ReadBusMonitor(Monitor):
    def __init__(self,name,clock,addr_ready,addr_valid,addr,data_ready,
            data_valid,data,reset,request_only=False,callback=None,event=None):
        self.name = name
        self.log = SimLog(f"cocotb.{self.name}")
        self.request_only = request_only
        self.read_event = Event()
        self.read_channel = FullChannelMonitor(self.name+'_mon',
            clock = clock,
            req_ready = addr_ready,
            req_valid = addr_valid,
            req_payload = addr,
            resp_ready = data_ready,
            resp_valid = data_valid,
            resp_payload = data,
            request_only=request_only,
            event=self.read_event
        )
        super().__init__(callback=callback,event=event)
    async def _monitor_recv(self):
        while True:
            await self.read_event.wait()
            read_transaction = self.read_event.data
            transaction = BusReadTransaction(addr=read_transaction.request)
            if not self.request_only:
                transaction.data=read_transaction.response
            self._recv(transaction)
            self.read_event.clear()

class WriteBusMonitor(Monitor):
    def __init__(self,name,clock,req_ready,req_valid,req_data,req_addr,
            req_strobe,resp_ready,resp_valid,resp,reset,request_only=False,callback=None,event=None):
        self.name = name
        self.log = SimLog(f"cocotb.{self.name}")
        self.request_only = request_only
        self.write_event = Event()
        self.write_channel = FullChannelMonitor(self.name+'_mon',
            clock = clock,
            req_ready = req_ready,
            req_valid = req_valid,
            req_payload = dict(data=req_data,addr=req_addr,strobe=req_strobe),
            resp_ready = resp_ready,
            resp_valid = resp_valid,
            resp_payload = resp,
            request_only=request_only,
            event=self.write_event
        )
        super().__init__(callback=callback,event=event)
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

class RespChannelDriver(Driver):
    def __init__(self,name,clock,ready,valid,payload):
        self.name = name
        self.log = SimLog(f"cocotb.{self.name}")
        self.clock = clock
        self.ready = ready
        self.valid = valid
        self.payload = payload
        super().__init__()
    async def _driver_send(self, transaction, sync: bool=True):
        await wait_for_signal(self.ready)
        await RisingEdge(self.clock)
        await NextTimeStep()
        self.valid <= 1
        if isinstance(transaction, dict):
            for k in self.payload.keys():
                self.payload[k] <= int(transaction[k])
        elif isinstance(transaction, list):
            for k in range(len(self.payload)):
                self.payload[k] <= int(transaction[k])
        else:
            self.payload <= int(transaction)
        await RisingEdge(self.clock)
        await NextTimeStep()
        self.valid <= 0

class ReqChannelDriver(Driver):
    def __init__(self,name,clock,ready):
        self.name = name
        self.log = SimLog(f"cocotb.{self.name}")
        self.clock = clock
        self.ready = ready
        super().__init__()
    async def _driver_send(self, transaction, sync: bool=True):
        await RisingEdge(self.clock)
        await NextTimeStep()
        self.ready <= bool(transaction)

class ReadBusSourceDriver(Driver):
    def __init__(self,name,clock,addr_valid,addr_ready,addr,data_valid,data_ready,data,reset):
        self.name = name
        self.log = SimLog(f"cocotb.{self.name}")
        self.req_driver = ReqChannelDriver(self.name+'.hreq',clock=clock,ready=addr_ready)
        self.resp_driver = RespChannelDriver(self.name+'.hresp',clock=clock,ready=data_ready,valid=data_valid,payload=data)
        self.req_driver.append(True)
        super().__init__()
    async def _driver_send(self, transaction: BusWriteTransaction, sync: bool = True):
        if isinstance(transaction, BusReadTransaction):
            self.log.debug("Responding read transaction: %s", transaction)
            self.resp_driver.append(transaction.data)
        elif transaction == "deassert_ready":
            self.req_driver.append(False)

class WriteBusSourceDriver(Driver):
    def __init__(self,name,clock,req_ready,req_valid,req_data,req_addr,req_strobe,
            resp_ready,resp_valid,resp,reset):
        self.name = name
        self.log = SimLog(f"cocotb.{self.name}")
        self.req_driver = ReqChannelDriver(self.name+'.hreq',clock=clock,ready=req_ready)
        self.resp_driver = RespChannelDriver(self.name+'.hresp',clock=clock,ready=resp_ready,valid=resp_valid,payload=resp)
        self.req_driver.append(True)
        super().__init__()
    async def _driver_send(self, transaction: BusWriteTransaction, sync: bool = True):
        if isinstance(transaction, BusWriteTransaction):
            self.log.debug("Responding read transaction: %s", transaction)
            self.resp_driver.append(transaction.response)
        elif transaction == "deassert_ready":
            self.req_driver.append(False)

