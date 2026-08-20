# syntax=docker/dockerfile:1.4
ARG BASE_VARIANT_ID

FROM arkes:${BASE_VARIANT_ID}

RUN /usr/lib/system/package_layer \
  lib32-nvidia-utils \
  nvidia-open-dkms \
  nvidia-container-toolkit \
  nvidia-utils \
  nvidia-settings
