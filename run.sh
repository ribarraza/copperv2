#!/bin/bash

set -e

steps=(chisel sim_build sim_run)
source ./scripts/steps.sh

root=.
work_dir=${root}/work
mkdir -p $work_dir
chisel_work_dir=${work_dir}/chisel
sim_work_dir=${work_dir}/sim

step chisel << EOF
    ./scripts/chisel.sh "runMain gcd.GCDDriver --target-dir $chisel_work_dir"
EOF

step sim_build << EOF
    ./scripts/verilator.sh cmake -f ./scripts/CMakeLists.txt -B $sim_work_dir
    ./scripts/verilator.sh cmake --build $sim_work_dir
EOF

step sim_run << EOF
    pushd $sim_work_dir
    ./Vour
    popd
EOF


