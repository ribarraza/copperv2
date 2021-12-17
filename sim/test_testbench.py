import os
from pathlib import Path
from textwrap import dedent

import pytest
from cocotb_test.simulator import run

from cocotb_utils import Bfm

import cocotb
from cocotb.triggers import Join, RisingEdge
from bus import ReadyValidBfm
from cocotb_utils import anext

if os.environ.get("VS_DEBUG",False):
    import debugpy
    debugpy.listen(4440)
    print("Info: debugpy waiting for client...")
    debugpy.wait_for_client()

root_dir = Path(__file__).resolve().parent.parent
work_dir = root_dir/'work/sim/test_testbench'
work_dir.mkdir(exist_ok=True,parents=True)

@pytest.fixture
def ready_valid_rtl():
    rtl = work_dir/"ready_valid.v"
    rtl.write_text(dedent("""
    `timescale 1ns/1ps
    module top(
        input clock,
        input reset,
        input ready,
        output valid,
        output [7:0] data
    );
    initial #1000;
    endmodule
    """))
    print("Generated",rtl)
    return rtl

@pytest.fixture
def fake_signals():
    return Bfm.make_signals("FakeSignals",["a","b"],optional=["c"])

@cocotb.test()
async def run_ready_valid_bfm_test(dut):
    """ ready/valid BFM test """
    reference = 123
    signals = ReadyValidBfm.Signals(ready = dut.ready, valid = dut.valid)
    payload = dict(data = dut.data)
    bfm = ReadyValidBfm(dut.clock,signals,payload)
    bfm.start_clock()
    await bfm.reset()
    await bfm.drive_ready(1)
    send_task = cocotb.start_soon(bfm.send_payload(data=reference))
    received = await anext(bfm.recv_payload())
    assert received['data'] == reference
    await Join(send_task)
    await RisingEdge(dut.clock)

def test_ready_valid(ready_valid_rtl):
    run(
        verilog_sources=[ready_valid_rtl],
        toplevel="top",
        module="test_testbench",
        waves = True,
        sim_build=work_dir/'test_ready_valid',
        testcase = "run_ready_valid_bfm_test",
    )

def test_signals_dataclass_required(fake_signals):
    foo = fake_signals(a=1,b=2)
    assert foo.a == 1
    assert foo.b == 2
    assert foo.c is None
    assert 'a' in foo
    assert 'b' in foo
    assert not 'c' in foo

def test_signals_dataclass_optional(fake_signals):
    foo = fake_signals(a=1,b=2,c=3)
    assert foo.a == 1
    assert foo.b == 2
    assert foo.c == 3

def test_signals_dataclass_unexpected(fake_signals):
    with pytest.raises(TypeError):
        foo = fake_signals(a=1,b=2,d=4)

def test_signals_dataclass_missing(fake_signals):
    with pytest.raises(TypeError):
        foo = fake_signals(a=1)
