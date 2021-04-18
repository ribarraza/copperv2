#!/bin/bash

#./chisel.sh "runMain gcd.GCDDriver"

./scripts/verilator.sh cmake -f ./sim/CMakeLists.txt -B work
./scripts/verilator.sh cmake --build work

cd work
./Vour

