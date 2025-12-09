# syntax=docker/dockerfile:1.4
# x-name=GNOME
# x-depends=base
ARG HASH

FROM arkes:base

RUN /usr/lib/system/package_layer \
  gdm \
  gnome-shell \
  ghostty \
  xorg-server \
  gnome-software \
  flatpak-xdg-utils \
  gnome-packagekit \
  fwupd \
  gnome-tweaks \
  gnome-control-center

RUN systemctl enable gdm

COPY overlay/gnome /
