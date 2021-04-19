#!/bin/bash

podman build -t diegob94/open_eda:verilator -f ./scripts/tools/verilator.Dockerfile .
podman build -t diegob94/open_eda:chisel -f ./scripts/tools/chisel.Dockerfile .
