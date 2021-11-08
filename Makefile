
.PHONY: all clean
all: work/test
clean:
	rm -rf work/rtl work/sim work/logs
	rm -f work/setup work/chisel work/test

work/setup:
	mkdir -p work
	date > $@

work/chisel: work/setup
	sbt "runMain Copperv2Driver"
	date > $@

work/test: work/chisel
	pytest
	date > $@

