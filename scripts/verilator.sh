#!/bin/bash

podman run --rm -it -v $PWD:/work:Z diegob94/open_eda:verilator "$@"
