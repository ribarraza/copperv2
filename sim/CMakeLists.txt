cmake_minimum_required(VERSION 3.16)

project(sim)

find_package(verilator HINTS $ENV{VERILATOR_ROOT})

add_executable(Vour sim_main.cpp)
verilate(Vour SOURCES our.v)
target_include_directories(Vour PUBLIC "${PROJECT_BINARY_DIR}")
#${PROJECT_BINARY_DIR}/../chisel/GCD.v
