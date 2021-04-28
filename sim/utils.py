import cocotb

def verilog_string(x):
    return int.from_bytes(x.encode("utf-8"),byteorder='big')
def get_test_name():
    return cocotb.regression_manager._test.__name__
