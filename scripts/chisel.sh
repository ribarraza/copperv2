#!/bin/bash

mkdir -p ~/.ivy2
mkdir -p ~/.sbt
mkdir -p ~/.cache

#shell="--entrypoint bash"
CHOME=/home/chisel

podman run --rm $shell -it -p 8888:8888 -v $PWD:$CHOME/work:Z -v ~/.ivy2:$CHOME/.ivy2:Z -v ~/.sbt:$CHOME/.sbt:Z -v ~/.cache:$CHOME/.cache:Z diegob94/open_eda:chisel "$@"
