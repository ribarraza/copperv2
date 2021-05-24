import dataclasses
import typing

import cocotb
from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep, Event, First
from cocotb_bus.monitors import Monitor
from cocotb_bus.drivers import Driver
from cocotb.log import SimLog
from cocotb.queue import Queue

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
class ReqRespTransaction:
    request: typing.Any
    response: typing.Any = None

class BusLowLevel:
    def __init__(self,log,clock,reset):
        self.log = log
        self.clock = clock
        self.reset = reset
    def in_reset(self):
        return not self.reset.value
    async def recv_half_channel(self,ready,valid,payload,queue):
        while(True):
            await RisingEdge(self.clock)
            await ReadOnly()
            if self.in_reset():
                continue
            if ready.value and valid.value:
                payload_value = self.get_payload_value(payload)
                self.log.debug(f"Half channel received: {payload_value}")
                queue.put_nowait(payload_value)
    async def send_half_channel(self,ready,valid,payload,transaction):
        await wait_for_signal(ready)
        await RisingEdge(self.clock)
        await NextTimeStep()
        valid <= 1
        self.put_payload_value(payload,transaction)
        await RisingEdge(self.clock)
        await NextTimeStep()
        valid <= 0
    async def drive_ready(self,ready,value):
        await RisingEdge(self.clock)
        await NextTimeStep()
        ready <= value
    @staticmethod
    def get_payload_value(payload):
        if isinstance(payload, list):
            payload_value = [int(p.value) for p in payload]
        elif isinstance(payload, dict):
            payload_value = {k:int(p.value) for k,p in payload.items()}
        else:
            payload_value = int(payload.value)
        return payload_value
    @staticmethod
    def put_payload_value(payload,transaction):
        if isinstance(transaction, dict):
            for k in payload.keys():
                payload[k] <= int(transaction[k])
        elif isinstance(transaction, list):
            for k in range(len(payload)):
                payload[k] <= int(transaction[k])
        else:
            payload <= int(transaction)

class FullChannelMonitor(Monitor):
    def __init__(self,name,clock,req_ready,req_valid,req_payload,resp_ready,
            resp_valid,resp_payload,reset,request_only=False,callback=None,event=None):
        self.name = name
        self.request_only = request_only
        self.clock = clock
        self.reset = reset
        self.req_ready = req_ready
        self.req_valid = req_valid
        self.req_payload = req_payload
        self.resp_ready = resp_ready
        self.resp_valid = resp_valid
        self.resp_payload = resp_payload
        self.log = SimLog(f"cocotb.{self.name}")
        self.low_level = BusLowLevel(
            clock = self.clock,
            reset = self.reset,
            log = self.log
        )
        super().__init__(callback=callback,event=event)
    async def _monitor_recv(self):
        req_queue = Queue()
        resp_queue = Queue()
        cocotb.fork(self.low_level.recv_half_channel(self.req_ready,self.req_valid,self.req_payload,req_queue))
        if not self.request_only:
            cocotb.fork(self.low_level.recv_half_channel(self.resp_ready,self.resp_valid,self.resp_payload,resp_queue))
        resp_transaction = None
        req_transaction = None
        while True:
            if not self.request_only:
                resp_transaction = await resp_queue.get()
            req_transaction = await req_queue.get()
            transaction = ReqRespTransaction(
                request = req_transaction,
                response = resp_transaction
            )
            translated = self.translate(transaction)
            self.log.debug("Receiving transaction: %s", translated)
            self._recv(translated)
    def translate(self, transaction):
        return transaction

class ReadBusMonitor(FullChannelMonitor):
    def __init__(self,name,clock,addr_ready,addr_valid,addr,data_ready,
            data_valid,data,reset,request_only=False,callback=None,event=None):
        self.request_only = request_only
        super().__init__(
            name = name,
            clock = clock,
            reset = reset,
            req_ready = addr_ready,
            req_valid = addr_valid,
            req_payload = addr,
            resp_ready = data_ready,
            resp_valid = data_valid,
            resp_payload = data,
            request_only=request_only,
            callback=callback,
            event=event
        )
    def translate(self, transaction):
        translated = BusReadTransaction(addr=transaction.request)
        if transaction.response is not None:
            translated.data = transaction.response
        return translated

class WriteBusMonitor(FullChannelMonitor):
    def __init__(self,name,clock,req_ready,req_valid,req_data,req_addr,
            req_strobe,resp_ready,resp_valid,resp,reset,request_only=False,callback=None,event=None):
        super().__init__(
            name = name,
            clock = clock,
            reset = reset,
            req_ready = req_ready,
            req_valid = req_valid,
            req_payload = dict(data=req_data,addr=req_addr,strobe=req_strobe),
            resp_ready = resp_ready,
            resp_valid = resp_valid,
            resp_payload = resp,
            request_only=request_only,
            callback=callback,
            event=event
        )
    def translate(self, transaction):
        translated = BusWriteTransaction(
            data=transaction.request['data'],
            addr=transaction.request['addr'],
            strobe=transaction.request['strobe'],
        )
        if transaction.response is not None:
            translated.response = transaction.response
        return translated

class SourceDriver(Driver):
    def __init__(self,name,clock,reset,req_ready,resp_valid,resp_ready,resp_payload):
        self.name = name
        self.log = SimLog(f"cocotb.{self.name}")
        self.clock = clock
        self.reset = reset
        self.req_ready = req_ready
        self.resp_valid = resp_valid
        self.resp_ready = resp_ready
        self.resp_payload = resp_payload
        self.low_level = BusLowLevel(
            clock = self.clock,
            reset = self.reset,
            log = self.log
        )
        super().__init__()
        self.append("assert_ready")
    async def _driver_send(self, transaction, sync: bool = True):
        translated = self.translate(transaction)
        if isinstance(translated, ReqRespTransaction):
            self.log.debug("Responding read translated: %s", transaction)
            await self.low_level.send_half_channel(self.resp_ready,self.resp_valid,self.resp_payload,translated.response)
        elif translated == "assert_ready":
            self.log.debug("Assert ready")
            await self.low_level.drive_ready(self.req_ready,True)
        elif translated == "deassert_ready":
            self.log.debug("Deassert ready")
            await self.low_level.drive_ready(self.req_ready,False)
    def translate(self,transaction):
        return transaction

class ReadBusSourceDriver(SourceDriver):
    def __init__(self,name,clock,addr_valid,addr_ready,addr,data_valid,data_ready,data,reset):
        super().__init__(
            name = name,
            clock = clock,
            reset = reset,
            req_ready=addr_ready,
            resp_ready=data_ready,
            resp_valid=data_valid,
            resp_payload=data
        )
    def translate(self,transaction):
        translated = transaction
        if isinstance(transaction,BusReadTransaction):
            translated = ReqRespTransaction(
                request = transaction.addr,
                response = transaction.data
            )
        return translated

class WriteBusSourceDriver(SourceDriver):
    def __init__(self,name,clock,req_ready,req_valid,req_data,req_addr,req_strobe,
            resp_ready,resp_valid,resp,reset):
        super().__init__(
            name=name,
            clock=clock,
            reset=reset,
            req_ready=req_ready,
            resp_ready=resp_ready,
            resp_valid=resp_valid,
            resp_payload=resp
        )
    def translate(self,transaction):
        translated = transaction
        if isinstance(transaction,BusWriteTransaction):
            translated = ReqRespTransaction(
                request = dict(data=transaction.data,addr=transaction.addr,strobe=transaction.strobe),
                response = transaction.response
            )
        return translated

