from types import SimpleNamespace

import cocotb
from cocotb_bus.monitors import BusMonitor, Monitor
from cocotb_bus.drivers import BusDriver, Driver
from cocotb.log import SimLog

class Bus2(SimpleNamespace):
    def __contains__(self, signal):
        return signal in self.__dict__

class ReusableBus:
    """Abstract class providing common functionality for bus agents with enhanced re usability."""
    _signals = []
    _optional_signals = []
    def __init__(self, name, bind):
        self.name = name
        self.bus = Bus2(**self.validate_map(bind))
        self.log = SimLog(f"cocotb.{self}")
    def validate_map(self, _map):
        for virtual_signal in self._signals:
            if not virtual_signal in _map.keys():
                raise ValueError(f'Missing signal "{virtual_signal}"')
        for actual_signal in _map.keys():
            if not actual_signal in self._signals and not actual_signal in self._optional_signals:
                raise ValueError(f'Cannot bind "{actual_signal}"')
        return dict(_map)

class BusMonitor2(ReusableBus,BusMonitor):
    """Wrapper providing common functionality for monitoring buses with enhanced re usability."""
    def __init__(self, name, bind, reset = None, reset_n = None, callback = None, event = None):
        self._reset = reset
        self._reset_n = reset_n
        ReusableBus.__init__(self, name=name, bind=bind)
        Monitor.__init__(self, callback=callback, event=event)

class BusDriver2(ReusableBus,BusDriver):
    """Wrapper providing common functionality for driving buses with enhanced re usability."""
    def __init__(self, name, bind):
        ReusableBus.__init__(self, name=name, bind=bind)
        Driver.__init__(self)

def get_top_module(name):
    return cocotb.handle.SimHandle(cocotb.simulator.get_root_handle(name))

def verilog_string(string):
    return int.from_bytes(string.encode("utf-8"),byteorder='big')

def get_test_name():
    return cocotb.regression_manager._test.__name__ # pylint: disable=protected-access
