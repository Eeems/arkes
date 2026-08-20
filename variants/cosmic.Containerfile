# syntax=docker/dockerfile:1.4
# x-name=COSMIC
# x-depends=graphical
ARG HASH

FROM arkes:graphical

RUN /usr/lib/system/package_layer \
  cosmic \
  cosmic-greeter \
  greetd

RUN systemctl enable greetd.service

COPY overlay/cosmic /
