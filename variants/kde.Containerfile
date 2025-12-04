# syntax=docker/dockerfile:1.4
# x-depends=base
ARG HASH

FROM arkes:base

ARG \
  VARIANT="KDE Plasma" \
  VARIANT_ID="kde"

RUN /usr/lib/system/package_layer \
  plasma \
  sddm \
  discover \
  xorg-xwayland

RUN systemctl enable sddm

COPY overlay/kde /

ARG VERSION_ID HASH TAR_DETERMINISTIC TAR_SORT

LABEL \
  os-release.VARIANT="${VARIANT}" \
  os-release.VARIANT_ID="${VARIANT_ID}" \
  os-release.VERSION_ID="${VERSION_ID}" \
  org.opencontainers.image.ref.name="${VARIANT_ID}" \
  hash="${HASH}"

RUN /usr/lib/system/set_variant