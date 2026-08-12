# syntax=docker/dockerfile:1.4
ARG HASH
ARG BASE_VARIANT_ID

FROM arkes:${BASE_VARIANT_ID}

RUN /usr/lib/system/package_layer \
  fprintd \
  framework-system

COPY overlay/framework /
