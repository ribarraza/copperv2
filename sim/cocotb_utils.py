from collections import namedtuple
import subprocess

import cocotb
from cocotb.log import SimLog
from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep, FallingEdge
from cocotb.types import Logic
from cocotb.clock import Clock

import typing
import dataclasses

class Bfm:
    Signals = None
    def __init__(self,entity=None,signals=None):
        self.log = SimLog(f"bfm.{type(self).__qualname__}")
        actual_signals = {}
        for field in dataclasses.fields(self.Signals):
            if signals is None:
                handle = field.name
            else:
                handle = getattr(signals,field.name,None)
            if isinstance(handle,str):
                handle = getattr(entity,handle,None)
            if handle is None:
                if field.default is None:
                    continue
                else:
                    raise ValueError(f"Signal not found {handle}")
            actual_signals[field.name] = handle
        self.bus = self.Signals(**actual_signals)
    @staticmethod
    def make_signals(name,args,optional=()):
        def contains(self,other):
            return other in [i.name for i in dataclasses.fields(self) if getattr(self,i.name) is not None]
        fields = []
        fields.extend(args)
        fields.extend([(key,typing.Any,dataclasses.field(default=None)) for key in optional])
        return dataclasses.make_dataclass(name,fields,namespace={"__contains__":contains})
    async def wait_for_signal(self,signal):
        await ReadOnly()
        while Logic(signal.value.binstr) != Logic(1):
            await RisingEdge(signal)
            await ReadOnly()
        await NextTimeStep()
    async def wait_for_nsignal(self,signal):
        await ReadOnly()
        while Logic(signal.value.binstr) != Logic(0):
            await FallingEdge(signal)
            await ReadOnly()
        await NextTimeStep()

class SimpleBfm(Bfm):
    def __init__(self,clock,reset=None,reset_n=None,entity=None,signals=None,period=10,period_unit="ns"):
        self.clock = clock
        self._reset = reset
        self._reset_n = reset_n
        self.period = period
        self.period_unit = period_unit
        super().__init__(entity=entity,signals=signals)
    @property
    def in_reset(self):
        """Boolean flag showing whether the bus is in reset state or not."""
        if self._reset is not None:
            return bool(self._reset.value.integer)
        if self._reset_n is not None:
            return not bool(self._reset_n.value.integer)
        return False
    def start_clock(self):
        cocotb.start_soon(Clock(self.clock,self.period,self.period_unit).start())
    async def reset(self):
        if self._reset is not None:
            await RisingEdge(self.clock)
            self._reset.value = 1
            await RisingEdge(self.clock)
            self._reset.value = 0
        if self._reset_n is not None:
            await RisingEdge(self.clock)
            self._reset_n.value = 0
            await RisingEdge(self.clock)
            self._reset_n.value = 1

def anext(async_generator):
    return async_generator.__anext__()

def get_top_module(name):
    return cocotb.handle.SimHandle(cocotb.simulator.get_root_handle(name))

def to_verilog_string(string):
    return int.from_bytes(string.encode("utf-8"),byteorder='big')

def from_array(data,addr):
    buf = []
    for i in range(4):
        value = 0
        if addr+i in data:
            value = data[addr+i]
        buf.append(value)
    return int.from_bytes(buf,byteorder='little')

def to_bytes(data):
    return (data).to_bytes(length=4,byteorder='little')

def run(*args,**kwargs):
    log = SimLog("cocotb")
    log.debug(f"run: {args}")
    r = subprocess.run(*args,shell=True,encoding='utf-8',capture_output=True,**kwargs)
    if r.returncode != 0:
        log.error(f"run stdout: {r.stdout}")
        log.error(f"run stderr: {r.stderr}")
        raise ChildProcessError(f"Error during command execution: {args}")
    return r