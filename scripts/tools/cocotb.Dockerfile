FROM ubuntu:focal-20210217

ARG DEBIAN_FRONTEND=noninteractive 

ENV PATH="/eda/iverilog/bin:${PATH}"
COPY --from=diegob94/open_eda:iverilog /eda/iverilog /eda/iverilog

RUN apt-get update \
    && apt-get install --no-install-recommends -y python3 python3-pip python3-dev \
    && apt-get install --no-install-recommends -y cmake make gcc g++ gdb perl ccache \
    && pip3 install --no-cache-dir cocotb cocotb-coverage pytest \
    && echo "alias pip=pip3" >> "${HOME}/.bashrc" \
    && echo "alias python=python3" >> "${HOME}/.bashrc" \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /container

