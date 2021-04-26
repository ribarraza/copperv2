import dataclasses
import logging

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly, ClockCycles
from cocotb_bus.monitors import BusMonitor
from cocotb_bus.drivers import BusDriver

@dataclasses.dataclass
class ReadTransaction:
    data: int = 0
    addr: int = 0

@dataclasses.dataclass
class ReadReqTransaction:
    addr: int = 0

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
                assert transaction is None, f"{self.__class__.__name__}: Receiving new request before sending response for last request"
                transaction = ReadReqTransaction(
                    addr = int(self.bus.addr_bits.value),
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
        await self._wait_for_signal(self.bus.data_ready)
        await RisingEdge(self.clock)
        self.bus.data_valid <= 1
        self.bus.data_bits <= transaction.data
        await RisingEdge(self.clock)
        self.bus.data_valid <= 0

def instruction_read_callback(driver: BusDriver):
    def get_response(transaction) -> ReadTransaction:
        if isinstance(transaction,ReadReqTransaction):
            driver.append(ReadTransaction(
                data = transaction.addr + 1,
                addr = transaction.addr,
            ))
    return get_response

@cocotb.test()
async def basic_test(dut):
    dut._log.setLevel(logging.DEBUG)
    dut._log.info("Running test...")

    cocotb.fork(Clock(dut.clock,10,units='ns').start())
    bus_ir_driver = ReadBusSourceDriver(dut, "bus_ir", dut.clock)
    bus_ir_monitor = ReadBusMonitor(dut, "bus_ir", dut.clock,
        callback=instruction_read_callback(bus_ir_driver))

    dut.reset <= 0;
    await ClockCycles(dut.clock,10)
    dut.reset <= 1;
    await RisingEdge(dut.clock)

    for i in range(10):
        dut._log.info(f"Loop {i}")
        await RisingEdge(dut.clock)

    dut._log.info("Running test...done")
