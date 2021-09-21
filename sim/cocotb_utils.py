from types import SimpleNamespace

import cocotb
from cocotb_bus.monitors import BusMonitor, Monitor
from cocotb_bus.drivers import BusDriver, Driver
from cocotb.log import SimLog
from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep, FallingEdge

def anext(async_generator):
    return async_generator.__anext__()

def get_top_module(name):
    return cocotb.handle.SimHandle(cocotb.simulator.get_root_handle(name))

def verilog_string(string):
    return int.from_bytes(string.encode("utf-8"),byteorder='big')

def get_test_name():
    return cocotb.regression_manager._test.__name__ # pylint: disable=protected-access

@cocotb.coroutine
async def wait_for_signal(signal):
    await ReadOnly()
    while signal.value.integer != 1:
        await RisingEdge(signal)
        await ReadOnly()
    await NextTimeStep()

@cocotb.coroutine
async def wait_for_nsignal(signal):
    await ReadOnly()
    while signal.value.integer != 0:
        await FallingEdge(signal)
        await ReadOnly()
    await NextTimeStep()

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

