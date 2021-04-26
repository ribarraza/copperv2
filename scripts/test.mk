# defaults
DUT_COPPERV1 ?= 1
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

ROOT = $(abspath ../..)

ifneq ($(DUT_COPPERV1),1)
	VERILOG_SOURCES += $(ROOT)/sim/tb_wrapper.v $(ROOT)/work/chisel/Copperv2.v
else
	VERILOG_SOURCES += $(ROOT)/sim/tb_wrapper.v $(wildcard $(ROOT)/rtl_v1/*.v)
	COMPILE_ARGS += -DDUT_COPPERV1
endif

TOPLEVEL = tb_wrapper
MODULE = test_copperv2
COMPILE_ARGS += -I$(ROOT)/rtl_v1/include

include $(shell cocotb-config --makefiles)/Makefile.sim

