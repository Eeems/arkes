# syntax=docker/dockerfile:1.4
# x-name=Graphical
# x-depends=base
ARG HASH

FROM arkes:base

RUN /usr/lib/system/package_layer \
  lib32-vulkan-icd-loader \
  lib32-vulkan-swrast \
  vulkan-icd-loader \
  vulkan-swrast

COPY overlay/graphical /
