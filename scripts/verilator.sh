#!/bin/bash

podman run --rm -v $PWD:/work:Z diegob94/open_eda:verilator "$@"
