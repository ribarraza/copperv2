import dataclasses
import typing

import cocotb
from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep, ClockCycles
from cocotb_bus.monitors import Monitor
from cocotb_bus.drivers import Driver
from cocotb.log import SimLog

from cocotb_utils import Bfm, anext

@dataclasses.dataclass
class BusReadTransaction:
    bus_name: str
    data: int = None
    addr: int = None
    @classmethod
    def from_string(cls, string):
        addr, data = string.split()
        return cls(
            bus_name=None,
            data=int(data,0),
            addr=int(addr,0))
    @classmethod
    def from_reqresp(cls, bus_name, request, response = None):
        new = cls(bus_name=bus_name,addr=request['addr'])
        if response is not None:
            new.data = response['data']
        return new
    def to_reqresp(self):
        return dict(request = self.addr, response = dict(data=self.data))
    @classmethod
    def default_transaction(cls,bus_name):
        return cls(bus_name=bus_name,addr=0,data=0)
    def __eq__(self, other) -> bool:
        return self.addr == other.addr and self.data == other.data
    def __str__(self):
        data = f'0x{self.data:X}' if self.data is not None else None
        addr = f'0x{self.addr:X}' if self.addr is not None else None
        return f'{self.__class__.__name__}(bus_name={self.bus_name}, addr={addr}, data={data})'


@dataclasses.dataclass
class BusWriteTransaction:
    bus_name: str
    data: int = None
    addr: int = None
    strobe: int = None
    response: int = None
    @classmethod
    def from_string(cls, string):
        addr, data, strobe, response = string.split()
        return cls(
            bus_name=None,
            data=int(data,0),
            addr=int(addr,0),
            strobe=int(strobe,0),
            response=int(response,0))
    @classmethod
    def from_reqresp(cls, bus_name, request, response = None):
        new = cls(
            bus_name = bus_name,
            data = request['data'],
            addr = request['addr'],
            strobe = request['strobe'])
        if response is not None:
            new.response = response['resp']
        return new
    def to_reqresp(self):
        return dict(
                request = dict(data=self.data,addr=self.addr,strobe=self.strobe),
                response = dict(resp=self.response)
            )
    @classmethod
    def default_transaction(cls,bus_name):
        return cls(bus_name=bus_name,addr=0,data=0,strobe=0,response=0)
    def __eq__(self, other) -> bool:
        return self.addr == other.addr and self.data == other.data \
            and self.strobe == other.strobe and self.response == other.response
    def __str__(self):
        data = f'0x{self.data:X}' if self.data is not None else None
        addr = f'0x{self.addr:X}' if self.addr is not None else None
        strobe = f'0x{self.strobe:X}' if self.strobe is not None else None
        response = f'0x{self.response:X}' if self.response is not None else None
        return f'{self.__class__.__name__}(bus_name={self.bus_name}, addr={addr}, data={data}, strobe={strobe}, response={response})'

class ReadyValidBfm(Bfm):
    """ bus: [ready,valid]
        payload: {...}"""
    def __init__(self,signals,payload,clock,reset_n,init_valid=False):
        self.clock = clock
        self.payload = payload
        Bfm.__init__(self,signals,reset_n = reset_n)
        if init_valid:
            self.bus.valid.setimmediatevalue(0)
    async def recv_payload(self):
        while(True):
            await RisingEdge(self.clock)
            await ReadOnly()
            if self.in_reset:
                continue
            if self.bus.ready.value and self.bus.valid.value:
                actual_payload = {k:int(p.value) for k,p in self.payload.items()}
                yield actual_payload
    async def send_payload(self,**kwargs):
        self.log.debug(f"Send payload {self.bus.ready.name} {kwargs}")
        await self.wait_for_signal(self.bus.ready)
        await RisingEdge(self.clock)
        self.bus.valid.value = 1
        for name,payload_signal in self.payload.items():
            payload_signal.value = int(kwargs[name])
        await RisingEdge(self.clock)
        self.bus.valid.value = 0
    async def drive_ready(self,value):
        self.log.debug(f"Drive ready {self.bus.ready.name} {value}")
        await RisingEdge(self.clock)
        self.bus.ready.value = value
    async def drive_valid(self,value):
        self.log.debug(f"Drive valid {self.bus.valid.name} {value}")
        await RisingEdge(self.clock)
        self.bus.valid.value = value

class ChannelBfm(Bfm):
    """ bus: [req_ready,req_valid,resp_ready,resp_valid]
        resp_payload: {...}
        req_payload: {...}"""
    def __init__(self,signals,req_payload,resp_payload,clock,reset_n):
        self.clock = clock
        Bfm.__init__(self,signals,reset_n = reset_n)
        self.req_bfm = ReadyValidBfm(
            signals=dict(
                ready = self.bus.req_ready,
                valid = self.bus.req_valid,
            ),
            payload=req_payload,
            clock = self.clock,
            reset_n = self.bus.reset_n,
        )
        self.resp_bfm = ReadyValidBfm(
            signals=dict(
                ready = self.bus.resp_ready,
                valid = self.bus.resp_valid,
            ),
            payload=resp_payload,
            clock = self.clock,
            reset_n = self.bus.reset_n,
            init_valid = True
        )
    async def send_response(self,**kwargs):
        await self.resp_bfm.send_payload(**kwargs)
    async def drive_ready(self,value):
        await self.req_bfm.drive_ready(value)
    def get_request(self):
        return self.req_bfm.recv_payload()
    def get_response(self):
        return self.resp_bfm.recv_payload()

class BusMonitor(Monitor):
    def __init__(self,name,transaction_type,bfm_recv_req,bfm_recv_resp=None,callback=None,event=None,bus_name=None):
        self.bus_name = bus_name
        if self.bus_name is None:
            self.bus_name = name
        self.name = name
        self.log = SimLog(f"cocotb.{self.name}")
        self.bfm_recv_req = bfm_recv_req
        self.bfm_recv_resp = bfm_recv_resp
        self.transaction_type = transaction_type
        super().__init__(callback=callback,event=event)
    async def _monitor_recv(self):
        req_transaction = None
        resp_transaction = None
        while True:
            req_transaction = await anext(self.bfm_recv_req())
            if self.bfm_recv_resp is not None:
                resp_transaction = await anext(self.bfm_recv_resp())
            transaction = self.transaction_type.from_reqresp(
                bus_name = self.bus_name,
                request = req_transaction,
                response = resp_transaction
            )
            _type = "req" if self.bfm_recv_resp is None else "full"
            if _type == "full":
                self.log.debug(f"Receiving transaction: %s",transaction)
            self._recv(transaction)

class BusSourceDriver(Driver):
    def __init__(self,name,transaction_type,bfm_send_resp,bfm_drive_ready):
        self.name = name
        self.log = SimLog(f"cocotb.{self.name}")
        self.bfm_send_resp = bfm_send_resp
        self.bfm_drive_ready = bfm_drive_ready
        self.transaction_type = transaction_type
        super().__init__()
        ## reset
        self.append('assert_ready')
    async def _driver_send(self, transaction, sync: bool = True):
        if isinstance(transaction, self.transaction_type):
            transaction = self.transaction_type.to_reqresp(transaction)
            self.log.debug("%s responding read transaction: %s", self.name, transaction)
            await self.bfm_send_resp(**transaction['response'])
        elif transaction == "assert_ready":
            await self.bfm_drive_ready(True)
        elif transaction == "deassert_ready":
            await self.bfm_drive_ready(False)
