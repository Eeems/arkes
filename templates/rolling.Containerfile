# syntax=docker/dockerfile:1.4
ARG BASE_VARIANT_ID

FROM arkes:${BASE_VARIANT_ID} AS build

RUN mkdir -p /var/roothome/.cache \
  && /usr/lib/system/initialize_pacman \
  && /usr/lib/system/install_packages reflector \
  && reflector --latest 5 --sort rate --save /etc/pacman.d/mirrorlist \
  && /usr/lib/system/remove_packages reflector \
  && /usr/lib/system/remove_unused_packages \
  && echo "[system] Updating packages" \
  && chronic pacman -Syu --needed --noconfirm \
  && /usr/lib/system/remove_pacman_files \
  && rm -r /var/roothome/.cache

FROM scratch

COPY --from=build / /
