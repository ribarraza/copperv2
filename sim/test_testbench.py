from pathlib import Path
from textwrap import dedent

import pytest
from cocotb_test.simulator import run

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

def test_ready_valid(ready_valid_rtl):
    run(
        verilog_sources=[ready_valid_rtl],
        toplevel="top",
        module="cocotb_testbench",
        waves = True,
        sim_build=work_dir/'test_ready_valid',
        testcase = "run_ready_valid_bfm_test",
    )

