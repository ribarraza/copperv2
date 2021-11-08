import logging
import dataclasses
import os
import toml
from pathlib import Path

import cocotb
from cocotb.triggers import with_timeout, Timer
from cocotb.log import SimLog
from cocotb.regression import TestFactory
from cocotb_test.simulator import run
import pytest

from testbench import Testbench
from riscv_utils import compile_instructions, parse_data_memory, compile_riscv_test

if os.environ.get("VS_DEBUG",False):
    import debugpy
    debugpy.listen(4440)
    print("Info: debugpy waiting for client...")
    debugpy.wait_for_client()

root_dir = Path(__file__).resolve().parent.parent
sim_dir = root_dir/'sim'
chisel_dir = root_dir/'work/rtl'
rtl_v1_dir = root_dir/'src/main/resources/rtl_v1'
toml_path = sim_dir/"tests/unit_tests.toml"
unit_tests = toml.loads(toml_path.read_text())
rv_asm_paths = list(sim_dir.glob('tests/isa/rv32ui/*.S'))

common_run_opts = dict(
    verilog_sources=[
        chisel_dir/"copperv2.v",
        rtl_v1_dir/"idecoder.v",
        rtl_v1_dir/"register_file.v",
    ],
    includes=[rtl_v1_dir/'include'],
    toplevel="copperv2",
    module="test_copperv2",
    waves = True,
)

T_ADDR = 0x80000000
O_ADDR = 0x80000004
TC_ADDR = 0x80000008
T_PASS = 0x01000001
T_FAIL = 0x02000001

@dataclasses.dataclass
class TestParameters:
    name: str
    instructions: list = dataclasses.field(default_factory=list)
    expected_regfile_read: list = dataclasses.field(default_factory=list)
    expected_regfile_write: list = dataclasses.field(default_factory=list)
    expected_data_read: list = dataclasses.field(default_factory=list)
    expected_data_write: list = dataclasses.field(default_factory=list)
    data_memory: list = dataclasses.field(default_factory=list)
    def __repr__(self):
        p = '\n'.join([f"{k} = {repr(v)}" for k,v in dataclasses.asdict(self).items()])
        return '\n' + p

@cocotb.test(timeout_time=10,timeout_unit="us")
async def run_unit_test(dut):
    """ Copperv unit tests """
    test_name = os.environ['TEST_NAME']
    params = TestParameters(test_name,**unit_tests[test_name])
    SimLog("cocotb").setLevel(logging.DEBUG)

    instruction_memory = compile_instructions(params.instructions)
    data_memory = parse_data_memory(params.data_memory)
    tb = Testbench(dut,
        test_name,
        expected_data_read=params.expected_data_read,
        expected_data_write=params.expected_data_write,
        expected_regfile_read=params.expected_regfile_read,
        expected_regfile_write=params.expected_regfile_write,
        instruction_memory=instruction_memory,
        data_memory=data_memory)
    tb.bus_bfm.start_clock()
    await tb.bus_bfm.do_reset()
    await tb.finish()

@cocotb.test(timeout_time=100,timeout_unit="us")
async def run_riscv_test(dut):
    """ RISCV compliance tests """
    test_name = os.environ['TEST_NAME']
    asm_path = Path(os.environ['ASM_PATH'])
    SimLog("cocotb").setLevel(logging.DEBUG)

    instruction_memory, data_memory = compile_riscv_test(asm_path)
    tb = Testbench(dut,
        test_name,
        instruction_memory=instruction_memory,
        data_memory=data_memory,
        enable_self_checking=False,
        pass_fail_address = T_ADDR,
        pass_fail_values = {T_FAIL:False,T_PASS:True})

    tb.bus_bfm.start_clock()
    await tb.bus_bfm.do_reset()
    await tb.end_test.wait()

@pytest.mark.parametrize(
    "parameters", [pytest.param({"TEST_NAME":name},id=name) for name in unit_tests]
)
def test_unit(parameters):
    run(
        **common_run_opts,
        extra_env=parameters,
        sim_build=f"work/sim/unit_test_{parameters['TEST_NAME']}",
        testcase = "run_unit_test",
    )

@pytest.mark.parametrize(
    "parameters", [pytest.param({"TEST_NAME":path.stem,"ASM_PATH":str(path.resolve())},id=path.stem)
        for path in rv_asm_paths]
)
def test_riscv(parameters):
    run(
        **common_run_opts,
        extra_env=parameters,
        sim_build=f"work/sim/riscv_test_{parameters['TEST_NAME']}",
        testcase = "run_riscv_test",
    )

