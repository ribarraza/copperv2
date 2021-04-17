#!/bin/bash

mkdir -p ~/.ivy2
mkdir -p ~/.sbt
mkdir -p ~/.cache

#shell="--entrypoint bash"

podman run --rm -it $shell -v $PWD:/work:Z -v ~/.ivy2:/root/.ivy2:Z -v ~/.sbt:/root/.sbt:Z -v ~/.cache:/root/.cache:Z diegob94/open_eda:chisel "$@"
