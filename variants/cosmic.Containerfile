# syntax=docker/dockerfile:1.4
# x-depends=base
ARG HASH

FROM arkes:base

ARG \
  VARIANT="COSMIC" \
  VARIANT_ID="cosmic"

RUN /usr/lib/system/package_layer \
  cosmic \
  cosmic-greeter \
  greetd

RUN systemctl enable greetd.service

COPY overlay/cosmic /

ARG VERSION_ID HASH TAR_DETERMINISTIC TAR_SORT

LABEL \
  os-release.VARIANT="${VARIANT}" \
  os-release.VARIANT_ID="${VARIANT_ID}" \
  os-release.VERSION_ID="${VERSION_ID}" \
  org.opencontainers.image.ref.name="${VARIANT_ID}" \
  hash="${HASH}"

RUN /usr/lib/system/set_variant