# syntax=docker/dockerfile:1.4
ARG BASE_VARIANT_ID

FROM arkes:${BASE_VARIANT_ID}

RUN /usr/lib/system/package_layer \
  --rm \
  $(pacman -Qq vulkan-nouveau >/dev/null 2>&1 \
  && echo vulkan-nouveau) \
  $(pacman -Qq lib32-vulkan-nouveau >/dev/null 2>&1 \
  && echo lib32-vulkan-nouveau) \
  --add \
  lib32-nvidia-utils \
  nvidia-open-dkms \
  nvidia-container-toolkit \
  nvidia-utils \
  nvidia-settings
