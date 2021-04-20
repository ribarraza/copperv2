FROM ubuntu:focal-20210217

ARG DEBIAN_FRONTEND=noninteractive 
WORKDIR /src

RUN apt-get update \
    && apt-get install --no-install-recommends -y default-jdk gnupg2 \
    && echo "deb https://dl.bintray.com/sbt/debian /" | tee -a /etc/apt/sources.list.d/sbt.list \
    && apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 642AC823 \
    && apt-get update \
    && apt-get install --no-install-recommends -y sbt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get install --no-install-recommends -y python3-pip curl \
    && pip3 install jupyterlab \
    && curl -Lo coursier https://git.io/coursier-cli \
    && chmod +x coursier \
    && ./coursier launch --fork almond -- --install \
    && rm -f coursier \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/chisel/work

