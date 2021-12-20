from cocotb_utils import SimpleBfm
from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep, ClockCycles
from cocotb.types import Logic

class WishboneBfm(SimpleBfm):
    Signals = SimpleBfm.make_signals("WishboneBfm",[
        "adr", "datwr", "datrd",
        "we", "cyc", "stb", "ack",
    ])
    def __init__(self, clock, entity = None, signals = None, reset=None, reset_n=None, period=10, period_unit="ns"):
        super().__init__(clock, signals=signals, entity=entity, reset=reset, reset_n=reset_n, period=period, period_unit=period_unit)
    def init_source(self):
        self.bus.cyc.setimmediatevalue(0)
        self.bus.stb.setimmediatevalue(0)
        self.bus.we.setimmediatevalue(0)
        self.bus.adr.setimmediatevalue(0)
        self.bus.datwr.setimmediatevalue(0)
    def init_sink(self):
        self.bus.ack.setimmediatevalue(0)
        self.bus.datrd.setimmediatevalue(0)
    async def read(self,addr):
        await RisingEdge(self.clock)
        self.bus.cyc.value = 1
        self.bus.stb.value = 1
        self.bus.adr.value = addr
        self.bus.we.value = 0
        while True:
            await RisingEdge(self.clock)
            await ReadOnly()
            if Logic(self.bus.ack.value.binstr) == Logic(1):
                return dict(data=int(self.bus.datrd.value),ack=True)
    async def write(self,data,addr):
        await RisingEdge(self.clock)
        self.bus.cyc.value = 1
        self.bus.stb.value = 1
        self.bus.datwr.value = data
        self.bus.adr.value = addr
        self.bus.we.value = 1
        while True:
            await RisingEdge(self.clock)
            await ReadOnly()
            if Logic(self.bus.ack.value.binstr) == Logic(1):
                return dict(ack=True)
    async def receive(self):
        while True:
            await RisingEdge(self.clock)
            await ReadOnly()
            self.log.debug(f"Receive heartbeat {self.bus.cyc.value=} {self.bus.stb.value=}")
            if self.in_reset:
                self.log.debug(f"WB receive in_reset true, continue...")
                continue
            if Logic(self.bus.cyc.value.binstr) == Logic(1) and Logic(self.bus.stb.value.binstr) == Logic(1):
                self.log.debug("Enter if!")
                received = dict(addr=int(self.bus.adr.value))
                if Logic(self.bus.we.value.binstr) == Logic(1):
                    received['data'] = int(self.bus.datwr.value)
                self.log.debug(f"Received {received}")
                yield received
    async def reply(self,data=None):
        await RisingEdge(self.clock)
        self.bus.ack.value = 1
        if Logic(self.bus.we.value.binstr) == Logic(0):
            self.bus.datrd.value = data

