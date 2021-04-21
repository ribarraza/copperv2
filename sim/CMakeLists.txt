cmake_minimum_required(VERSION 3.16)

project(sim)

find_package(verilator HINTS $ENV{VERILATOR_ROOT})

add_executable(Vsim sim_main.cpp)
verilate(Vsim 
    SOURCES 
        top.sv 
        copperv2_bfm.sv
        ${PROJECT_BINARY_DIR}/../chisel/Copperv2.v
)
#target_include_directories(Vsim PUBLIC "${PROJECT_BINARY_DIR}")
