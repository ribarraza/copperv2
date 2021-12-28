from pathlib import Path
from cocotb_test.simulator import run

root_dir = Path(__file__).resolve().parent.parent
sim_dir = root_dir/'sim'
chisel_dir = root_dir/'work/rtl'
rtl_v1_dir = root_dir/'src/main/resources/rtl_v1'

def timescale_fix(verilog):
    verilog = Path(verilog)
    lines = verilog.read_text()
    if not any(['timescale' in line for line in lines.splitlines()]):
        verilog.write_text("`timescale 1ns/1ps\n"+lines)
    return verilog

def test_wishbone_adapter():
    wb_adapter_rtl = timescale_fix(chisel_dir/"wb_adapter.v")
    run(
        toplevel = "WishboneAdapter",
        verilog_sources=[wb_adapter_rtl],        
        sim_build=f"work/sim/test_wishbone_adapter",
        testcase = "run_wishbone_adapter_test",
        module = "cocotb_tests",
        waves = True,
    )