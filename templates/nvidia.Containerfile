# syntax=docker/dockerfile:1.4
ARG BASE_VARIANT_ID

FROM arkes:${BASE_VARIANT_ID}

RUN /usr/lib/system/package_layer \
  nvidia-open-dkms \
  nvidia-container-toolkit \
  nvidia-utils \
  nvidia-settings
