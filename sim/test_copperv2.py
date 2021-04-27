import dataclasses
import ctypes
import logging
import subprocess
from pathlib import Path
import re

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly, ClockCycles, NextTimeStep
from cocotb_bus.monitors import Monitor, BusMonitor
from cocotb_bus.drivers import BusDriver
from cocotb.log import SimLog
from cocotb_bus.scoreboard import Scoreboard

from elftools.elf.elffile import ELFFile

abi_map = {
    "zero":0,
    "ra":1,
    "sp":2,
    "gp":3,
    "tp":4,
    "t0":5,
    "t1":6,
    "t2":7,
    "s0":8,
    "s1":9,
    "a0":10,
    "a1":11,
    "a2":12,
    "a3":13,
    "a4":14,
    "a5":15,
    "a6":16,
    "a7":17,
    "s2":18,
    "s3":19,
    "s4":20,
    "s5":21,
    "s6":22,
    "s7":23,
    "s8":24,
    "s9":25,
    "s10":26,
    "s11":27,
    "t3":28,
    "t4":29,
    "t5":30,
    "t6":31,
}

@dataclasses.dataclass
class ReadTransaction:
    data: int = 0
    addr: int = 0
    type: str = "full"

@dataclasses.dataclass
class RegFileWriteTransaction:
    reg: int = 0
    data: int = 0
    @classmethod
    def from_string(cls, string):
        reg, value = re.split('\s+',string)
        return cls(abi_map[reg],int(value,0))

class ReadBusMonitor(BusMonitor):
    _signals = [
        "addr_ready",
        "addr_valid",
        "addr_bits",
        "data_ready",
        "data_valid",
        "data_bits",
    ]
    async def _monitor_recv(self):
        transaction = None
        while True:
            await RisingEdge(self.clock)
            await ReadOnly()
            if self.bus.addr_ready.value and self.bus.addr_valid.value:
                assert transaction is None, f"Receiving new request before sending response for last request"
                transaction = ReadTransaction(
                    addr = int(self.bus.addr_bits.value),
                    type = "request",
                )
                self.log.debug("Receiving read transaction request: %s", transaction)
                self._recv(transaction)
            if transaction is not None and self.bus.data_ready.value and self.bus.data_valid.value:
                transaction = ReadTransaction(
                    data = int(self.bus.data_bits.value),
                    addr = transaction.addr,
                )
                self.log.debug("Receiving full read transaction: %s", transaction)
                self._recv(transaction)
                transaction = None

class ReadBusSourceDriver(BusDriver):
    _signals = [
        "addr_ready",
        "data_valid",
        "data_ready",
        "data_bits",
    ]
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.bus.addr_ready <= 1
    async def _driver_send(self, transaction: ReadTransaction, sync: bool = True):
        self.log.debug("Responding read transaction: %s", transaction)
        if transaction.type == "full":
            await self._wait_for_signal(self.bus.data_ready)
            await RisingEdge(self.clock)
            self.bus.data_valid <= 1
            self.bus.data_bits <= transaction.data
            await RisingEdge(self.clock)
            self.bus.data_valid <= 0
        elif transaction.type == "deassert_ready":
            await NextTimeStep()
            self.bus.addr_ready <= 0

class RegFileWriteMonitor(Monitor):
    def __init__(self, dut, clock, callback=None, event=None):
        self.name = "regfile"
        self.log = SimLog("cocotb.%s.%s" % (dut._path, self.name))
        print(self.log)
        self.clock = clock
        regfile = dut.regfile
        self.rd_en = regfile.rd_en
        self.rd = regfile.rd
        self.rd_din = regfile.rd_din
        super().__init__(callback,event)
    async def _monitor_recv(self):
        while True:
            await RisingEdge(self.clock)
            await ReadOnly()
            if self.rd_en.value:
                transaction = RegFileWriteTransaction(
                    reg = int(self.rd.value),
                    data = int(self.rd_din.value),
                )
                self.log.debug("Receiving register file transaction: %s", transaction)
                self._recv(transaction)

def instruction_read_callback(driver: BusDriver, elf):
    def get_response(transaction):
        if transaction.type == "request":
            section_start = elf['.text']['addr']
            section_data = elf['.text']['data']
            section_size = len(section_data)
            driver_transaction = ReadTransaction(type="deassert_ready")
            if transaction.addr < section_start + section_size:
                assert section_start <= transaction.addr < section_start + section_size, "Reading invalid address"
                addr = transaction.addr - section_start
                driver_transaction = ReadTransaction(
                    data = int.from_bytes(section_data[addr:addr+4],byteorder='little'),
                    addr = transaction.addr,
                )
            driver.append(driver_transaction)
    return get_response

def verilog_string(x):
    return int.from_bytes(x.encode("utf-8"),byteorder='big')
def get_test_name():
    return cocotb.regression_manager._test.__name__

linker_script_content = """
OUTPUT_ARCH("riscv")
ENTRY(_start)

SECTIONS
{
	. = 0x00000000;
	.text.init : { *(.text.init) }
	. = ALIGN(0x1000);
	_end = .;
}
"""
linker_script = Path('linker.ld')
linker_script.write_text(linker_script_content)

@cocotb.test()
async def basic_test(tb_wrapper):
    tb_wrapper.test_name <= verilog_string(get_test_name())
    SimLog("cocotb").setLevel(logging.DEBUG)
    tb_wrapper._log.info("Running test...")
    dut = tb_wrapper.dut
    clock = dut.clk

    instructions = [
        ".global _start",
        "_start:",
        "lui t0, 1",
    ]
    expected_reg_file = [
        RegFileWriteTransaction.from_string("t0 0x1000"),
    ]

    test_s = Path(get_test_name()).with_suffix('.S')
    test_elf = Path(get_test_name()).with_suffix('.elf')
    test_s.write_text('\n'.join(instructions) + '\n')
    cmd = f"riscv64-unknown-elf-gcc -march=rv32i -mabi=ilp32 -Wl,-T,{linker_script},-Bstatic -nostartfiles -ffreestanding -g {test_s} -o {test_elf}"
    tb_wrapper._log.debug(f"gcc cmd: {cmd}")
    r = subprocess.run(cmd,shell=True,encoding='utf-8',capture_output=True)
    if r.returncode != 0:
        tb_wrapper._log.error(f"gcc stdout: {r.stdout}")
        tb_wrapper._log.error(f"gcc stderr: {r.stderr}")
        raise ChildProcessError(f"Failed test compile: {cmd}")
    file = test_elf.open('rb')
    elffile = ELFFile(file)
    elf = {}
    for spec in ['.text']:
        section = elffile.get_section_by_name(spec)
        elf[spec] = dict(
            addr = section['sh_addr'],
            data = section.data(),
        )
    tb_wrapper._log.debug(f"elf: {elf}")

    cocotb.fork(Clock(clock,10,units='ns').start())
    bus_ir_driver = ReadBusSourceDriver(tb_wrapper, "bus_ir", clock)
    bus_ir_monitor = ReadBusMonitor(tb_wrapper, "bus_ir", clock,
        callback=instruction_read_callback(bus_ir_driver, elf))
    regfile_monitor = RegFileWriteMonitor(dut, clock)
    scoreboard = Scoreboard(dut)
    scoreboard.add_interface(regfile_monitor, expected_reg_file)

    tb_wrapper.reset <= 0;
    await ClockCycles(clock,10)
    tb_wrapper.reset <= 1;
    await RisingEdge(clock)

    while len(expected_reg_file) > 0:
        await RisingEdge(clock)
    await ClockCycles(clock,20)

    tb_wrapper._log.info("Running test...done")

