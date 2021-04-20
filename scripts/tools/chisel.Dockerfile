FROM ubuntu:focal-20210217

ARG DEBIAN_FRONTEND=noninteractive 

RUN apt-get update \
    && apt-get install --no-install-recommends -y default-jdk gnupg2 \
    && echo "deb https://dl.bintray.com/sbt/debian /" | tee -a /etc/apt/sources.list.d/sbt.list \
    && apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 642AC823 \
    && apt-get update \
    && apt-get install --no-install-recommends -y sbt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
