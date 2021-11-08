
.PHONY: all
all: work/test

work/setup:
	mkdir -p work
	date > $@

work/chisel: work/setup
	sbt "runMain Copperv2Driver"
	date > $@

work/test: work/chisel
	pytest
	date > $@

