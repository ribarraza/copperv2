import os

import cocotb
from cocotb.triggers import Join, RisingEdge
from bus import ReadyValidBfm
from cocotb_utils import anext

if os.environ.get("VS_DEBUG",False):
    import debugpy
    debugpy.listen(4440)
    print("Info: debugpy waiting for client...")
    debugpy.wait_for_client()

@cocotb.test()
async def run_ready_valid_bfm_test(dut):
    """ ready/valid BFM test """
    reference = 123
    signals = dict(ready = dut.ready, valid = dut.valid)
    payload = dict(data = dut.data)
    bfm = ReadyValidBfm(signals,payload,dut.clock,dut.reset)
    bfm.start_clock()
    await bfm.reset()
    await bfm.drive_ready(1)
    send_task = cocotb.start_soon(bfm.send_payload(data=reference))
    received = await anext(bfm.recv_payload())
    assert received['data'] == reference
    await Join(send_task)
    await RisingEdge(dut.clock)

