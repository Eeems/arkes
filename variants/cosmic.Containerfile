# syntax=docker/dockerfile:1.4
# x-name=COSMIC
# x-depends=base
ARG HASH

FROM arkes:base

RUN /usr/lib/system/package_layer \
  cosmic \
  cosmic-greeter \
  greetd

RUN systemctl enable greetd.service

COPY overlay/cosmic /
