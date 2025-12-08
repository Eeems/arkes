# syntax=docker/dockerfile:1.4
# x-name=KDE Plasma
# x-depends=base
ARG HASH

FROM arkes:base

RUN /usr/lib/system/package_layer \
  plasma \
  sddm \
  discover \
  xorg-xwayland

RUN systemctl enable sddm

COPY overlay/kde /
