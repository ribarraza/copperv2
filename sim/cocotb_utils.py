from collections import namedtuple
import subprocess

import cocotb
from cocotb.log import SimLog
from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep, FallingEdge
from cocotb.types import Logic
from cocotb.clock import Clock

class Bfm:
    def __init__(self,signals,reset=None,reset_n=None,period=10,period_unit="ns"):
        self.log = SimLog(f"cocotb.{type(self).__qualname__}")
        self._reset = reset
        self._reset_n = reset_n
        self.period = period
        self.period_unit = period_unit
        if self._reset is not None:
            signals['reset'] = self._reset
        if self._reset_n is not None:
            signals['reset_n'] = self._reset_n
        self._bus_class = namedtuple(type(self).__name__+"Bus",signals.keys())
        self.bus = self._bus_class(**signals)
    @property
    def in_reset(self):
        """Boolean flag showing whether the bus is in reset state or not."""
        if self._reset_n is not None:
            return not bool(self._reset_n.value.integer)
        if self._reset is not None:
            return bool(self._reset.value.integer)
        return False
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
    def start_clock(self):
        cocotb.start_soon(Clock(self.clock,self.period,self.period_unit).start())
    async def reset(self):
        if self._reset_n is not None:
            await RisingEdge(self.clock)
            self._reset_n.value = 0
            await RisingEdge(self.clock)
            self._reset_n.value = 1
        if self._reset is not None:
            await RisingEdge(self.clock)
            self._reset.value = 1
            await RisingEdge(self.clock)
            self._reset.value = 0

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