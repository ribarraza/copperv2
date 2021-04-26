import dataclasses

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly, ClockCycles
from cocotb_bus.monitors import BusMonitor

@dataclasses.dataclass
class Cuv2ReadTransaction:
    data: int = 0
    addr: int = 0

class Cuv2ReadBusMonitor(BusMonitor):
    _signals = [
        "addr_ready",
        "addr_valid",
        "addr_bits",
        "data_ready",
        "data_valid",
        "data_bits",
    ]
    async def _monitor_recv(self):
        read_transaction = Cuv2ReadTransaction()
        while True:
            await RisingEdge(self.clock)
            await ReadOnly()
            if self.bus.addr_ready.value and self.bus.addr_valid.value:
                read_transaction.addr = int(self.bus.addr_bits.value)
            if self.bus.data_ready.value and self.bus.data_valid.value:
                read_transaction.data = int(self.bus.data_bits.value)
                self._recv(read_transaction)

@cocotb.test()
async def basic_test(dut):
    dut._log.info("Running test...")
    cocotb.fork(Clock(dut.clock,10,units='ns').start())

    dut.reset <= 0;
    await ClockCycles(dut.clock,20)
    dut.reset <= 1;
    await RisingEdge(dut.clock)

    ir_bus = Cuv2ReadBusMonitor(dut, "bus_ir", dut.clock)

    dut.bus_ir_data_valid <= 1;
    dut.bus_ir_data_bits <= 123;

    for i in range(10):
        dut._log.info(f"Loop {i}")
        await RisingEdge(dut.clock)

    dut._log.info("Running test...done")
