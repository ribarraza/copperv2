import dataclasses
import typing

import cocotb
from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep, ClockCycles
from cocotb.clock import Clock
from cocotb_bus.monitors import Monitor
from cocotb_bus.drivers import Driver
from cocotb.log import SimLog
from cocotb.queue import Queue

from cocotb_utils import wait_for_signal, anext

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
        new = cls(bus_name=bus_name,addr=request)
        if response is not None:
            new.data = response
        return new
    def to_reqresp(self):
        return dict(request = self.addr, response = self.data)
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
            new.response = response
        return new
    def to_reqresp(self):
        return dict(
                request = dict(data=self.data,addr=self.addr,strobe=self.strobe),
                response = self.response
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

class BusBfm:
    def __init__(self,
            clock,
            reset,
            ir_addr_valid,
            ir_addr_ready,
            ir_addr,
            ir_data_valid,
            ir_data_ready,
            ir_data,
            dr_addr_valid,
            dr_addr_ready,
            dr_addr,
            dr_data_valid,
            dr_data_ready,
            dr_data,
            dw_data_addr_ready,
            dw_data_addr_valid,
            dw_data,
            dw_addr,
            dw_strobe,
            dw_resp_ready,
            dw_resp_valid,
            dw_resp,
        ):
        self.clock = clock
        self.reset = reset
        self.ir_addr_valid = ir_addr_valid
        self.ir_addr_ready = ir_addr_ready
        self.ir_addr = ir_addr
        self.ir_data_valid = ir_data_valid
        self.ir_data_ready = ir_data_ready
        self.ir_data = ir_data
        self.dr_addr_valid = dr_addr_valid
        self.dr_addr_ready = dr_addr_ready
        self.dr_addr = dr_addr
        self.dr_data_valid = dr_data_valid
        self.dr_data_ready = dr_data_ready
        self.dr_data = dr_data
        self.dw_data_addr_ready = dw_data_addr_ready
        self.dw_data_addr_valid = dw_data_addr_valid
        self.dw_data = dw_data
        self.dw_addr = dw_addr
        self.dw_strobe = dw_strobe
        self.dw_resp_ready = dw_resp_ready
        self.dw_resp_valid = dw_resp_valid
        self.dw_resp = dw_resp
        self.name = "bus_bfm"
        self.log = SimLog(f"cocotb.{self.name}")
        self.queues = {}
    def recv_ir_req(self):
        return self.recv_channel(self.ir_addr_ready,self.ir_addr_valid,self.ir_addr)
    def recv_ir_resp(self): 
        return self.recv_channel(self.ir_data_ready,self.ir_data_valid,self.ir_data)
    def recv_ir_req(self):
        return self.recv_channel(self.ir_addr_ready,self.ir_addr_valid,self.ir_addr)
    def recv_ir_resp(self):
        return self.recv_channel(self.ir_data_ready,self.ir_data_valid,self.ir_data)
    def recv_dr_req(self):
        return self.recv_channel(self.dr_addr_ready,self.dr_addr_valid,self.dr_addr)
    def recv_dr_resp(self):
        return self.recv_channel(self.dr_data_ready,self.dr_data_valid,self.dr_data)
    def recv_dw_req(self):
        dw_payload = dict(addr=self.dw_addr,data=self.dw_data,strobe=self.dw_strobe)
        return self.recv_channel(self.dw_data_addr_ready,self.dw_data_addr_valid,dw_payload)
    def recv_dw_resp(self): 
        return self.recv_channel(self.dw_resp_ready,self.dw_resp_valid,self.dw_resp)
    def send_ir_resp(self,transaction):
        return self.send_channel(self.ir_data_ready,self.ir_data_valid,self.ir_data,transaction)
    def send_dr_resp(self,transaction):
        return self.send_channel(self.dr_data_ready,self.dr_data_valid,self.dr_data,transaction)
    def send_dw_resp(self,transaction):
        return self.send_channel(self.dw_resp_ready,self.dw_resp_valid,self.dw_resp,transaction)
    def drive_ir_ready(self,value):
        return self.drive_ready(self.ir_addr_ready,value)
    def drive_dr_ready(self,value):
        return self.drive_ready(self.dr_addr_ready,value)
    def drive_dw_ready(self,value):
        return self.drive_ready(self.dw_data_addr_ready,value)
    async def recv_channel(self,ready,valid,payload):
        while(True):
            await RisingEdge(self.clock)
            await ReadOnly()
            if self.in_reset():
                continue
            if ready.value and valid.value:
                if isinstance(payload, dict):
                    payload_value = {k:int(p.value) for k,p in payload.items()}
                else:
                    payload_value = int(payload.value)
                yield payload_value
    async def send_channel(self,ready,valid,payload,transaction):
        await wait_for_signal(ready)
        await RisingEdge(self.clock)
        await NextTimeStep()
        valid.value = 1
        payload.value = int(transaction)
        await RisingEdge(self.clock)
        await NextTimeStep()
        valid.value = 0
    async def drive_ready(self,ready,value):
        await RisingEdge(self.clock)
        await NextTimeStep()
        ready.value = value
    def in_reset(self):
        return not self.reset.value
    def start_clock(self):
        cocotb.fork(Clock(self.clock,10,units='ns').start())
    async def do_reset(self):
        self.reset.value = 0
        await ClockCycles(self.clock,4)
        self.reset.value = 1
        await RisingEdge(self.clock)

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
        self.append(self.transaction_type.default_transaction(name))
        self.append('assert_ready')
    async def _driver_send(self, transaction, sync: bool = True):
        if isinstance(transaction, self.transaction_type):
            transaction = self.transaction_type.to_reqresp(transaction)
            #self.log.debug("%s responding read transaction: %s", self.name, transaction)
            await self.bfm_send_resp(transaction['response'])
        elif transaction == "assert_ready":
            self.log.debug("Assert ready")
            await self.bfm_drive_ready(True)
        elif transaction == "deassert_ready":
            self.log.debug("Deassert ready")
            await self.bfm_drive_ready(False)
