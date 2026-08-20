# syntax=docker/dockerfile:1.4
# x-name=KDE Plasma
# x-depends=graphical
ARG HASH

FROM arkes:graphical

RUN /usr/lib/system/package_layer \
  plasma \
  sddm \
  discover \
  xorg-xwayland

RUN systemctl enable sddm

COPY overlay/kde /
