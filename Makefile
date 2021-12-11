
.PHONY: all
all: work/sim/result.xml

.PHONY: clean
clean:
	rm -rf work/rtl work/sim work/logs

.PHONY: work/rtl/copperv2_rtl.v
work/rtl/copperv2_rtl.v:
	./scripts/mill copperv2.run

work/sim/result.xml: work/rtl/copperv2_rtl.v
	pytest -n $(shell nproc) --junitxml="$@"
